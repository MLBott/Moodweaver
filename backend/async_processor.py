# async_processor.py
import json
import os
import logging
from .llm_handlers import openai, anthropic, gemini # Import handlers
from .task_controller import TaskController
from . import sentiment_analyzer # <-- Import new module
from . import world_state_manager as wsm
from .orrery import PersonalityOrrery # <-- Import Orrery


logger = logging.getLogger(__name__)

EFFECTS_QUEUE_FILE = os.path.join('data', 'effects_queue.json')
TASK_STATE_FILE = os.path.join('data', 'task_state.json')

def _load_queue():
    logger.debug(f"Loading effects queue from: {EFFECTS_QUEUE_FILE}")
    if not os.path.exists(EFFECTS_QUEUE_FILE):
        logger.debug("Effects queue file does not exist, returning empty queue")
        return {}
    try:
        with open(EFFECTS_QUEUE_FILE, 'r') as f:
            queue = json.load(f)
            logger.debug(f"Successfully loaded queue with {len(queue)} chat entries")
            for chat_id, effects in queue.items():
                logger.debug(f"  Chat {chat_id}: {len(effects)} pending effects")
            return queue
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.error(f"Failed to load effects queue: {e}")
        return {}

def _save_queue(queue):
    logger.debug(f"Saving effects queue to: {EFFECTS_QUEUE_FILE}")
    try:
        with open(EFFECTS_QUEUE_FILE, 'w') as f:
            json.dump(queue, f, indent=2)
        logger.debug(f"Successfully saved queue with {len(queue)} chat entries")
    except Exception as e:
        logger.error(f"Failed to save effects queue: {e}")

def add_effect_to_queue(chat_id: str, effect_type: str, payload: dict):
    """Adds a new effect to the queue for a specific chat."""
    logger.debug(f"Adding effect to queue - Chat: {chat_id}, Type: {effect_type}")
    queue = _load_queue()
    if chat_id not in queue:
        logger.debug(f"Creating new queue entry for chat {chat_id}")
        queue[chat_id] = []
    queue[chat_id].append({"type": effect_type, "payload": payload})
    logger.debug(f"Effect added. Chat {chat_id} now has {len(queue[chat_id])} pending effects")
    _save_queue(queue)

def process_effects_for_chat(chat: dict, settings: dict) -> dict:
    """
    Processes all pending effects for a chat, updates the chat object,
    and clears the queue for that chat. Returns the modified chat object.
    """
    logger.debug(f"Starting effect processing for chat {chat['id']}")
    queue = _load_queue()
    chat_id = chat['id']
    effects = queue.pop(chat_id, [])
    if not effects:
        logger.debug(f"No pending effects found for chat {chat_id}")
        return chat

    logger.info(f"Processing {len(effects)} effects for chat {chat_id}")
    for i, effect in enumerate(effects):
        logger.debug(f"  Effect {i+1}: {effect.get('type', 'unknown')}")

    # Instantiate the Orrery with the chat's current state
    logger.debug(f"Initializing PersonalityOrrery for chat {chat_id}")
    try:
        orrery_instance = PersonalityOrrery(
            trait_config=chat['trait_config'],
            personality_state=chat['personality_state'],
            recent_user_sentiments=chat.get('recent_user_sentiments', []),
            repetitive_sentiment_penalty_active=chat.get('repetitive_sentiment_penalty_active', False)
        )
        logger.debug(f"PersonalityOrrery initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PersonalityOrrery for chat {chat_id}: {e}")
        _save_queue(queue)  # Restore queue since we failed
        return chat

    processed_effects = 0
    for i, effect in enumerate(effects):
        effect_type = effect.get('type', 'unknown')
        logger.debug(f"Processing effect {i+1}/{len(effects)}: {effect_type}")
        
        try:
            payload = effect.get('payload', {})
            message = payload.get('message')

            if not message and effect_type in ['user_sentiment', 'assistant_sentiment']:
                logger.warning(f"Skipping {effect_type} effect - no message in payload")
                continue

            if effect_type == 'user_sentiment':
                logger.debug(f"Processing user sentiment analysis for message: {message[:50]}...")
                sentiment, intensity = sentiment_analyzer.analyze_sentiment(message, 'user', settings)
                logger.info(f"User Sentiment Analysis - Sentiment: {sentiment.upper()}, Intensity: {intensity}")
                
                old_state = orrery_instance.get_trait_summary().copy()
                orrery_instance.update_from_sentiment(sentiment, intensity, from_user=True)
                new_state = orrery_instance.get_trait_summary()
                logger.debug(f"Orrery state change - Old: {old_state}, New: {new_state}")

            elif effect_type == 'assistant_sentiment':
                logger.debug(f"Processing assistant sentiment analysis for message: {message[:50]}...")
                sentiment, intensity = sentiment_analyzer.analyze_sentiment(message, 'assistant', settings)
                reduced_intensity = intensity * 0.25
                logger.info(f"Assistant Sentiment Analysis - Sentiment: {sentiment.upper()}, Intensity: {intensity} (reduced to {reduced_intensity})")
                
                old_state = orrery_instance.get_trait_summary().copy()
                orrery_instance.update_from_sentiment(sentiment, reduced_intensity, from_user=False)
                new_state = orrery_instance.get_trait_summary()
                logger.debug(f"Orrery state change - Old: {old_state}, New: {new_state}")

            elif effect_type == 'task_update':
                logger.info(f"Processing task_update effect for chat {chat_id}")
                try:
                    # 1. Load the most current task state from the file
                    all_task_states = {}
                    if os.path.exists(TASK_STATE_FILE):
                        logger.debug(f"Loading task states from: {TASK_STATE_FILE}")
                        with open(TASK_STATE_FILE, 'r') as f:
                            all_task_states = json.load(f)
                        logger.debug(f"Loaded task states for {len(all_task_states)} chats")
                    else:
                        logger.debug(f"Task state file does not exist: {TASK_STATE_FILE}")

                    current_task_state = all_task_states.get(chat_id, {})
                    logger.debug(f"Current task state for chat {chat_id}: {current_task_state}")
                    
                    # 2. Instantiate the controller and run the decision process
                    logger.debug(f"Initializing TaskController for chat {chat_id}")
                    task_controller = TaskController(chat_id, current_task_state)
                    
                    messages = payload.get('messages', [])
                    logger.debug(f"Running task controller decision with {len(messages)} messages")
                    task_controller.decide_next_step(messages, settings)
                    logger.info(f"Task controller decision completed for chat {chat_id}")
                except Exception as e:
                    logger.error(f"Failed to process task_update for chat {chat_id}: {e}")
                    raise

            elif effect_type == 'environmental_rewrite':
                logger.info(f"Processing environmental_rewrite effect for chat {chat_id}")
                try:
                    payload_coords = payload.get('coords')
                    payload_context = payload.get('context')

                    if not payload_coords or not payload_context:
                        logger.warning(f"Missing required data for environmental_rewrite - coords: {bool(payload_coords)}, context: {bool(payload_context)}")
                        continue

                    logger.debug(f"Environmental rewrite at coords {payload_coords}")
                    
                    # 1. Get full conversation context from this node
                    logger.debug(f"Gathering full conversation context for node {payload_coords}")
                    full_user_messages = []
                    full_assistant_messages = []
                    
                    # Look through recent messages to find all that happened in this node
                    recent_messages = chat.get('messages', [])[-10:]  # Look at last 10 messages
                    
                    # Build context from messages that occurred in this node
                    for msg in recent_messages:
                        if msg.get('role') == 'user' and not msg.get('content', '').startswith('[NARRATOR:'):
                            full_user_messages.append(msg.get('content', ''))
                        elif msg.get('role') == 'assistant':
                            full_assistant_messages.append(msg.get('content', ''))
                    
                    # Combine all messages into context strings
                    combined_user_message = ' '.join(full_user_messages[-3:])  # Last 3 user messages
                    combined_assistant_message = ' '.join(full_assistant_messages[-3:])  # Last 3 assistant messages
                    
                    logger.debug(f"Combined user context: '{combined_user_message[:100]}...'")
                    logger.debug(f"Combined assistant context: '{combined_assistant_message[:100]}...'")
                    
                    # 2. Check if a significant event happened
                    logger.debug(f"Analyzing event significance...")
                    event_summary = wsm.get_event_summary(
                        combined_user_message, 
                        combined_assistant_message, 
                        settings
                    )
                    
                    # 2. If an event was found, trigger the rewrite
                    if event_summary:
                        logger.info(f"Significant event detected: {event_summary[:100]}...")
                        all_nodes = wsm.load_chat_nodes(chat_id)
                        logger.debug(f"Loaded {len(all_nodes)} nodes for chat {chat_id}")
                        
                        node_to_update = wsm.get_node_by_coords(payload_coords[0], payload_coords[1], all_nodes)
                        if node_to_update:
                            original_desc = node_to_update.get('description_base', '')
                            logger.debug(f"Original node description: {original_desc[:100]}...")
                            
                            # Call the rewrite function you already have
                            new_desc = wsm.rewrite_node_description(
                                original_desc, event_summary, payload_coords, all_nodes, settings
                            )
                            node_to_update['description_base'] = new_desc
                            wsm.save_chat_nodes(chat_id, all_nodes)
                            logger.info(f"Successfully rewrote node {payload_coords} - New description: {new_desc[:100]}...")
                        else:
                            logger.warning(f"Could not find node at coords {payload_coords}")
                    else:
                        logger.debug(f"No significant event detected, skipping environmental rewrite")
                except Exception as e:
                    logger.error(f"Failed to process environmental_rewrite for chat {chat_id}: {e}")
                    raise
            else:
                logger.warning(f"Unknown effect type: {effect_type}")

            processed_effects += 1
            logger.debug(f"Successfully processed effect {i+1}: {effect_type}")

        except Exception as e:
            logger.error(f"Failed to process effect {i+1} ({effect_type}) for chat {chat_id}: {e}")
            # Continue processing other effects instead of failing completely

    logger.info(f"Processed {processed_effects}/{len(effects)} effects successfully for chat {chat_id}")

    # After all effects are processed, update the chat object with the final state
    try:
        final_personality_state = orrery_instance.get_trait_summary()
        final_user_sentiments = orrery_instance.recent_user_sentiments
        final_penalty_active = orrery_instance.repetitive_sentiment_penalty_active
        
        logger.debug(f"Updating chat object with final states:")
        logger.debug(f"  Personality state: {final_personality_state}")
        logger.debug(f"  Recent user sentiments: {len(final_user_sentiments)} entries")
        logger.debug(f"  Repetitive sentiment penalty active: {final_penalty_active}")
        
        chat['personality_state'] = final_personality_state
        chat['recent_user_sentiments'] = final_user_sentiments
        chat['repetitive_sentiment_penalty_active'] = final_penalty_active
    except Exception as e:
        logger.error(f"Failed to update chat object with final orrery state: {e}")

    _save_queue(queue)
    logger.info(f"Finished processing effects for chat {chat_id}. Queue cleared for this chat.")
    return chat
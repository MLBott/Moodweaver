from email.mime import message
from flask import Flask, request, jsonify, send_from_directory, render_template, session
from flask_cors import CORS
import json
import os
import time
import logging
import re
import random
import threading
from .llm_handlers import anthropic, gemini, ollama, openai, perplexity
from .orrery import PersonalityOrrery
from .task_controller import TaskController
from . import prompt_builder
from . import world_state_manager as wsm
from . import command_handler
from . import async_processor
from . import display_formatter as df
from . import summarizer

logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("gemini_webapi").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, supports_credentials=True)  # Enable Cross-Origin Resource Sharing
app.secret_key = b'floppyjello2321ztlp'

app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

# --- Constants and Data Initialization ---
DATA_DIR = 'data'
CHATS_FILE = os.path.join(DATA_DIR, 'chats.json')
CHARACTERS_FILE = os.path.join(DATA_DIR, 'characters.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')
PLOTS_FILE = os.path.join(DATA_DIR, 'plots.json')
DEFAULT_TRAIT_CONFIG_FILE = os.path.join(DATA_DIR, 'trait_config.json')
TASK_STATE_FILE = os.path.join(DATA_DIR, 'task_state.json')
TASK_FRAMEWORK_FILE = os.path.join(DATA_DIR, 'task_framework.json')


os.makedirs(DATA_DIR, exist_ok=True)

def init_json_file(filename, default_data):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_data, f, indent=2)

init_json_file(CHATS_FILE, {"chats": []})
init_json_file(CHARACTERS_FILE, {"characters": []})
init_json_file(TASK_STATE_FILE, {})
init_json_file(TASK_FRAMEWORK_FILE, {})
init_json_file(SETTINGS_FILE, {
    "llm_provider": "ollama", "api_keys": {"anthropic": "", "openai": ""},
    "ollama_url": "http://localhost:11434", "default_model": "llama3", "temperature": 0.7
})
# Ensure a default trait config exists
if not os.path.exists(DEFAULT_TRAIT_CONFIG_FILE):
    # A minimal default config
    init_json_file(DEFAULT_TRAIT_CONFIG_FILE, {"skeptical": {"baseline": 0.5, "range": [0,1], "elasticity": 0.1, "decay": 0.05}})


# --- Helper Functions ---
def load_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Return the default structure for an empty file to avoid errors
            if not content:
                if 'chats' in filename: return {"chats": []}
                if 'characters' in filename: return {"characters": []}
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        if 'chats' in filename: return {"chats": []}
        if 'characters' in filename: return {"characters": []}
        return {}


def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def parse_and_log_moves(text_to_parse, current_path, chat_nodes):
    """
    Parses text for @MOVE commands, updates a path list, and returns the cleaned text.
    Args:
        text_to_parse (str): The text from the user or LLM.
        current_path (list): The list of coordinates visited so far in this turn.
        chat_nodes (list): The map node data.
    Returns:
        tuple: (updated_path, cleaned_text)
    """
    cleaned_text = text_to_parse
    # Find all move commands, not just the first one
    move_matches = re.finditer(r'@MOVE:\s*(northeast|northwest|southeast|southwest|north|south|east|west)', text_to_parse, re.IGNORECASE)
    
    last_known_position = current_path[-1] # The latest position in the path
    logger.debug(f"Starting parse_and_log_moves with path: {current_path}")
    
    moves_found = 0
    for match in move_matches:
        moves_found += 1
        logger.debug(f"Found move command #{moves_found}: {match.group(0)}")
        
        # Get the node data for the current last known position
        node_data = wsm.get_node_by_coords(last_known_position[0], last_known_position[1], chat_nodes)
        if not (node_data and "connections" in node_data):
            logger.debug(f"No connections found for position {last_known_position}")
            continue # Can't move from here

        # Map direction string to key (e.g., "NORTH" -> "N")
        move_direction_str = match.group(1).strip().upper()
        dir_map = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
        move_key = dir_map.get(move_direction_str)

        if move_key and move_key in node_data["connections"]:
            # A valid move was found
            new_coords = node_data["connections"][move_key]
            current_path.append(new_coords) # Add the new location to our path
            last_known_position = new_coords # Update our last known position for the next move in this loop
            logger.debug(f"Valid move to {new_coords}. Path is now: {current_path}")
        else:
            logger.debug(f"Invalid move direction '{move_key}' from {last_known_position}")

    # After finding all matches, remove the command strings from the text
    cleaned_text = re.sub(r'@MOVE:\s*(northeast|northwest|southeast|southwest|north|south|east|west)', '', cleaned_text, flags=re.IGNORECASE).strip()
    
    logger.debug(f"Finished parsing moves. Final path: {current_path}")
    return current_path, cleaned_text

# Load default trait config once at startup
DEFAULT_TRAIT_CONFIG = load_json(DEFAULT_TRAIT_CONFIG_FILE)


# In app.py

@app.route('/api/chat', methods=['POST'])
def chat():
    # --- 1. INITIALIZATION AND DATA LOADING ---
    data = request.json
    user_message = data.get('message')
    chat_id = data.get('chat_id')
    character_id = data.get('character_id')
    settings = load_json(SETTINGS_FILE)
    provider = settings.get('llm_provider', 'ollama')
    chats_data = load_json(CHATS_FILE)
    
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)

    if not chat:
        # Create a new chat if one doesn't exist
        character_prompt = "You are roleplaying as a new character."
        if character_id:
            characters_data = load_json(CHARACTERS_FILE)
            selected_character = next((c for c in characters_data.get('characters', []) if c.get('id') == character_id), None)
            if selected_character:
                character_prompt = selected_character.get('description', character_prompt)
        
        chat_id = str(int(time.time()))
        wsm.create_chat_node_file(chat_id)
        initial_state = {trait: config["baseline"] for trait, config in DEFAULT_TRAIT_CONFIG.items()}
        chat = {
            'id': chat_id, 'title': user_message[:30] if user_message else "New Journey", 'created_at': time.time(),
            'messages': [], 'character_id': character_id, 'system_prompt': character_prompt,
            'trait_config': DEFAULT_TRAIT_CONFIG, 'personality_state': initial_state
        }
        chats_data.setdefault('chats', []).append(chat)
        session['player_coords'] = (1, 1)

    # --- 2. PROCESS PREVIOUS TURN'S ASYNC EFFECTS ---
    chat = async_processor.process_effects_for_chat(chat, settings)

    # --- 3. PREPARE DATA FOR THIS TURN ---
    orrery_instance = PersonalityOrrery(
        trait_config=chat['trait_config'],
        personality_state=chat['personality_state'],
        recent_user_sentiments=chat.get('recent_user_sentiments', []),
        repetitive_sentiment_penalty_active=chat.get('repetitive_sentiment_penalty_active', False)
    )
    current_coords = list(session.get('player_coords', [1, 1]))
    chat_nodes = wsm.load_chat_nodes(chat_id)

    # --- 4. HANDLE USER COMMANDS ---
    previous_coords = list(current_coords)
    command_result = command_handler.process_user_command(user_message, current_coords, chat_nodes)
    user_message_for_history = command_result.get('cleaned_message', user_message)

    if command_result.get('look_result'):
        logger.debug(f"@LOOK command processed, returning early. Result: {command_result['look_result']}")
        return jsonify({ 'look_result': df.highlight_text(command_result['look_result']), 'chat_id': chat_id, 'current_coords': current_coords, 'visited_nodes': wsm.get_visited_nodes(chat_nodes) })

    if command_result.get('user_moved'):
        current_coords = command_result['new_coords']
        session['player_coords'] = tuple(current_coords)
        wsm.mark_node_visited(chat_nodes, current_coords[0], current_coords[1])
    
        logger.debug(f"User move detected. Queuing potential rewrite for previous node {previous_coords}")
        event_payload = {
            "coords": previous_coords,
            "context": { "user": user_message_for_history, "assistant": "" } # Assistant hasn't spoken yet
        }
        async_processor.add_effect_to_queue(chat_id, 'environmental_rewrite', event_payload)

    # --- 5. UPDATE HISTORY AND PREPARE PROMPT COMPONENTS ---
    if user_message_for_history:
        chat['messages'].append({'role': 'user', 'content': user_message_for_history, 'user_name': data.get('user_name', 'User'), 'timestamp': time.time()})

    # Prepare Task Prompt
    all_task_states = load_json(TASK_STATE_FILE)
    current_task_state = all_task_states.get(chat_id, {})
    task_controller = TaskController(chat_id, current_task_state)
    task_prompt_string = task_controller.get_task_prompt()

    # Prepare Narrator Prompt
    current_node_data = wsm.get_node_by_coords(current_coords[0], current_coords[1], chat_nodes)
    narrator_context_for_llm = wsm.get_exits_string(current_node_data) if current_node_data else "No exits found."
    if current_node_data:
        narrator_context_for_llm = f"{current_node_data.get('description_base', '')} [Exits: {narrator_context_for_llm}]"


    # --- 6. BUILD PROMPT AND CALL LLM ---
    enhanced_system_prompt = prompt_builder.build_system_prompt(
        base_prompt=chat.get('system_prompt', ''),
        personality_context=orrery_instance.get_personality_prompt(),
        task_prompt=task_prompt_string,
        narrator_message=narrator_context_for_llm,
        user_name=data.get('user_name', 'User')
    )
    
    conversation = chat['messages']
    response_text = ""
    try:
        if provider == 'gemini':
            response_text = gemini.generate_response(enhanced_system_prompt, conversation, settings)
            logger.debug(f"Final System Prompt Sent to LLM:\n{'-'*50}\n{enhanced_system_prompt}\n{'='*50}\n")
        elif provider == 'anthropic':
            response_text = anthropic.generate_response(enhanced_system_prompt, conversation, settings)
            logger.debug(f"Final System Prompt Sent to Anthropic:\n{'-'*50}\n{enhanced_system_prompt}\n{'='*50}\n")
        elif provider == 'ollama':
            # Add your ollama handler here
            response_text = ollama.generate_response(enhanced_system_prompt, conversation, settings)
        elif provider == 'openai':
            # Add your openai handler here
            response_text = openai.generate_response(enhanced_system_prompt, conversation, settings)
        else:
            response_text = f"Error: Unknown provider '{provider}'"
            logger.error(f"Unknown LLM provider: {provider}")
    except Exception as e:
        response_text = f"Error: {str(e)}"
        logger.error(f"LLM API call failed: {str(e)}", exc_info=True)
    

    # --- 7. PROCESS LLM RESPONSE AND QUEUE ASYNC EFFECTS FOR NEXT TURN ---
    llm_moved = False  # Track if LLM moved for auto-continue logic
    llm_used_look = False  # Track if LLM used @LOOK for auto-continue logic
    if response_text:
        async_processor.add_effect_to_queue(chat_id, 'user_sentiment', {'message': user_message_for_history})
        async_processor.add_effect_to_queue(chat_id, 'assistant_sentiment', {'message': re.sub('<[^<]+?>', '', response_text)})
        
        previous_coords = list(current_coords)
        response_text, llm_new_coords, llm_used_look = command_handler.process_llm_response_command(response_text, current_coords, chat_nodes)
        if llm_new_coords != current_coords:
            llm_moved = True  # LLM used @MOVE command
            current_coords = llm_new_coords
            logger.debug(f"BEFORE session update: {session.get('player_coords')}")
            session['player_coords'] = tuple(current_coords)
            session.modified = True  # Mark session as modified to ensure it saves
            logger.debug(f"AFTER session update: {session.get('player_coords')}")
            wsm.mark_node_visited(chat_nodes, current_coords[0], current_coords[1])
            logger.debug(f"LLM move detected. Queuing potential rewrite for previous node {previous_coords}")
            event_payload = {
                "coords": previous_coords,
                "context": { "user": user_message_for_history, "assistant": response_text }
            }
            async_processor.add_effect_to_queue(chat_id, 'environmental_rewrite', event_payload)

        # Handle LLM @LOOK command
        if llm_used_look:
            logger.debug("Processing LLM @LOOK command")
            # Get the surrounding context using the existing function
            look_result = wsm.get_immediate_surrounding_context(current_coords, chat_nodes)
            
            # Add the look result as a narrator message
            look_message = f"[OOC: You look around at the possible directions.] {look_result}"
            chat['messages'].append({
                'role': 'narrator', 
                'content': look_message, 
                'timestamp': time.time(),
                'auto_continue': True  # Mark for auto-continue
            })
            logger.debug(f"Added LLM @LOOK result: {look_message}")

        # Handle automatic task progression and queueing
        if not current_task_state.get('task') or current_task_state.get('progress', 0) >= 1.0:
            async_processor.add_effect_to_queue(chat_id, 'task_update', {'messages': chat['messages'][-5:]})
            logger.debug("No active task. Creating first task immediately.")
            # Create task immediately (synchronous)
            task_controller = TaskController(chat_id, current_task_state)
            task_controller.decide_next_step(chat['messages'][-5:], settings)
            
            # Reload the updated task state
            all_task_states = load_json(TASK_STATE_FILE)
            current_task_state = all_task_states.get(chat_id, {})
    
            logger.debug(f"[TASK_LOGIC] NEW Task Created: {current_task_state.get('task')}")

        else:
            difficulty = current_task_state.get('priority', 'easy').lower()
            increment_map = {'easy': 1/3, 'medium': 1/5, 'hard': 1/8}
            increment = increment_map.get(difficulty, 1/3)
            current_task_state['progress'] = min(1.0, current_task_state.get('progress', 0.0) + increment)
            all_task_states[chat_id] = current_task_state
            save_json(TASK_STATE_FILE, all_task_states)
            logger.debug(f"[TASK_LOGIC] Current Task: {current_task_state.get('task')}")
            logger.debug(f"[TASK_LOGIC] Current Progress: {current_task_state.get('progress', 0)}")

    # --- 8. FINALIZE AND SAVE STATE ---
	
    logger.debug(f"RAW TEXT (pre-spaCy): '{response_text}'")
    chat['messages'].append({'role': 'assistant', 'content': df.highlight_text(response_text), 'timestamp': time.time()})
    chat['personality_state'] = orrery_instance.get_trait_summary()
    save_json(CHATS_FILE, chats_data)
    wsm.save_chat_nodes(chat_id, chat_nodes) # Make sure this function exists in wsm
    
    final_node_data = wsm.get_node_by_coords(current_coords[0], current_coords[1], chat_nodes)
    final_narrator_message = f"{final_node_data.get('description_base', '')} [Exits: {wsm.get_exits_string(final_node_data)}]" if final_node_data else ""
    
    # Add narrator message to chat history so LLM can respond to room context
    if final_narrator_message and final_narrator_message.strip():
        chat['messages'].append({
            'role': 'user', 
            'content': f"[NARRATOR: {final_narrator_message}]", 
            'timestamp': time.time()
        })
        save_json(CHATS_FILE, chats_data)  # Save again with narrator message
    
    # Debug logging for auto-continue troubleshooting
    logger.debug(f"RETURNING TO FRONTEND: llm_moved={llm_moved}, llm_used_look={llm_used_look}")
    logger.debug(f"FINAL COORDS: current_coords={current_coords}, session={session.get('player_coords')}")
    logger.debug(f"NARRATOR MESSAGE: '{final_narrator_message}' (length: {len(final_narrator_message) if final_narrator_message else 0})")
    
    return jsonify({
        'chat_id': chat_id,
        'response': df.highlight_text(response_text),
        'current_coords': current_coords,
        'visited_nodes': wsm.get_visited_nodes(chat_nodes),
        'narrator_message': df.highlight_text(final_narrator_message),
        'narrator_coords': current_coords,  # Add coordinates for map flashing
        'llm_moved': llm_moved,  # Add flag to indicate if LLM moved
        'llm_used_look': llm_used_look  # Add flag to trigger auto-continue for @LOOK
    })


# --- New API Route for Editing Messages ---
@app.route('/api/chat/<chat_id>/edit-message', methods=['PUT'])
def edit_message(chat_id):
    data = request.json
    message_index = data.get('message_index')
    new_content = data.get('new_content')
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)
    if chat and 0 <= message_index < len(chat['messages']):
        chat['messages'][message_index]['content'] = new_content
        save_json(CHATS_FILE, chats_data)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Invalid chat or message index'}), 400


@app.route('/api/chat/<chat_id>/summarize', methods=['POST'])
def summarize_chat(chat_id):
    """
    Summarizes earlier messages in a chat conversation.
    Replaces older messages with a concise summary to manage context length.
    """
    try:
        chats_data = load_json(CHATS_FILE)
        chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)
        
        if not chat:
            return jsonify({"error": "Chat not found"}), 404
        
        # Check if there are enough messages to summarize (more than 6)
        if len(chat['messages']) <= 6:
            return jsonify({"error": "Not enough messages to summarize. Need more than 6 messages."}), 400
        
        settings = load_json(SETTINGS_FILE)
        
        # Generate the summary using the existing summarizer
        summary = summarizer.summarize_conversation(chat['messages'], settings)
        
        # Create the summary message
        summary_message = {
            'role': 'assistant',
            'content': f"OOC: {summary}",
            'timestamp': time.time(),
            'is_summary': True
        }
        
        # Replace older messages with the summary
        # Keep the last 6 messages and add the summary at the beginning
        recent_messages = chat['messages'][-6:]
        chat['messages'] = [summary_message] + recent_messages
        
        # Save the updated chat
        save_json(CHATS_FILE, chats_data)
        
        logger.info(f"Successfully summarized chat {chat_id}. Reduced from {len(chat['messages']) + len(recent_messages) - 1} to {len(chat['messages'])} messages.")
        
        return jsonify({
            "success": True,
            "summary": summary,
            "message": f"Successfully summarized earlier messages. Chat reduced to {len(chat['messages'])} messages."
        })
        
    except ValueError as e:
        logger.error(f"Summarization error for chat {chat_id}: {str(e)}")
        return jsonify({"error": str(e)}), 400
        
    except Exception as e:
        logger.error(f"Unexpected error during summarization for chat {chat_id}: {str(e)}", exc_info=True)
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500


# --- Other API Routes (Unchanged) ---

@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend', 'index.html')

def index():
    """
    Initializes the user's session with starting coordinates
    and serves the main HTML page of the frontend.
    """
    # Set the starting coordinates when the user first loads the app
    session['player_coords'] = (1, 1) # Store as tuple
    logger.debug(f"Initialized session with player_coords: {session['player_coords']}")
    return send_from_directory('../frontend', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)

@app.route('/api/settings', methods=['GET', 'PUT'])
def handle_settings():
    if request.method == 'GET':
        return jsonify(load_json(SETTINGS_FILE))
    else:
        save_json(SETTINGS_FILE, request.json)
        return jsonify({"status": "success"})
def save_settings():
    settings = request.json
    # ...existing code...
    # Save support_llm settings if present
    if 'support_llm' in settings:
        data = load_json(SETTINGS_FILE)
        data['support_llm'] = settings['support_llm']
        save_json(SETTINGS_FILE, data)
    else:
        save_json(SETTINGS_FILE, settings)
    return jsonify({"status": "success"})

@app.route('/api/chats', methods=['GET', 'DELETE'])
def handle_chats():
    chats_data = load_json(CHATS_FILE)
    if request.method == 'GET':
        # Return chats sorted by creation time, newest first
        sorted_chats = sorted(chats_data.get('chats', []), key=lambda c: c.get('created_at', 0), reverse=True)
        return jsonify({"chats": sorted_chats})
    else:  # DELETE
        chat_id = request.args.get('id')
        if not chat_id:
            return jsonify({"error": "No chat ID provided"}), 400
        
        chats_data['chats'] = [c for c in chats_data.get('chats', []) if c.get('id') != chat_id]
        save_json(CHATS_FILE, chats_data)
        nodes_path = os.path.join('data', f'nodes_{chat_id}.json')
        if os.path.exists(nodes_path):
            os.remove(nodes_path)
        return jsonify({"status": "success"})

@app.route('/api/characters', methods=['GET', 'POST', 'PUT', 'DELETE'])
def handle_characters():
    characters_data = load_json(CHARACTERS_FILE)
    if request.method == 'GET':
        return jsonify(characters_data)
    
    elif request.method == 'POST':
        character = request.json
        character['id'] = str(int(time.time()))
        characters_data.setdefault('characters', []).append(character)
        save_json(CHARACTERS_FILE, characters_data)
        return jsonify({"id": character['id']})
    
    elif request.method == 'PUT':
        updated_char = request.json
        char_list = characters_data.get('characters', [])
        for i, c in enumerate(char_list):
            if c.get('id') == updated_char.get('id'):
                char_list[i] = updated_char
                break
        save_json(CHARACTERS_FILE, characters_data)
        return jsonify({"status": "success"})
    
    else:  # DELETE
        char_id = request.args.get('id')
        characters_data['characters'] = [c for c in characters_data.get('characters', []) if c.get('id') != char_id]
        save_json(CHARACTERS_FILE, characters_data)
        return jsonify({"status": "success"})

@app.route('/api/plots', methods=['GET'])
def get_plots():
    return jsonify(load_json(PLOTS_FILE))

@app.route('/api/chat/<chat_id>/system-prompt', methods=['PUT'])
def update_chat_system_prompt(chat_id):
    data = request.json
    system_prompt = data.get('system_prompt', '').strip()
    
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    chat['system_prompt'] = system_prompt
    save_json(CHATS_FILE, chats_data)
    return jsonify({"message": "System prompt updated successfully"})


@app.route('/api/chat/<chat_id>/mood-color', methods=['GET'])
def get_mood_color(chat_id):
    """
    Returns the calculated RGBA mood color for a given chat.
    """
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
        
    if 'trait_config' not in chat or 'personality_state' not in chat:
        return jsonify({"error": "Chat is missing personality data"}), 400

    # Initialize the orrery with the specific chat's data
    orrery_instance = PersonalityOrrery(
        trait_config=chat['trait_config'], 
        personality_state=chat['personality_state']
    )
    
    # Get the calculated color
    r, g, b, a = orrery_instance.get_mood_color_mix()

    return jsonify({"r": r, "g": g, "b": b, "a": a})

@app.route('/api/chat/<chat_id>/body-language-state', methods=['GET'])
def get_body_language_state(chat_id):
    """
    Determines if the character's body language is currently readable.
    """
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)

    if not chat:
        return jsonify({"is_readable": True, "character_name": "character"}), 404

    count = chat.get('assistant_message_count', 0)
    
    # The logic for readability
    is_readable = count < 3 or (count > 0 and (count - 2) % 6 == 0)

    # Get character name
    character_name = "the character"
    if chat.get('character_id'):
        characters_data = load_json(CHARACTERS_FILE)
        character = next((c for c in characters_data.get('characters', []) if c.get('id') == chat['character_id']), None)
        if character:
            character_name = character.get('name', 'the character')

    return jsonify({"is_readable": is_readable, "character_name": character_name})

@app.route('/api/chat/<chat_id>/read-body-language', methods=['POST'])
def trigger_read_body_language(chat_id):
    """
    This endpoint is called ONLY when the user clicks the overlay.
    It applies the trait changes and sets the temporary prompt.
    """
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)

    if not chat:
        return jsonify({"success": False, "error": "Chat not found"}), 404

    logger.debug(f"DEBUG: Chat {chat_id} - User clicked to read body language. Applying effects.\n")

    # Roll the 20-sided die
    dice_roll = random.randint(1, 20)
    logger.debug(f"DEBUG: Dice roll result: {dice_roll}")

    # Calculate modifier
    base_modifier = 0.1
    if dice_roll < 10:
        modifier = base_modifier + (0.01 * (10 - dice_roll))
    elif dice_roll > 11:
        modifier = base_modifier - (0.01 * (dice_roll - 11))
    else:
        modifier = base_modifier

    logger.debug(f"DEBUG: Modifier after dice adjustment: {modifier:.2f}")

    # Apply modified trait effects
    state = chat['personality_state']
    state['grudge'] = min(state.get('grudge', 0) + modifier, 1.0)
    state['tension'] = min(state.get('tension', 0) + modifier, 1.0)
    state['trust'] = max(state.get('trust', 0) - modifier, 0.0)
    state['openness'] = max(state.get('openness', 0) - modifier, 0.0)

    chat['assistant_message_count'] = 2  # So next message will be (count - 2) % 6 == 0

    # Set temporary prompt
    chat['temporary_prompt'] = (
        "TELL USER TO STOP STARING AT YOU, in your own way! It's weird! "
        "Interject, interrupt to tell them to stop staring at you. "
        "If they keep doing it, use stronger response."
    )
    chat['temporary_prompt_turns_left'] = 2

    save_json(CHATS_FILE, chats_data)

    return jsonify({"success": True, "message": "Body language event triggered.\n"})

@app.route('/api/debug/world-map')
def debug_world_map(chat_id):
    """Debug route to inspect world map connections for a SPECIFIC chat."""
    chat_nodes = wsm.load_chat_nodes(chat_id)
    if not chat_nodes:
        return jsonify({"error": f"No node file found for chat_id: {chat_id}"}), 404
        
    debug_info = []
    for y, row in enumerate(chat_nodes):
        for x, node in enumerate(row):
            if node:
                node_info = {
                    'coords': [x, y],
                    'description': node.get('description_base', 'No description')[:50] + '...',
                    'connections': node.get('connections', {}),
                    'gameplay': node.get('gameplay', {}) # Show visited status
                }
                debug_info.append(node_info)
    return jsonify(debug_info)

@app.route('/api/debug/node/<int:x>/<int:y>')
def debug_node(chat_id,x, y):
    """Debug a specific node for a SPECIFIC chat."""
    chat_nodes = wsm.load_chat_nodes(chat_id)
    if not chat_nodes:
        return jsonify({"error": f"No node file found for chat_id: {chat_id}"}), 404

    node = wsm.get_node_by_coords(x, y, chat_nodes)
    if not node:
        return jsonify({'error': 'Node not found or is null'}), 404
    
    return jsonify({
        'coords': [x, y],
        'node_data': node
    })
@app.route('/api/debug/teleport', methods=['POST'])
def debug_teleport():
    data = request.json
    chat_id = data.get('chat_id')
    x = data.get('x')
    y = data.get('y')
    session['player_coords'] = (x, y)
    session.modified = True
    return jsonify({"status": "teleported", "coords": [x, y]})


# --- API endpoint for getting node coordinates for map flashing ---
@app.route('/api/chat/<chat_id>/node-coords', methods=['GET'])
def get_node_coords(chat_id):
    """
    Returns the coordinates for a given node description.
    Used for flashing nodes on the map when narrator descriptions are clicked.
    """
    x = request.args.get('x', type=int)
    y = request.args.get('y', type=int)
    
    if x is None or y is None:
        return jsonify({"error": "Missing x or y coordinates"}), 400
    
    chat_nodes = wsm.load_chat_nodes(chat_id)
    if not chat_nodes:
        return jsonify({"error": f"No node file found for chat_id: {chat_id}"}), 404
    
    node_data = wsm.get_node_by_coords(x, y, chat_nodes)
    if not node_data:
        return jsonify({"error": "Node not found"}), 404
    
    return jsonify({
        "coords": [x, y],
        "description": node_data.get('description_base', ''),
        "exits": wsm.get_exits_string(node_data) if node_data else ""
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
from email.mime import message
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import time
import logging
from .llm_handlers import anthropic, ollama, openai
from .orrery import PersonalityOrrery
from .task_controller import TaskController

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

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

# Load default trait config once at startup
DEFAULT_TRAIT_CONFIG = load_json(DEFAULT_TRAIT_CONFIG_FILE)

# In backend/app.py, REPLACE the entire old chat() function with this:

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    chat_id = data.get('chat_id')
    character_id = data.get('character_id', None)
    
    settings = load_json(SETTINGS_FILE)
    provider = settings.get('llm_provider', 'ollama')
    chats_data = load_json(CHATS_FILE)
    
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)
    
    if not chat:
        chat_id = str(int(time.time()))
        initial_state = {trait: config["baseline"] for trait, config in DEFAULT_TRAIT_CONFIG.items()}
        chat = {
            'id': chat_id, 'title': user_message[:30], 'created_at': time.time(),
            'messages': [], 'character_id': character_id,
            'system_prompt': "You are roleplaying as a new character.",
            'trait_config': DEFAULT_TRAIT_CONFIG, 'personality_state': initial_state,
            'recent_user_sentiments': [],
            'repetitive_sentiment_penalty_active': False
        }
        chats_data.setdefault('chats', []).append(chat)

    user_name = data.get('user_name', 'User')

    # --- CORRECTED MESSAGE HANDLING ---
    # Append the new user message to the history FIRST.
    INSTRUCTIONAL_CONTINUE_MESSAGE = "[OOC: Continue.]"
    if user_message:
        chat['messages'].append({
        'role': 'user',
        'content': user_message,
        'user_name': user_name,  # <-- store user name
        'timestamp': time.time()
    })

   
    chat['assistant_message_count'] = chat.get('assistant_message_count', 0) + 1


    # Now, the conversation history is up-to-date for all subsequent steps.
    conversation = []
    for msg in chat['messages']:
        if msg['role'] == 'user' and 'user_name' in msg:
            # Include user name in the message content
            conversation.append({
                "role": "user",
                "content": f"{msg['user_name']}: {msg['content']}"
            })
        else:
            conversation.append({
                "role": msg['role'],
                "content": msg['content']
            })

    

    # --- SENTIMENT ANALYSIS ---
    orrery_instance = PersonalityOrrery(trait_config=chat['trait_config'], personality_state=chat['personality_state'],
        recent_user_sentiments=chat.get('recent_user_sentiments', []), 
        repetitive_sentiment_penalty_active=chat.get('repetitive_sentiment_penalty_active', False))
    last_user_message_content = user_message # Use the current message directly
    
    if last_user_message_content and last_user_message_content != INSTRUCTIONAL_CONTINUE_MESSAGE:
        sentiment, intensity = "neutral", 0.5
        try:
            if provider == 'openai':
                handler = openai.OpenAIHandler()
                api_key = settings.get('api_keys', {}).get('openai', '')
                # We will make this _analyze_sentiment function in the next step
                sentiment, intensity = handler._analyze_sentiment(
                    last_user_message_content, api_key, settings, role="user"
                )
            elif provider == 'anthropic':
                handler = anthropic.AnthropicHandler()
                api_key = settings.get('api_keys', {}).get('anthropic', '')
                # We will make this _analyze_sentiment function in the next step
                sentiment, intensity = handler._analyze_sentiment(
                    last_user_message_content, api_key, settings, role="user"
                )
            # Add other providers here in the future

        except Exception as e:
            logger.debug("\n" + "="*50)
            logger.debug("!!! SENTIMENT ANALYSIS FAILED !!!\n")
            logger.debug(f"ERROR: {e}\n")
            logger.debug("Defaulting to neutral.\n")
            logger.debug("="*50 + "\n")

        logger.debug("\n" + "="*50)
        logger.debug(f"DEBUG: Sentiment Detected: {sentiment.upper()} (Intensity: {intensity:.2f})\n")
        orrery_instance.update_from_sentiment(sentiment, intensity, from_user=True)
        chat['recent_user_sentiments'] = orrery_instance.recent_user_sentiments
        chat['repetitive_sentiment_penalty_active'] = orrery_instance.repetitive_sentiment_penalty_active
        # Save the chat data to disk
        save_json(CHATS_FILE, chats_data)

        

    # --- TASK CONTROLLER (CTPS) LOGIC ---
    all_task_states = load_json(TASK_STATE_FILE)
    current_task_state = all_task_states.get(chat_id, {
        "task": "Settle in and figure out the situation.", "progress": 0.5, "priority": "low", "turn_counter": 0
    })
    task_controller = TaskController(chat_id, current_task_state)
    current_task_state['turn_counter'] += 1
    if current_task_state['turn_counter'] >= 2:
        logger.debug(f"DEBUG: Turn counter hit {current_task_state['turn_counter']}. Running TaskController.\n")
        recent_messages = chat.get('messages', [])[-5:]
        current_task_state = task_controller.decide_next_step(recent_messages, settings)
        current_task_state['turn_counter'] = 0
    
    task_prompt_string = task_controller.get_task_prompt()

    # --- FINAL PROMPT CONSTRUCTION & LLM CALL ---
    system_prompt = chat.get('system_prompt', '')
    if user_name:
        system_prompt += f"\nThe user's name is {user_name}."
    if character_id:
        # (Your logic to add character description to system_prompt is correct and goes here)
        # Load character info
        characters_data = load_json(CHARACTERS_FILE)
        character = next((c for c in characters_data.get('characters', []) if c.get('id') == character_id), None)
        if character:
            system_prompt = f'You are {character["name"]}. {character["description"]}'
            chat['system_prompt'] = system_prompt  # Update in chat object for persistence
        pass

    # --- NEW: Inject the temporary prompt if it's active ---
    if chat.get('temporary_prompt_turns_left', 0) > 0:
        system_prompt += f"\n{chat['temporary_prompt']}"
        chat['temporary_prompt_turns_left'] -= 1 # Decrement the counter
        if chat['temporary_prompt_turns_left'] == 0:
            chat['temporary_prompt'] = "" # Clear after use

    response_text = ""
    try:
        personality_context = orrery_instance.get_personality_prompt()
        enhanced_system_prompt = (task_prompt_string + " " + personality_context + " " + system_prompt).strip()
        
        logger.debug("\nDEBUG: Final System Prompt Sent to LLM:\n")
        logger.debug("-" * 50)
        logger.debug(enhanced_system_prompt)
        logger.debug("=" * 50 + "\n")

        if provider == 'openai':
            response_text = openai.generate_response(enhanced_system_prompt, conversation, settings)
        elif provider == 'anthropic':
            response_text = anthropic.generate_response(enhanced_system_prompt, conversation, settings)
        else:
            response_text = f"Ollama response based on: {enhanced_system_prompt}"
            logger.debug("Simplified Ollama call.\n")

    except Exception as e:
        response_text = f"Error: {str(e)}"

    try:
        # Use the same handler as above, or create a new one if needed
        if provider == 'openai':
            handler = openai.OpenAIHandler()
            api_key = settings.get('api_keys', {}).get('openai', '')
            env_sentiment, env_intensity = handler._analyze_sentiment(
                response_text, api_key, settings, role="assistant"
            )
        elif provider == 'anthropic':
            handler = anthropic.AnthropicHandler()
            api_key = settings.get('api_keys', {}).get('anthropic', '')
            env_sentiment, env_intensity = handler._analyze_sentiment(
                response_text, api_key, settings, role="assistant"
            )
        else:
            env_sentiment, env_intensity = "neutral", 0.5

        logger.debug(f"DEBUG: Environmental Sentiment Detected: {env_sentiment.upper()} (Intensity: {env_intensity:.2f})\n")
        # Apply at 25% effectiveness
        orrery_instance.update_from_sentiment(env_sentiment, env_intensity * 0.25, from_user=False)

    except Exception as e:
        logger.debug(f"Environmental sentiment analysis failed: {e}\n")

    # ...then save the updated personality state as usual...
    chat['personality_state'] = orrery_instance.get_trait_summary()
    
    # --- SAVE STATE ---
    chat['messages'].append({'role': 'assistant', 'content': response_text, 'timestamp': time.time()})
    chat['personality_state'] = orrery_instance.get_trait_summary()
    all_task_states[chat_id] = current_task_state
    
    save_json(CHATS_FILE, chats_data)
    save_json(TASK_STATE_FILE, all_task_states)
    
    return jsonify({'chat_id': chat_id, 'response': response_text})

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


# --- New API Route for Summarizing Chats ---
@app.route('/api/chat/<chat_id>/summarize', methods=['POST'])
def summarize_chat(chat_id):
    chats_data = load_json(CHATS_FILE)
    chat = next((c for c in chats_data.get('chats', []) if c.get('id') == chat_id), None)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    messages = chat['messages']
    if len(messages) <= 6:
        return jsonify({"error": "Not enough messages to summarize"}), 400

    # Find previous OOC summary if it exists (optional, for chaining summaries)
    previous_summary = ""
    for msg in messages:
        if msg['role'] == 'assistant' and msg['content'].startswith("OOC:"):
            previous_summary = msg['content']

    # Get messages to summarize (all but last 6, and not previous OOC summaries)
    to_summarize = [
        msg for msg in messages[:-6]
        if not (msg['role'] == 'assistant' and msg['content'].startswith("OOC:"))
    ]
    if not to_summarize:
        return jsonify({"error": "No messages to summarize"}), 400

    # Build text for summarization
    text = "\n".join(
        (f"{msg.get('user_name', 'User')}: {msg['content']}" if msg['role'] == 'user' else f"{msg['role'].capitalize()}: {msg['content']}")
        for msg in to_summarize
    )
    if previous_summary:
        text = f"Previous summary:\n{previous_summary}\n\nNew messages:\n{text}"

    # Use LLM to summarize
    settings = load_json(SETTINGS_FILE)
    provider = settings.get('llm_provider', 'ollama')
    summary_prompt = (
        "Convert this paragraph into ultra-compact shorthand using abbreviations, symbols, and minimal syntax "
        "while preserving major details and relationship. Use techniques like: acronyms, mathematical symbols "
        "(→, ∵, ∴, &, +, =), but *NO EMOJIS*, drop articles/prepositions where clear, use punctuation as operators, compress similar "
        "concepts. Ensure an LLM can fully reconstruct the original meaning. "
        "Do not include OOC or meta commentary. Only summarize the story and character actions/dialogue.\n\n"
        f"{text}"
    )
    summary_text = ""
    try:
        if provider == 'openai':
            summary_text = openai.generate_response(summary_prompt, [], settings)
        elif provider == 'anthropic':
            summary_text = anthropic.generate_response(summary_prompt, [], settings)
        else:
            summary_text = f"Ollama summary: {summary_prompt[:200]}..."
    except Exception as e:
        return jsonify({"error": f"Summarization failed: {str(e)}"}), 500

    # Keep only the newest 6 messages (excluding previous OOC summaries)
    last_6 = [msg for msg in messages[-6:] if not (msg['role'] == 'assistant' and msg['content'].startswith("OOC:"))]

    # Build new messages list: new OOC summary as assistant, last 6 messages
    new_messages = [{
        "role": "assistant",
        "content": f"OOC: {summary_text}",
        "timestamp": time.time()
    }]
    new_messages.extend(last_6)
    chat['messages'] = new_messages

    save_json(CHATS_FILE, chats_data)
    return jsonify({"summary": summary_text})



# --- Other API Routes (Unchanged) ---

@app.route('/')
def serve_frontend():
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
    
    # Apply the trait hits
    state = chat['personality_state']
    state['grudge'] = min(state.get('grudge', 0) + 0.1, 1.0)
    state['tension'] = min(state.get('tension', 0) + 0.1, 1.0)
    state['trust'] = max(state.get('trust', 0) - 0.1, 0.0)
    state['openness'] = max(state.get('openness', 0) - 0.1, 0.0)

    chat['assistant_message_count'] = 2  # So next message will be (count - 2) % 6 == 0

    # Set the temporary prompt
    chat['temporary_prompt'] = "TELL USER TO STOP STARING AT YOU, in your own way! It's weird! Interject, interrpt to tell them to stop staring at you. If they keep doing it, use stronger response."
    chat['temporary_prompt_turns_left'] = 2

    save_json(CHATS_FILE, chats_data)

    return jsonify({"success": True, "message": "Body language event triggered.\n"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
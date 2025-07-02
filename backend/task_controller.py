import json
import os
import re
import logging
from .llm_handlers import anthropic, gemini, ollama, openai, perplexity  # We'll use the OpenAI handler for this

# Define paths for our data files
DATA_DIR = 'data'
TASK_STATE_FILE = os.path.join(DATA_DIR, 'task_state.json')
TASK_FRAMEWORK_FILE = os.path.join(DATA_DIR, 'task_framework.json')

logger = logging.getLogger(__name__)

class TaskController:
    def __init__(self, chat_id: str, task_state: dict):
        """
        Initializes the Task Controller for a specific chat.
        Args:
            chat_id (str): The ID of the current chat.
            task_state (dict): The current task state for this chat.
        """
        self.chat_id = chat_id
        self.state = task_state
        # Load the task generation framework once
        try:
            with open(TASK_FRAMEWORK_FILE, 'r', encoding='utf-8') as f:
                self.task_framework = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.error("Warning: task_framework.json not found or is invalid. Using an empty framework.\n")
            self.task_framework = {}

    def _save_state(self):
        """Saves the current state for this chat back to the main state file."""
        all_states = {}
        if os.path.exists(TASK_STATE_FILE):
            with open(TASK_STATE_FILE, 'r') as f:
                try:
                    all_states = json.load(f)
                except json.JSONDecodeError:
                    logger.error("Could not decode task_state.json, starting fresh.")
        
        all_states[self.chat_id] = self.state
        with open(TASK_STATE_FILE, 'w') as f:
            json.dump(all_states, f, indent=2)
        logger.debug(f"Task state saved for chat {self.chat_id}")

    def get_task_prompt(self) -> str:
        """Generates the OOC note for the main character's system prompt."""
        if not self.state or not self.state.get('task'):
            return ""
        
        task = self.state['task']
        progress = int(self.state.get('progress', 0) * 100)
        priority = self.state.get('priority', 'low')
        task_prompt = f"[OOC Note: Your current focus is to '{task}'. Progress: {progress}%. This is a {priority} priority.]"
        logger.debug(f"[TaskController] Returning task prompt: '{task_prompt}'")
        return task_prompt

    # In task_controller.py

    def decide_next_step(self, chat_history: list, settings: dict):
        """
        Calls an LLM to generate a NEW task for the character and saves it.
        This is now only called when a previous task is complete.
        """
        provider = settings.get('llm_provider', 'ollama')
        logger.debug(f"TaskController: Generating a NEW task for chat {self.chat_id}\n")
        
        recent_history = chat_history[-4:] # We still only need the most recent context
        formatted_history = "\n".join([f"[{msg.get('role', 'unknown')}]: {msg.get('content', '')}" for msg in recent_history])
        
        # FIX: A much simpler prompt focused only on generating a new task.
        controller_system_prompt = f"""You are a Task Controller for an RPG character that returns raw json, no wrapping labels. The character's previous task is complete. Your job is to analyze their situation and generate their NEXT most important task. You MUST respond ONLY with raw valid JSON, no code blocks or backticks.

Analyze the following:
1.  **Previous Task State**: {json.dumps(self.state)}
2.  **Recent Conversation**:
    {formatted_history}

Decision Logic:
PATH A: UPD CURR PERS TASK
If curr pers task ≠ complete (progress < 1.0) & no new urgent pers task fm convo → Assess convo progress/priority
PATH B: START NEW PERS TASK
If curr pers task complete (progress == 1.0) OR new urgent pers task fm convo → Gen new pers task:
If new urgent: use that
If old complete: 30% chance select theme fm Task Generation Framework
Set progress → 0.0
Set priority (low/med/high/critical)

The `priority` field now represents difficulty. It MUST be one of: "easy" (2 turns), "medium" (5 turns), or "hard" (8 turns).

**Task Generation Framework:**
4 Tensions: Being(body/mind): vitality/decay, indulgence/discipline, presence/escape. Relating: connection/autonomy, authenticity/mask, protection/vulnerability. 
Meaning: survival/legacy, ambition/acceptance, control/fate. Action: freedom/responsibility, justice/mercy, truth/loyalty. 
8 Hooks: Provider/Dreamer, Warrior/Obsolete, Brotherhood/Isolation, Strength/Decay, Protector/Destroyer, Appetite/Discipline, Mask/Truth, Control/Chaos.

Based on your analysis, return the new state in a single, raw JSON object. JUST JSON, NEVER wrap in code block backticks.
Example response: {{"task": "Find a quiet corner to reflect on the strange encounter.", "progress": 0.0, "priority": "easy", "turn_counter": 0}}
""" 

        try:
            # The rest of this function remains the same as it correctly calls the LLM
            # and saves the state.
            response_text = ""
            if provider == 'openai':
                response_text = openai.generate_response(controller_system_prompt, [], settings)
            elif provider == 'anthropic':
                response_text = anthropic.generate_response(controller_system_prompt, [], settings)
            elif provider == 'gemini':
                # FIX: For Gemini, we treat the entire prompt as the first user message
                # in the conversation history.
                messages = [
                    {'role': 'user', 'content': controller_system_prompt}
                ]
                # We pass an empty string for the system_prompt and the full prompt in the conversation.
                response_text = gemini.generate_response("", messages, settings)
            elif provider == 'perplexity':
                response_text = perplexity.generate_response(controller_system_prompt, [], settings)
            elif provider == 'ollama':
                response_text = ollama.generate_response(controller_system_prompt, [], settings)
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
            # ... other providers ...
            
            # DEBUG: Log the raw response
            logger.debug(f"TaskController RAW LLM Response: '{response_text}'")
            logger.debug(f"TaskController Response length: {len(response_text) if response_text else 0}")

            cleaned_json = response_text
            # Check if the response is wrapped in a JSON markdown block
            if cleaned_json.strip().startswith("```json"):
                # Use a regular expression to find the content between the curly braces
                match = re.search(r'\{.*\}', cleaned_json, re.DOTALL)
                if match:
                    cleaned_json = match.group(0)
            
            if not response_text or response_text.strip() == "":
                raise ValueError("LLM returned empty response")

            new_state = json.loads(response_text)
            if 'task' in new_state and 'progress' in new_state and 'priority' in new_state:
                logger.debug(f"TaskController successfully created new task: {new_state}\n")
                self.state = new_state
            else:
                raise ValueError("LLM response was valid JSON but missed required keys.")
        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.error(f"ERROR: TaskController failed to get a valid JSON response. Error: {e}. Keeping previous state.\n")
        
        self._save_state()
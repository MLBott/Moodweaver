import json
import os
import logging
from .llm_handlers import openai  # We'll use the OpenAI handler for this

# Define paths for our data files
DATA_DIR = 'data'
TASK_STATE_FILE = os.path.join(DATA_DIR, 'task_state.json')
TASK_FRAMEWORK_FILE = os.path.join(DATA_DIR, 'task_framework.json')

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
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

    def get_task_prompt(self) -> str:
        """Generates the OOC note for the main character's system prompt."""
        if not self.state or not self.state.get('task'):
            return ""
        
        task = self.state['task']
        progress = int(self.state.get('progress', 0) * 100)
        priority = self.state.get('priority', 'low')

        return f"[OOC Note: Your current focus is to '{task}'. Progress: {progress}%. This is a {priority} priority.]"

    def decide_next_step(self, chat_history: list, settings: dict) -> dict:
        """
        Calls an LLM to act as the Story Controller. It analyzes the current state
        and conversation to determine the character's next task state.
        """
        logger.debug(f"DEBUG: TaskController deciding next step for chat {self.chat_id}\n")

        # Format the recent chat history for the prompt
        formatted_history = "\n".join([f"[{msg['role']}]: {msg['content']}" for msg in chat_history])

        # This is the detailed prompt for our Story Controller LLM
        controller_system_prompt = f"""You are a Task Controller for an RPG character. Your job is to analyze the character's situation and determine their most important task. You MUST respond ONLY with a valid JSON object. Do not add any other text.

Analyze the following:
1.  **Current Task State**: {json.dumps(self.state)}
2.  **Recent Conversation**:
    {formatted_history}

**Your Decision Logic:**

**PATH A: UPDATE CURRENT PERSONAL TASK**
If the current personal task is NOT complete (`progress` < 1.0) AND no new, more urgent personal task has emerged from the conversation, then:
1.  Assess if the conversation shows progress on the personal task. Easy tasks progress quickly.
2.  Update the `progress` value (e.g., from 0.25 to 0.5). Keep `progress` at 1.0 if the personal task is now finished.
3.  Keep the `task` and `priority` the same unless the urgency has clearly changed.

**PATH B: START NEW PERSONAL TASK**
If the current personal task IS complete (`progress` == 1.0) OR a new personal task has emerged from the conversation that is clearly more important (e.g., an emergency, a direct user request that is accepted), then:
1.  Generate a NEW personal task.
    - If a new urgent personal task emerged, use that, but small chance (10%) of selecting a fitting core_conflict/manifestation or description/hook task from the "Task Generation Framework" below.
    - (10% chance) If the old personal task was just completed, select a theme (with core_conflict/manifestation or description/hook) from the Task Generation Framework below and create a new interesting, insightful, or unpredictable task based on it.
2.  Set `progress` to 0.0.
3.  Set the `priority` for the new personal task (low, medium, high, critical).

**Task Generation Framework:**
{json.dumps(self.task_framework, indent=2)}

Based on your analysis, return the new state in a single, raw JSON object.
Example response: {{"task": "Order a strong drink from the bartender and pay tab.", "progress": 0.0, "priority": "high", "turn_counter": 0}}
"""

        try:
            # We need a dedicated function in the handler for getting structured JSON.
            # For now, we assume the handler can be made to return a raw JSON string.
            # We'll use the main `openai` handler but with a prompt that strictly requests JSON.
            
            # NOTE: This uses a simplified call for clarity. The actual implementation in openai.py might be slightly different.
            # We pass an empty conversation list because the history is already in the system prompt.
            response_text = openai.generate_response(
                system_prompt=controller_system_prompt, 
                conversation=[], 
                settings=settings,
            )

            new_state = json.loads(response_text)

            # Basic validation to ensure we got a valid object
            if 'task' in new_state and 'progress' in new_state and 'priority' in new_state:
                logger.debug(f"DEBUG: TaskController successfully updated state to: {new_state}\n")
                self.state = new_state
            else:
                raise ValueError("LLM response was valid JSON but missed required keys.")

        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.error(f"ERROR: TaskController failed to get a valid JSON response. Error: {e}. Keeping previous state.\n")
            # Fallback: If the LLM fails or returns garbage, we don't change the task state.
            pass

        return self.state
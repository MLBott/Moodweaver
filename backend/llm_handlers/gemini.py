import logging
import google.generativeai as genai
from typing import List, Dict

logger = logging.getLogger(__name__)

class GeminiHandler:
    def _prepare_conversation(self, conversation: List[Dict]) -> List[Dict]:
        """
        Prepares the conversation history by ensuring roles are 'user' or 'model'.
        The Gemini API is strict about alternating roles.
        """
        prepared_convo = []
        last_role = "model" # Assume the turn before the history starts was a model response.
        
        for msg in conversation:
            role = "model" if msg.get("role") == "assistant" else "user"
            
            # If the current role is the same as the last one, skip it to maintain alternation.
            # This handles cases where there might be two user messages in a row.
            if role == last_role:
                logger.warning(f"Skipping duplicate role message to maintain alternation: {msg}")
                continue
                
            prepared_convo.append({
                "role": role,
                "parts": [msg.get("content", "")]
            })
            last_role = role
            
        return prepared_convo

    # In llm_handlers/gemini.py, inside the GeminiHandler class

    def generate_response(self, system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
        """
        Generates a response using the Google Gemini API.
        """
        api_key = settings.get('api_keys', {}).get('gemini_key', '')
        if not api_key:
            return "Error: Google Gemini API key not found in settings"

        try:
            genai.configure(api_key=api_key)
            
            model_name = settings.get('default_model', 'gemini-1.5-flash-latest')
            
            generation_config = genai.types.GenerationConfig(
                temperature=float(settings.get('temperature', 0.7)),
                max_output_tokens=1000,
            )
            
            # FIX: Intelligently combine the system prompt and conversation into a single list
            # This handles all use cases correctly.
            full_contents = []
            if system_prompt:
                # The official way to add a system prompt is to place it at the start
                # of the contents list before the first user message.
                full_contents.append({'role': 'user', 'parts': [system_prompt]})
                full_contents.append({'role': 'model', 'parts': ["OK, I will follow these instructions."]})

            # Add the rest of the conversation, ensuring roles alternate
            full_contents.extend(self._prepare_conversation(conversation))

            if not full_contents:
                 raise ValueError("The 'contents' of the Gemini API call cannot be empty.")

            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config
            )

            response = model.generate_content(full_contents)
            
            return response.text

        except Exception as e:
            logger.error(f"Error with Google Gemini API: {e}")
            return f"Error with Google Gemini API: {str(e)}"

# This is the public function that the rest of your app will call
def generate_response(system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
    """
    Public function to generate a response using the Gemini handler.
    """
    handler_instance = GeminiHandler()
    return handler_instance.generate_response(system_prompt, conversation, settings)
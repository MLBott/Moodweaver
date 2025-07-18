import openai
import json
import logging
from typing import Dict, List, Tuple
from ..orrery import PersonalityOrrery

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class OpenAIHandler:
    def __init__(self):
        self.client = None
    
    def get_client(self, api_key: str):
        """Get or create OpenAI client"""
        if not self.client:
            self.client = openai.OpenAI(api_key=api_key)
        return self.client
    

    def generate_response(self, system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
        """
        Generate a response using the OpenAI API.
        This function now receives the final, fully-formed system prompt from app.py.
        """
        
        api_key = settings.get('api_keys', {}).get('openai', '')
        if not api_key:
            return "Error: OpenAI API key not found in settings"
        
        # The sentiment analysis and orrery logic have been removed from this file,
        # as app.py now orchestrates the prompt construction.

        # Format messages for OpenAI
        messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
        messages.extend(conversation)
        
        model = settings.get('default_model', 'gpt-4.1')
        temperature = settings.get('temperature', 0.8)
        
        try:
            client = self.get_client(api_key)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error with OpenAI API: {str(e)}"

# NEW corrected code for the bottom of openai.py
def generate_response(system_prompt, conversation, settings):
    """
    This is the public function that app.py calls.
    It creates an instance of the handler and runs the generation.
    """
    # Create a new instance of the handler for each call.
    handler_instance = OpenAIHandler()
    # Call the method on the instance.
    return handler_instance.generate_response(system_prompt, conversation, settings)
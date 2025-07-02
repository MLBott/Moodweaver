# llm_handlers/perplexity.py

import openai
import logging
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class PerplexityHandler:
    def __init__(self):
        self.client = None

    def get_client(self, api_key: str):
        """Get or create Perplexity client, which uses the OpenAI library."""
        if not self.client:
            # The key difference is providing the base_url for Perplexity
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai"
            )
        return self.client


    def generate_response(self, system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
        """Generate a response using the Perplexity API."""
        
        api_key = settings.get('api_keys', {}).get('perplexity', '')
        if not api_key:
            return "Error: Perplexity API key not found in settings"
        
        messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
        messages.extend(conversation)
        
        # Use the model specified for Perplexity in settings, or a default
        model = settings.get('default_model', 'llama-3-sonar-large-32k-online')
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
            return f"Error with Perplexity API: {str(e)}"

# Public function that app.py will call
def generate_response(system_prompt, conversation, settings):
    """Creates an instance of the handler and runs the generation."""
    handler_instance = PerplexityHandler()
    return handler_instance.generate_response(system_prompt, conversation, settings)
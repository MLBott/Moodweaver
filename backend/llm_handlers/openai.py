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
    
    def _analyze_sentiment(self, message_content: str, api_key: str, settings: Dict, role: str = "user") -> Tuple[str, float]:
        """Analyze message sentiment using OpenAI"""
        sentiment_prompt = f"""Analyze this message. The message is from the {role}. If from assistant, ignore dialogue and actions, analyze ONLY 
the physical environment of the assistant and return ONLY the primary sentiment of the physical environment from ONLY this list that best fits 
how the affective atmosphere of the physical environment would affect a typical male fictional character in an exaggerated way. If from user, return ONLY the primary 
sentiment of the user's message from ONLY this list:
praise, criticism, hostility, curiosity, levity, sarcasm, confusion, gratitude, dismissal, agreement, disagreement, 
frustration, excitement, boredom, concern, disgust, affection, flirtation, vulnerability, jealousy, deception, fear, 
sadness, awe, shame, hope, intimidation, pleading, contemplation, doubt, command, neutral, betrayal, admiration, 
playfulness, accusation, surprise, challenge, respect, mockery, achievement, failure, competitiveness, loyalty, comfort, confidence, neutral

Then rate the intensity from 0.1 (very mild) to 1.0 (very strong).

Message: "{message_content}"

Response format: sentiment_word intensity_number
Example: curiosity 0.7"""

        try:
            client = self.get_client(api_key)
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "You are a precise sentiment analyzer. Follow instructions exactly."},
                    {"role": "user", "content": sentiment_prompt}
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            # Parse response
            result = response.choices[0].message.content.strip().split()
            if len(result) >= 2:
                sentiment = result[0].lower()
                intensity = float(result[1])
                return sentiment, max(0.1, min(1.0, intensity))
                
        except Exception as e:
            logger.debug(f"Sentiment analysis failed: {e}\n")
        
        return "neutral", 0.5
    
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
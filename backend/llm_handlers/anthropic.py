import anthropic
from typing import Dict, List, Tuple
import logging
from ..orrery import PersonalityOrrery

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class AnthropicHandler:
    def __init__(self):
        self.client = None

    def _get_client(self, api_key: str):
        """Get or create Anthropic client"""
        if not self.client:
            self.client = anthropic.Anthropic(api_key=api_key)
        return self.client

    def _analyze_sentiment(self, message_content: str, api_key: str, settings: Dict, role: str = "user") -> Tuple[str, float]:
        """Analyze message sentiment using Claude"""
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
            client = self._get_client(api_key)
            response = client.messages.create(
                model="claude-3-5-haiku-latest",  # Use cheaper model for sentiment analysis
                system="You are a precise sentiment analyzer. Follow instructions exactly.",
                messages=[{"role": "user", "content": sentiment_prompt}],
                max_tokens=10
            )
            # Parse response
            result = response.content[0].text.strip().split()
            if len(result) >= 2:
                sentiment = result[0].lower()
                try:
                    intensity = float(result[1])
                except Exception:
                    intensity = 0.5
                return sentiment, max(0.1, min(1.0, intensity))
        except Exception as e:
            logger.debug(f"Sentiment analysis failed: {e}\n")

        return "neutral", 0.5

    def generate_response(self, system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
        """Generate a response using the Anthropic API."""
        api_key = settings.get('api_keys', {}).get('anthropic', '')
        if not api_key:
            return "Error: Anthropic API key not found in settings"

        # Format messages for Anthropic
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in conversation]

        model = settings.get('default_model', 'claude-3-sonnet-20240229')
        temperature = settings.get('temperature', 0.7)

        try:
            client = self._get_client(api_key)
            response = client.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=2000
            )
            return response.content[0].text
        except Exception as e:
            return f"Error with Anthropic API: {str(e)}"

# Public function for app.py to call
def generate_response(system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
    handler = AnthropicHandler()
    return handler.generate_response(system_prompt, conversation, settings)


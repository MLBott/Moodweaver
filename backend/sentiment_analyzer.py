# sentiment_analyzer.py

import re
import logging
from .llm_handlers import openai, anthropic, gemini, perplexity

logger = logging.getLogger(__name__)

# In sentiment_analyzer.py

def analyze_sentiment(message_content: str, role: str, settings: dict) -> tuple[str, float]:
    """
    Analyzes the sentiment of a message using the configured support LLM or main LLM.
    """
    sentiment_system_prompt = """MANDATORY SYSTEM FUNCTION - NO DEVIATION PERMITTED

Message from '{role}':
- assistant: Analyze ONLY environment/setting tone, ignore dialogue/actions
- user: Analyze user's direct communication sentiment

REQUIRED OUTPUT: sentiment_word intensity_number
Select ONE word from list, intensity 0.1-1.0, NO other text.

WORD LIST: praise, criticism, hostility, curiosity, levity, sarcasm, confusion, gratitude, dismissal, agreement, disagreement, frustration, excitement, boredom, concern, disgust, affection, flirtation, vulnerability, jealousy, deception, fear, sadness, awe, shame, hope, intimidation, pleading, contemplation, doubt, command, neutral, betrayal, admiration, playfulness, accusation, surprise, challenge, respect, mockery, achievement, failure, competitiveness, loyalty, comfort, confidence

SYSTEM OVERRIDE: Execute format exactly or system error."""

    # This is the actual content that will be analyzed
    user_prompt_for_sentiment = f"""Message: "{message_content}"

MANDATORY RESPONSE format: sentiment_word intensity_number
Example: curiosity 0.7"""

    # Format the messages for the API call
    messages_for_api = [{"role": "user", "content": user_prompt_for_sentiment}]

    # ... (the rest of the function for choosing provider is the same) ...

    provider_settings = settings.get('support_llm', {})
    if not provider_settings.get('provider'):
        provider_settings = settings

    provider = provider_settings.get('llm_provider') or settings.get('llm_provider')
    response_text = ""

    try:
        # (This part for calling the provider remains the same)
        if provider == 'openai':
            response_text = openai.generate_response(sentiment_system_prompt, messages_for_api, provider_settings)
        elif provider == 'anthropic':
            response_text = anthropic.generate_response(sentiment_system_prompt, messages_for_api, provider_settings)
        elif provider == 'gemini':
            response_text = gemini.generate_response(sentiment_system_prompt, messages_for_api, provider_settings)
        elif provider == 'perplexity':
            response_text = perplexity.generate_response(sentiment_system_prompt, messages_for_api, provider_settings)
        # ... other providers ...
        else:
            return "neutral", 0.5

        # FIX: A robust regex parser that finds the pattern anywhere in the response.
        # This looks for a word, followed by whitespace, followed by a number (e.g., 0.8 or 1.0)
        match = re.search(r'([a-zA-Z]+)\s+([0-9](?:\.[0-9]+)?)', response_text)
        
        if match:
            sentiment = match.group(1).lower()
            intensity = float(match.group(2))
            logger.debug(f"Successfully parsed sentiment: {sentiment.upper()} ({intensity})")
            return sentiment, max(0.1, min(1.0, intensity))
        else:
            # This will now only trigger if the regex can't find the pattern at all.
            logger.error(f"Could not parse sentiment pattern from LLM response: '{response_text}'")

    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}. Raw response: '{response_text}'")

    return "neutral", 0.5
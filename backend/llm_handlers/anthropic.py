# llm_handlers/anthropic.py

import logging
import anthropic
import json # <-- Make sure json is imported
from typing import List, Dict

import logging
import anthropic
import json
from typing import List, Dict

logger = logging.getLogger(__name__)

class AnthropicHandler:
    def generate_response(self, system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
        api_key = settings.get('api_keys', {}).get('anthropic', '')
        if not api_key:
            return "Error: Anthropic API key not found in settings"

        try:
            client = anthropic.Anthropic(api_key=api_key)
            model_name = settings.get('default_model', 'claude-3-5-sonnet-20240620')
            temperature = float(settings.get('temperature', 0.7))

            # --- Prepare the messages for the API call ---
            api_messages = []
            
            # Process the conversation history
            last_role = None
            for msg in conversation:
                role = "assistant" if msg.get("role") in ["assistant", "character", "system"] else "user"
                content = msg.get("content", "").strip()
                
                # Skip empty messages
                if not content:
                    continue
                    
                # Skip duplicate consecutive roles
                if role == last_role:
                    # Merge with previous message instead of skipping
                    if api_messages:
                        api_messages[-1]["content"] += "\n\n" + content
                    continue
                
                api_messages.append({"role": role, "content": content})
                last_role = role
            
            # If we have no messages, create a simple greeting prompt
            if not api_messages:
                api_messages.append({"role": "user", "content": "Hello, let's begin our conversation."})
            
            # Ensure the conversation starts with a user message
            if api_messages and api_messages[0]["role"] != "user":
                api_messages.insert(0, {"role": "user", "content": "Hello, let's begin our conversation."})
            
            # Ensure we don't end with a user message (Anthropic expects assistant to respond to user)
            if api_messages and api_messages[-1]["role"] == "user":
                # This is correct - we want to end with a user message so assistant can respond
                pass
            else:
                # If we end with assistant message, add a continuation prompt
                api_messages.append({"role": "user", "content": "Please continue."})

            # --- DEBUGGING BLOCK ---
            logger.debug("--- Anthropic API Request Payload ---")
            logger.debug(f"  Model: {model_name}")
            logger.debug(f"  System Prompt: {system_prompt[:200]}...")  # Truncate for readability
            logger.debug(f"  Number of Messages: {len(api_messages)}")
            for i, msg in enumerate(api_messages):
                logger.debug(f"    Message {i}: {msg['role']} - {msg['content'][:100]}...")
            logger.debug("---------------------------------")
            # --- END DEBUGGING BLOCK ---

            response = client.messages.create(
                model=model_name,
                system=system_prompt,
                messages=api_messages,
                max_tokens=1024,
                temperature=temperature,
            )
            
            logger.debug(f"--- Anthropic API Raw Response ---")
            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response content length: {len(response.content) if response.content else 0}")
            logger.debug(f"First content block: {response.content[0] if response.content else 'None'}")
            logger.debug("---------------------------------")

            if response.content and len(response.content) > 0:
                result_text = response.content[0].text
                logger.debug(f"Extracted text length: {len(result_text)}")
                logger.debug(f"Extracted text preview: {result_text[:200]}...")
                return result_text
            else:
                logger.warning("Anthropic API returned a valid response with no content.")
                return ""

        except Exception as e:
            logger.error(f"An exception occurred in the Anthropic handler: {e}", exc_info=True)
            return f"Error with Anthropic API: {str(e)}"


def generate_response(system_prompt: str, conversation: List[Dict], settings: Dict) -> str:
    handler_instance = AnthropicHandler()
    return handler_instance.generate_response(system_prompt, conversation, settings)
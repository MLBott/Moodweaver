from .llm_handlers import openai, anthropic, gemini, perplexity, ollama

def summarize_conversation(messages: list, settings: dict) -> str:
    """
    Uses an LLM to create a concise summary of a conversation.
    """
    to_summarize = [msg for msg in messages[:-6] if not (msg['role'] == 'assistant' and msg['content'].startswith("OOC:"))]
    if not to_summarize:
        raise ValueError("Not enough messages to summarize.")

    text = "\n".join(
        (f"{msg.get('user_name', 'User')}: {msg['content']}" if msg['role'] == 'user' else f"{msg['role'].capitalize()}: {msg['content']}")
        for msg in to_summarize
    )
    
    summary_prompt = (
        "Create a concise timeline summary of this roleplay conversation. Focus on: "
        "key events & actions by characters, important dialogue/decisions, relationship "
        "developments/emotional moments, plot progression. Careful attention to correct association of who with what.Format as brief bullet points "
        "or chronological entries. Remove all OOC commentary, formatting symbols "
        "(*italics*, **bold**), & redundant descriptions. Compress similar actions. Use "
        "abbreviations & symbols (→, &, +) where clear. Drop articles/prepositions. Avoid 'you' descrip, use 'user' or user's 'user_name'."
        "Goal: preserve story continuity for context while drastically reducing token count.\n\n"
        f"{text}"
    )
    
    provider = settings.get('llm_provider', 'ollama')
    
    if provider == 'openai':
        return openai.generate_response(summary_prompt, [], settings)
    elif provider == 'anthropic':
        return anthropic.generate_response(summary_prompt, [], settings)
    elif provider == 'gemini':
        return gemini.generate_response(summary_prompt, [], settings)
    elif provider == 'perplexity':
        return perplexity.generate_response(summary_prompt, [], settings)
    elif provider == 'ollama':
        return ollama.generate_response(summary_prompt, [], settings)
    else:
        raise ValueError(f"Unsupported provider for summarization: {provider}")
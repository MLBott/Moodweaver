

def build_system_prompt(base_prompt: str, personality_context: str, task_prompt: str, narrator_message: str, user_name: str) -> str:
    """
    Assembles the final system prompt from various context pieces.
    """
    prompt_parts = []

    # The character's core instructions come first.
    prompt_parts.append(base_prompt)
    prompt_parts.append(f"The user's name is {user_name}.")

    # --- GLOBAL INSTRUCTION: NO HTML ---
    prompt_parts.append(
        "GLOBAL: NO HTML/code/fmt in resp. Plain txt only."
    )

    # Dynamic context is added next.
    if task_prompt:
        prompt_parts.append(task_prompt)
    
    if personality_context:
        prompt_parts.append(personality_context)

    # The narrator note about the environment is highly immediate context.
    if narrator_message:
        prompt_parts.append(f"\n[OOC NARRATOR NOTE: {narrator_message}]")
    
    # Finally, add the instructions on HOW to respond.
    final_instructions = (
        "Resp naturally w/ full context of mind. Show don't tell traits/goals."
    )
    prompt_parts.append(final_instructions)

    return " ".join(part for part in prompt_parts if part).strip()
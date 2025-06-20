# STILL NEED TO UPDATE FOR APP NEW VERSION CODE CHANGES

import requests
import json
from ..orrery import PersonalityOrrery, analyze_message_sentiment

def generate_response(system_prompt, conversation, settings):
    """Generate a response using Ollama locally"""
    
    ollama_url = settings.get('ollama_url', 'http://localhost:11434')
    model = settings.get('default_model', 'llama3')  # Using a more common default model
    temperature = settings.get('temperature', 0.7)
    
    # Format messages for Ollama
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        
    for msg in conversation:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    try:
        response = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "options": {
                    "temperature": temperature
                }
            },
            headers={"Content-Type": "application/json"},
            stream=True  # Enable streaming
        )
        
        # Log the raw response for debugging
        print("Streaming response from Ollama:")
        
        # Process the streamed response
        final_content = ""
        for line in response.iter_lines(decode_unicode=True):
            if line.strip():  # Ignore empty lines
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    final_content += content
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON chunk: {line}")
        
        if final_content:
            return final_content.strip()
        else:
            return "The assistant did not provide a response. Please check the input or model configuration."
    
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running at {ollama_url}."
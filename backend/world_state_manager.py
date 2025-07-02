from flask import Flask, request, jsonify, send_from_directory, render_template, session
from flask_cors import CORS
import json
import os
import time
import logging
import spacy
import re
from .llm_handlers import anthropic, gemini, ollama, openai, perplexity

logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("gemini_webapi").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def create_chat_node_file(chat_id):
    """Copies the base world_map.json to a new chat-specific node file."""
    src = os.path.join('data', 'world_map.json')
    dst = os.path.join('data', f'nodes_{chat_id}.json')
    logger.debug(f"Creating chat node file for chat_id={chat_id}: {dst}")
    if not os.path.exists(dst):
        try:
            with open(src, 'r') as f_src:
                data = json.load(f_src)
                logger.debug(f"Loaded base world_map.json for chat_id={chat_id}")
                # Mark the starting node [1, 1] as visited upon creation
                if 1 < len(data['nodes']) and 1 < len(data['nodes'][1]) and data['nodes'][1][1]:
                    data['nodes'][1][1].setdefault('gameplay', {})['visited'] = True
            with open(dst, 'w') as f_dst:
                # We only need to store the nodes array, not the whole world object
                json.dump(data['nodes'], f_dst, indent=2)
                logger.info(f"Created node file for chat_id={chat_id} at {dst}")
        except Exception as e:
            logger.error(f"Failed to create chat node file for chat_id={chat_id}: {e}")
    else:
        logger.debug(f"Node file already exists for chat_id={chat_id}: {dst}")


def load_chat_nodes(chat_id):
    path = os.path.join('data', f'nodes_{chat_id}.json')
    logger.debug(f"Loading chat nodes from {path}")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                nodes = json.load(f)
                logger.debug(f"Loaded nodes for chat_id={chat_id}, nodes count: {len(nodes)}")
                return nodes
        except Exception as e:
            logger.error(f"Failed to load nodes for chat_id={chat_id}: {e}")
            return []
    logger.warning(f"Node file does not exist for chat_id={chat_id}: {path}")
    return []

def save_chat_nodes(chat_id, nodes):
    path = os.path.join('data', f'nodes_{chat_id}.json')
    logger.debug(f"Saving chat nodes to {path} for chat_id={chat_id}")
    try:
        with open(path, 'w') as f:
            json.dump(nodes, f, indent=2)
        logger.info(f"Saved nodes for chat_id={chat_id} at {path}")
    except Exception as e:
        logger.error(f"Failed to save nodes for chat_id={chat_id}: {e}")

def get_visited_nodes(nodes):
    """Gets a list of coordinates for all visited nodes."""
    visited = []
    logger.debug("Getting visited nodes")
    for row in nodes:
        for node in row:
            if node and node.get("gameplay", {}).get("visited"):
                coords = node.get("coords")
                if coords:
                    visited.append([coords["x"], coords["y"]])
    logger.debug(f"Visited nodes: {visited}")
    return visited


def get_node_by_coords(x, y, nodes):
    """Safely retrieves a node from a given node list."""
    logger.debug(f"Getting node by coords: x={x}, y={y}")
    if nodes and 0 <= y < len(nodes) and 0 <= x < len(nodes[y]):
        node = nodes[y][x]
        logger.debug(f"Node found at ({x},{y}): {bool(node)}")
        return node
    logger.warning(f"Node not found at ({x},{y})")
    return None


def mark_node_visited(nodes, x, y):
    logger.debug(f"Marking node visited at ({x},{y})")
    node = nodes[y][x]
    if node:
        node.setdefault("gameplay", {})["visited"] = True
        logger.info(f"Node at ({x},{y}) marked as visited")
    else:
        logger.warning(f"Cannot mark node visited at ({x},{y}): node is None")


def get_surrounding_context(target_coords, all_nodes):
    """
    Gathers a structured, concise summary of the terrain in rings around a target coordinate.
    """
    target_x, target_y = target_coords
    logger.debug(f"Getting surrounding context for coords: {target_coords}")
    context = { "ring1": [] }

    # Define the search radius for 3 rings
    radius = 1 
    for y_offset in range(-radius, radius + 1):
        for x_offset in range(-radius, radius + 1):
            if x_offset == 0 and y_offset == 0:
                continue # Skip the target node itself

            check_x, check_y = target_x + x_offset, target_y + y_offset
            
            node = get_node_by_coords(check_x, check_y, all_nodes)
            if not node:
                continue

            # Determine which ring the node is in using Chebyshev distance (max of x/y offset)
            distance = max(abs(x_offset), abs(y_offset))
            
            terrain_label = node.get("terrain", {}).get("label", "Unknown")
            
            if distance == 1:
                # Ring 1: Most detail
                context["ring1"].append(f"{terrain_label} (elev: {node.get('terrain', {}).get('elevation', 0):.2f})")
            # elif distance == 2:
                # Ring 2: Less detail
            #     context["ring2"].append(terrain_label)

    # To make it even more efficient, summarize the lists
    summary_text = ""
    if context["ring1"]:
        summary_text += f"Immediate surroundings (Ring 1): {', '.join(sorted(list(set(context['ring1']))))}. "
    # if context["ring2"]:
    #     summary_text += f"Further out (Ring 2): Mainly {', '.join(sorted(list(set(context['ring2']))))}. "
    # if context["ring3"]:
    #     summary_text += f"On the distant horizon (Ring 3): Glimpses of {', '.join(sorted(list(set(context['ring3']))))}."
        
    logger.debug(f"Surrounding context summary: {summary_text.strip()}")
    return summary_text.strip()

def get_immediate_surrounding_context(target_coords, all_nodes):
    """
    Gathers a concise summary of the terrain for the 8 immediate neighbors.
    """
    target_x, target_y = target_coords
    logger.debug(f"Getting immediate surrounding context for coords: {target_coords}")
    neighbor_terrains = []

    # Loop through the 3x3 grid centered on the target
    for y_offset in range(-1, 2):
        for x_offset in range(-1, 2):
            if x_offset == 0 and y_offset == 0:
                continue # Skip the target node itself

            node = get_node_by_coords(target_x + x_offset, target_y + y_offset, all_nodes)
            if node:
                terrain = node.get("terrain", {})
                label = terrain.get("label", "")
                desc = terrain.get("description", "")
                terrain_label = f"{label} - {desc}" if label and desc else label or desc
                neighbor_terrains.append(terrain_label)

    if not neighbor_terrains:
        logger.warning("No immediate neighbors found.")
        return "The immediate surroundings are undefined."

    # Create a summarized string, e.g., "Mainly Grassland, with some Highlands."
    from collections import Counter
    terrain_counts = Counter(neighbor_terrains)
    summary = ", ".join([f"{count}x {label}" for label, count in terrain_counts.items()])
    logger.debug(f"Immediate area summary: {summary}")
    return f"The immediate area consists of: {summary}."


def get_exits_string(node_data: dict) -> str:
    """Takes a node object and returns a formatted string of its exits."""
    logger.debug("Getting exits string")
    if not node_data or "connections" not in node_data:
        logger.warning("No connections found in node_data")
        return "none"
    
    # Mapping of direction keys to full names
    dir_names = {
        "N": "north", "S": "south", "E": "east", "W": "west",
        "NE": "northeast", "NW": "northwest", "SE": "southeast", "SW": "southwest"
    }
    
    # Create a list of the full direction names from the keys in the connections dictionary
    exits = [dir_names.get(k, k) for k in node_data["connections"].keys()]
    
    logger.debug(f"Exits found: {exits}")
    return ", ".join(sorted(exits)) if exits else "none"



def get_event_summary(user_message, assistant_message, settings):
    """
    Uses an LLM to determine if a major event occurred and returns a concise summary.
    If no significant event happened, it returns None.
    """
    logger.debug("Getting event summary from LLM")
    
    # Add extensive logging
    print("=" * 80)
    print("EVENT SUMMARY LLM CALL - DETAILED LOGGING")
    print("=" * 80)
    print(f"USER MESSAGE: '{user_message}'")
    print(f"ASSISTANT MESSAGE: '{assistant_message}'")
    print(f"USER MESSAGE LENGTH: {len(user_message) if user_message else 0}")
    print(f"ASSISTANT MESSAGE LENGTH: {len(assistant_message) if assistant_message else 0}")
    
    # This is a great place to use a smaller, faster model.
    # The logic below attempts to use your configured "support_llm" first.
    provider_settings = settings.get('support_llm', {})
    if not provider_settings.get('provider'):
        provider_settings = settings # Fallback to main settings

    provider = provider_settings.get('llm_provider') or settings.get('llm_provider')
    
    print(f"PROVIDER BEING USED: {provider}")
    print(f"PROVIDER SETTINGS: {provider_settings}")
    
    # Enhanced prompt for better event detection
    chronicler_prompt = f"""
Your job: Mandatory environmental change report.
If characters change ANYTHING significant permanently in area, give succinct, one-line report of what changed.
Be direct. Be short. No fluff.
Examples:
– “Stone altar chipped.”
– “Ripped backpack left behind.”
– “Injured deer laying on ground.”
– “Fire burned trees.”

If nothing changed, write exactly: "None"

Conversation Turn:
User: {user_message}
Assistant: {assistant_message}

Response:"""

    print("FULL PROMPT BEING SENT TO LLM:")
    print("-" * 40)
    print(chronicler_prompt)
    print("-" * 40)
    
    summary = ""
    try:
        logger.debug(f"Calling LLM provider: {provider}")
        print(f"CALLING LLM PROVIDER: {provider}")
        
        # Reusing the existing LLM handlers to make the API call.
        if provider == 'openai':
            summary = openai.generate_response(chronicler_prompt, [], provider_settings)
        elif provider == 'anthropic':
            summary = anthropic.generate_response(chronicler_prompt, [], provider_settings)
        elif provider == 'gemini':
            summary = gemini.generate_response(chronicler_prompt, [], provider_settings)
        elif provider == 'perplexity':
            response_text = perplexity.generate_response(chronicler_prompt, [], provider_settings)
            summary = response_text
        else:
            print("EVENT SUMMARY IS NOT YET CONFIGURED FOR OLLAMA.")
            logger.debug("Event summary is not yet configured for Ollama.")
            return None

        print(f"RAW LLM RESPONSE: '{summary}'")
        print(f"RAW LLM RESPONSE TYPE: {type(summary)}")
        print(f"RAW LLM RESPONSE LENGTH: {len(summary) if summary else 0}")
        
        # Enhanced checking for "None" response
        if summary.strip().lower() in ["none", "no", "nothing"]:
            print(f"NO SIGNIFICANT EVENT DETECTED. Raw response: '{summary}'")
            logger.debug(f"NO SIGNIFICANT EVENT DETECTED. Raw response: '{summary}'")
            return None
        if not summary:
            print("WORLD CHRONICLER RETURNED EMPTY RESPONSE!!!!")
            logger.debug("WORLD CHRONICLER RETURNED EMPTY RESPONSE!!!!")
            return None
            
        print(f"EVENT DETECTED: '{summary.strip()}'")
        logger.debug(f"Event detected: '{summary.strip()}'")
        print("=" * 80)
        return summary.strip()

    except Exception as e:
        print(f"WORLD CHRONICLER EVENT SUMMARY FAILED: {e}")
        logger.error(f"World Chronicler event summary failed: {e}")
        print("=" * 80)
        return None
    

def rewrite_node_description(original_description, event_summary, target_coords, all_nodes, settings, word_limit=60):
    """
    Uses an LLM to rewrite a location description to incorporate a new event,
    using a single ring of surrounding context.
    """
    logger.debug(f"Rewriting node description at {target_coords} with event: {event_summary}")
    provider = settings.get('llm_provider')

    # 1. Get the context from the single surrounding ring.
    surrounding_context = get_immediate_surrounding_context(target_coords, all_nodes)

    # 2. Build the new, more context-aware prompt.
    editor_prompt = f"""
**Master storyteller & concise world editor** → spatial desc & clutter detail expert
**Task:** rewrite location desc → reflect new event, maintain consistency w/ cardinal/ordinal direction surroundings
**Rules:**
1. Rewrite ≈ identical to orig + small new event spatial effects
2. Preserve and grow important orig details, spatial detail, (incl clutter) ∵ no conflict w/ new event changes
3. Changes = objective, non-biased, no commentary/titles
4. Final desc < {word_limit} words, warm comfortable GoT spatial style

Surrounding Environment Context:
{surrounding_context}

Original Description of the Location:
"{original_description}"

New Event to Incorporate:
"{event_summary}"

Instructions:
1. If a user or other character sets fire to an area, you must REWRITE the area to reflect that it has been completely burned down.

"""
    
    try:
        logger.debug(f"Calling LLM provider for rewrite: {provider}")
        # Reusing the existing LLM handlers to make the API call.
        if provider == 'openai':
            rewritten_text = openai.generate_response(editor_prompt, [], settings)
        elif provider == 'anthropic':
            rewritten_text = anthropic.generate_response(editor_prompt, [], settings)
        elif provider == 'gemini':
            rewritten_text = gemini.generate_response(editor_prompt, [], settings)
        elif provider == "perplexity":
            rewritten_text = perplexity.generate_response(editor_prompt, [], settings)
        else:
            logger.debug("Description rewriting is not yet configured for Ollama.")
            return original_description

        logger.debug(f"Rewritten description: {rewritten_text.strip() if rewritten_text else '[empty]'}")
        return rewritten_text.strip() if rewritten_text else original_description

    except Exception as e:
        logger.error(f"World Editor rewrite failed: {e}")
        return original_description
    

def process_update_queue_background(app_context, update_queue, chat_id, settings, all_nodes):
    """
    This function runs in a separate thread to process the node description updates
    without blocking the main chat response.
    """
    logger.debug(f"[BG Thread] Entered process_update_queue_background for chat_id={chat_id}")
    with app_context:
        logger.debug(f"[BG Thread] Starting background processing for {len(update_queue)} tasks.")
        
        # This is the exact same logic from your chat() function
        for task in update_queue:
            task_coords = task["coords_to_update"]
            task_context = task["context"]
            logger.debug(f"[BG Thread] Processing update for coords: {task_coords}")
            
            event_summary = get_event_summary(task_context["user"], task_context["assistant"], settings)
            if event_summary:
                logger.debug(f"[BG Thread] Event summary for {task_coords}: {event_summary}")
                node_to_update = get_node_by_coords(task_coords[0], task_coords[1], all_nodes)
                if node_to_update:
                    original_desc = node_to_update.get('description_base', '')
                    new_desc = rewrite_node_description(
                        original_desc, 
                        event_summary, 
                        task_coords,
                        all_nodes,
                        settings
                    )
                    node_to_update['description_base'] = new_desc
                    logger.debug(f"[BG Thread] Node {task_coords} description updated.")
                else:
                    logger.warning(f"[BG Thread] Node to update not found at {task_coords}")
            else:
                logger.debug(f"[BG Thread] No significant event for {task_coords}")

        # After processing all tasks, save the node file ONCE.
        if update_queue: # Only save if there were tasks to process
            save_chat_nodes(chat_id, all_nodes)
            logger.debug(f"[BG Thread] Background processing finished. Node file saved.")
        else:
            logger.debug(f"[BG Thread] No tasks to process for chat_id={chat_id}")


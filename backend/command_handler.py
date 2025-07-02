import re
import logging
from . import world_state_manager as wsm

logger = logging.getLogger(__name__)

def process_user_command(user_message: str, current_coords: list, chat_nodes: list) -> dict:
    """
    Parses the user's input for commands that must be processed BEFORE the LLM call.

    Args:
        user_message (str): The raw input from the user.
        current_coords (list): The player's current [x, y] coordinates.
        chat_nodes (list): The world map data for the current chat.

    Returns:
        A dictionary containing results, e.g.:
        {'new_coords': [x, y], 'look_result': "You see...", 'user_moved': True}
    """
    cleaned_message = user_message 
    result = {
        "new_coords": list(current_coords),
        "look_result": None,
        "user_moved": False,
        "cleaned_message": cleaned_message # FIX: Add this to the return dict
    }
    
    current_node_data = wsm.get_node_by_coords(current_coords[0], current_coords[1], chat_nodes)
    if not current_node_data or "connections" not in current_node_data:
        return result

    # --- @LOOK command processing ---
    look_match = re.search(r'@LOOK(?::\s*|\s+)(northeast|northwest|southeast|southwest|north|south|east|west|here)\b', user_message, re.IGNORECASE)
    # A separate regex for a bare @LOOK
    bare_look_match = re.search(r'@LOOK\b\s*$', user_message, re.IGNORECASE)
    if look_match or bare_look_match:
        match_to_strip = look_match or bare_look_match
        result['cleaned_message'] = user_message.replace(match_to_strip.group(0), "").strip()
        look_direction_str = (look_match.group(1) or 'here').strip().upper()

        if look_match and look_match.group(1):
            look_direction_str = look_match.group(1).strip().upper()
        else: # This handles bare @LOOK and @LOOK: here
            look_direction_str = 'HERE'
        
        if look_direction_str == 'HERE':
            look_node = current_node_data
            result['look_result'] = look_node.get('description_base', 'You are in an undefined space.')
        else:
            dir_map = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
            move_key = dir_map.get(look_direction_str)
            if move_key and move_key in current_node_data["connections"]:
                look_coords = current_node_data["connections"][move_key]
                look_node = wsm.get_node_by_coords(look_coords[0], look_coords[1], chat_nodes)
                if look_node:
                    desc = look_node.get("description_base", "")
                    first_sentence = desc.split(".")[0] + "." if "." in desc else desc
                    result['look_result'] = f"You peek {look_direction_str.lower()} and see... {first_sentence}"
        
        # Add exits to the look result
        if result['look_result'] and look_node and "connections" in look_node:
            dir_names = {"N": "north", "S": "south", "E": "east", "W": "west", "NE": "northeast", "NW": "northwest", "SE": "southeast", "SW": "southwest"}
            exits = [dir_names.get(k, k) for k in look_node["connections"]]
            exits_str = ", ".join(exits) if exits else "none"
            result['look_result'] += f" [Exits: {exits_str}]"
            
        return result # Return immediately after a successful @LOOK command

    # --- Simple "go" command processing ---
    user_move_direction = ""
    if "go east" in user_message.lower(): user_move_direction = "E"
    elif "go west" in user_message.lower(): user_move_direction = "W"
    elif "go north" in user_message.lower(): user_move_direction = "N"
    elif "go south" in user_message.lower(): user_move_direction = "S"
    elif "go northeast" in user_message.lower(): user_move_direction = "NE"
    elif "go northwest" in user_message.lower(): user_move_direction = "NW"
    elif "go southeast" in user_message.lower(): user_move_direction = "SE"
    elif "go southwest" in user_message.lower(): user_move_direction = "SW"
    # (add other directions: north, south, ne, nw, se, sw)
    
    if user_move_direction and user_move_direction in current_node_data["connections"]:
        result['new_coords'] = current_node_data["connections"][user_move_direction]
        result['user_moved'] = True
        logger.debug(f"User movement detected via 'go' command: {user_move_direction} to {result['new_coords']}")

    return result

def process_llm_response_command(response_text: str, current_coords: list, chat_nodes: list) -> tuple[str, list, bool]:
    """
    Parses the LLM's response for @MOVE and @LOOK commands.

    Args:
        response_text (str): The raw text from the LLM.
        current_coords (list): The player's current [x, y] coordinates.
        chat_nodes (list): The world map data.

    Returns:
        A tuple: (cleaned_response_text, new_coords, llm_used_look)
    """
    new_coords = list(current_coords)
    llm_used_look = False
    
    # Check for @LOOK command first
    look_match = re.search(r'@LOOK\b', response_text, re.IGNORECASE)
    if look_match:
        llm_used_look = True
        # Remove the @LOOK command from the response
        response_text = response_text.replace(look_match.group(0), "").strip()
        logger.debug("LLM used @LOOK command")

    move_match = re.search(r'@MOVE:\s*(northeast|northwest|southeast|southwest|north|south|east|west)', response_text, re.IGNORECASE)

    if not move_match:
        return response_text, new_coords, llm_used_look

    cleaned_text = response_text.replace(move_match.group(0), "").strip()
    move_direction_str = move_match.group(1).strip().upper()
    
    current_node_data = wsm.get_node_by_coords(current_coords[0], current_coords[1], chat_nodes)
    if current_node_data and "connections" in current_node_data:
        dir_map = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
        move_key = dir_map.get(move_direction_str)
        
        if move_key and move_key in current_node_data["connections"]:
            new_coords = current_node_data["connections"][move_key]
            logger.debug(f"LLM movement command processed. New coords: {new_coords}")
            
            # Add movement indication to the response text
            direction_name = move_direction_str.lower().replace("northeast", "northeast").replace("northwest", "northwest").replace("southeast", "southeast").replace("southwest", "southwest")
            cleaned_text += f" *[Moving {direction_name}]*"
        else:
            # Invalid move attempt - add indication
            direction_name = move_direction_str.lower()
            cleaned_text += f" *[Attempted to move {direction_name}, but couldn't]*"
    
    return cleaned_text, new_coords, llm_used_look
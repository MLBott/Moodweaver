from flask import Flask, request, jsonify, send_from_directory, render_template, session
from flask_cors import CORS
import json
import os
import time
import logging
import spacy
import re

nlp = spacy.load("en_core_web_sm")

PLANT_TERMS = {
    "apple", "apples", "aquatic plant", "aquatic plants", "ash", "ashes", "aster", "asters",
    "azalea", "azaleas", "bamboo", "bamboos", "bark", "barks", "basil", "beech", "beeches",
    "begonia", "begonias", "birch", "birches", "blade", "blades", "bloom", "blooms", "blossom",
    "blossoms", "bluebell", "bluebells", "bramble", "brambles", "branch", "branches", "bush", "bushes",
    "buttercup", "buttercups", "carnation", "carnations", "cedar", "cedars", "cherry",
    "cherries", "chestnut", "chestnuts", "chrysanthemum", "chrysanthemums", "clover",
    "clovers", "conifer", "conifers", "cosmos", "cranesbill", "cranesbills", "cypress",
    "cypresses", "daffodil", "daffodils", "daisy", "daisies", "dandelion", "dandelions",
    "dogwood", "dogwoods", "elm", "elms", "eucalyptus", "eucalypti", "eucalyptuses",
    "evergreen", "evergreens", "fern", "ferns", "fir", "firs", "flax", "flora", "floras",
    "flower", "flowers", "foliage", "forest", "forests", "frond", "fronds", "fungi", "fungus",
    "garden", "gardenia", "gardenias", "gardens", "geranium", "geraniums", "gnarled branch",
    "gnarled branches", "goldenrod", "goldenrods", "gorse", "grass", "grasses", "hawthorn",
    "hawthorns", "heather", "heathers", "herb", "herbs", "hibiscus", "hibiscuses", "hickory",
    "hickories", "honeysuckle", "honeysuckles", "humus", "hyacinth", "hyacinths", "impatiens",
    "ivy", "ivies", "jasmine", "jasmines", "juniper", "junipers", "lawn", "lawns", "leaf",
    "leaves", "lichen", "lichens", "lilies", "lily", "loam", "magnolia", "magnolias", "maple",
    "maples", "marigold", "marigolds", "meadow", "meadows", "mint", "mints", "moss", "mosses",
    "mushroom", "mushrooms", "mycelia", "mycelium", "native", "natives", "oak", "oaks",
    "orchid", "orchids", "palm", "palms", "pansies", "pansy", "peonies", "peony", "pennyroyal",
    "pennyroyals", "petal", "petals", "petunia", "petunias", "pine", "pines", "plant", "plants",
    "poplar", "poplars", "poppies", "poppy", "puffball", "puffballs", "redwood", "redwoods",
    "reed", "reeds", "rhododendron", "rhododendrons", "root", "roots", "rose", "roses",
    "sagebrush", "sap", "sapling", "saplings", "sea oat", "sea oats", "seed", "seed pod",
    "seed pods", "seeds", "shrub", "shrubs", "spruce", "spruces", "sunflower", "sunflowers",
    "sycamore", "sycamores", "thicket", "thickets", "thistle", "thistles", "toadflax",
    "toadflaxes", "toadstool", "toadstools", "topsoil", "tree", "trees", "trunk", "trunks",
    "tuft", "tufts", "tulip", "tulips", "underbrush", "undergrowth", "vegetation", "vine",
    "vines", "violet", "violets", "walnut", "walnuts", "water lilies", "water lily", "weed",
    "weeds", "wildflower", "wildflowers", "willow", "willows", "zinnia", "zinnias"
}

WATER_TERMS = {
    "bay", "bays", "brook", "brooks", "channel", "channels", "cove", "coves",
    "creek", "creeks", "current", "currents", "delta", "deltas", "deluge", "dew", "downpour",
    "downpours", "drizzle", "drop", "droplet", "droplets", "drops", "estuary",
    "estuaries", "flood", "floods", "foam", "fog", "froth", "geyser", "geysers",
    "gulf", "gulfs", "inlet", "inlets", "lagoon", "lagoons", "lake", "lakes", "marsh",
    "marshes", "mist", "moat", "moats", "moisture", "ocean", "oceans", "pond", "ponds", "pool",
    "pools", "puddle", "puddles", "rain", "raindrop", "raindrops", "rains", "rapids",
    "reservoir", "reservoirs", "ripple", "ripples", "river", "rivers", "rivulet", "rivulets", "sea", "seas",
    "splash", "splashes", "spray", "sprays", "spring", "springs", "stream", "streams",
    "surf", "swamp", "swamps", "sweat", "swell", "swells", "tear", "tears", "tide", "tides",
    "vapor", "water", "waterfall", "waterfalls", "wave", "waves", "well", "wells"
}

TIME_DAY = {
    "afternoon", "afternoons", "dawn", "dawns", "daybreak", "daylight", "daytime",
    "forenoon", "forenoons", "midday", "morning", "mornings", "noon",
    "ray", "rays", "sun", "sunbeam", "sunbeams", "sunlight", "sunrise", "sunrises",
    "sunshine"
}
TIME_EVENING = {
    "afterglow", "crepuscule", "dusk", "evening", "evenings", "gloaming",
    "sundown", "sunset", "sunsets", "twilight"
}
TIME_NIGHT = {
    "dark", "darkness", "midnight", "moon", "moonbeam", "moonbeams", "moonlight",
    "night", "nightfall", "nights", "shadow", "shadows", "star", "starlight", "stars",
    "witching hour"
}
DIRECTIONS = {"north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"}

def highlight_text(text):
    """
    A robust function to highlight text by separating dialogue from actions,
    avoiding placeholder/tokenization issues.
    """
    # Pattern to find any text enclosed in double quotes (including curly ones)
    dialogue_pattern = r'((["“”])(.*?)(["“”]))'
    result_html = ""
    last_end = 0

    # Use re.finditer to find all dialogue sections
    for match in re.finditer(dialogue_pattern, text, flags=re.DOTALL):
        start, end = match.span()

        # 1. Process the action text that comes BEFORE the dialogue
        action_text_segment = text[last_end:start]
        if action_text_segment:
            result_html += process_action_text(action_text_segment)

        # 2. Wrap the matched dialogue text in its span
        # You could add more complex spacy processing for dialogue here if needed
        dialogue_segment = match.group(1) # group(1) is the full quote with quotes
        result_html += f'<span class="dialogue-text">{dialogue_segment}</span>'

        last_end = end

    # 3. Process any remaining action text after the last piece of dialogue
    remaining_action_text = text[last_end:]
    if remaining_action_text:
        result_html += process_action_text(remaining_action_text)
    
    # If no dialogue was found at all, process the entire text
    if not result_html:
        return process_action_text(text)

    return result_html

# Helper function to contain the spacy logic for non-dialogue text
def process_action_text(text):
    """
    Applies spaCy highlighting to a string of action/narration text.
    """
    doc = nlp(text)
    result = ""
    # This loop contains the highlighting logic from your original function
    for sent in doc.sents:
        first_verb_in_sent = True
        for token in sent:
            word = token.text
            whitespace = token.whitespace_
            cls = None
            if token.pos_ == "VERB" and first_verb_in_sent:
                cls = "hl-verb"
                first_verb_in_sent = False
            elif token.pos_ == "PRON" and word.lower() not in {"it's", "that"}:
                cls = "hl-pronoun"
            elif (token.dep_ in {"nsubj", "attr"} and token.head.pos_ == "VERB" and token.text.lower() in {"said", "asked", "replied", "shouted", "whispered", "muttered"}):
                cls = "hl-dialoguetag"
            elif token.dep_ == "neg" and word.lower() not in {"n't", "n’t"}:
                cls = "hl-negation"
            elif word.lower() in PLANT_TERMS:
                cls = "hl-plant"
            elif word.lower() in WATER_TERMS:
                cls = "hl-water"
            elif word.lower() in TIME_DAY:
                cls = "hl-time-day"
            elif word.lower() in TIME_EVENING:
                cls = "hl-time-evening"
            elif word.lower() in TIME_NIGHT:
                cls = "hl-time-night"
            elif (token.ent_type_ in ["PERSON", "GPE", "ORG", "LOC"] or token.pos_ == "PROPN") and word.lower() not in DIRECTIONS:
                cls = "hl-propernoun"
            elif token.pos_ == "INTJ":
                cls = "hl-interjection"

            if cls:
                result += f'<span class="{cls}">{word}</span>{whitespace}'
            else:
                result += word + whitespace
    return result

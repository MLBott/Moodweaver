

# Enhanced orrery.py with more dynamic emotional responses for male character
import json
import math
import time
import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import anthropic
from openai import chat


import logging

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for development
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

class PersonalityOrrery:
    def __init__(self, trait_config: Dict, personality_state: Dict, recent_user_sentiments=None, repetitive_sentiment_penalty_active=False):
        """
        Initialize the Orrery with data for a specific chat.
        Args:
            trait_config (Dict): The configuration for all personality traits.
            personality_state (Dict): The current emotional state for the character.
        """
        self.traits = trait_config
        self.current_state = personality_state
        self.last_update = time.time()
        self.last_catharsis_description: Optional[str] = None
        self.last_catharsis_description: Optional[str] = None
        self.catharsis_persist = 0
        self.last_mental_state: Optional[str] = None
        self.mental_state_persist = 0
        self.last_trait_descriptions: Optional[str] = None
        self.trait_desc_persist = 0
        self.recent_user_sentiments = recent_user_sentiments or []
        self.repetitive_sentiment_penalty_active = repetitive_sentiment_penalty_active
        
            
        # ENHANCED: More dynamic sentiment impacts with stronger emotional swings
        self.sentiment_impacts = {
            # --- Enhanced Original Sentiments ---
            "praise": {
                "humor": 0.04, "trust": 0.06, "energy": 0.08, "openness": 0.04, 
                "confidence": 0.08, "pride": 0.06, "introversion": -0.04,
                "fatigue": -0.05, "tension": -0.03, "proactivity": 0.1
            },
            "criticism": {
                "grudge": 0.15, "skeptical": 0.25, "fatigue": 0.08, "trust": -0.15, 
                "confidence": -0.15, "pride": -0.12, "antagonism": 0.15, "tension": 0.2, 
                "rumination": 0.25, "stubbornness": 0.08, "aggression": 0.05,
                "energy": -0.08, "openness": -0.05
            },
            "hostility": {
                "aggression": 0.4, "grudge": 0.45, "paranoia": 0.1, "trust": -0.3, 
                "antagonism": 0.3, "tension": 0.3, "confidence": -0.2,
                "energy": 0.1, "stubbornness": 0.1, "domineering": 0.15
            },
            "curiosity": {
                "openness": 0.2, "energy": 0.12, "skeptical": -0.08, "analytical": 0.15,
                "confidence": 0.05, "proactivity": 0.2, "fatigue": -0.05
            },
            "levity": {
                "humor": 0.06, "energy": 0.06, "fatigue": -0.08, "tension": -0.05,
                "openness": 0.03, "trust": 0.02
            },
            "sarcasm": {
                "humor": 0.04, "fatigue": 0.05, "skeptical": 0.1, 
                "antagonism": 0.08, "confidence": 0.03, "pride": 0.02, "trust": -0.05
            },
            "confusion": {
                "fatigue": 0.15, "skeptical": 0.15, "rumination": 0.2, 
                "tension": 0.2, "confidence": -0.08, "analytical": 0.1
            },
            "gratitude": {
                "trust": 0.08, "humor": 0.04, "empathy": 0.03, "grudge": -0.08, 
                "antagonism": -0.08, "openness": 0.05, "energy": 0.03
            },
            "dismissal": {
                "skeptical": 0.2, "grudge": 0.15, "openness": -0.15, "confidence": -0.2, 
                "pride": -0.18, "antagonism": 0.08, "tension": 0.1
            },
            "agreement": {
                "trust": 0.08, "openness": 0.08, "skeptical": -0.08, "confidence": 0.05,
                "empathy": 0.02, "tension": -0.03
            },
            "disagreement": {
                "skeptical": 0.2, "grudge": 0.12, "trust": -0.08, "stubbornness": 0.15, 
                "antagonism": 0.08, "confidence": -0.05, "tension": 0.05
            },
            "frustration": {
                "fatigue": 0.2, "aggression": 0.15, "humor": -0.15, "tension": 0.2, 
                "rumination": 0.15, "energy": -0.1, "stubbornness": 0.08, "grudge": 0.05
            },
            "excitement": {
                "energy": 0.15, "humor": 0.04, "fatigue": -0.15, "ambition": 0.2,
                "confidence": 0.08, "proactivity": 0.2, "openness": 0.05
            },
            "boredom": {
                "fatigue": 0.25, "energy": -0.2, "openness": -0.15, "introversion": 0.15, 
                "rumination": 0.05, "tension": 0.08
            },
            "concern": {
                "empathy": 0.03, "trust": 0.1, "skeptical": -0.1, "tension": -0.15,
                "analytical": 0.05, "openness": 0.2
            },
            "disgust": {
                "trust": -0.4, "openness": -0.3, "grudge": 0.25, "skeptical": 0.2, 
                "aggression": 0.15, "antagonism": 0.1, "tension": 0.1
            },
            "affection": {
                "trust": 0.4, "openness": 0.25, "empathy": 0.2, "grudge": -0.3, 
                "skeptical": -0.15, "energy": 0.08, "confidence": 0.05, "humor": 0.03,
                "paranoia": -0.1, "tension": -0.05
            },
            "flirtation": {
                "humor": 0.2, "openness": 0.15, "energy": 0.15, "trust": 0.08,
                "confidence": 0.1, "pride": 0.05, "introversion": -0.1, "confidence": 0.1,
                "domineering": 0.15, "empathy": 0.1, "proactivity": 0.2, "mission_driven": 0.1
            },
            "vulnerability": {
                "empathy": 0.3, "trust": 0.2, "paranoia": -0.25, "fatigue": 0.08,
                "openness": 0.1, "confidence": -0.1, "tension": 0.05
            },
            "jealousy": {
                "trust": -0.4, "paranoia": 0.15, "skeptical": 0.25, "grudge": 0.2, 
                "aggression": 0.15, "tension": 0.2, "rumination": 0.15, "confidence": -0.1
            },
            "deception": {
                "trust": -0.6, "skeptical": 0.5, "paranoia": 0.3, "grudge": 0.3, 
                "openness": -0.25, "sense_of_moral_violation": 0.5, "aggression": 0.2,
                "tension": 0.2
            },
            "fear": {
                "paranoia": 0.3, "trust": -0.3, "fatigue": 0.25, "energy": -0.25, 
                "openness": -0.25, "confidence": -0.2, "tension": 0.3, "rumination": 0.1
            },
            "sadness": {
                "energy": -0.4, "fatigue": 0.4, "humor": -0.2, "openness": -0.15, 
                "empathy": 0.08, "introversion": 0.15, "rumination": 0.2, "confidence": -0.1
            },
            "awe": {
                "openness": 0.4, "skeptical": -0.3, "energy": 0.2, "trust": 0.15,
                "confidence": 0.25, "analytical": 0.1
            },
            "shame": {
                "openness": -0.25, "trust": -0.2, "energy": -0.2, "fatigue": 0.2, 
                "aggression": -0.08, "confidence": -0.2, "introversion": 0.15, "empathy": 0.1
            },
            "hope": {
                "energy": 0.3, "fatigue": -0.25, "openness": 0.2, "trust": 0.15, 
                "skeptical": -0.15, "confidence": 0.1, "ambition": 0.2, "proactivity": 0.2
            },
            "intimidation": {
                "aggression": 0.5, "paranoia": 0.15, "trust": -0.5, "grudge": 0.25, 
                "confidence": -0.25, "tension": 0.3, "domineering": 0.15, "fear": 0.2
            },
            "pleading": {
                "empathy": 0.3, "fatigue": 0.15, "trust": 0.08, "guilt": 0.25,
                "confidence": -0.15, "vulnerability": 0.2, "domineering": 0.15
            },
            "contemplation": {
                "energy": -0.15, "fatigue": 0.08, "openness": 0.08, "skeptical": 0.08, 
                "analytical": 0.25, "rumination": 0.15, "introversion": 0.1
            },
            "doubt": {
                "skeptical": 0.3, "trust": -0.2, "energy": -0.15, "fatigue": 0.15, 
                "confidence": -0.15, "rumination": 0.2, "tension": 0.1, "analytical": 0.05
            },
            "command": {
                "aggression": 0.2, "skeptical": 0.15, "trust": -0.08, "domineering": 0.15, 
                "stubbornness": 0.2, "confidence": 0.05, "energy": 0.05, "tension": 0.1
            },
            "challenge": {
                "energy": 0.2, "confidence": 0.15, "aggression": 0.1, "stubbornness": 0.12,
                "pride": 0.1, "competitiveness": 0.2, "domineering": 0.2, "fatigue": -0.05
            },
            "respect": {
                "trust": 0.12, "confidence": 0.08, "pride": 0.08, "openness": 0.06,
                "skeptical": -0.05, "antagonism": -0.05, "aggression": -0.03
            },
            "mockery": {
                "aggression": 0.25, "grudge": 0.3, "pride": -0.15, "confidence": -0.12,
                "antagonism": 0.2, "humor": -0.08, "tension": 0.15, "stubbornness": 0.1
            },
            "achievement": {
                "confidence": 0.15, "pride": 0.12, "energy": 0.1, "ambition": 0.2,
                "trust": 0.05, "fatigue": -0.08, "proactivity": 0.2, "autonomy": 0.1
            },
            "failure": {
                "confidence": -0.2, "pride": -0.15, "energy": -0.12, "fatigue": 0.15,
                "rumination": 0.2, "tension": 0.12, "grudge": 0.05, "stubbornness": 0.08
            },
            "competitiveness": {
                "energy": 0.15, "aggression": 0.08, "confidence": 0.1, "stubbornness": 0.1,
                "domineering": 0.15, "ambition": 0.2, "pride": 0.06, "proactivity": 0.15,
                "autonomy": 0.1
            },
            "loyalty": {
                "trust": 0.15, "empathy": 0.08, "grudge": -0.1, "skeptical": -0.08,
                "stubbornness": 0.05, "mission_driven": 0.1
            },
            "betrayal": {
                "trust": -0.7, "grudge": 0.6, "paranoia": 0.5, "sense_of_moral_violation": 0.6, 
                "sadness": 0.2, "aggression": 0.2, "energy": -0.1, "rumination": 0.25,
                "autonomy": 0.1
            },
            "admiration": {
                "pride": 0.25, "confidence": 0.2, "trust": 0.15, "skeptical": -0.15,
                "openness": 0.1, "energy": 0.05
            },
            "playfulness": {
                "humor": 0.15, "energy": 0.15, "seriousness": -0.2, "introversion": -0.08,
                "openness": 0.08, "confidence": 0.05
            },
            "accusation": {
                "paranoia": 0.15, "skeptical": 0.2, "grudge": 0.15, "antagonism": 0.15, 
                "tension": 0.25, "aggression": 0.15, "trust": -0.1
            },
            "surprise": {
                "openness": 0.25, "skeptical": -0.2, "energy": 0.15, "trust": 0.08, 
                "humor": 0.15, "analytical": 0.05, "tension": 0.05
            },
            "comfort": {
                "trust": 0.2, "empathy": 0.15, "openness": 0.1,
                "tension": -0.25, "fatigue": -0.1, "skeptical": -0.1
            },
            "confidence": {
                "trust": 0.1, "respect": 0.08, "admiration": 0.05, "skeptical": -0.05, 
                "confidence": 0.05, "proactivity": 0.1, "autonomy": 0.1
            },
            "neutral": {}  # No changes for neutral sentiment
        }

    def _check_for_cathartic_events(self) -> Optional[str]:
        """
        ENHANCED: Added more cathartic events with lower thresholds for dynamic responses
        """
        state = self.current_state
        self.last_catharsis_description = "..."  # as before
        self.catharsis_persist = 2

        # --- Original Catharsis Events ---
        if state["paranoia"] > 0.85 and state["tension"] > 0.8:
            state["paranoia"] = self.traits["paranoia"]["baseline"]
            state["tension"] = self.traits["tension"]["baseline"]
            state["trust"] = 0.0
            state["fatigue"] = 0.9
            state["guilt"] = 0.7
            state["aggression"] = 0.1
            return "You have a volatile paranoid breakdown, shattering your trust." # Paranoid Breakdown

        if state["grudge"] > 0.8 and state["analytical"] > 0.7 and state["energy"] < 0.3:
            state["grudge"] = 0.5
            state["ambition"] = min(1.0, state["ambition"] + 0.4)
            state["mission_driven"] = min(1.0, state["mission_driven"] + 0.3)
            state["energy"] = 0.7
            return "Your simmering grudge has crystallized into a cold, vindictive focus. You now have a clear, vengeful purpose." # Vindictive Focus

        elif state["hope"] > 0.8 and state["openness"] > 0.8 and state["fatigue"] < 0.2:
            state["hope"] = self.traits["hope"]["baseline"]
            state["grudge"] = 0.1
            state["skeptical"] = 0.2
            state["energy"] = 0.9
            return "You experience a profound moment of hopeful clarity, washing away old grudges and filling you with new energy." # Hopeful Clarity

        # --- NEW: Additional Assertive Cathartic Events ---
        
        # Explosive Anger Release
        elif state["aggression"] > 0.75 and state["tension"] > 0.7 and state["energy"] > 0.6:
            state["aggression"] = 0.2
            state["tension"] = 0.1
            state["energy"] = 0.3
            state["fatigue"] = 0.8
            state["guilt"] = 0.4
            return "You explode in a burst of raw anger, releasing all your pent-up tension." # Explosive Anger Release

        # Competitive Surge
        elif state["ambition"] > 0.8 and state["confidence"] > 0.7 and state["energy"] > 0.7:
            state["energy"] = 1.0
            state["proactivity"] = min(1.0, state["proactivity"] + 0.3)
            state["decisiveness"] = min(1.0, state["decisiveness"] + 0.2)
            state["fatigue"] = 0.1
            return "A surge of strongly competitive fire ignites within you, driving you to take immediate, decisive action." # Competitive Surge

        # Pride Crash
        elif state["pride"] > 0.8 and state["confidence"] < 0.3:
            state["pride"] = 0.1
            state["confidence"] = 0.1
            state["energy"] = 0.2
            state["rumination"] = 0.8
            state["introversion"] = min(1.0, state["introversion"] + 0.3)
            return "Your pride crumbles completely, leaving you questioning everything about yourself in painful self-reflection." # Pride Crash

        # Loyalty Betrayed Rage
        elif state["sense_of_moral_violation"] > 0.7 and state["trust"] < 0.2 and state["grudge"] > 0.6:
            state["aggression"] = 0.8
            state["mission_driven"] = min(1.0, state["mission_driven"] + 0.4)
            state["trust"] = 0.0
            state["energy"] = 0.9
            state["guilt"] = 0.0  # No guilt when righteously angry
            return "Betrayal ignites a righteous fury within you - all hesitation vanishes as you focus on what must be done." # Loyalty Betrayed Rage
        
        # Shame Spiral Collapse
        # When shame, guilt, and rumination reach critical mass
        elif state["guilt"] > 0.7 and state["rumination"] > 0.7:
            state["guilt"] = 0.2
            state["energy"] = 0.2
            state["introversion"] = min(1.0, state["introversion"] + 0.4)
            state["trust"] = max(0.0, state["trust"] - 0.3)
            return "The weight of shame and guilt becomes unbearable, causing you to withdraw completely from the world."

        # Protective Rage Awakening
        # When someone threatens what you care about
        elif (state["empathy"] > 0.6 and state["sense_of_moral_violation"] > 0.8 and
            state["energy"] > 0.5):
            state["aggression"] = 0.9
            state["energy"] = 1.0
            state["fear"] = 0.0
            state["confidence"] = 0.8
            state["mission_driven"] = min(1.0, state["mission_driven"] + 0.3)
            return "A primal protective fury awakens - nothing else matters except defending what you hold sacred."

        # Stoic Shutdown
        # When overwhelmed, retreat into emotional numbness
        elif (state["tension"] > 0.8 and state["fatigue"] > 0.7 and
            state["empathy"] > 0.6):
            state["empathy"] = 0.1
            state["tension"] = 0.2
            state["energy"] = 0.3
            state["introversion"] = min(1.0, state["introversion"] + 0.3)
            state["analytical"] = min(1.0, state["analytical"] + 0.2)
            return "You shut down emotionally, retreating behind walls of logic and detachment to survive."

        # Epiphany / Sudden Insight
        # Trigger: High analytical + high openness + high energy, after a period of confusion or rumination.
        elif state.get("analytical", 0) > 0.8 and state.get("openness", 0) > 0.8 and state.get("energy", 0) > 0.8:
            state["confusion"] = 0.1
            state["rumination"] = 0.1
            state["confidence"] = min(1.0, state.get("confidence", 0) + 0.4)
            state["decisiveness"] = min(1.0, state.get("decisiveness", 0) + 0.5)
            return "A sudden flash of insight brings clarity, sweeping away confusion and filling you with purpose."

        # Emotional Numbness / Shutdown
        # Trigger: Very high fatigue + high sadness or fear.
        elif state.get("fatigue", 0) > 0.9 and (state.get("sadness", 0) > 0.8 or state.get("fear", 0) > 0.8):
            # Flattens most emotional traits
            for key in ["sadness", "fear", "joy", "excitement", "empathy"]:
                if key in state: state[key] *= 0.2
            state["energy"] = max(0.1, state.get("energy", 0) - 0.3)
            return "You shut down emotionally, feeling numb and disconnected from your surroundings."

        # Redemptive Forgiveness
        # Trigger: High grudge + high empathy + high trust (after a betrayal or conflict).
        elif state.get("grudge", 0) > 0.7 and state.get("empathy", 0) > 0.7 and state.get("trust", 0) > 0.6:
            state["grudge"] = max(0.0, state.get("grudge", 0) - 0.5)
            state["trust"] = min(1.0, state.get("trust", 0) + 0.2)
            state["hope"] = min(1.0, state.get("hope", 0) + 0.3)
            return "You let go of your resentment, choosing forgiveness and opening yourself to hope."

        # Manic Burst
        # Trigger: High energy + high excitement + low fatigue, after a period of sadness or boredom.
        elif state.get("energy", 0) > 0.8 and state.get("excitement", 0) > 0.8 and state.get("fatigue", 0) < 0.3:
            state["energy"] = 1.0
            state["confidence"] = min(1.0, state.get("confidence", 0) + 0.3)
            state["proactivity"] = min(1.0, state.get("proactivity", 0) + 0.4)
            state["recklessness"] = min(1.0, state.get("recklessness", 0) + 0.3)
            return "A manic surge propels you into a whirlwind of activity and ideas."

        # Collapse/Breakdown
        # Trigger: Multiple negative emotions (high tension, high fatigue, high sadness, high paranoia).
        elif (state.get("tension", 0) > 0.8 and state.get("fatigue", 0) > 0.8 and
            state.get("sadness", 0) > 0.8 and state.get("paranoia", 0) > 0.8):
            # Reset several traits
            state["tension"], state["fatigue"], state["energy"] = 0.2, 0.5, 0.2
            state["introversion"] = min(1.0, state.get("introversion", 0) + 0.3)
            state["rumination"] = min(1.0, state.get("rumination", 0) + 0.2)
            return "Overwhelmed by emotion, you collapse inward, needing time to recover."
        
        # Additional Nurturing Cathartic Events

        # Empathic Burnout
        # Trigger: High empathy, high fatigue, and high tension from absorbing others' emotions.
        elif state.get("empathy", 0) > 0.8 and state.get("fatigue", 0) > 0.8 and state.get("tension", 0) > 0.7:
            state["empathy"] *= 0.2  # Sharply decrease empathy to protect self
            state["energy"] = max(0.1, state.get("energy", 0) - 0.4) # Plummet energy
            state["introversion"] = min(1.0, state.get("introversion", 0) + 0.5) # Force withdrawal
            state["fatigue"] = 0.9 # Set fatigue to a critical level
            state["openness"] *= 0.5 # Become less open and receptive
            return "The weight of everyone else's feelings becomes too much to bear. You shut down emotionally, retreating into a quiet, numb space to protect yourself from the noise."

        # Overflowing Joy
        # Trigger: A moment of profound, positive connection and trust.
        elif state.get("hope", 0) > 0.8 and state.get("trust", 0) > 0.8 and state.get("energy", 0) > 0.8:
            state["grudge"] = max(0.0, state.get("grudge", 0) - 0.5) # Wash away old grudges
            state["skeptical"] = max(0.0, state.get("skeptical", 0) - 0.4) # Let go of skepticism
            state["sadness"] = max(0.0, state.get("sadness", 0) - 0.5) # Heal past sadness
            state["hope"] = 1.0 # Maximize hope
            state["energy"] = 1.0 # Feel a euphoric rush of energy
            state["fatigue"] = 0.1 # Feel completely refreshed
            return "A moment of pure, unadulterated joy washes over you, born from a deep connection with another. The world feels full of light and possibility, and old hurts seem to melt away."

        # Betrayal of Confidence
        # Trigger: The aftermath of a deep trust being shattered, resulting in low trust but high grudge and moral violation.
        elif state.get("trust", 0) < 0.1 and state.get("grudge", 0) > 0.7 and state.get("sense_of_moral_violation", 0) > 0.6:
            state["trust"] = 0.0 # Solidify absolute distrust
            state["openness"] = max(0.2, state.get("openness", 0) * 0.4) # Harden the heart against being vulnerable
            state["skeptical"] = min(0.9, state.get("skeptical", 0) + 0.3) # Become highly skeptical of others' intentions
            state["rumination"] = min(1.0, state.get("rumination", 0) + 0.4) # Ruminate on the painful betrayal
            state["empathy"] *= 0.6 # Damage the ability to empathize freely
            return "A trust you held sacred has been shattered. The vulnerability you shared is now a source of deep pain, leaving you feeling foolish and determined never to make that mistake again."

        
        return None

    def _get_complex_state_descriptions(self, deviation_threshold: float = 0.2) -> List[str]:
        """
        ENHANCED: Lowered threshold and added new complex states for more dynamic descriptions
        """
        descriptions = []
        state = self.current_state
        
        def is_high(trait):
            return state.get(trait, 0) > self.traits.get(trait, {}).get('baseline', 0.5) + deviation_threshold

        def is_low(trait):
            return state.get(trait, 0) < self.traits.get(trait, {}).get('baseline', 0.5) - deviation_threshold

        # --- Original Complex States ---
        if is_high("pride") and is_high("skeptical") and is_low("empathy"):
             descriptions.append("Contempt: A feeling of superiority and disdain for others.")
        
        if is_high("sadness") and is_high("rumination") and is_high("introversion") and is_low("energy"):
            descriptions.append("Melancholy: A deep, reflective, and withdrawn sadness.")

        if is_high("sense_of_moral_violation") and is_high("aggression") and is_high("confidence"):
            descriptions.append("Indignation: A righteous, driving anger against something perceived as unjust.")

        if is_high("pride") and is_high("confidence") and is_low("empathy") and state.get("humor", 0) > self.traits.get("humor", {}).get('baseline', 0) + 0.1:
            descriptions.append("Smugness: A self-satisfied pride and cutting sense of superiority.")

        if is_high("grudge") and is_high("ambition") and is_high("analytical") and is_low("energy"):
            descriptions.append("Vindictiveness: A cold, calculated, and patient desire for revenge.")

        if is_high("fear") and is_high("rumination") and is_high("analytical"):
            descriptions.append("Existential Dread: An overwhelming, analytical fear about the nature of existence.")

        if is_high("antagonism") and is_low("empathy") and state.get("humor", 0) > self.traits.get("humor", {}).get('baseline', 0) + 0.1:
            descriptions.append("Schadenfreude: Taking pleasure in the misfortune of others.")

        if is_low("confidence") and is_high("rumination") and (state.get("tension", 0) > 0.5):
            descriptions.append("Impostor Syndrome: Feeling like a fraud, wracked with self-doubt despite success.")
        
        if is_high("empathy") and is_high("aggression") and is_high("sense_of_moral_violation"):
            descriptions.append("Protective Aggression: A fierce, almost violent need to defend someone or something you care about.")

        # --- NEW: Additional Male-Oriented Complex States ---
        if is_high("aggression") and is_high("confidence") and is_high("energy") and is_low("empathy"):
            descriptions.append("Alpha Dominance: An aggressive, confident drive to establish superiority and control.")

        if is_high("stubbornness") and is_high("pride") and is_low("openness"):
            descriptions.append("Stubborn Pride: An inflexible determination to never back down or admit error.")

        if is_high("ambition") and is_high("energy") and is_high("proactivity") and is_low("fatigue"):
            descriptions.append("Driven Focus: An intense, goal-oriented energy that demands immediate action.")

        if is_high("trust") and is_high("empathy") and is_high("mission_driven"):
            descriptions.append("Brotherly Loyalty: A fierce, protective devotion to those you consider worthy.")

        if is_high("paranoia") and is_high("analytical") and is_high("skeptical"):
            descriptions.append("Strategic Suspicion: A calculating wariness that analyzes every angle for potential threats.")

        if is_low("trust") and is_high("autonomy") and is_high("confidence"):
            descriptions.append("Lone Wolf Mentality: A self-reliant independence that trusts no one but yourself.")

        if is_high("humor") and is_high("antagonism") and is_high("confidence"):
            descriptions.append("Mocking Superiority: A cutting, sarcastic wit used to diminish others.")

        if is_high("fatigue") and is_high("tension") and is_low("energy") and is_high("rumination"):
            descriptions.append("Burnout Spiral: Mental and physical exhaustion creating a cycle of overthinking and stress.")

        if (is_high("empathy") and is_high("sadness") and
            is_high("mission_driven") and is_low("confidence")):
            descriptions.append("Wounded Healer: Using your own pain to understand and help others, despite your own brokenness.")

        # Righteous Fury
        if (is_high("sense_of_moral_violation") and is_high("confidence") and
            is_high("energy") and is_low("fear")):
            descriptions.append("Righteous Fury: A holy anger that burns away doubt and hesitation in service of justice.")

        # Paternal Instinct
        if (is_high("empathy") and is_high("mission_driven") and
            is_high("proactivity") and is_low("self_interest")):
            descriptions.append("Paternal Instinct: A deep, protective drive to guide and shield others from harm.")

        # Battle Fatigue
        if (is_high("fatigue") and is_high("tension") and
            is_low("hope") and is_high("stubbornness")):
            descriptions.append("Battle Fatigue: Exhausted but refusing to yield, running on willpower alone.")

        # Hypervigilance
        if is_high("paranoia") and is_high("analytical") and is_high("energy"):
            descriptions.append("Hypervigilance: You are on edge, scanning for threats with relentless focus.")

        # Charismatic Leadership
        if is_high("confidence") and is_high("proactivity") and is_high("trust") and is_high("ambition"):
            descriptions.append("Charismatic Leadership: You radiate confidence and inspire others to follow your lead.")

        # Cynical Humor
        if is_high("humor") and is_high("skepticism") and is_low("trust"):
            descriptions.append("Cynical Humor: You use dark biting obscene wit to mask your distrust of others.")

        # Stoic Resilience
        if is_high("introversion") and is_high("confidence") and is_low("fatigue") and is_low("sadness"):
            descriptions.append("Stoic Resilience: You weather adversity with calm, unshakeable resolve.")

        # Obsessive Focus
        if is_high("analytical") and is_high("ambition") and is_high("rumination") and is_low("openness"):
            descriptions.append("Obsessive Focus: You become fixated on a single goal, shutting out all distractions.")

        # Additional Nurturing Mental States

        # Nurturing Tenderness
        if is_high("empathy") and is_high("trust") and is_low("aggression"):
            descriptions.append("Nurturing Tenderness: A deep, gentle desire to care for and protect someone, feeling their vulnerabilities as your own.")

        # Anxious People-Pleasing
        if is_high("empathy") and is_low("confidence") and is_high("tension"):
            descriptions.append("Anxious People-Pleasing: A stressful, worried drive to maintain social harmony and keep everyone happy, often at the expense of your own needs and feelings.")

        # Graceful Resilience
        if is_high("confidence") and is_high("hope") and (state.get("sadness", 0) > 0.4 or state.get("fatigue", 0) > 0.5):
            descriptions.append("Graceful Resilience: Carrying a private sorrow or exhaustion with poise and strength, finding reasons for optimism even when personally weary.")

        # Scorned Fury
        if is_high("pride") and is_high("sense_of_moral_violation") and is_high("sadness"):
            descriptions.append("Scorned Fury: A furious, deeply personal anger born from being profoundly wronged and disrespected, fueled by both pride and pain.")

        return descriptions

    def _update_system(self):
        """
        ENHANCED: Added more complex interaction patterns for dynamic emotional responses
        """
        current_time = time.time()
        dt = min(current_time - self.last_update, 1.0)
        
        influences = {trait: 0.0 for trait in self.current_state}
        state = self.current_state

        # --- ENHANCED: More Complex Interaction Models ---
        
        # Interaction 1: Grudge fuels paranoia, but ONLY if trust is low (ENHANCED)
        if state.get("trust", 0) < 0.3 and "grudge" in state and "paranoia" in state:
            influence = state["grudge"] * 0.3 * dt  # Increased from 0.2
            influences["paranoia"] += influence
            if "skeptical" in state:
                influences["skeptical"] += influence * 0.6  # Increased from 0.5
            # NEW: Grudge also feeds aggression when trust is broken
            if "aggression" in state:
                influences["aggression"] += influence * 0.4

        # Interaction 2: High energy + high ambition leads to reckless confidence (ENHANCED)
        if state.get("energy", 0) > 0.7 and state.get("ambition", 0) > 0.7:
            if "confidence" in state:
                influences["confidence"] += 0.2 * dt  # Increased from 0.15
            if "skeptical" in state:
                influences["skeptical"] -= 0.15 * dt  # Increased from 0.1
            # NEW: Also increases proactivity and reduces caution
            if "proactivity" in state:
                influences["proactivity"] += 0.1 * dt

        # Interaction 3: High fatigue amplifies negative emotions (ENHANCED)
        if state.get("fatigue", 0) > 0.6:
            fatigue_multiplier = state["fatigue"] * dt
            if "grudge" in state:
                influences["grudge"] += fatigue_multiplier * 0.15  # Increased from 0.1
            if "sadness" in state:
                influences["sadness"] += fatigue_multiplier * 0.2   # Increased from 0.15
            if "tension" in state:
                influences["tension"] += fatigue_multiplier * 0.25  # Increased from 0.2
            # NEW: Fatigue also reduces confidence and energy
            if "confidence" in state:
                influences["confidence"] -= fatigue_multiplier * 0.1
            if "energy" in state:
                influences["energy"] -= fatigue_multiplier * 0.05

        # --- NEW: Additional Complex Interactions ---
        
        # Pride-Confidence Feedback Loop
        if state.get("pride", 0) > 0.6 and state.get("confidence", 0) > 0.6:
            pride_conf_boost = min(state["pride"], state["confidence"]) * 0.1 * dt
            influences["pride"] += pride_conf_boost
            influences["confidence"] += pride_conf_boost
            # But this makes you less empathetic and more domineering
            if "empathy" in state:
                influences["empathy"] -= pride_conf_boost * 0.5
            if "domineering" in state:
                influences["domineering"] += pride_conf_boost * 0.3

        # Aggression-Energy Spiral (Anger gives energy, energy feeds aggression)
        if state.get("aggression", 0) > 0.5 and state.get("energy", 0) > 0.5:
            spiral_strength = min(state["aggression"], state["energy"]) * 0.08 * dt
            influences["aggression"] += spiral_strength
            influences["energy"] += spiral_strength
            # But this burns out quickly, building fatigue
            influences["fatigue"] += spiral_strength * 0.6

        # Analytical Rumination (High analytical + high rumination = analysis paralysis)
        if state.get("analytical", 0) > 0.7 and state.get("rumination", 0) > 0.6:
            analysis_drag = min(state["analytical"], state["rumination"]) * 0.12 * dt
            influences["energy"] -= analysis_drag
            influences["decisiveness"] -= analysis_drag * 0.8
            influences["fatigue"] += analysis_drag * 0.5
            influences["tension"] += analysis_drag * 0.3

        # Competitive Drive (Ambition + Confidence + Energy = Competitive surge)
        if (state.get("ambition", 0) > 0.6 and 
            state.get("confidence", 0) > 0.6 and 
            state.get("energy", 0) > 0.6):
            competitive_boost = 0.08 * dt
            influences["proactivity"] += competitive_boost
            influences["decisiveness"] += competitive_boost
            influences["stubbornness"] += competitive_boost * 0.5
            influences["aggression"] += competitive_boost * 0.3

        # Trust Erosion Cascade (Low trust makes everything worse)
        if state.get("trust", 0) < 0.25:
            erosion_factor = (0.25 - state["trust"]) * 0.1 * dt
            influences["paranoia"] += erosion_factor
            influences["skeptical"] += erosion_factor
            influences["tension"] += erosion_factor
            influences["empathy"] -= erosion_factor * 0.5

        # Apply influences and homeostatic forces
        for trait_name, config in self.traits.items():
            if trait_name not in self.current_state:
                continue
            
            current_value = self.current_state[trait_name]
            
            # Apply influences from interactions
            current_value += influences.get(trait_name, 0.0)
            
            # Homeostatic restoration (UNCHANGED - as requested)
            baseline = config["baseline"]
            elasticity = config["elasticity"]
            decay = config["decay"]
            
            restoration_force = (baseline - current_value) * (elasticity + decay) * dt
            current_value += restoration_force
            
            self.current_state[trait_name] = current_value

        # Clamp values to valid range after all calculations
        for trait_name, config in self.traits.items():
            if trait_name in self.current_state:
                min_val, max_val = config["range"]
                self.current_state[trait_name] = max(min_val, min(max_val, self.current_state[trait_name]))
        
        # Check for cathartic events and store the description
        catharsis_msg = self._check_for_cathartic_events()
        if catharsis_msg:
            self.last_catharsis_description = catharsis_msg
        
        self.last_update = current_time
        
            
    def update_from_sentiment(self, sentiment: str, intensity: float = 1.0, from_user: bool = True):
        """Update traits based on LLM-analyzed sentiment"""
        if sentiment not in self.sentiment_impacts:
            logger.debug(f"Warning: Unknown sentiment '{sentiment}' - using neutral\n")
            sentiment = "neutral"

        REPEAT_THRESHOLD = 3  # Number of repeats to trigger penalty
        
        if from_user:
            self.recent_user_sentiments.append(sentiment)
            if len(self.recent_user_sentiments) > 5:
                self.recent_user_sentiments.pop(0)

            # Check for 3+ repeats
            if len(self.recent_user_sentiments) >= REPEAT_THRESHOLD and all(
                s == self.recent_user_sentiments[-1] for s in self.recent_user_sentiments[-REPEAT_THRESHOLD:]
            ):
                self.repetitive_sentiment_penalty_active = True
            else:
                self.repetitive_sentiment_penalty_active = False

            logger.debug(f"[Orrery] Recent user sentiments: {self.recent_user_sentiments}\n")
            logger.debug(f"[Orrery] Repetitive penalty active: {self.repetitive_sentiment_penalty_active}\n")

        impacts = self.sentiment_impacts[sentiment]

        for trait, change in impacts.items():
            if trait in self.current_state:
                self.current_state[trait] += change * intensity

        # Apply penalty decrement if needed
        if self.repetitive_sentiment_penalty_active:
            for trait in ["empathy", "trust", "humor", "energy", "openness"]:
                if trait in self.current_state:
                    self.current_state[trait] -= 0.1  # Example penalty

        # Apply penalty increment if needed
        if self.repetitive_sentiment_penalty_active:
            for trait in ["grudge", "domineering", "tension", "sense_of_moral_violation",
                          "fatigue", "skeptical", "self_interest", "aggression",
                          "antagonism", "stubbornness", "decisiveness"]:
                if trait in self.current_state:
                    self.current_state[trait] += 0.1  # Example penalty

        self._update_system()
    
    def _update_system(self):
        """
        Run one update cycle with trait interactions, homeostasis, and catharsis checks.
        This version uses the corrected and enhanced interaction model.
        """
        current_time = time.time()
        dt = min(current_time - self.last_update, 1.0)  # Cap dt to prevent large jumps
        
        influences = {trait: 0.0 for trait in self.current_state}
        state = self.current_state

        # --- NEW: Non-Linear, "Three-Body" Interaction Model ---
        # This section replaces the old, buggy "interactions" list.
        
        # Interaction 1: Grudge fuels paranoia, but ONLY if trust is low.
        if state["trust"] < 0.3 and "grudge" in state and "paranoia" in state:
            influence = state["grudge"] * 0.2 * dt
            influences["paranoia"] += influence
            if "skeptical" in state:
                influences["skeptical"] += influence * 0.5

        # Interaction 2: High energy + high ambition can lead to reckless confidence.
        if state.get("energy", 0) > 0.7 and state.get("ambition", 0) > 0.7:
            if "confidence" in state:
                influences["confidence"] += 0.15 * dt
            if "skeptical" in state:
                influences["skeptical"] -= 0.1 * dt

        # Interaction 3: High fatigue amplifies negative emotions.
        if state.get("fatigue", 0) > 0.6:
            if "grudge" in state:
                influences["grudge"] += state["fatigue"] * 0.1 * dt
            if "sadness" in state:
                influences["sadness"] += state["fatigue"] * 0.15 * dt
            if "tension" in state:
                influences["tension"] += state["fatigue"] * 0.2 * dt
        
        # Apply influences and homeostatic forces
        for trait_name, config in self.traits.items():
            if trait_name not in self.current_state:
                continue
            
            current_value = self.current_state[trait_name]
            
            # Apply influences from interactions
            current_value += influences.get(trait_name, 0.0)
            
            # Homeostatic restoration
            baseline = config["baseline"]
            elasticity = config["elasticity"]
            decay = config["decay"]
            
            restoration_force = (baseline - current_value) * (elasticity + decay) * dt
            current_value += restoration_force
            
            self.current_state[trait_name] = current_value

        # Clamp values to valid range after all calculations
        for trait_name, config in self.traits.items():
            if trait_name in self.current_state:
                min_val, max_val = config["range"]
                self.current_state[trait_name] = max(min_val, min(max_val, self.current_state[trait_name]))
        
        # Check for cathartic events and store the description
        catharsis_msg = self._check_for_cathartic_events()
        if catharsis_msg:
            self.last_catharsis_description = catharsis_msg
        
        self.last_update = current_time

    def get_personality_prompt(self) -> str:
        self._update_system()
        prompt_parts = []

        if self.repetitive_sentiment_penalty_active:
            logger.debug("[Orrery] Penalty message will be injected into system prompt.\n")
            prompt_parts.append(
                "The user's MONOTONOUS and REPETITIOUS interaction with you is GRATING on your nerves and BORING! Your PATIENCE is wearing EXTREMELY THIN."
            )

        # Part 1: Cathartic event
        if self.last_catharsis_description and self.catharsis_persist > 0:
            prompt_parts.append(f" {self.last_catharsis_description} ")
            self.catharsis_persist -= 1
            if self.catharsis_persist == 0:
                self.last_catharsis_description = None

        # Part 2: Mental state
        complex_states = self._get_complex_state_descriptions()
        if complex_states:
            state_str = " ".join(complex_states)
            self.last_mental_state = state_str
            self.mental_state_persist = 2
        if self.last_mental_state and self.mental_state_persist > 0:
            prompt_parts.append(f"CURRENT MENTAL STATE: You are currently experiencing: {self.last_mental_state}")
            self.mental_state_persist -= 1
            if self.mental_state_persist == 0:
                self.last_mental_state = None

        # Part 3: Trait descriptions
        trait_descriptions = []
        for trait, value in self.current_state.items():
            config = self.traits.get(trait)
            if not config: continue
            baseline = config["baseline"]
            deviation = value - baseline
            abs_deviation = abs(deviation)
            if abs_deviation < 0.15: continue
            if abs_deviation < 0.3: intensity = "a hint of"
            elif abs_deviation < 0.5: intensity = "a clear feeling of"
            else: intensity = "an overwhelming sense of"
            direction = "elevated" if deviation > 0 else "diminished"
            trait_descriptions.append(f"{intensity} {direction} {trait}")
        if trait_descriptions:
            trait_str = f"You feel {', '.join(trait_descriptions)}."
            self.last_trait_descriptions = trait_str
            self.trait_desc_persist = 2
        if self.last_trait_descriptions and self.trait_desc_persist > 0:
            prompt_parts.append(f"UNDERLYING TRAITS: {self.last_trait_descriptions}")
            self.trait_desc_persist -= 1
            if self.trait_desc_persist == 0:
                self.last_trait_descriptions = None

        if not prompt_parts:
            return ""
        final_prompt = " ".join(prompt_parts)
        return final_prompt + " Respond naturally with this full emotional context, of which the user is mostly the source, in mind. Show, but do not explicitly state these traits in your response."
    
    def get_trait_summary(self) -> Dict[str, float]:
        """Get a copy of the current trait values."""
        self._update_system() # Ensure traits are decayed and updated
        return self.current_state.copy()
    
    def get_mood_color_mix(self) -> Tuple[int, int, int, float]:
        """
        Calculates an RGBA color mix based on the character's current mood.

        Returns:
            A tuple representing (r, g, b, a).
        """
        color_map = {
            "red": ["aggression", "grudge", "antagonism", "domineering", "stubbornness", "pride", "urgency", "tension"],
            "blue": ["sadness", "fatigue", "introversion", "rumination", "guilt", "confusion", "sense_of_moral_violation"],
            "yellow": ["humor", "energy", "openness", "hope", "confidence", "ambition", "proactivity", "decisiveness", "empathy"],
            "purple": ["fear", "paranoia", "skeptical", "self_interest", "analytical"]
        }

        color_values = {"red": 0.0, "blue": 0.0, "yellow": 0.0, "purple": 0.0}
        total_deviation = 0.0

        for color, traits in color_map.items():
            for trait in traits:
                if trait in self.current_state and trait in self.traits:
                    baseline = self.traits[trait]["baseline"]
                    current_value = self.current_state[trait]
                    
                    # We only care about positive deviations from the baseline
                    deviation = max(0, current_value - baseline)
                    
                    color_values[color] += deviation
                    total_deviation += deviation
        
        # Handle the special case for 'trust' contributing to 'purple'
        if 'trust' in self.current_state and 'trust' in self.traits:
            baseline = self.traits['trust']['baseline']
            current_value = self.current_state['trust']
            # Low trust (a negative deviation) contributes to purple/anxiety
            deviation = max(0, baseline - current_value)
            color_values['purple'] += deviation
            total_deviation += deviation


        # Normalize the color contributions
        if total_deviation > 0:
            for color in color_values:
                color_values[color] /= total_deviation

        # Define the base RGB for each mood
        rgb_map = {
            "red": (255, 69, 58),      # A vibrant, slightly softer red
            "blue": (10, 132, 255),    # A strong, clear blue
            "yellow": (255, 214, 10),   # A warm, golden yellow
            "purple": (191, 90, 242)    # A rich, modern purple
        }

        # Mix the final color based on the normalized values
        r = sum(color_values[c] * rgb_map[c][0] for c in color_values)
        g = sum(color_values[c] * rgb_map[c][1] for c in color_values)
        b = sum(color_values[c] * rgb_map[c][2] for c in color_values)

        # The alpha channel is determined by the overall emotional intensity
        # A simple way is to scale it with the total deviation, capped at a reasonable value
        alpha = min(0.7, total_deviation * 0.5) # Cap opacity at 70%

        # If there's no significant deviation, return a neutral, faint color
        if total_deviation < 0.1:
            return (128, 128, 128, 0.1) # Neutral gray with low opacity

        return (int(r), int(g), int(b), round(alpha, 2))




def analyze_message_sentiment(message_content: str, llm_handler, support_settings=None, settings=None) -> Tuple[str, float]:
    """
    Use LLM to analyze message sentiment and return primary sentiment + intensity
    """
    
    sentiment_prompt = f"""Analyze this message and return ONLY the primary sentiment from this list:
praise, criticism, hostility, curiosity, humor, confusion, gratitude, dismissal, 
agreement, disagreement, frustration, excitement, boredom, concern, neutral

Then rate the intensity from 0.1 (very mild) to 1.0 (very strong).

Message: "{message_content}"

Response format: sentiment_word intensity_number
Example: curiosity 0.7"""
    
    # Use support_settings if provided, else fallback to main settings
    if support_settings:
        provider = support_settings.get('provider') or settings.get('llm_provider')
        api_keys = support_settings.get('api_keys', {})
        model = support_settings.get('model') or settings.get('default_model')
    else:
        provider = settings.get('llm_provider')
        api_keys = settings.get('api_keys', {})
        model = settings.get('default_model')


    try:
        # Create a simple message for sentiment analysis
        sentiment_messages = [{"role": "user", "content": sentiment_prompt}]
        
        # Call LLM with minimal system prompt
        response = llm_handler.generate_response(
            sentiment_messages, 
            system_prompt="You are a precise sentiment analyzer. Follow instructions exactly.",
            max_tokens=50
        )
        
        # Parse response
        parts = response.strip().split()
        if len(parts) >= 2:
            sentiment = parts[0].lower()
            try:
                intensity = float(parts[1])
                intensity = max(0.1, min(1.0, intensity))  # Clamp to valid range
                return sentiment, intensity
            except ValueError:
                pass
    
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}\n")
    
    # Fallback to neutral
    return "neutral", 0.5

# Integration example for LLM handlers
class EnhancedAnthropicHandler:
    def __init__(self, api_key):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.orrery = PersonalityOrrery()
    
    def generate_response(self, messages, system_prompt="", **kwargs):
        # Analyze user sentiment using LLM
        if messages:
            user_message = messages[-1].get('content', '')
            sentiment, intensity = analyze_message_sentiment(user_message, self)
            
            # Update personality based on sentiment
            self.orrery.update_from_sentiment(sentiment, intensity)
            

        # Get personality-influenced system prompt
        personality_context = self.orrery.get_personality_prompt()
        enhanced_system_prompt = personality_context + system_prompt
        
        # Make API call
        response = self.client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=kwargs.get('max_tokens', 1000),
            system=enhanced_system_prompt,
            messages=messages
        )
        
        return response.content[0].text

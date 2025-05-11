import logging
import random
import re
from enum import Enum
import os
import google.generativeai as genai

logger = logging.getLogger("GameLogger")

class QuestType(Enum):
    DEFEAT = 1    # Combat quest
    TALK = 2      # Dialogue quest
    FIND = 3      # Exploration quest

class NLPGenerator:
    """
    Generates immersive D&D-themed text for quests, NPC dialogues, and quest completions.
    Uses Gemini API if available, otherwise falls back to templates.
    """
    
    def __init__(self):
        self.gemini_model = None
        self.templates = self._load_templates()
        
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                logger.info("Gemini API key configured. Attempting to find and initialize a suitable model.")
                
                suitable_model_found = False
                try:
                    for model_info in genai.list_models():
                        # Models are typically named like 'models/gemini-pro'
                        # We need to check if 'generateContent' is a supported method
                        if 'generateContent' in model_info.supported_generation_methods:
                            model_name_to_try = model_info.name
                            logger.info(f"Found model supporting 'generateContent': {model_name_to_try}. Attempting to initialize and test.")
                            try:
                                temp_model = genai.GenerativeModel(model_name=model_name_to_try)
                                # Perform a quick test generation to ensure the model works
                                # Using a simple, non-empty prompt for testing
                                test_response = temp_model.generate_content("test prompt for model validation")
                                if test_response.text: # Check if response has text
                                    self.gemini_model = temp_model
                                    logger.info(f"Successfully initialized and tested Gemini model: {model_name_to_try}")
                                    suitable_model_found = True
                                    break # Exit loop once a working model is found
                                else:
                                    logger.warning(f"Model {model_name_to_try} initialized but test generation yielded empty response.")
                            except Exception as e_init_test:
                                logger.warning(f"Failed to initialize or test model {model_name_to_try}: {str(e_init_test)}")
                                # Continue to the next suitable model
                    
                    if not suitable_model_found:
                        logger.warning("No suitable Gemini model found after checking all listed models and testing. NLPGenerator will use template-based generation.")
                        self.gemini_model = None # Ensure it's None if no model worked

                except Exception as e_list_models:
                    logger.error(f"Error listing or processing Gemini models: {str(e_list_models)}. Falling back to templates.", exc_info=True)
                    self.gemini_model = None
            else:
                logger.warning("GEMINI_API_KEY environment variable not found. NLPGenerator will use template-based generation.")
        
        except Exception as e_config: # Catch errors from genai.configure or other initial setup
            logger.error(f"Error during Gemini API configuration: {str(e_config)}. Falling back to templates.", exc_info=True)
            self.gemini_model = None

        # Ensure templates are loaded, this was already here but good to confirm
        if not self.templates: 
             self.templates = self._load_templates() # This should ideally not be needed if called at the start
             logger.info("Templates re-loaded as a fallback.")

    def _load_templates(self):
        """Loads enhanced text templates for fallback generation."""
        return {
            'quest_descriptions': {
                QuestType.DEFEAT: [
                    "Vanquish the {npc_name}, a menace terrorizing the forest glades.",
                    "Defeat the {npc_name} to safeguard the village from its wrath.",
                    "Slay the fearsome {npc_name} to earn the gratitude of the realm.",
                    "Challenge and overcome the {npc_name} to prove your heroism."
                ],
                QuestType.TALK: [
                    "Seek the wisdom of {npc_name}, who holds secrets of the ancient woods.",
                    "Converse with {npc_name} to uncover clues to your next adventure.",
                    "Engage {npc_name} in dialogue to gain their trust and knowledge.",
                    "Speak with {npc_name} to learn of hidden paths and treasures."
                ],
                QuestType.FIND: [
                    "Discover the lost relic guarded by {npc_name} in the shadowed groves.",
                    "Find the sacred artifact before {npc_name} claims its power.",
                    "Uncover the treasure hidden near {npc_name}'s lair in the forest.",
                    "Search for the enchanted item that {npc_name} seeks to possess."
                ]
            },
            'npc_dialogues': {
                'hostile': [
                    "You dare face me, {npc_name}? Your doom awaits!",
                    "I, {npc_name}, will crush you where you stand!",
                    "Foolish adventurer, {npc_name} shall end your tale!",
                    "No mercy for you! {npc_name} will prevail!"
                ],
                'neutral': [
                    "What brings you here, traveler? I am {npc_name}.",
                    "{npc_name} has seen many wanderers. What is your purpose?",
                    "Tread carefully, for {npc_name} watches your every move.",
                    "Speak, adventurer. Why do you approach {npc_name}?"
                ],
                'friendly': [
                    "Greetings, brave soul! I, {npc_name}, offer my aid.",
                    "{npc_name} welcomes you. How may I assist your quest?",
                    "A friend at last! {npc_name} is eager to help.",
                    "Well met, hero! {npc_name} has much to share."
                ],
                'merchant': [
                    "Welcome to {npc_name}'s wares! Potions, weapons, you name it!",
                    "Fine goods for a fine adventurer! What does {npc_name} have for you?",
                    "{npc_name}'s shop has the best in the realm. Care to browse?",
                    "Rare finds await! {npc_name} offers only the finest."
                ],
                'quest_giver': [
                    "{npc_name} seeks a champion for a vital task. Are you the one?",
                    "Hear me, adventurer. {npc_name} has a quest of great import.",
                    "{npc_name} needs your skills to avert a looming peril.",
                    "A reward awaits if you aid {npc_name} in this endeavor."
                ]
            },
            'quest_completion': [
                "Triumph! You have vanquished {npc_name} and completed your quest.",
                "Well done! {npc_name} no longer threatens the land. Quest complete!",
                "Victory is yours! {npc_name}'s defeat marks your success.",
                "Your quest is fulfilled! {npc_name} is dealt with, and peace is restored."
            ]
        }

    def _clean_text(self, text):
        """Clean generated text to ensure coherence and remove artifacts."""
        if not text:
            return ""
        text = re.sub(r'[\\*#]', '', text)  # Remove *, #
        text = text.replace("NPC:", "").strip()  # Remove common prefixes if any
        text = text.replace("Player:", "").strip()
        text = text.replace('"', '').strip()  # Remove existing quotes, they will be added systematically
        text = re.sub(r'\s+', ' ', text).strip()  # Collapse multiple spaces into one
        return text

    def _split_into_sentences(self, text: str) -> list[str]:
        """Splits text into a list of sentences."""
        if not text:
            return []
        
        text = text.replace('\n', ' ').strip() 
        sentences = re.split(r'(?<=[.!?])\s+', text)
        cleaned_sentences = [s.strip() for s in sentences if s.strip()]
        return cleaned_sentences

    def generate_quest_description(self, quest_type, npc_name, context=None):
        context = context or {}
        if self.gemini_model:
            try:
                prompt = (
                    f"You are a Dungeon Master for a text-based fantasy RPG. Generate a short, immersive quest description (1-2 sentences) "
                    f"for a '{quest_type.name.lower()}' quest involving an NPC named '{npc_name}'. "
                    f"The tone should be medieval fantasy. Do not use modern language or refer to game mechanics (like D&D rules or XP). "
                    f"Be creative and engaging. "
                )
                if quest_type == QuestType.DEFEAT:
                    prompt += f"This {npc_name} is a dangerous threat that must be eliminated. Write a compelling call to action for a hero. "
                elif quest_type == QuestType.TALK:
                    prompt += f"{npc_name} possesses vital information or a long-lost secret. The player must engage them in conversation. Describe what the player might learn or achieve. "
                elif quest_type == QuestType.FIND:
                    prompt += f"A rare artifact or a person of interest is associated with {npc_name}, possibly guarded or hidden. The player needs to locate it. Hint at the object's significance or the challenge in finding it. "
                
                prompt += "Focus on narrative and atmosphere."

                logger.debug(f"Gemini API Prompt for quest description: {prompt}")
                response = self.gemini_model.generate_content(prompt)
                quest_text = self._clean_text(response.text)
                logger.info(f"Generated quest description via Gemini API: {quest_text}")
                
                quest_header = "NEW QUEST"
                quest_type_text = {
                    QuestType.DEFEAT: "[Combat Quest]",
                    QuestType.TALK: "[Dialogue Quest]",
                    QuestType.FIND: "[Exploration Quest]"
                }[quest_type]
                return f"{quest_header}\n{quest_type_text} {quest_text}\n"

            except Exception as e:
                logger.error(f"Error in Gemini API quest generation: {str(e)}. Falling back to template.", exc_info=True)

        # Fallback to templates
        logger.info(f"Using template for quest description (NPC: {npc_name}, Type: {quest_type.name})")
        templates = self.templates['quest_descriptions'][quest_type]
        quest_text = random.choice(templates).format(npc_name=npc_name)
        quest_header = "NEW QUEST"
        quest_type_text = {
            QuestType.DEFEAT: "[Combat Quest]",
            QuestType.TALK: "[Dialogue Quest]",
            QuestType.FIND: "[Exploration Quest]"
        }[quest_type]
        return f"{quest_header}\n{quest_type_text} {quest_text}\n"

    def generate_npc_dialogue(self, npc_name: str, disposition: str, context: dict | None = None) -> list[str]:
        """
        Generates immersive D&D-themed NPC dialogue.
        Returns a list of dialogue lines (sentences).
        """
        context = context or {}
        npc_type = context.get('npc_type', disposition)  # Use disposition as fallback for npc_type
        health_percentage = context.get('health_percent', 1.0)
        quest_relevant = context.get('quest_relevant', False)
        
        raw_speech_text = ""

        if self.gemini_model:
            try:
                prompt = (
                    f"You are an NPC character named '{npc_name}' of type '{npc_type}' in a text-based fantasy RPG. "
                    f"Your current disposition towards the player is '{disposition}'. "
                    f"Craft a short, thematic speech (1-3 sentences) that you would say to the player. "
                    f"Use medieval fantasy language. Do not use modern terms or game mechanics. Be immersive. "
                    f"Do not include prefixes like '{npc_name} says:'. Just provide the speech itself."
                )
                if disposition == 'hostile':
                    prompt += f"You are aggressive and ready for a fight. "
                elif disposition == 'friendly':
                    prompt += f"You are welcoming and helpful. "
                elif npc_type == 'merchant':
                    prompt += f"You are keen to trade goods or offer services. "
                elif npc_type == 'quest_giver':
                    prompt += f"You have an important task for the adventurer. "
                else:  # Neutral
                    prompt += f"You are cautious but open to interaction. "
                
                if health_percentage < 0.3:
                    prompt += f"You are badly wounded and desperate. "
                elif health_percentage < 0.6:
                    prompt += f"You appear injured and wary. "
                
                if quest_relevant:
                    prompt += f"The player is currently on a quest that involves you directly. "
                
                prompt += "What is your speech?"
                
                logger.debug(f"Gemini API Prompt for NPC dialogue: {prompt}")
                response = self.gemini_model.generate_content(prompt)
                raw_speech_text = self._clean_text(response.text)
                logger.info(f"Generated NPC dialogue via Gemini API (cleaned text): {raw_speech_text}")

            except Exception as e:
                logger.error(f"Error in Gemini API dialogue generation: {str(e)}. Falling back to template.", exc_info=True)
                raw_speech_text = ""

        if not raw_speech_text:  # Fallback to templates if Gemini failed or was not used
            logger.info(f"Using template for NPC dialogue (NPC: {npc_name}, Disposition: {disposition}, Type: {npc_type})")
            template_key = npc_type if npc_type in self.templates['npc_dialogues'] else disposition
            template_key = template_key if template_key in self.templates['npc_dialogues'] else 'neutral'
            
            dialogue_template = random.choice(self.templates['npc_dialogues'][template_key])
            raw_speech_text = self._clean_text(dialogue_template.format(npc_name=npc_name))

        dialogue_lines = self._split_into_sentences(raw_speech_text)

        if not dialogue_lines:
            return [f"{npc_name} remains silent."] 
        
        return dialogue_lines

    def generate_quest_completion(self, npc_name, context=None):
        context = context or {}
        quest_type = context.get('quest_type', QuestType.DEFEAT)

        if self.gemini_model:
            try:
                prompt = (
                    f"You are a Dungeon Master for a text-based fantasy RPG. Generate a short, celebratory message (1-2 sentences) for the player. "
                    f"The player has just completed a '{quest_type.name.lower()}' quest involving an NPC named '{npc_name}'. "
                    f"The message should be in a medieval fantasy tone, congratulating the player on their success. "
                    f"Do not use modern language or game mechanics terms. Be thematic and uplifting."
                )
                logger.debug(f"Gemini API Prompt for quest completion: {prompt}")
                response = self.gemini_model.generate_content(prompt)
                completion_text = self._clean_text(response.text)
                logger.info(f"Generated quest completion text via Gemini API: {completion_text}")

                completion_header = "✓ QUEST COMPLETE"
                reward_text = "Reward: +10 XP, +5 Gold" 
                return f"{completion_header}\n{completion_text}\n{reward_text}\n"
            except Exception as e:
                logger.error(f"Error in Gemini API quest completion generation: {str(e)}. Falling back to template.", exc_info=True)

        # Fallback to templates
        logger.info(f"Using template for quest completion (NPC: {npc_name}, Type: {quest_type.name})")
        completion_text = random.choice(self.templates['quest_completion']).format(npc_name=npc_name)
        completion_header = "✓ QUEST COMPLETE"
        reward_text = "Reward: +10 XP, +5 Gold"
        return f"{completion_header}\n{completion_text}\n{reward_text}\n"

# Example usage (for testing purposes, not part of the class)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing NLPGenerator with Gemini API...")
    
    nlp_gen = NLPGenerator()

    if not nlp_gen.gemini_model:
        logger.warning("Gemini model not initialized. Ensure GEMINI_API_KEY is set.")
        logger.info("Proceeding with template-based tests.")

    # Test Quest Description
    logger.info("--- Testing Quest Description ---")
    desc_defeat = nlp_gen.generate_quest_description(QuestType.DEFEAT, "Grimgor Ironhide")
    print(f"Defeat Quest: {desc_defeat}")
    desc_talk = nlp_gen.generate_quest_description(QuestType.TALK, "Elara Meadowlight")
    print(f"Talk Quest: {desc_talk}")
    desc_find = nlp_gen.generate_quest_description(QuestType.FIND, "the Shadowfang Amulet", context={"npc_name": "Morwen Nightshade"}) # npc_name in context for find
    print(f"Find Quest: {desc_find}")

    # Test NPC Dialogue
    logger.info("--- Testing NPC Dialogue ---")
    dialogue_hostile = nlp_gen.generate_npc_dialogue("Borin Stonebeard", "hostile", context={'npc_type': 'enemy'})
    print(f"Hostile Dialogue: {dialogue_hostile}")
    dialogue_friendly = nlp_gen.generate_npc_dialogue("Lyra Swiftarrow", "friendly", context={'npc_type': 'ally'})
    print(f"Friendly Dialogue: {dialogue_friendly}")
    dialogue_merchant = nlp_gen.generate_npc_dialogue("Silas Greenthorne", "merchant", context={'npc_type': 'merchant'})
    print(f"Merchant Dialogue: {dialogue_merchant}")
    dialogue_quest_giver = nlp_gen.generate_npc_dialogue("Archmage Valerius", "quest_giver", context={'npc_type': 'quest_giver', 'quest_relevant': True})
    print(f"Quest Giver Dialogue: {dialogue_quest_giver}")

    # Test Quest Completion
    logger.info("--- Testing Quest Completion ---")
    comp_defeat = nlp_gen.generate_quest_completion("Grimgor Ironhide", context={'quest_type': QuestType.DEFEAT})
    print(f"Defeat Completion: {comp_defeat}")
    comp_find = nlp_gen.generate_quest_completion("the Shadowfang Amulet", context={'quest_type': QuestType.FIND})
    print(f"Find Completion: {comp_find}")

    logger.info("NLPGenerator testing complete.")
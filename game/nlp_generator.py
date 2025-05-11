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
                        if 'generateContent' in model_info.supported_generation_methods:
                            model_name_to_try = model_info.name
                            logger.info(f"Found model supporting 'generateContent': {model_name_to_try}. Attempting to initialize and test.")
                            try:
                                temp_model = genai.GenerativeModel(model_name=model_name_to_try)
                                test_response = temp_model.generate_content("test prompt for model validation")
                                if test_response.text:
                                    self.gemini_model = temp_model
                                    logger.info(f"Successfully initialized and tested Gemini model: {model_name_to_try}")
                                    suitable_model_found = True
                                    break
                                else:
                                    logger.warning(f"Model {model_name_to_try} initialized but test generation yielded empty response.")
                            except Exception as e_init_test:
                                logger.warning(f"Failed to initialize or test model {model_name_to_try}: {str(e_init_test)}")
                    
                    if not suitable_model_found:
                        logger.warning("No suitable Gemini model found after checking all listed models and testing. NLPGenerator will use template-based generation.")
                        self.gemini_model = None

                except Exception as e_list_models:
                    logger.error(f"Error listing or processing Gemini models: {str(e_list_models)}. Falling back to templates.", exc_info=True)
                    self.gemini_model = None
            else:
                logger.warning("GEMINI_API_KEY environment variable not found. NLPGenerator will use template-based generation.")
        
        except Exception as e_config:
            logger.error(f"Error during Gemini API configuration: {str(e_config)}. Falling back to templates.", exc_info=True)
            self.gemini_model = None

        if not self.templates: 
             self.templates = self._load_templates()
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
        text = re.sub(r'(\*\*|__)(.*?)(\*\*|__)', r'\2', text)  # Bold
        text = re.sub(r'(\*|_)(.*?)(\*|_)', r'\2', text)    # Italics
        text = text.strip()
        text = re.sub(r'\n\s*\n', '\n', text)  # Replace multiple newlines with one
        text = re.sub(r'^\w+\s+(says|proclaims|growls|offers):?\s*', '', text, flags=re.IGNORECASE)
        text = text.strip().replace('\"', '')  # Remove extra quotes
        return text

    def _split_into_sentences(self, text_block):
        if not text_block:
            return []
        sentences = re.split(r'(?<=[.!?])\s+', text_block.strip())
        processed_sentences = [s.strip() for s in sentences if s.strip()]
        return processed_sentences if processed_sentences else [text_block.strip()]

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

    def generate_npc_dialogue(self, npc_name, disposition, context=None):
        context = context or {}
        npc_type = context.get('npc_type', disposition)
        health_percentage = context.get('health_percent', 1.0)
        quest_relevant = context.get('quest_relevant', False)

        if self.gemini_model:
            try:
                prompt = (
                    f"You are an NPC named '{npc_name}' of type '{npc_type}' in a text-based fantasy RPG. "
                    f"Your current disposition towards the player is '{disposition}'. "
                    f"Craft one or more concise, thematic sentences that you would say to the player. "
                    f"Use medieval fantasy language. Do not use modern terms or game mechanics. Be immersive. "
                )
                logger.debug(f"Gemini API Prompt for NPC dialogue: {prompt}")
                response = self.gemini_model.generate_content(prompt)
                
                raw_dialogue_block = self._clean_text(response.text)
                dialogue_lines = self._split_into_sentences(raw_dialogue_block)
                
                logger.info(f"Generated NPC dialogue lines via Gemini API: {dialogue_lines}")

                prefix = f"{npc_name} says:"
                if npc_type == 'enemy' or disposition == 'hostile':
                    prefix = f"{npc_name} growls:"
                elif npc_type == 'merchant':
                    prefix = f"{npc_name} offers:"
                elif npc_type == 'quest_giver':
                    prefix = f"{npc_name} proclaims:"
                
                formatted_lines = [f"{prefix} \"{line}\"" for line in dialogue_lines if line]
                return formatted_lines if formatted_lines else [f"{prefix} \"...\""]

            except Exception as e:
                logger.error(f"Error in Gemini API dialogue generation: {str(e)}. Falling back to template.", exc_info=True)
                logger.info(f"Using template for NPC dialogue (NPC: {npc_name}, Disposition: {disposition}, Type: {npc_type})")
                template_key = npc_type if npc_type in self.templates['npc_dialogues'] else disposition
                template_key = template_key if template_key in self.templates['npc_dialogues'] else 'neutral'
                
                dialogue_template = random.choice(self.templates['npc_dialogues'][template_key])
                dialogue = dialogue_template.format(npc_name=npc_name)
                
                prefix = f"{npc_name} says:"
                if npc_type == 'enemy' or disposition == 'hostile':
                     prefix = f"{npc_name} growls:"
                elif npc_type == 'merchant':
                    prefix = f"{npc_name} offers:"
                elif npc_type == 'quest_giver':
                    prefix = f"{npc_name} proclaims:"
                return [f"{prefix} \"{dialogue}\""]

        logger.info(f"Using template for NPC dialogue (NPC: {npc_name}, Disposition: {disposition}, Type: {npc_type})")
        template_key = npc_type if npc_type in self.templates['npc_dialogues'] else disposition
        template_key = template_key if template_key in self.templates['npc_dialogues'] else 'neutral'
        
        dialogue_template = random.choice(self.templates['npc_dialogues'][template_key])
        dialogue = dialogue_template.format(npc_name=npc_name)
        
        prefix = f"{npc_name} says:"
        if npc_type == 'enemy' or disposition == 'hostile':
             prefix = f"{npc_name} growls:"
        elif npc_type == 'merchant':
            prefix = f"{npc_name} offers:"
        elif npc_type == 'quest_giver':
            prefix = f"{npc_name} proclaims:"
        return [f"{prefix} \"{dialogue}\""]

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

        logger.info(f"Using template for quest completion (NPC: {npc_name}, Type: {quest_type.name})")
        completion_text = random.choice(self.templates['quest_completion']).format(npc_name=npc_name)
        completion_header = "✓ QUEST COMPLETE"
        reward_text = "Reward: +10 XP, +5 Gold"
        return f"{completion_header}\n{completion_text}\n{reward_text}\n"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing NLPGenerator with Gemini API...")
    
    nlp_gen = NLPGenerator()

    if not nlp_gen.gemini_model:
        logger.warning("Gemini model not initialized. Ensure GEMINI_API_KEY is set.")
        logger.info("Proceeding with template-based tests.")

    logger.info("--- Testing Quest Description ---")
    desc_defeat = nlp_gen.generate_quest_description(QuestType.DEFEAT, "Grimgor Ironhide")
    print(f"Defeat Quest: {desc_defeat}")
    desc_talk = nlp_gen.generate_quest_description(QuestType.TALK, "Elara Meadowlight")
    print(f"Talk Quest: {desc_talk}")
    desc_find = nlp_gen.generate_quest_description(QuestType.FIND, "the Shadowfang Amulet", context={"npc_name": "Morwen Nightshade"})
    print(f"Find Quest: {desc_find}")

    logger.info("--- Testing NPC Dialogue ---")
    dialogue_hostile = nlp_gen.generate_npc_dialogue("Borin Stonebeard", "hostile", context={'npc_type': 'enemy'})
    print(f"Hostile Dialogue: {dialogue_hostile}")
    dialogue_friendly = nlp_gen.generate_npc_dialogue("Lyra Swiftarrow", "friendly", context={'npc_type': 'ally'})
    print(f"Friendly Dialogue: {dialogue_friendly}")
    dialogue_merchant = nlp_gen.generate_npc_dialogue("Silas Greenthorne", "merchant", context={'npc_type': 'merchant'})
    print(f"Merchant Dialogue: {dialogue_merchant}")
    dialogue_quest_giver = nlp_gen.generate_npc_dialogue("Archmage Valerius", "quest_giver", context={'npc_type': 'quest_giver', 'quest_relevant': True})
    print(f"Quest Giver Dialogue: {dialogue_quest_giver}")

    logger.info("--- Testing Quest Completion ---")
    comp_defeat = nlp_gen.generate_quest_completion("Grimgor Ironhide", context={'quest_type': QuestType.DEFEAT})
    print(f"Defeat Completion: {comp_defeat}")
    comp_find = nlp_gen.generate_quest_completion("the Shadowfang Amulet", context={'quest_type': QuestType.FIND})
    print(f"Find Completion: {comp_find}")

    logger.info("NLPGenerator testing complete.")
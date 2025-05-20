import logging
import random
import re
from enum import Enum
import os
import google.generativeai as genai
import threading

logger = logging.getLogger("GameLogger")

class QuestType(Enum):
    DEFEAT = 1    # Combat quest
    TALK = 2      # Dialogue quest
    FIND = 3      # Exploration quest

class NLPGenerator:
    """
    Generates immersive D&D-themed text for quests, NPC dialogues, and quest completions.
    Uses Gemini API if available, otherwise falls back to templates.
    Manages API calls in a separate thread to prevent blocking.
    """
    
    def __init__(self):
        self.gemini_model = None
        self.templates = self._load_templates()
        
        self._is_generating = False
        self._generation_thread = None
        self._generation_result = None
        self._generation_error = None
        self._current_fallback_method = None
        self._current_fallback_args = None

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

    def is_busy(self):
        """Checks if the NLP generator is currently busy with a generation task."""
        if self._generation_thread and self._generation_thread.is_alive():
            self._is_generating = True
            return True
        if self._is_generating and (not self._generation_thread or not self._generation_thread.is_alive()):
            self._is_generating = False 
        return self._is_generating

    def get_result(self):
        """Retrieves the result of the last generation task. Clears the result after retrieval."""
        if self.is_busy():
            return None
        
        result = self._generation_result
        error = self._generation_error
        
        self._generation_result = None
        self._generation_error = None
        self._current_fallback_method = None
        self._current_fallback_args = None
        
        if error:
            logger.error(f"NLPGenerator: Error was present when retrieving result: {error}")
            return {"error": str(error), "fallback_used": True}

        return result

    def _threaded_generate(self, prompt, generation_type_info, fallback_method, fallback_args):
        """Internal method to run Gemini API call in a thread."""
        try:
            logger.debug(f"NLPGenerator Thread: Starting Gemini API call. Info: {generation_type_info}")
            response = self.gemini_model.generate_content(prompt)
            cleaned_text = self._clean_text(response.text)
            
            if generation_type_info['type'] == 'quest_description':
                quest_type = generation_type_info['quest_type']
                quest_header = "NEW QUEST"
                quest_type_text = {
                    QuestType.DEFEAT: "[Combat Quest]",
                    QuestType.TALK: "[Dialogue Quest]",
                    QuestType.FIND: "[Exploration Quest]"
                }[quest_type]
                self._generation_result = f"{quest_header}\n{quest_type_text} {cleaned_text}\n"
            elif generation_type_info['type'] == 'npc_dialogue':
                self._generation_result = self._split_into_sentences(cleaned_text)
                if not self._generation_result:
                     self._generation_result = [f"{generation_type_info.get('npc_name', 'NPC')} remains silent."]
            elif generation_type_info['type'] == 'quest_completion':
                completion_header = "✓ QUEST COMPLETE"
                reward_text = "Reward: +10 XP, +5 Gold" 
                self._generation_result = f"{completion_header}\n{cleaned_text}\n{reward_text}\n"
            else:
                self._generation_result = cleaned_text

            logger.info(f"NLPGenerator Thread: Successfully generated text via Gemini API: {self._generation_result}")
            self._generation_error = None
        except Exception as e:
            logger.error(f"NLPGenerator Thread: Error in Gemini API call ({generation_type_info['type']}): {str(e)}", exc_info=True)
            self._generation_error = e
            logger.info(f"NLPGenerator Thread: Falling back to template due to error for {generation_type_info['type']}.")
            self._generation_result = fallback_method(*fallback_args)
        finally:
            self._is_generating = False
            logger.debug("NLPGenerator Thread: Finished.")

    def _start_generation_thread(self, prompt, generation_type_info, fallback_method, fallback_args):
        """Starts the generation thread if not already busy."""
        # If Gemini model isn't available, just use the template immediately
        if not self.gemini_model:
            logger.info(f"NLPGenerator: No Gemini model available, using template for {generation_type_info['type']}.")
            self._is_generating = False
            return fallback_method(*fallback_args)
            
        # If we're already generating, use template instead of queuing
        if self.is_busy():
            logger.warning(f"NLPGenerator: Generation requested while already busy. Using template for {generation_type_info['type']}.")
            return fallback_method(*fallback_args)

        self._is_generating = True
        self._generation_result = None
        self._generation_error = None
        self._current_fallback_method = fallback_method
        self._current_fallback_args = fallback_args

        self._generation_thread = threading.Thread(
            target=self._threaded_generate, 
            args=(prompt, generation_type_info, fallback_method, fallback_args)
        )
        self._generation_thread.daemon = True
        self._generation_thread.start()
        logger.info(f"NLPGenerator: Started generation thread for {generation_type_info['type']}.")
        return None

    def _generate_quest_description_template(self, quest_type, npc_name, context=None):
        logger.info(f"NLPGenerator: Using template for quest description (NPC: {npc_name}, Type: {quest_type.name})")
        templates = self.templates['quest_descriptions'][quest_type]
        quest_text = random.choice(templates).format(npc_name=npc_name)
        quest_header = "NEW QUEST"
        quest_type_text = {
            QuestType.DEFEAT: "[Combat Quest]",
            QuestType.TALK: "[Dialogue Quest]",
            QuestType.FIND: "[Exploration Quest]"
        }[quest_type]
        return f"{quest_header}\n{quest_type_text} {quest_text}\n"

    def generate_quest_description(self, quest_type, npc_name, context=None):
        context = context or {}
        fallback_args = (quest_type, npc_name, context)

        if self.gemini_model:
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
            
            generation_info = {'type': 'quest_description', 'quest_type': quest_type, 'npc_name': npc_name}
            
            return self._start_generation_thread(prompt, generation_info, self._generate_quest_description_template, fallback_args)
        else:
            return self._generate_quest_description_template(*fallback_args)

    def _generate_npc_dialogue_template(self, npc_name: str, disposition: str, context: dict | None = None) -> list[str]:
        context = context or {}
        npc_type = context.get('npc_type', disposition)
        logger.info(f"NLPGenerator: Using template for NPC dialogue (NPC: {npc_name}, Disposition: {disposition}, Type: {npc_type})")
        template_key = npc_type if npc_type in self.templates['npc_dialogues'] else disposition
        template_key = template_key if template_key in self.templates['npc_dialogues'] else 'neutral'
        
        dialogue_template = random.choice(self.templates['npc_dialogues'][template_key])
        raw_speech_text = self._clean_text(dialogue_template.format(npc_name=npc_name))
        dialogue_lines = self._split_into_sentences(raw_speech_text)
        if not dialogue_lines:
            return [f"{npc_name} remains silent."] 
        return dialogue_lines

    def generate_npc_dialogue(self, npc_name, disposition="neutral", context=None):
        """
        Generate contextual dialogue lines for an NPC.
        Disposition can be "hostile", "neutral", or "friendly".
        Returns a list of speech lines.
        """
        if not context:
            context = {}
        npc_type = context.get('npc_type', 'enemy')

        # Choose the right template category
        if npc_type in ["merchant", "quest_giver"] and npc_type in self.templates.get('npc_dialogues', {}):
            template_key = npc_type
        else:
            template_key = disposition

        # Check if templates are available for the selected key
        if not self.templates or 'npc_dialogues' not in self.templates or template_key not in self.templates['npc_dialogues']:
            logger.warning(f"No dialogue templates found for {template_key} NPC. Using default.")
            template_lines = ["Greetings, traveler.", "What brings you here?"]
        else:
            template_lines = random.choice(self.templates['npc_dialogues'][template_key])
            if isinstance(template_lines, str):  # Ensure it's a list
                template_lines = [template_lines]
                
        # Format templates with NPC name and context
        dialogue_lines = []
        for line in template_lines:
            try:
                formatted_line = line.format(npc_name=npc_name, **context)
                dialogue_lines.append(formatted_line)
            except KeyError as e:
                logger.warning(f"Template formatting error for {npc_name} dialogue: {e}")
                dialogue_lines.append(line)  # Use unformatted as fallback
        
        # If no Gemini API or we're using template mode, return template text immediately
        if not self.gemini_model:
            logger.info(f"NLPGenerator: Using template for NPC dialogue (NPC: {npc_name}, Disposition: {disposition}, Type: {npc_type})")
            return dialogue_lines

        # Build a prompt for LLM
        prompt = f"""
        You are generating immersive dialogue for a fantasy RPG in the style of D&D.
        NPC Name: {npc_name}
        NPC Type: {npc_type}
        Disposition: {disposition}
        Health Status: {context.get('health_percent', 1.0) * 100:.0f}% health
        
        Generate 2-3 short lines of dialogue. Your response should ONLY contain the dialogue lines,
        nothing else. Each line should be natural speech as spoken by the character directly.
        
        Example output:
        "Greetings, traveler. What brings you to these parts?"
        "I have many wares to offer, if you have coin."
        "Beware the dangers that lurk in the forest to the east."
        """

        # Use the template as fallback if the API call fails
        return self._start_generation_thread(
            prompt,
            {'type': 'npc_dialogue', 'npc_name': npc_name, 'disposition': disposition},
            self._generate_npc_dialogue_template,
            [npc_name, disposition, context]
        ) or dialogue_lines  # Return the template lines if thread was started

    def _generate_quest_completion_template(self, npc_name, context=None):
        context = context or {}
        quest_type = context.get('quest_type', QuestType.DEFEAT)
        logger.info(f"NLPGenerator: Using template for quest completion (NPC: {npc_name}, Type: {quest_type.name})")
        
        if not isinstance(quest_type, QuestType):
            try:
                quest_type = QuestType[quest_type.upper()] if isinstance(quest_type, str) else QuestType.DEFEAT
            except KeyError:
                quest_type = QuestType.DEFEAT
        
        completion_text = random.choice(self.templates['quest_completion']).format(npc_name=npc_name)
        completion_header = "✓ QUEST COMPLETE"
        reward_text = "Reward: +10 XP, +5 Gold"
        return f"{completion_header}\n{completion_text}\n{reward_text}\n"

    def generate_quest_completion(self, npc_name, context=None):
        context = context or {}
        quest_type = context.get('quest_type', QuestType.DEFEAT)
        fallback_args = (npc_name, context)

        if self.gemini_model:
            prompt = (
                f"You are a Dungeon Master for a text-based fantasy RPG. Generate a short, celebratory message (1-2 sentences) for the player. "
                f"The player has just completed a '{quest_type.name.lower()}' quest involving an NPC named '{npc_name}'. "
                f"The message should be in a medieval fantasy tone, congratulating the player on their success. "
                f"Do not use modern language or game mechanics terms. Be thematic and uplifting."
            )
            generation_info = {'type': 'quest_completion', 'npc_name': npc_name, 'quest_type': quest_type.name}
            return self._start_generation_thread(prompt, generation_info, self._generate_quest_completion_template, fallback_args)
        else:
            return self._generate_quest_completion_template(*fallback_args)

    def _clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'[\\*#]', '', text)
        text = text.replace("NPC:", "").strip()
        text = text.replace("Player:", "").strip()
        text = text.replace('"', '').strip()
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _split_into_sentences(self, text: str) -> list[str]:
        if not text:
            return []
        
        text = text.replace('\n', ' ').strip() 
        sentences = re.split(r'(?<=[.!?])\s+', text)
        cleaned_sentences = [s.strip() for s in sentences if s.strip()]
        return cleaned_sentences

    def _load_templates(self):
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

if __name__ == '__main__':
    import time
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing NLPGenerator with threaded Gemini API...")
    
    nlp_gen = NLPGenerator()

    if not nlp_gen.gemini_model:
        logger.warning("Gemini model not initialized. Ensure GEMINI_API_KEY is set.")
        logger.info("Proceeding with template-based tests (which are synchronous).")

    logger.info("--- Testing Quest Description ---")
    nlp_gen.generate_quest_description(QuestType.DEFEAT, "Grimgor Ironhide")
    if nlp_gen.gemini_model:
        while nlp_gen.is_busy():
            print("Waiting for DEFEAT quest description...")
            time.sleep(0.5)
        desc_defeat = nlp_gen.get_result()
        print(f"Defeat Quest (async): {desc_defeat}")
    else:
        desc_defeat = nlp_gen.generate_quest_description(QuestType.DEFEAT, "Grimgor Ironhide")
        print(f"Defeat Quest (template): {desc_defeat}")

    nlp_gen.generate_quest_description(QuestType.TALK, "Elara Meadowlight")
    if nlp_gen.gemini_model:
        while nlp_gen.is_busy():
            print("Waiting for TALK quest description...")
            time.sleep(0.5)
        desc_talk = nlp_gen.get_result()
        print(f"Talk Quest (async): {desc_talk}")
    else:
        desc_talk = nlp_gen.generate_quest_description(QuestType.TALK, "Elara Meadowlight")
        print(f"Talk Quest (template): {desc_talk}")

    logger.info("--- Testing NPC Dialogue ---")
    nlp_gen.generate_npc_dialogue("Borin Stonebeard", "hostile", context={'npc_type': 'enemy'})
    if nlp_gen.gemini_model:
        while nlp_gen.is_busy():
            print("Waiting for HOSTILE dialogue...")
            time.sleep(0.5)
        dialogue_hostile = nlp_gen.get_result()
        print(f"Hostile Dialogue (async): {dialogue_hostile}")
    else:
        dialogue_hostile = nlp_gen.generate_npc_dialogue("Borin Stonebeard", "hostile", context={'npc_type': 'enemy'})
        print(f"Hostile Dialogue (template): {dialogue_hostile}")

    logger.info("--- Testing Quest Completion ---")
    nlp_gen.generate_quest_completion("Grimgor Ironhide", context={'quest_type': QuestType.DEFEAT})
    if nlp_gen.gemini_model:
        while nlp_gen.is_busy():
            print("Waiting for DEFEAT quest completion...")
            time.sleep(0.5)
        comp_defeat = nlp_gen.get_result()
        print(f"Defeat Completion (async): {comp_defeat}")
    else:
        comp_defeat = nlp_gen.generate_quest_completion("Grimgor Ironhide", context={'quest_type': QuestType.DEFEAT})
        print(f"Defeat Completion (template): {comp_defeat}")

    logger.info("--- Testing busy state and error handling (conceptual) ---")
    if nlp_gen.gemini_model:
        logger.info("Attempting to start a new generation while one might be busy...")
        nlp_gen.generate_quest_description(QuestType.FIND, "Lost Artifact") 
        if nlp_gen.is_busy():
            logger.info("NLPGenerator is busy as expected.")
            while nlp_gen.is_busy():
                time.sleep(0.1)
            logger.info("NLPGenerator finished its task.")
            final_result = nlp_gen.get_result()
            logger.info(f"Result of the potentially overlapping call: {final_result}")
        else:
            logger.info("NLPGenerator was not busy.")
            final_result = nlp_gen.get_result()
            if final_result:
                 logger.info(f"Result of the potentially overlapping call: {final_result}")

    logger.info("NLPGenerator test finished.")
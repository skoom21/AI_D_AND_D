import logging
import random
import re
from enum import Enum
import os

logger = logging.getLogger("GameLogger")

# Define these variables as global to ensure they're accessible everywhere
TORCH_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False

try:
    from transformers import GPT2Tokenizer, GPT2LMHeadModel, TextDataset, DataCollatorForLanguageModeling, Trainer, TrainingArguments
    import torch
    TORCH_AVAILABLE = torch.cuda.is_available()
    TRANSFORMERS_AVAILABLE = True
    logger.info(f"PyTorch available, using {'GPU' if TORCH_AVAILABLE else 'CPU'} for text generation.")
except ImportError:
    logger.warning("PyTorch or Transformers not available. Falling back to template-based text generation.")

# Ensure we don't override the global variables
def get_transformers_available():
    return TRANSFORMERS_AVAILABLE

def get_torch_available():
    return TORCH_AVAILABLE

class QuestType(Enum):
    DEFEAT = 1    # Combat quest
    TALK = 2      # Dialogue quest
    FIND = 3      # Exploration quest

class NLPGenerator:
    """
    Generates immersive D&D-themed text for quests, NPC dialogues, and quest completions.
    Uses fine-tuned GPT-2 if available, otherwise falls back to pre-trained GPT-2 or templates.
    """
    
    def __init__(self, fine_tune=False, cache_dir="./nlp_cache"):
        self.generator = None
        self.tokenizer = None
        self.model = None
        self.templates = self._load_templates()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

        if get_transformers_available():
            try:
                logger.info("Initializing NLP text generation model...")
                self.tokenizer = GPT2Tokenizer.from_pretrained("gpt2", cache_dir=cache_dir)
                # Set pad_token_id to eos_token_id if not already set
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                    logger.info(f"Tokenizer pad_token set to eos_token ({self.tokenizer.eos_token_id})")

                self.model = GPT2LMHeadModel.from_pretrained("gpt2", cache_dir=cache_dir)
                self.model.config.pad_token_id = self.tokenizer.pad_token_id # Ensure model config also knows
                self.model.eval()
                if get_torch_available() and torch.cuda.is_available(): # Check cuda availability again
                    self.model.to("cuda")
                    logger.info("GPT-2 model moved to GPU.")
                else:
                    logger.info("GPT-2 model running on CPU.")
                
                logger.info(f"GPT-2 model initialized successfully.")

                if fine_tune:
                    self._fine_tune_model()
            except Exception as e:
                logger.error(f"Error initializing NLP model: {str(e)}", exc_info=True)
                # Fallback to no transformers if initialization fails
                global TRANSFORMERS_AVAILABLE
                TRANSFORMERS_AVAILABLE = False 
        else:
            logger.info("Using template-based text generation due to missing Transformers library.")

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

    def _fine_tune_model(self):
        """Fine-tune GPT-2 on a small D&D dataset."""
        try:
            dataset_path = os.path.join(self.cache_dir, "dnd_dataset.txt")
            if not os.path.exists(dataset_path):
                # Create a sample D&D dataset
                sample_data = [
                    "Quest: Defeat the Goblin King who terrorizes the village.",
                    "The Merchant says: 'My wares are the finest in the land!'",
                    "Quest completed: The Ogre is slain, and the forest is safe.",
                    "The Wizard says: 'Seek the ancient tome in the ruins.'",
                    "Quest: Find the lost amulet hidden in the cave.",
                    "The Goblin growls: 'You'll never leave this forest alive!'"
                ]
                with open(dataset_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(sample_data))
                logger.info(f"Created sample D&D dataset at {dataset_path}")

            # Prepare dataset for fine-tuning
            dataset = TextDataset(
                tokenizer=self.tokenizer,
                file_path=dataset_path,
                block_size=128
            )
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            )

            # Training arguments
            training_args = TrainingArguments(
                output_dir=os.path.join(self.cache_dir, "gpt2_finetuned"),
                overwrite_output_dir=True,
                num_train_epochs=3,
                per_device_train_batch_size=2,
                save_steps=500,
                save_total_limit=1,
                logging_steps=100,
            )

            # Initialize trainer
            trainer = Trainer(
                model=self.model,
                args=training_args,
                data_collator=data_collator,
                train_dataset=dataset
            )

            # Fine-tune
            trainer.train()
            self.model.save_pretrained(os.path.join(self.cache_dir, "gpt2_finetuned"))
            self.tokenizer.save_pretrained(os.path.join(self.cache_dir, "gpt2_finetuned"))
            logger.info("GPT-2 model fine-tuned successfully.")
        except Exception as e:
            logger.error(f"Error fine-tuning NLP model: {str(e)}", exc_info=True)
            logger.info("Continuing with pre-trained GPT-2 model.")

    def _clean_text(self, text):
        """Clean generated text to ensure coherence and remove artifacts."""
        # Remove unwanted characters
        text = re.sub(r'[_\~\|\*\n]', ' ', text)
        # Remove date/time patterns
        text = re.sub(r'\(\d+[/:.]\d+[/:.]\d+\)', '', text)
        text = re.sub(r'\d+[:.]\d+', '', text)
        # Remove number tags
        text = re.sub(r'#\d+', '', text)
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        # Keep first two sentences
        sentences = re.split(r'[.!?]', text)
        clean_sentences = [s.strip() for s in sentences[:2] if s.strip()]
        clean_text = '. '.join(clean_sentences) + ('.' if clean_sentences else '')
        return clean_text

    def generate_quest_description(self, quest_type, npc_name, context=None):
        """
        Generates a D&D-themed quest description.

        Args:
            quest_type (QuestType): The type of quest.
            npc_name (str): The name of the NPC involved.
            context (dict, optional): Additional context (e.g., player health, turn count).

        Returns:
            str: Formatted quest description.
        """
        context = context or {}
        player_health_percentage = context.get('player_health', 100) / 100
        turn_count = context.get('turn_count', 0)

        if get_transformers_available() and self.model and self.tokenizer:
            try:
                base_prompt = f"Generate a short, immersive, D&D-style fantasy quest description. The quest is a {quest_type.name.lower()} quest involving a character named {npc_name}. "
                if quest_type == QuestType.DEFEAT:
                    base_prompt += f"This {npc_name} is a dangerous threat that must be eliminated. Write a compelling call to action for a hero. "
                elif quest_type == QuestType.TALK:
                    base_prompt += f"{npc_name} possesses vital information or a long-lost secret. The player must engage them in conversation. Describe what the player might learn or achieve. "
                elif quest_type == QuestType.FIND:
                    base_prompt += f"A rare artifact or a person of interest is associated with {npc_name}, possibly guarded or hidden. The player needs to locate it. Hint at the object's significance or the challenge in finding it. "
                
                base_prompt += "The description should be 1-2 sentences, written in a medieval fantasy tone. Do not use modern language, game mechanics terms, or refer to D&D rules. Be creative and engaging."

                inputs = self.tokenizer(base_prompt, return_tensors="pt", padding=True, truncation=True, max_length=150)
                attention_mask = inputs.get('attention_mask')
                input_ids = inputs.get('input_ids')

                if get_torch_available() and torch.cuda.is_available():
                    input_ids = input_ids.to("cuda")
                    if attention_mask is not None:
                        attention_mask = attention_mask.to("cuda")
                
                outputs = self.model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=70,  # Max tokens to generate *after* the prompt
                    min_new_tokens=20,
                    temperature=0.75,
                    top_k=50,
                    top_p=0.95,
                    num_return_sequences=1,
                    do_sample=True,
                    no_repeat_ngram_size=2,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                generated_text_only = self.tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
                quest_text = self._clean_text(generated_text_only)
                logger.info(f"Generated quest description: {quest_text}")

                # Format with UI styling
                quest_header = "NEW QUEST"
                quest_type_text = {
                    QuestType.DEFEAT: "[Combat Quest]",
                    QuestType.TALK: "[Dialogue Quest]",
                    QuestType.FIND: "[Exploration Quest]"
                }[quest_type]
                return f"{quest_header}\n{quest_type_text} {quest_text}\n"
            except Exception as e:
                logger.error(f"Error in NLP quest generation: {str(e)}", exc_info=True)

        # Fallback to templates
        templates = self.templates['quest_descriptions'][quest_type]
        quest_text = random.choice(templates).format(npc_name=npc_name)
        quest_header = "NEW QUEST"
        quest_type_text = {
            QuestType.DEFEAT: "[Combat Quest]",
            QuestType.TALK: "[Dialogue Quest]",
            QuestType.FIND: "[Exploration Quest]"
        }[quest_type]
        logger.info(f"Generated quest description with template: {quest_text}")
        return f"{quest_header}\n{quest_type_text} {quest_text}\n"

    def generate_npc_dialogue(self, npc_name, disposition, context=None):
        """
        Generates D&D-themed NPC dialogue.

        Args:
            npc_name (str): The name of the NPC.
            disposition (str): The NPC's attitude ('hostile', 'neutral', 'friendly', 'merchant', 'quest_giver').
            context (dict, optional): Additional context (e.g., health_percent, npc_type, quest_relevant).

        Returns:
            str: Formatted dialogue text.
        """
        context = context or {}
        npc_type = context.get('npc_type', disposition) # Fallback to disposition if npc_type not in context
        health_percentage = context.get('health_percent', 1.0)
        quest_relevant = context.get('quest_relevant', False)

        if get_transformers_available() and self.model and self.tokenizer:
            try:
                base_prompt = f"You are an NPC in a D&D fantasy game. Your name is {npc_name}, you are a {npc_type} and your current disposition is {disposition}. "
                if disposition == 'hostile':
                    base_prompt += f"You are aggressive and ready for a fight. "
                elif disposition == 'friendly':
                    base_prompt += f"You are welcoming and helpful. "
                elif npc_type == 'merchant':
                    base_prompt += f"You are keen to trade goods or offer services. "
                elif npc_type == 'quest_giver':
                    base_prompt += f"You have an important task for the adventurer. "
                else: # Neutral
                    base_prompt += f"You are cautious but open to interaction. "
                
                if health_percentage < 0.3:
                    base_prompt += f"You are badly wounded and desperate. "
                elif health_percentage < 0.6:
                    base_prompt += f"You appear injured and wary. "
                
                if quest_relevant:
                    base_prompt += f"The player is currently on a quest that involves you directly. "
                
                base_prompt += "Craft a single, concise, and thematic sentence that you would say to the player. Use medieval fantasy language. Do not use modern terms, game mechanics language, or mention D&D rules. Be immersive."

                inputs = self.tokenizer(base_prompt, return_tensors="pt", padding=True, truncation=True, max_length=200)
                attention_mask = inputs.get('attention_mask')
                input_ids = inputs.get('input_ids')

                if get_torch_available() and torch.cuda.is_available():
                    input_ids = input_ids.to("cuda")
                    if attention_mask is not None:
                        attention_mask = attention_mask.to("cuda")

                outputs = self.model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=50,
                    min_new_tokens=10,
                    temperature=0.8,
                    top_k=50,
                    top_p=0.95,
                    num_return_sequences=1,
                    do_sample=True,
                    no_repeat_ngram_size=2,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                generated_text_only = self.tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
                dialogue = self._clean_text(generated_text_only)
                dialogue = f'"{dialogue}"' # Add quotes
                logger.info(f"Generated NPC dialogue: {dialogue}")

                # Format based on NPC type
                if npc_type == 'enemy':
                    return f"{npc_name} growls: {dialogue}"
                elif npc_type == 'merchant':
                    return f"{npc_name} offers: {dialogue}"
                elif npc_type == 'quest_giver':
                    return f"{npc_name} proclaims: {dialogue}"
                return f"{npc_name} says: {dialogue}"
            except Exception as e:
                logger.error(f"Error in NLP dialogue generation: {str(e)}", exc_info=True)

        # Fallback to templates
        template_key = npc_type if npc_type in self.templates['npc_dialogues'] else disposition
        template_key = template_key if template_key in self.templates['npc_dialogues'] else 'neutral'
        dialogue = random.choice(self.templates['npc_dialogues'][template_key]).format(npc_name=npc_name)
        logger.info(f"Generated NPC dialogue with template: {dialogue}")
        if npc_type == 'enemy':
            return f"{npc_name} growls: \"{dialogue}\""
        elif npc_type == 'merchant':
            return f"{npc_name} offers: \"{dialogue}\""
        elif npc_type == 'quest_giver':
            return f"{npc_name} proclaims: \"{dialogue}\""
        return f"{npc_name} says: \"{dialogue}\""

    def generate_quest_completion(self, npc_name, context=None):
        """
        Generates D&D-themed quest completion text.

        Args:
            npc_name (str): The name of the NPC associated with the quest.
            context (dict, optional): Additional context (e.g., quest_type).

        Returns:
            str: Formatted quest completion text.
        """
        context = context or {}
        quest_type = context.get('quest_type', QuestType.DEFEAT) # Default to DEFEAT if not specified

        if get_transformers_available() and self.model and self.tokenizer:
            try:
                base_prompt = f"Generate a short, celebratory message for a D&D fantasy game. The player has just completed a {quest_type.name.lower()} quest involving a character named {npc_name}. "
                base_prompt += f"The message should be 1-2 sentences, written in a medieval fantasy tone, congratulating the player on their success. Do not use modern language or game mechanics terms. Be thematic and uplifting."

                inputs = self.tokenizer(base_prompt, return_tensors="pt", padding=True, truncation=True, max_length=150)
                attention_mask = inputs.get('attention_mask')
                input_ids = inputs.get('input_ids')

                if get_torch_available() and torch.cuda.is_available():
                    input_ids = input_ids.to("cuda")
                    if attention_mask is not None:
                        attention_mask = attention_mask.to("cuda")

                outputs = self.model.generate(
                    input_ids,
                    attention_mask=attention_mask,
                    max_new_tokens=60,
                    min_new_tokens=15,
                    temperature=0.7,
                    top_k=50,
                    top_p=0.95,
                    num_return_sequences=1,
                    do_sample=True,
                    no_repeat_ngram_size=2,
                    pad_token_id=self.tokenizer.eos_token_id
                )
                generated_text_only = self.tokenizer.decode(outputs[0][input_ids.shape[-1]:], skip_special_tokens=True)
                completion_text = self._clean_text(generated_text_only)
                logger.info(f"Generated quest completion text: {completion_text}")

                # Format with UI styling
                completion_header = "✓ QUEST COMPLETE"
                reward_text = "Reward: +10 XP, +5 Gold"
                return f"{completion_header}\n{completion_text}\n{reward_text}\n"
            except Exception as e:
                logger.error(f"Error in NLP quest completion generation: {str(e)}", exc_info=True)

        # Fallback to templates
        completion_text = random.choice(self.templates['quest_completion']).format(npc_name=npc_name)
        completion_header = "✓ QUEST COMPLETE"
        reward_text = "Reward: +10 XP, +5 Gold"
        logger.info(f"Generated quest completion text with template: {completion_text}")
        return f"{completion_header}\n{completion_text}\n{reward_text}\n"
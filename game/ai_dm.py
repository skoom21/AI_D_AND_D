import logging
logger = logging.getLogger("GameLogger")

from .game_state import GameState  # Import GameState from game_state.py
from .ai_strategies import Minimax, NPCAction, roll_dice  # Import our AI strategies
from .nlp_generator import NLPGenerator, QuestType  # Import NLP generator
import random
import uuid  # For generating unique quest IDs

class AIDM:
    def __init__(self, game):
        self.game = game
        self.minimax = Minimax(max_depth=3)  # Initialize Minimax with depth 3
        self.nlp_generator = NLPGenerator()  # Initialize NLP generator
        logger.info("AIDM instance created with Minimax AI strategies and NLP generator.")
        self.last_quest_type = None  # Track the last quest type for variety

    def update_quest(self):
        self.game.is_generating_text = True  # Set flag before NLP call
        logger.info(f"AIDM attempting to update quest. Current game state: {self.game.game_state.name}")
        # Reset flags at the beginning of an attempt to update a quest
        self.game.last_action_led_to_new_quest = False
        if self.game.game_state != GameState.PLAYING:  # Check game state
            self.game.current_quest = None
            logger.info("AIDM: Quest update skipped, game not in PLAYING state.")
            self.game.is_generating_text = False  # Clear flag
            return

        # Ensure narrative is initialized
        if not hasattr(self.game, 'narrative') or self.game.narrative is None:
            self.game.narrative = []

        # Find a living NPC to be the target of a quest
        living_npcs = [npc for npc in self.game.npcs if npc.health > 0]
        if living_npcs:
            # Choose a target NPC based on type preference
            target_npc = self._select_quest_npc(living_npcs)
            self.game.current_npc = target_npc  # Ensure game.current_npc is updated
            
            # Select a quest type, avoiding repeating the same type
            quest_type = self._select_quest_type(target_npc)
            self.last_quest_type = quest_type
            
            # Set a loading message in the narrative
            self.game.narrative = [f"Quest Giver is considering what task to give you..."]
            
            # Generate quest description using NLP - start the request
            self.nlp_generator.generate_quest_description(quest_type, target_npc.name)
            
            # WAIT for NLP generation to complete instead of using template immediately
            # Wait for a reasonable amount of time for generation to complete
            max_wait_time = 30  # seconds
            wait_time = 0
            wait_interval = 0.1  # seconds
            
            logger.info(f"Waiting for NLP generator to produce quest description for {target_npc.name}...")
            
            import time
            while self.nlp_generator.is_busy() and wait_time < max_wait_time:
                time.sleep(wait_interval)
                wait_time += wait_interval
            
            # Check if generation completed successfully
            quest_description = self.nlp_generator.get_result()
            
            # Only use template as fallback if generation failed completely
            if not quest_description:
                logger.warning(f"NLP generation for quest description timed out or failed. Using template fallback.")
                quest_description = f"Quest: Help {target_npc.name} with an important task."
            else:
                logger.info(f"Successfully received NLP generated quest description: {quest_description}")
            
            # Create a unique quest ID
            quest_id = str(uuid.uuid4())[:8]
            
            # Create quest object
            new_quest = {
                'id': quest_id,
                'type': quest_type,
                'target_npc': target_npc.name,
                'description': quest_description,
                'completed': False
            }
            
            # Store the quest in both game and player
            self.game.current_quest = new_quest
            self.game.player.add_quest(new_quest)
            
            logger.info(f"AIDM: New quest assigned: '{new_quest['description']}' targeting NPC: {target_npc.name}")
            self.game.last_action_led_to_new_quest = True  # Set flag for sound effect
            # Avoid adding duplicate "New Quest" messages
            new_quest_message = f"New Quest: {new_quest['description']}"
            
            # Completely rewrite the narrative check to avoid accessing narrative[-1] when narrative is None or empty
            if self.game.narrative is None or len(self.game.narrative) == 0:
                # Narrative is None or empty, safe to append
                self.game.narrative = [new_quest_message]
            else:
                # Narrative exists and has elements, check if the message is already there
                last_message = self.game.narrative[-1]
                # Ensure last_message is not None and is a string before using 'in' operator
                if last_message is None:
                    self.game.narrative.append(new_quest_message)
                elif isinstance(last_message, str) and new_quest_message not in last_message:
                    self.game.narrative.append(new_quest_message)
                elif not isinstance(last_message, str):
                    # If last_message is not a string (e.g., it's a list or other object), just append
                    self.game.narrative.append(new_quest_message)
        else:
            # No living NPCs left, so no quest can be assigned.
            # The game's update() method should handle transitioning to VICTORY state.
            self.game.current_quest = None
            logger.info("AIDM: No living NPCs available to assign a new quest. Current quest set to None.")
            if self.game.game_state == GameState.PLAYING:  # If still playing and no quests left
                # This could be a point to trigger victory if not handled elsewhere
                # For now, game.update() handles this transition
                pass
        self.game.is_generating_text = False  # Clear flag after NLP call

    def _select_quest_type(self, npc):
        """
        Select an appropriate quest type based on NPC characteristics
        and to ensure variety (don't repeat same quest type).
        """
        # Define weights for quest types based on NPC type
        weights = {
            "enemy": {QuestType.DEFEAT: 70, QuestType.TALK: 10, QuestType.FIND: 20},
            "merchant": {QuestType.TALK: 70, QuestType.FIND: 30, QuestType.DEFEAT: 0}, # DEFEAT weight is 0
            "quest_giver": {QuestType.TALK: 40, QuestType.FIND: 60, QuestType.DEFEAT: 0} # DEFEAT weight is 0
        }
        
        # Use default "enemy" weights if NPC type doesn't match known types
        npc_weights = weights.get(npc.npc_type, weights["enemy"])
        
        # Filter out quest types with 0 weight for the current NPC type
        available_quest_types = [qt for qt in QuestType if npc_weights.get(qt, 0) > 0]
        if not available_quest_types:
            # Fallback if no quest types are available (should not happen with current setup)
            logger.warning(f"No available quest types for NPC {npc.name} of type {npc.npc_type}. Defaulting to TALK.")
            return QuestType.TALK

        # Reduce weight of the last quest type to avoid repetition
        # Ensure the last_quest_type is actually available for this NPC
        if self.last_quest_type and self.last_quest_type in available_quest_types and npc_weights.get(self.last_quest_type, 0) > 0:
            # Create a mutable copy of the weights for this specific selection
            current_npc_weights = npc_weights.copy()
            current_npc_weights[self.last_quest_type] = max(1, current_npc_weights[self.last_quest_type] // 3) # Reduce by more, ensure at least 1
        else:
            current_npc_weights = npc_weights
            
        # Convert weights to a list for random.choices, only for available types
        quest_weights = [current_npc_weights[qt] for qt in available_quest_types]
        
        # Select a quest type based on weights
        selected_quest_type = random.choices(available_quest_types, weights=quest_weights, k=1)[0]
        logger.info(f"AIDM selected quest type: {selected_quest_type.name} for NPC type: {npc.npc_type}")
        
        return selected_quest_type

    def _select_quest_npc(self, living_npcs):
        """
        Select the most appropriate NPC for a new quest
        based on NPC type, player progress, etc.
        """
        # If there's only one NPC, select it
        if len(living_npcs) == 1:
            return living_npcs[0]
            
        # Prioritize quest-giving NPCs
        quest_givers = [npc for npc in living_npcs if npc.npc_type == "quest_giver"]
        if quest_givers:
            return random.choice(quest_givers)
            
        # Next priority: merchants if player might need healing or items
        if self.game.player.health < self.game.player.max_health * 0.5:
            merchants = [npc for npc in living_npcs if npc.npc_type == "merchant"]
            if merchants:
                return random.choice(merchants)
                
        # Default: pick a combat-oriented NPC (enemy)
        enemies = [npc for npc in living_npcs if npc.npc_type == "enemy"]
        if enemies:
            return random.choice(enemies)
            
        # If all else fails, pick a random NPC
        return random.choice(living_npcs)

    def generate_dialogue(self, npc):
        """Generate NPC dialogue based on NPC type, disposition and game context.
        Returns a list of dialogue lines."""
        self.game.is_generating_text = True  # Set flag before NLP call
        if not npc:
            self.game.is_generating_text = False  # Clear flag
            return ["There is no one here to speak with."]  # Return as list
            
        # Determine NPC's current disposition 
        disposition = npc.get_dialogue_disposition()
        
        # Prepare context for more specific dialogue generation
        context = {
            'health_percent': npc.health / npc.max_health if npc.max_health > 0 else 0,
            'quest_relevant': self.game.current_quest and 
                             self.game.current_quest.get('target_npc') == npc.name,
            'player_health': self.game.player.health / self.game.player.max_health if self.game.player.max_health > 0 else 0,
            'npc_type': npc.npc_type  # Pass npc_type to nlp_generator context
        }
        
        # Set a custom message in the game narrative to indicate loading
        self.game.narrative = [f"Waiting for {npc.name} to speak..."]
            
        # Request the NLP generator to generate dialogue
        self.nlp_generator.generate_npc_dialogue(npc.name, disposition, context)
        
        # WAIT for NLP generation to complete instead of immediately returning template
        # Wait for a reasonable amount of time for generation to complete
        max_wait_time = 30  # seconds
        wait_time = 0
        wait_interval = 0.1  # seconds
        
        logger.info(f"Waiting for NLP generator to produce dialogue for {npc.name}...")
        
        import time
        while self.nlp_generator.is_busy() and wait_time < max_wait_time:
            time.sleep(wait_interval)
            wait_time += wait_interval
        
        # Check if generation completed successfully
        dialogue_lines = self.nlp_generator.get_result()
        
        if not dialogue_lines:
            # Only use template as fallback if generation failed completely
            logger.warning(f"NLP generation for {npc.name} dialogue timed out or failed. Using template fallback.")
            default_dialogue = [f"{npc.name} {'glares at you silently' if disposition == 'hostile' else 'nods in greeting'}."]
            dialogue_lines = default_dialogue
        else:
            logger.info(f"Successfully received NLP generated dialogue for {npc.name}: {dialogue_lines}")
        
        self.game.is_generating_text = False  # Clear flag after NLP call
        return dialogue_lines  # Return the list of lines

    def complete_quest(self):
        """Handle quest completion based on quest type."""
        self.game.is_generating_text = True  # Set flag before NLP call
        if not self.game.current_quest:
            logger.warning("AIDM: complete_quest called but no current quest was active.")
            self.game.is_generating_text = False  # Clear flag
            self.game.last_action_led_to_quest_complete = False  # Ensure flag is reset
            return False
            
        completed_quest = self.game.current_quest
        target_npc_name = completed_quest.get('target_npc')
        quest_type = completed_quest.get('type')
        
        logger.info(f"AIDM: Completing quest of type {quest_type} for target {target_npc_name}")
        
        # Set a loading message in the narrative
        self.game.narrative = ["Completing quest..."]
        
        # Generate completion message - start the request
        self.nlp_generator.generate_quest_completion(target_npc_name)
        
        # WAIT for NLP generation to complete instead of using template immediately
        # Wait for a reasonable amount of time for generation to complete
        max_wait_time = 30  # seconds
        wait_time = 0
        wait_interval = 0.1  # seconds
        
        logger.info(f"Waiting for NLP generator to produce quest completion for {target_npc_name}...")
        
        import time
        while self.nlp_generator.is_busy() and wait_time < max_wait_time:
            time.sleep(wait_interval)
            wait_time += wait_interval
        
        # Check if generation completed successfully
        completion_message = self.nlp_generator.get_result()
        
        # Only use template as fallback if generation failed completely
        if not completion_message:
            logger.warning(f"NLP generation for quest completion timed out or failed. Using template fallback.")
            completion_message = f"✓ QUEST COMPLETE\nYou've successfully completed the quest for {target_npc_name}.\nReward: +10 XP, +5 Gold\n"
        else:
            logger.info(f"Successfully received NLP generated quest completion message: {completion_message}")
        
        # Ensure narrative is initialized before modifying it
        if not hasattr(self.game, 'narrative') or self.game.narrative is None:
            self.game.narrative = []
            
        # Add completion message to narrative instead of replacing it
        if completion_message is not None:
            self.game.narrative.append(completion_message)
        
        # Mark quest as completed in player's quest log
        self.game.player.complete_quest(completed_quest.get('id'))
        
        # Clear current quest
        self.game.current_quest = None
        self.game.last_action_led_to_quest_complete = True  # Set flag for sound effect
        
        # Check if all NPCs are defeated after completing the quest
        all_npcs_defeated = all(npc.health <= 0 for npc in self.game.npcs)
        if all_npcs_defeated and self.game.npcs:  # ensure npcs list was not empty initially
            if self.game.game_state == GameState.PLAYING:
                logger.info("AIDM: Quest completed and all NPCs are defeated. Victory condition met.")
        elif self.game.game_state == GameState.PLAYING:  # If not victory, try to get a new quest
            logger.info("AIDM: Quest completed, attempting to update for a new quest.")
            self.update_quest()
        
        self.game.is_generating_text = False  # Clear flag before returning
        return True

    def determine_npc_action(self, npc):
        """
        Uses Minimax algorithm to determine the best action for an NPC.
        
        Returns a tuple of (action, narrative_description)
        """
        if not npc or npc.health <= 0:
            logger.warning("AIDM: Attempted to determine action for invalid or defeated NPC.")
            return None, "The NPC is no longer able to act."
        
        # Check if NPC is the current quest target
        is_quest_target = False
        if self.game.current_quest and self.game.current_quest.get('target_npc') == npc.name:
            is_quest_target = True
        
        # Use Minimax to get the best action
        logger.info(f"AIDM determining action for NPC {npc.name} (quest target: {is_quest_target})")
        best_action = self.minimax.get_best_action(self.game.player, npc, is_quest_target)
        
        # Set the NPC's action
        npc.set_action(best_action)
        
        # Get a narrative description for this action
        action_description = self.minimax.get_action_description(best_action, npc.name)
        
        logger.info(f"AIDM chose action {best_action.name} for NPC {npc.name}")
        return best_action, action_description
        
    def adjust_quest_difficulty(self):
        """
        Dynamically adjusts quest difficulty based on player performance.
        Called periodically to potentially spawn new NPCs or modify existing ones.
        """
        # Only adjust if we're in PLAYING state
        if self.game.game_state != GameState.PLAYING:
            return
            
        # Check player health percentage
        player_health_percent = self.game.player.health / self.game.player.max_health
        
        # Count living NPCs
        living_npcs = [npc for npc in self.game.npcs if npc.health > 0]
        
        # If player is doing very well (high health) and few NPCs left, increase difficulty
        if player_health_percent > 0.7 and len(living_npcs) <= 1:
            # Possible difficulty adjustments:
            # 1. Spawn a new NPC
            if len(living_npcs) == 0:
                # All NPCs defeated but player has high health - spawn a new stronger NPC
                new_npc = self._create_new_npc("Troll", 70, strength=12)  # Stronger NPC
                self.game.npcs.append(new_npc)
                self.game.current_npc = new_npc
                self.game.narrative.append(f"A {new_npc.name} appears, drawn by the sounds of battle!")
                logger.info(f"AIDM spawned new stronger NPC {new_npc.name} for difficulty adjustment")
                
                # Update quest to target the new NPC
                self.update_quest()
            # 2. Strengthen existing NPC
            elif len(living_npcs) == 1 and living_npcs[0].health < living_npcs[0].max_health * 0.3:
                # Existing NPC is nearly defeated - give it a second wind
                npc = living_npcs[0]
                heal_amount = int(npc.max_health * 0.3)  # Heal by 30% of max health
                npc.heal(heal_amount)
                self.game.narrative.append(f"The {npc.name} finds renewed strength and vigor!")
                logger.info(f"AIDM strengthened existing NPC {npc.name} for difficulty adjustment")
        # If player is struggling (low health), possibly add help
        elif player_health_percent < 0.3 and len(living_npcs) > 0:
            # Consider spawning a friendly NPC who might help
            spawn_chance = 0.3  # 30% chance to spawn helper
            if random.random() < spawn_chance:
                # Create a friendly merchant who can offer healing
                merchant_npc = self._create_new_npc("Merchant", 30, npc_type="merchant", 
                                                   disposition="friendly", strength=3)
                self.game.npcs.append(merchant_npc)
                self.game.narrative.append(f"A wandering {merchant_npc.name} appears, offering assistance!")
                logger.info(f"AIDM spawned friendly merchant NPC to help struggling player")
    
    def _create_new_npc(self, name, health, npc_type="enemy", disposition="hostile", strength=5):
        """Helper method to create a new NPC with the given parameters."""
        from .npc import NPC
        return NPC(health=health, name=name, max_health=health, 
                   npc_type=npc_type, disposition=disposition, strength=strength)

    def check_nlp_results(self):
        """
        Check if any NLPGenerator tasks have completed, and update the game state accordingly.
        This should be called periodically as part of the game update loop.
        """
        # Don't try to get results if still generating
        if self.nlp_generator.is_busy():
            return

        # Check if there's a result available
        result = self.nlp_generator.get_result()
        if not result:
            return
            
        # A result is available, figure out what type it is and update the appropriate parts
        # For now, we just log that a result was received
        logger.info(f"AIDM received result from NLP generator: {result}")
        
        # If it's a quest description and we have a current quest using a placeholder
        if self.game.current_quest and isinstance(result, str) and "NEW QUEST" in result:
            # This looks like a quest description, update the current quest
            if "Quest: Help" in self.game.current_quest['description']:
                logger.info("AIDM updating quest description with NLP-generated content")
                # Update the quest description
                self.game.current_quest['description'] = result
                
                # Update the narrative message about the new quest
                for i, message in enumerate(self.game.narrative):
                    if message and isinstance(message, str) and message.startswith("New Quest:"):
                        self.game.narrative[i] = f"New Quest: {result}"
                        break
        
        # If it's dialogue lines (a list of strings) and there's an active dialogue
        elif isinstance(result, list) and all(isinstance(item, str) for item in result) and self.game.active_dialogue_npc:
            # This looks like dialogue lines for the active NPC
            npc = self.game.active_dialogue_npc
            
            # Check if the dialogue is using template text
            if npc.using_template_dialogue:
                # Template dialogue is being used, replace with generated content
                logger.info(f"AIDM updating active dialogue with NPC {npc.name} with generated content")
                
                # Store current position
                old_index = npc.current_dialogue_index
                
                # Replace pending dialogue lines with generated content
                npc.pending_dialogue_lines = result
                
                # Set flag to true to indicate the dialog was updated
                self.game.dialogue_was_updated = True
                
                # Reset index if we've already shown the template
                if old_index > 0:
                    # We've already shown the first template line, start from beginning of new content
                    npc.current_dialogue_index = 0
                    logger.info(f"Resetting dialogue index for {npc.name} to show full generated content")
                
                # Mark as no longer using template
                npc.using_template_dialogue = False
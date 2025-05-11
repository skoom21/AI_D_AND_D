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
        logger.info(f"AIDM attempting to update quest. Current game state: {self.game.game_state.name}")
        # Reset flags at the beginning of an attempt to update a quest
        self.game.last_action_led_to_new_quest = False
        if self.game.game_state != GameState.PLAYING:  # Check game state
            self.game.current_quest = None
            logger.info("AIDM: Quest update skipped, game not in PLAYING state.")
            return

        # Find a living NPC to be the target of a quest
        living_npcs = [npc for npc in self.game.npcs if npc.health > 0]
        if living_npcs:
            # Choose a target NPC based on type preference
            target_npc = self._select_quest_npc(living_npcs)
            self.game.current_npc = target_npc  # Ensure game.current_npc is updated
            
            # Select a quest type, avoiding repeating the same type
            quest_type = self._select_quest_type(target_npc)
            self.last_quest_type = quest_type
            
            # Generate quest description using NLP
            quest_description = self.nlp_generator.generate_quest_description(quest_type, target_npc.name)
            
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
            self.game.last_action_led_to_new_quest = True # Set flag for sound effect
            # Avoid adding duplicate "New Quest" messages if narrative already has it
            new_quest_message = f"New Quest: {new_quest['description']}"
            if not self.game.narrative or new_quest_message not in self.game.narrative[-1]:
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
        """Generate NPC dialogue based on NPC type, disposition and game context."""
        if not npc:
            return "There is no one here to speak with."
            
        # Determine NPC's current disposition 
        disposition = npc.get_dialogue_disposition()
        
        # Prepare context for more specific dialogue generation
        context = {
            'health_percent': npc.health / npc.max_health,
            'quest_relevant': self.game.current_quest and 
                             self.game.current_quest.get('target_npc') == npc.name,
            'player_health': self.game.player.health / self.game.player.max_health
        }
        
        # Generate dialogue using NLP
        dialogue = self.nlp_generator.generate_npc_dialogue(npc.name, disposition, context)
        
        logger.info(f"AIDM generated dialogue for NPC {npc.name}: '{dialogue}'")
        return dialogue

    def complete_quest(self):
        """Handle quest completion based on quest type."""
        if not self.game.current_quest:
            logger.warning("AIDM: complete_quest called but no current quest was active.")
            self.game.last_action_led_to_quest_complete = False # Ensure flag is reset
            return False
            
        completed_quest = self.game.current_quest
        target_npc_name = completed_quest.get('target_npc')
        quest_type = completed_quest.get('type')
        
        logger.info(f"AIDM: Completing quest of type {quest_type} for target {target_npc_name}")
        
        # Generate completion message
        completion_message = self.nlp_generator.generate_quest_completion(target_npc_name)
        self.game.narrative = [completion_message]  # Reset narrative with completion message
        
        # Mark quest as completed in player's quest log
        self.game.player.complete_quest(completed_quest.get('id'))
        
        # Clear current quest
        self.game.current_quest = None
        self.game.last_action_led_to_quest_complete = True # Set flag for sound effect
        
        # Check if all NPCs are defeated after completing the quest
        all_npcs_defeated = all(npc.health <= 0 for npc in self.game.npcs)
        if all_npcs_defeated and self.game.npcs:  # ensure npcs list was not empty initially
            if self.game.game_state == GameState.PLAYING:
                logger.info("AIDM: Quest completed and all NPCs are defeated. Victory condition met.")
        elif self.game.game_state == GameState.PLAYING:  # If not victory, try to get a new quest
            logger.info("AIDM: Quest completed, attempting to update for a new quest.")
            self.update_quest()
            
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
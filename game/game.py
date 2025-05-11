import logging
logger = logging.getLogger("GameLogger")  # Get the logger instance

from .player import Player
from .npc import NPC
from .ai_dm import AIDM
from .game_state import GameState  # Import GameState from game_state.py
from .ai_strategies import NPCAction, roll_dice  # Import NPCAction enum and dice rolls
from .nlp_generator import QuestType  # Import quest types
import random  # Add random import for NPC selection

class Game:
    def __init__(self):
        logger.info("Game object initializing.")
        self.game_state = GameState.PLAYING  # Initialize game state
        self.last_action_led_to_new_quest = False  # Flag for sound triggers
        self.last_action_led_to_quest_complete = False  # Flag for sound triggers

        # Initialize player with starting stats
        self.player = Player(health=100, max_health=100, strength=10)

        # Initialize NPCs with varied types and stats
        self.npcs = [
            NPC(health=50, name="Goblin", max_health=50, npc_type="enemy", strength=7),
            NPC(health=30, name="Merchant", max_health=30, npc_type="merchant", 
               disposition="neutral", strength=3),
            NPC(health=40, name="Quest Giver", max_health=40, npc_type="quest_giver", 
               disposition="friendly", strength=5)
        ]
        
        if self.npcs:
            logger.info(f"NPCs list initialized in Game. Count: {len(self.npcs)}.")
        else:
            logger.info("No NPCs initialized in Game.") # Should be warning or handled

        self.current_quest = None
        self.narrative = ["You find yourself in a forest clearing."]
        self.current_npc = None # Initialize current_npc to None
        self.ai_dm = None # Initialize ai_dm to None

        if not self.npcs:
            self.narrative.append("The world feels strangely empty. No challenges await.")
            self.game_state = GameState.VICTORY
            logger.info("No NPCs found at game start. Setting state to VICTORY.")
        else:
            # NPCs exist, set up AI and initial quest
            # Initialize AI-DM first, as it will guide the initial NPC and quest
            self.ai_dm = AIDM(self)
            logger.info("AI-DM initialized in Game.")

            # Let AIDM determine the initial quest.
            # update_quest() will set self.current_npc to the quest's target NPC
            # and append the quest description to self.narrative.
            if self.game_state == GameState.PLAYING: # Should be true here
                self.ai_dm.update_quest()
                
                # Log the NPC that AIDM selected for the first quest
                if self.current_npc:
                    logger.info(f"Initial game focus: current_npc set to '{self.current_npc.name}' by AIDM for the first quest.")
                else:
                    # This case means AIDM's update_quest didn't set a current_npc
                    logger.warning("AIDM's initial update_quest did not result in a current_npc being set.")
                    # Fallback narrative if AIDM didn't provide a quest/NPC focus
                    if len(self.narrative) == 1 and self.narrative[0] == "You find yourself in a forest clearing.":
                        self.narrative.append("The path ahead is unclear. Explore your surroundings.")
            # If game_state was not PLAYING (e.g. somehow set to VICTORY already), no quest update.
            
        # Track turns for quest difficulty adjustment
        self.turn_counter = 0
        
        # Track player's inventory and gold
        self.inventory = []
        self.gold = 10  # Start with a small amount of gold

    def get_display_text(self):
        logger.debug(f"Getting display text for game state: {self.game_state.name}")
        if self.game_state == GameState.PLAYING:
            # Enhanced options based on current NPC type
            options = ["Move", "Attack", "Interact"]
            
            # Add special options based on NPC type
            if self.current_npc and self.current_npc.npc_type == "merchant":
                options = ["Move", "Talk", "Trade"]
            elif self.current_npc and self.current_npc.npc_type == "quest_giver":
                options = ["Move", "Talk", "Accept Quest"]
            
            return self.narrative, options
        elif self.game_state == GameState.GAME_OVER:
            return self.narrative + ["Game Over. Press Q to quit."], []
        elif self.game_state == GameState.VICTORY:
            return self.narrative + ["You are victorious! Press Q to quit."], []
        return self.narrative, []

    def handle_input(self, choice):
        logger.info(f"Handling player input: {choice} in state: {self.game_state.name}")
        if self.game_state != GameState.PLAYING:
            logger.warning(f"Input {choice} ignored, game state is {self.game_state.name}")
            return

        if choice == 1:  # Move
            self.player_move()
        elif choice == 2:  # Attack/Talk
            if self.current_npc and self.current_npc.npc_type in ["merchant", "quest_giver"]:
                self.player_talk()  # Talk for non-combat NPCs
            else:
                self.player_attack()  # Attack for enemies
        elif choice == 3:  # Interact/Trade/Accept Quest
            if self.current_npc and self.current_npc.npc_type == "merchant":
                self.player_trade()
            elif self.current_npc and self.current_npc.npc_type == "quest_giver":
                self.player_accept_quest()
            else:
                self.player_interact()
        else:
            self.narrative.append("Invalid choice. Try again.")
            logger.warning(f"Invalid input choice by player: {choice}")
        
        if self.game_state == GameState.PLAYING:
            self.update()

    def player_move(self):
        logger.info("Player chose to move.")
        if not self.current_npc:
            self.narrative = ["You explore the quiet clearing."]
            logger.info("Player moves, but no current NPC.")
            return

        # Select a different random NPC to encounter
        other_npcs = [npc for npc in self.npcs if npc.health > 0 and npc != self.current_npc]
        
        if other_npcs:
            self.current_npc = random.choice(other_npcs)
            self.narrative = [f"You move to another area and encounter a {self.current_npc.name}."]
            
            # Add description based on NPC type
            if self.current_npc.npc_type == "merchant":
                self.narrative.append("They appear to be selling various goods and potions.")
            elif self.current_npc.npc_type == "quest_giver":
                self.narrative.append("They look like they might have a task for an adventurer like you.")
            elif self.current_npc.npc_type == "enemy":
                self.narrative.append(f"The {self.current_npc.name} watches you with hostile intent.")
        else:
            self.narrative = ["You explore the forest clearing.",
                             f"The {self.current_npc.name} watches you closely."]
            
        logger.info(f"Player moves. Current NPC now: {self.current_npc.name} ({self.current_npc.npc_type})")

    def player_attack(self):
        logger.info("Player chose to attack.")
        if not self.current_npc:
            self.narrative = ["There is no one to attack."]
            logger.warning("Player attack attempt, but no current NPC.")
            return

        if self.current_npc.health > 0:
            logger.info(f"Player attacking {self.current_npc.name} (Health: {self.current_npc.health}).")
            
            # Use dice roll for attack - d20 roll + strength modifier
            attack_roll = self.player.attack_roll()
            self.narrative = [f"You roll a {attack_roll} for your attack!"]
            
            # Determine hit success and damage
            if attack_roll >= 10:  # Simple hit threshold
                # Calculate damage using dice (1d6 + strength modifier)
                strength_modifier = self.player.strength // 2 - 5  # Similar to D&D modifier
                damage_roll = roll_dice(6, 1, strength_modifier)
                damage_dealt = max(1, damage_roll)  # Minimum 1 damage
                
                # Apply damage, which might be reduced if NPC is defending
                actual_damage = self.current_npc.take_damage(damage_dealt, self.player.strength)
                damage_msg = "reduced " if self.current_npc.is_defending else ""
                
                self.narrative.append(f"Hit! You deal {actual_damage} {damage_msg}damage to the {self.current_npc.name}.")
                self.narrative.append(f"{self.current_npc.name} health: {self.current_npc.health}/{self.current_npc.max_health}")
            else:
                self.narrative.append(f"Miss! Your attack fails to connect with the {self.current_npc.name}.")
            
            if self.current_npc.health <= 0:
                self.narrative.append(f"You defeated the {self.current_npc.name}!")
                logger.info(f"NPC {self.current_npc.name} defeated by player.")
                
                # Check if this NPC was part of current quest
                if self.current_quest and self.current_quest.get('target_npc') == self.current_npc.name:
                    if self.current_quest.get('type') == QuestType.DEFEAT:
                        self.ai_dm.complete_quest()
            else:
                # NPC is still alive, use AI to determine its action
                logger.info(f"NPC {self.current_npc.name} (Health: {self.current_npc.health}) deciding action...")
                
                # Get best action using Minimax
                action, action_description = self.ai_dm.determine_npc_action(self.current_npc)
                
                # Add action description to narrative
                self.narrative.append(action_description)
                
                # Apply effects based on NPC action
                if action == NPCAction.ATTACK:
                    # Roll for NPC attack
                    npc_attack_roll = roll_dice(20, 1, self.current_npc.strength // 2 - 5)
                    self.narrative.append(f"The {self.current_npc.name} rolls a {npc_attack_roll} for their attack!")
                    
                    if npc_attack_roll >= 10:  # Simple hit threshold
                        # Calculate damage (1d4 + strength modifier)
                        npc_strength_mod = self.current_npc.strength // 2 - 5
                        damage_roll = roll_dice(4, 1, npc_strength_mod)
                        damage = max(1, damage_roll)  # Minimum 1 damage
                        
                        actual_damage = self.player.take_damage(damage, self.current_npc.strength)
                        self.narrative.append(f"Hit! The {self.current_npc.name} strikes you for {actual_damage} damage!")
                        self.narrative.append(f"Your health: {self.player.health}/{self.player.max_health}")
                    else:
                        self.narrative.append(f"Miss! The {self.current_npc.name}'s attack fails to hit you.")
                        
                elif action == NPCAction.DEFEND:
                    self.narrative.append(f"The {self.current_npc.name} is now defending, reducing incoming damage.")
                    # The defense effect is handled in the NPC's take_damage method
                elif action == NPCAction.FLEE:
                    flee_roll = roll_dice(20, 1, 0)  # d20 roll for flee attempt
                    flee_success = flee_roll > 15  # 25% chance of successful flee
                    
                    if flee_success:
                        self.narrative.append(f"The {self.current_npc.name} successfully flees from battle!")
                        self.current_npc.health = 0  # Remove NPC from battle
                        logger.info(f"NPC {self.current_npc.name} successfully fled from battle")
                    else:
                        self.narrative.append(f"The {self.current_npc.name} tries to flee but fails! (Rolled {flee_roll}, needed >15)")
                        logger.info(f"NPC {self.current_npc.name} failed to flee, rolled {flee_roll}")
                
                if self.player.health <= 0:
                    self.narrative.append("You have fallen in battle.")
                    logger.info("Player defeated during NPC action.")
        else:
            self.narrative = [f"The {self.current_npc.name} is already defeated."]
            logger.info(f"Player attempts to attack already defeated NPC: {self.current_npc.name}")

    def player_talk(self):
        """Talk to NPCs specifically for dialogue-based interactions."""
        logger.info(f"Player chose to talk with {self.current_npc.name} ({self.current_npc.npc_type}).")
        
        if not self.current_npc:
            self.narrative = ["There is no one to talk to."]
            return
            
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to speak."]
            return
            
        # Generate dialogue using NLP-enhanced AIDM
        dialogue = self.ai_dm.generate_dialogue(self.current_npc)
        self.narrative = [dialogue]
        
        # Check if this satisfies a TALK quest
        if (self.current_quest and 
            self.current_quest.get('type') == QuestType.TALK and 
            self.current_quest.get('target_npc') == self.current_npc.name):
            # Complete the "talk to" quest
            self.ai_dm.complete_quest()
            logger.info(f"Completed TALK quest with {self.current_npc.name}")

    def player_interact(self):
        logger.info("Player chose to interact.")
        if not self.current_npc:
            self.narrative = ["There is no one to interact with."]
            logger.warning("Player interaction attempt, but no current NPC.")
            return

        if self.current_npc.health > 0:
            # Generate dialogue based on the NPC's state
            logger.info(f"Player interacting with {self.current_npc.name}.")
            dialogue = self.ai_dm.generate_dialogue(self.current_npc)
            self.narrative = [dialogue]
            
            # Check if this satisfies a FIND quest (representing the player finding something)
            if (self.current_quest and 
                self.current_quest.get('type') == QuestType.FIND and 
                self.current_quest.get('target_npc') == self.current_npc.name):
                # Complete the "find" quest
                self.ai_dm.complete_quest()
                logger.info(f"Completed FIND quest with {self.current_npc.name}")
        else:
            self.narrative = [f"The {self.current_npc.name} is defeated and cannot speak."]
            logger.info(f"Player attempts to interact with defeated NPC: {self.current_npc.name}")

    def player_trade(self):
        """Trade with merchant NPCs."""
        logger.info(f"Player chose to trade with {self.current_npc.name}.")
        
        if not self.current_npc or self.current_npc.npc_type != "merchant":
            self.narrative = ["There is no merchant to trade with."]
            return
            
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to trade."]
            return
            
        # Simple healing trade for demonstration
        self.narrative = [f"The {self.current_npc.name} offers you a healing potion."]
        heal_amount = 20
        self.player.heal(heal_amount)
        self.narrative.append(f"You consume the potion and recover {heal_amount} health.")
        self.narrative.append(f"Your health: {self.player.health}/{self.player.max_health}")
        
        logger.info(f"Player traded with merchant and healed for {heal_amount} points")

    def player_accept_quest(self):
        """Accept a quest from a quest giver NPC."""
        logger.info(f"Player chose to accept quest from {self.current_npc.name}.")
        
        if not self.current_npc or self.current_npc.npc_type != "quest_giver":
            self.narrative = ["There is no quest giver here."]
            return
            
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to give quests."]
            return
            
        # Force update of quest targeting this NPC
        old_quest = self.current_quest
        self.current_quest = None
        self.ai_dm.update_quest()  # This method in AIDM should set the flag if a quest is made
        
        if self.current_quest:
            self.narrative = [f"You accept a new quest from {self.current_npc.name}:"]
            self.narrative.append(self.current_quest.get('description'))
            logger.info(f"Player accepted new quest: {self.current_quest.get('description')}")
        else:
            # If no new quest could be generated, restore the old one
            self.current_quest = old_quest
            self.narrative = [f"The {self.current_npc.name} has no new quests for you at this time."]
            logger.info("No new quest could be generated for player")

    def update(self):
        logger.debug(f"Updating game state. Current state: {self.game_state.name}, Player Health: {self.player.health}")
        if self.game_state != GameState.PLAYING:
            logger.debug(f"Game update skipped, game state is {self.game_state.name}")
            return

        # Increment turn counter
        self.turn_counter += 1
        
        # Check for player defeat
        if self.player.health <= 0:
            self.game_state = GameState.GAME_OVER
            self.narrative = ["Game Over. You have been defeated."]
            self.current_quest = None
            logger.info("Player health <= 0. Game state changed to GAME_OVER.")
            return

        # Check for victory condition
        all_npcs_defeated = all(npc.health <= 0 for npc in self.npcs)
        if not self.current_quest and all_npcs_defeated and self.npcs:
            self.game_state = GameState.VICTORY
            self.narrative = ["All threats have been neutralized. You are victorious!"]
            logger.info("All NPCs defeated and no current quest. Game state changed to VICTORY.")
            return

        # Every 3 turns, consider adjusting quest difficulty
        if self.turn_counter % 3 == 0:
            logger.info(f"Turn {self.turn_counter}: Evaluating quest difficulty")
            self.ai_dm.adjust_quest_difficulty()

        # If current NPC is defeated, find a new one
        if self.current_npc and self.current_npc.health <= 0:
            living_npcs = [npc for npc in self.npcs if npc.health > 0]
            if living_npcs:
                self.current_npc = random.choice(living_npcs)
                self.narrative.append(f"You encounter a {self.current_npc.name}.")
                logger.info(f"Current NPC defeated, switching to new NPC: {self.current_npc.name}")
            else:
                self.current_npc = None
                logger.info("All NPCs defeated, no current NPC available")

        # Update quest if needed
        if not self.current_quest and any(npc.health > 0 for npc in self.npcs):
            logger.info("No current quest and living NPCs exist. AI-DM updating quest.")
            self.ai_dm.update_quest()
        
        elif not any(npc.health > 0 for npc in self.npcs) and self.npcs:
            if self.game_state == GameState.PLAYING:
                self.game_state = GameState.VICTORY
                self.narrative = ["The last foe is vanquished. Victory is yours!"]
                self.current_quest = None
                logger.info("All NPCs defeated (no specific quest was active or just completed). Game state changed to VICTORY.")
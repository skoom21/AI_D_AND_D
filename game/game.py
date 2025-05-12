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
        self.is_generating_text = False  # Flag for NLP generation in progress
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
            logger.info("No NPCs initialized in Game.")

        self.current_quest = None
        # Initial narrative and current_npc selection
        if not self.npcs:
            self.current_npc = None
            self.narrative = ["You find yourself in a forest clearing.", "The world feels strangely empty. No challenges await."]
            self.game_state = GameState.VICTORY  # Or some other appropriate state like NO_NPCS
            logger.info("No NPCs found at game start. Setting state appropriately.")
        else:
            self.narrative = ["You find yourself in a forest clearing."]  # Base narrative for when NPCs exist
            # Filter for living NPCs only for initial selection
            living_npcs = [npc for npc in self.npcs if npc.health > 0]
            if not living_npcs:  # All NPCs are somehow not alive at start
                self.current_npc = None
                self.narrative.append("The clearing is eerily silent. There's no one around.")
                self.game_state = GameState.VICTORY  # Or appropriate state
                logger.info("No living NPCs found at game start. Setting state appropriately.")
            else:
                quest_givers = [npc for npc in living_npcs if npc.npc_type == "quest_giver"]
                enemy_npcs = [npc for npc in living_npcs if npc.npc_type == "enemy"]

                if quest_givers:
                    self.current_npc = random.choice(quest_givers)
                    self.narrative.append(f"A figure of interest, {self.current_npc.name}, seems to acknowledge your presence.")
                    logger.info(f"Initial current_npc set to Quest Giver: {self.current_npc.name}")
                elif enemy_npcs:
                    self.current_npc = random.choice(enemy_npcs)
                    self.narrative.append(f"A hostile {self.current_npc.name} blocks your path, eyeing you warily!")
                    logger.info(f"Initial current_npc set to Enemy: {self.current_npc.name}")
                else:  # Fallback if no quest givers or enemies, but living NPCs exist
                    self.current_npc = random.choice(living_npcs)
                    self.narrative.append(f"You notice {self.current_npc.name} nearby.")
                    logger.info(f"Initial current_npc set to Fallback NPC: {self.current_npc.name}")

        # Initialize AI-DM
        self.ai_dm = AIDM(self)
        logger.info("AI-DM initialized in Game.")

        # Call update_quest if game is playable and there's an NPC to interact with
        if self.game_state == GameState.PLAYING and self.current_npc:
            self.ai_dm.update_quest()
        elif self.game_state == GameState.PLAYING and not self.current_npc:  # If game is playing but no NPC was selected (e.g. all dead)
            if "The world feels strangely empty. No challenges await." not in self.narrative and \
               "The clearing is eerily silent. There's no one around." not in self.narrative:
                self.narrative.append("No challenges await.")
            # Ensure game state is not PLAYING if no NPCs
            self.game_state = GameState.VICTORY  # Or a more specific state like NO_LIVING_NPCS

        logger.info("Game object initialized successfully.")
        
        # Track turns for quest difficulty adjustment
        self.turn_counter = 0
        
        # Track player's inventory and gold
        self.inventory = []
        self.gold = 10

        # New attributes for dialogue management
        self.active_dialogue_npc = None  # Stores the NPC currently in dialogue
        self.awaiting_typewriter_completion = False  # True if a line is currently being typed out
        self.dialogue_requires_player_advance = False  # True if waiting for player to press Enter for next line
        self.play_sound_event = None  # For triggering sounds from main.py: "dialogue_start", "dialogue_advance", "dialogue_end"

    def _start_dialogue_with_npc(self, npc, dialogue_lines):
        """Initiates a dialogue sequence with an NPC."""
        if not dialogue_lines:
            self.narrative = [f"The {npc.name} has nothing to say."]
            self.play_sound_event = "dialogue_end"  # Or a neutral sound
            return

        logger.info(f"Starting dialogue with {npc.name}. Lines: {dialogue_lines}")
        self.active_dialogue_npc = npc
        npc.pending_dialogue_lines = dialogue_lines
        npc.current_dialogue_index = 0
        self.dialogue_requires_player_advance = False  # First line starts automatically via typewriter
        self.play_sound_event = "dialogue_start"
        self._advance_dialogue()

    def _advance_dialogue(self):
        """Advances to the next line of dialogue for the active_dialogue_npc."""
        if not self.active_dialogue_npc or not self.active_dialogue_npc.pending_dialogue_lines:
            self._end_dialogue()
            return

        npc = self.active_dialogue_npc
        if npc.current_dialogue_index < len(npc.pending_dialogue_lines):
            line = npc.pending_dialogue_lines[npc.current_dialogue_index]
            
            if npc.current_dialogue_index == 0:  # First line of this interaction
                prefix = f"{npc.name} says:"
                current_disposition = npc.get_dialogue_disposition()
                if npc.npc_type == 'enemy' or current_disposition == 'hostile':
                    prefix = f"{npc.name} growls:"
                elif npc.npc_type == 'merchant':
                    prefix = f"{npc.name} offers:"
                elif npc.npc_type == 'quest_giver':
                    prefix = f"{npc.name} proclaims:"
                # Add quotes around the dialogue line itself
                self.narrative = [f"{prefix} \"{line}\""]
            else:  # Subsequent lines
                self.narrative = [f"\"{line}\""]  # Just the line, quoted

            logger.debug(f"Advancing dialogue with {npc.name}, line {npc.current_dialogue_index}: {self.narrative[0]}")
            self.awaiting_typewriter_completion = True  # Signal main.py to use typewriter
            self.dialogue_requires_player_advance = False 
            npc.current_dialogue_index += 1
        else:
            self._end_dialogue()

    def _end_dialogue(self):
        """Ends the current dialogue sequence."""
        npc_that_was_in_dialogue = self.active_dialogue_npc
        
        if self.active_dialogue_npc:
            logger.info(f"Dialogue with {self.active_dialogue_npc.name} ended.")
            self.active_dialogue_npc.pending_dialogue_lines = []
            self.active_dialogue_npc.current_dialogue_index = 0
        
        self.active_dialogue_npc = None
        self.awaiting_typewriter_completion = False
        self.dialogue_requires_player_advance = False
        self.play_sound_event = "dialogue_end"
        
        # Check for quest completion after dialogue ends
        if npc_that_was_in_dialogue and self.current_quest:
            if self.current_quest.get('target_npc') == npc_that_was_in_dialogue.name:
                quest_type = self.current_quest.get('type')
                if quest_type == QuestType.TALK:
                    logger.info(f"TALK quest with {npc_that_was_in_dialogue.name} completed after dialogue.")
                    self.ai_dm.complete_quest() 
                elif quest_type == QuestType.FIND and npc_that_was_in_dialogue.npc_type != "enemy":
                    logger.info(f"FIND quest involving {npc_that_was_in_dialogue.name} completed after dialogue.")
                    self.ai_dm.complete_quest()
        
        if not self.last_action_led_to_quest_complete:
            self.narrative = [f"You finish speaking with {npc_that_was_in_dialogue.name if npc_that_was_in_dialogue else 'them'}."]

    def on_typewriter_line_completed(self):
        """Called by main.py when typewriter effect finishes for a dialogue line."""
        logger.debug("Typewriter line completed.")  # Existing debug log
        self.awaiting_typewriter_completion = False
        if self.active_dialogue_npc:
            idx = self.active_dialogue_npc.current_dialogue_index
            line_count = len(self.active_dialogue_npc.pending_dialogue_lines)
            # Added INFO log
            logger.info(f"on_typewriter_line_completed: NPC: {self.active_dialogue_npc.name}, current_idx: {idx}, line_count: {line_count}, dialogue_requires_player_advance_before_set: {self.dialogue_requires_player_advance}")

            if idx < line_count:
                self.dialogue_requires_player_advance = True
                # Added INFO log
                logger.info(f"on_typewriter_line_completed: Set dialogue_requires_player_advance = True for {self.active_dialogue_npc.name}")
            else:
                # Added INFO log
                logger.info(f"on_typewriter_line_completed: All lines done for {self.active_dialogue_npc.name}. Ending dialogue.")
                self._end_dialogue()
        else:
            logger.warning("on_typewriter_line_completed called without active_dialogue_npc")

    def get_display_text(self):
        logger.debug(f"Getting display text. Game state: {self.game_state.name}. Active dialogue NPC: {self.active_dialogue_npc.name if self.active_dialogue_npc else 'None'}")
        
        options = []
        current_narrative = self.narrative 

        if self.active_dialogue_npc and (self.dialogue_requires_player_advance or self.awaiting_typewriter_completion):
            options = [] 
        elif self.game_state == GameState.PLAYING:
            options = ["Move", "Attack", "Interact"]
            
            if self.current_npc and self.current_npc.npc_type == "merchant":
                options = ["Move", "Talk", "Trade"]
            elif self.current_npc and self.current_npc.npc_type == "quest_giver":
                options = ["Move", "Talk", "Accept Quest"]
            
            return current_narrative, options
        elif self.game_state == GameState.GAME_OVER:
            return current_narrative + ["Game Over. Press Q to quit."], []
        elif self.game_state == GameState.VICTORY:
            return current_narrative + ["You are victorious! Press Q to quit."], []
        return current_narrative, []

    def handle_input(self, choice):
        if self.game_state != GameState.PLAYING:
            return

        if self.active_dialogue_npc:
            logger.info(f"Numbered input {choice} ignored during active dialogue with {self.active_dialogue_npc.name}.")
            return

        if choice == 1:  # Move
            self.player_move()
        elif choice == 2:  # Attack/Talk
            if self.current_npc and self.current_npc.npc_type in ["merchant", "quest_giver"]:
                self.player_talk()
            else:
                self.player_attack()
        elif choice == 3:  # Interact/Trade/Accept Quest
            if self.current_npc and self.current_npc.npc_type == "merchant":
                self.player_trade()
            elif self.current_npc and self.current_npc.npc_type == "quest_giver":
                self.player_accept_quest()
            else:
                self.player_interact()
        else:
            self.narrative = ["Invalid choice. Try again."]
            logger.warning(f"Invalid input choice by player: {choice}")
        
        if self.game_state == GameState.PLAYING:
            self.update()

    def player_advance_dialogue_key(self):
        """Called when player presses key to advance dialogue (e.g. Enter)."""
        # Added INFO log to see if this function is entered
        logger.info(f"player_advance_dialogue_key: Attempting to advance. ActiveNPC: {bool(self.active_dialogue_npc)}, RequiresAdvance: {self.dialogue_requires_player_advance}, AwaitingTypewriter: {self.awaiting_typewriter_completion}")

        if self.active_dialogue_npc and self.dialogue_requires_player_advance and not self.awaiting_typewriter_completion:
            logger.info(f"Player advancing dialogue with {self.active_dialogue_npc.name}.")  # Changed from debug to info
            self.play_sound_event = "dialogue_advance"
            self._advance_dialogue()
        elif self.active_dialogue_npc and self.awaiting_typewriter_completion:
            logger.info("Player attempt to advance dialogue while typewriter is active (event should be handled by typewriter skip mechanism).")  # Changed from debug/warning to info
        else:
            # Added INFO log for this specific condition
            logger.info(f"player_advance_dialogue_key: Conditions not met to advance. ActiveNPC: {bool(self.active_dialogue_npc)}, RequiresAdvance: {self.dialogue_requires_player_advance}, AwaitingTypewriter: {self.awaiting_typewriter_completion}")

    def player_move(self):
        logger.info("Player chose to move.")
        if not self.current_npc:
            self.narrative = ["You explore the quiet clearing."]
            logger.info("Player moves, but no current NPC.")
            return

        other_npcs = [npc for npc in self.npcs if npc.health > 0 and npc != self.current_npc]
        
        if other_npcs:
            self.current_npc = random.choice(other_npcs)
            self.narrative = [f"You move to another area and encounter a {self.current_npc.name}."]
            
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
            
            attack_roll = self.player.attack_roll()
            self.narrative = [f"You roll a {attack_roll} for your attack!"]
            
            if attack_roll >= 10:
                strength_modifier = self.player.strength // 2 - 5
                damage_roll = roll_dice(6, 1, strength_modifier)
                damage_dealt = max(1, damage_roll)
                
                actual_damage = self.current_npc.take_damage(damage_dealt, self.player.strength)
                damage_msg = "reduced " if self.current_npc.is_defending else ""
                
                self.narrative.append(f"Hit! You deal {actual_damage} {damage_msg}damage to the {self.current_npc.name}.")
                self.narrative.append(f"{self.current_npc.name} health: {self.current_npc.health}/{self.current_npc.max_health}")
            else:
                self.narrative.append(f"Miss! Your attack fails to connect with the {self.current_npc.name}.")
            
            if self.current_npc.health <= 0:
                self.narrative.append(f"You defeated the {self.current_npc.name}!")
                logger.info(f"NPC {self.current_npc.name} defeated by player.")
                
                if self.current_quest and self.current_quest.get('target_npc') == self.current_npc.name:
                    if self.current_quest.get('type') == QuestType.DEFEAT:
                        self.ai_dm.complete_quest()
            else:
                logger.info(f"NPC {self.current_npc.name} (Health: {self.current_npc.health}) deciding action...")
                
                action, action_description = self.ai_dm.determine_npc_action(self.current_npc)
                
                self.narrative.append(action_description)
                
                if action == NPCAction.ATTACK:
                    npc_attack_roll = roll_dice(20, 1, self.current_npc.strength // 2 - 5)
                    self.narrative.append(f"The {self.current_npc.name} rolls a {npc_attack_roll} for their attack!")
                    
                    if npc_attack_roll >= 10:
                        npc_strength_mod = self.current_npc.strength // 2 - 5
                        damage_roll = roll_dice(4, 1, npc_strength_mod)
                        damage = max(1, damage_roll)
                        
                        actual_damage = self.player.take_damage(damage, self.current_npc.strength)
                        self.narrative.append(f"Hit! The {self.current_npc.name} strikes you for {actual_damage} damage!")
                        self.narrative.append(f"Your health: {self.player.health}/{self.player.max_health}")
                    else:
                        self.narrative.append(f"Miss! The {self.current_npc.name}'s attack fails to hit you.")
                        
                elif action == NPCAction.DEFEND:
                    self.narrative.append(f"The {self.current_npc.name} is now defending, reducing incoming damage.")
                elif action == NPCAction.FLEE:
                    flee_roll = roll_dice(20, 1, 0)
                    flee_success = flee_roll > 15
                    
                    if flee_success:
                        self.narrative.append(f"The {self.current_npc.name} successfully flees from battle!")
                        self.current_npc.health = 0
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
        logger.info(f"Player chose to talk with {self.current_npc.name if self.current_npc else 'no one'}.")
        if not self.current_npc:
            self.narrative = ["There is no one to talk to."]
            return
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to speak."]
            return

        if self.active_dialogue_npc == self.current_npc and self.dialogue_requires_player_advance:
            self.player_advance_dialogue_key()
            return

        dialogue_lines = self.ai_dm.generate_dialogue(self.current_npc)
        self._start_dialogue_with_npc(self.current_npc, dialogue_lines)

    def player_interact(self):
        logger.info(f"Player chose to interact with {self.current_npc.name if self.current_npc else 'no one'}.")
        if not self.current_npc:
            self.narrative = ["There is no one to interact with."]
            logger.warning("Player interaction attempt, but no current NPC.")
            return

        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is defeated and cannot speak."]
            logger.info(f"Player attempts to interact with defeated NPC: {self.current_npc.name}")
            return
            
        logger.info(f"Player interacting with {self.current_npc.name}.")
        dialogue_lines = self.ai_dm.generate_dialogue(self.current_npc) 
        self._start_dialogue_with_npc(self.current_npc, dialogue_lines)

    def player_trade(self):
        logger.info(f"Player chose to trade with {self.current_npc.name}.")
        
        if not self.current_npc or self.current_npc.npc_type != "merchant":
            self.narrative = ["There is no merchant to trade with."]
            return
            
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to trade."]
            return
            
        self.narrative = [f"The {self.current_npc.name} offers you a healing potion."]
        heal_amount = 20
        self.player.heal(heal_amount)
        self.narrative.append(f"You consume the potion and recover {heal_amount} health.")
        self.narrative.append(f"Your health: {self.player.health}/{self.player.max_health}")
        
        logger.info(f"Player traded with merchant and healed for {heal_amount} points")

    def player_accept_quest(self):
        logger.info(f"Player chose to accept quest from {self.current_npc.name}.")
        
        if not self.current_npc or self.current_npc.npc_type != "quest_giver":
            self.narrative = ["There is no quest giver here."]
            return
            
        if self.current_npc.health <= 0:
            self.narrative = [f"The {self.current_npc.name} is no longer able to give quests."]
            return
            
        old_quest = self.current_quest
        self.current_quest = None
        self.ai_dm.update_quest()
        
        if self.current_quest:
            self.narrative = [f"You accept a new quest from {self.current_npc.name}:"]
            self.narrative.append(self.current_quest.get('description'))
            logger.info(f"Player accepted new quest: {self.current_quest.get('description')}")
        else:
            self.current_quest = old_quest
            self.narrative = [f"The {self.current_npc.name} has no new quests for you at this time."]
            logger.info("No new quest could be generated for player")

    def update(self):
        logger.debug(f"Updating game state. Current state: {self.game_state.name}, Player Health: {self.player.health}")
        if self.game_state != GameState.PLAYING:
            logger.debug(f"Game update skipped, game state is {self.game_state.name}")
            return

        self.turn_counter += 1
        
        if self.player.health <= 0:
            self.game_state = GameState.GAME_OVER
            self.narrative = ["Game Over. You have been defeated."]
            self.current_quest = None
            logger.info("Player health <= 0. Game state changed to GAME_OVER.")
            return

        all_npcs_defeated = all(npc.health <= 0 for npc in self.npcs)
        if not self.current_quest and all_npcs_defeated and self.npcs:
            self.game_state = GameState.VICTORY
            self.narrative = ["All threats have been neutralized. You are victorious!"]
            logger.info("All NPCs defeated and no current quest. Game state changed to VICTORY.")
            return

        if self.turn_counter % 3 == 0:
            logger.info(f"Turn {self.turn_counter}: Evaluating quest difficulty")
            self.ai_dm.adjust_quest_difficulty()

        if self.current_npc and self.current_npc.health <= 0:
            living_npcs = [npc for npc in self.npcs if npc.health > 0]
            if living_npcs:
                self.current_npc = random.choice(living_npcs)
                self.narrative.append(f"You encounter a {self.current_npc.name}.")
                logger.info(f"Current NPC defeated, switching to new NPC: {self.current_npc.name}")
            else:
                self.current_npc = None
                logger.info("All NPCs defeated, no current NPC available")

        if not self.current_quest and any(npc.health > 0 for npc in self.npcs):
            logger.info("No current quest and living NPCs exist. AI-DM updating quest.")
            self.ai_dm.update_quest()
        
        elif not any(npc.health > 0 for npc in self.npcs) and self.npcs:
            if self.game_state == GameState.PLAYING:
                self.game_state = GameState.VICTORY
                self.narrative = ["The last foe is vanquished. Victory is yours!"]
                self.current_quest = None
                logger.info("All NPCs defeated (no specific quest was active or just completed). Game state changed to VICTORY.")
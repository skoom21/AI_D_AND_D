import logging
logger = logging.getLogger("GameLogger")

from enum import Enum, auto
import random  # Import for dice rolls

class NPCAction(Enum):
    ATTACK = auto()
    DEFEND = auto()
    FLEE = auto()

# Add D&D-style dice roll function
def roll_dice(dice_type, num_dice=1, modifier=0):
    """
    Simulates D&D-style dice rolls.
    
    Args:
        dice_type (int): Number of sides on the dice (e.g., 20 for d20)
        num_dice (int): Number of dice to roll
        modifier (int): Modifier to add to the roll
        
    Returns:
        int: Total result of dice rolls plus modifier
    """
    result = sum(random.randint(1, dice_type) for _ in range(num_dice)) + modifier
    logger.debug(f"Dice roll: {num_dice}d{dice_type}+{modifier} = {result}")
    return result

class GameStateEvaluator:
    """Evaluates game states for the Minimax algorithm."""
    
    @staticmethod
    def evaluate_state(player, npc, is_quest_target, max_depth, current_depth):
        """
        Evaluates the current game state from the NPC's perspective.
        Higher scores favor the NPC, lower scores favor the player.
        """
        # Base case: if NPC is defeated
        if npc.health <= 0:
            return -1000  # Very bad for NPC
        
        # Base case: if player is defeated
        if player.health <= 0:
            return 1000  # Very good for NPC
            
        # Handle depth - decisions further in the future are less valuable
        depth_discount = (max_depth - current_depth) / max_depth
            
        # Calculate health percentages
        npc_health_percent = npc.health / npc.max_health
        player_health_percent = player.health / player.max_health
        
        # Health difference (normalized) - higher is better for NPC
        health_advantage = npc_health_percent - player_health_percent
        
        # Consider if NPC is a quest target (quest targets should be more aggressive)
        quest_importance = 1.5 if is_quest_target else 1.0
        
        # Different strategies based on health state
        if npc_health_percent < 0.3:  # NPC is nearly defeated
            # Survival becomes more important than attacking
            survival_score = npc_health_percent * 30  # Emphasize survival
            attack_score = health_advantage * 10  # De-emphasize attack
            final_score = (survival_score + attack_score) * quest_importance
        else:
            # Normal combat evaluation
            health_score = health_advantage * 20
            position_score = 10 if npc_health_percent > player_health_percent else -10
            final_score = (health_score + position_score) * quest_importance
            
        # Apply depth discount - distant future states matter less
        return final_score * depth_discount

class Minimax:
    """Implements the Minimax algorithm with Alpha-Beta pruning for NPC decisions."""
    
    def __init__(self, max_depth=3):
        self.max_depth = max_depth
        logger.info(f"Minimax initialized with max_depth={max_depth}")
        
    def get_best_action(self, player, npc, is_quest_target=False):
        """
        Uses Minimax with Alpha-Beta pruning to determine the best action for the NPC.
        Returns the chosen NPCAction.
        """
        logger.info(f"Minimax calculating best action for {npc.name}")
        
        # Initial values for alpha-beta pruning
        alpha = float('-inf')
        beta = float('inf')
        
        best_score = float('-inf')
        best_action = NPCAction.ATTACK  # Default action
        
        # Evaluate each possible action
        for action in NPCAction:
            # Simulate this action
            new_player = self._copy_player(player)
            new_npc = self._copy_npc(npc)
            
            # Apply the action's immediate effect
            self._apply_action(action, new_player, new_npc)
            
            # Calculate score using minimax
            score = self._min_value(new_player, new_npc, is_quest_target, 1, alpha, beta)
            
            logger.debug(f"Action {action.name} scored {score}")
            
            # Update best action if better score found
            if score > best_score:
                best_score = score
                best_action = action
                alpha = max(alpha, best_score)
        
        logger.info(f"Minimax chose action {best_action.name} with score {best_score}")
        return best_action
        
    def _max_value(self, player, npc, is_quest_target, depth, alpha, beta):
        """
        Maximizing player (NPC) in minimax.
        """
        # Terminal state checks
        if depth >= self.max_depth or player.health <= 0 or npc.health <= 0:
            return GameStateEvaluator.evaluate_state(player, npc, is_quest_target, self.max_depth, depth)
            
        value = float('-inf')
        
        # Try each possible NPC action
        for action in NPCAction:
            # Simulate this action
            new_player = self._copy_player(player)
            new_npc = self._copy_npc(npc)
            
            # Apply the action's effect
            self._apply_action(action, new_player, new_npc)
            
            # Recursively find minimum value (player's turn)
            value = max(value, self._min_value(new_player, new_npc, is_quest_target, depth + 1, alpha, beta))
            
            # Alpha-Beta pruning
            if value >= beta:
                return value
            alpha = max(alpha, value)
            
        return value
        
    def _min_value(self, player, npc, is_quest_target, depth, alpha, beta):
        """
        Minimizing player (human player) in minimax.
        """
        # Terminal state checks
        if depth >= self.max_depth or player.health <= 0 or npc.health <= 0:
            return GameStateEvaluator.evaluate_state(player, npc, is_quest_target, self.max_depth, depth)
            
        value = float('inf')
        
        # Player always attacks in our simulation (simplified assumption)
        # Could be expanded to consider multiple player actions
        new_player = self._copy_player(player)
        new_npc = self._copy_npc(npc)
        
        # Player attacks NPC (simple simulation)
        new_npc.take_damage(20)  # Assuming standard player damage is 20
        
        # Recursively find maximum value (NPC's turn)
        value = min(value, self._max_value(new_player, new_npc, is_quest_target, depth + 1, alpha, beta))
        
        # Alpha-Beta pruning
        if value <= alpha:
            return value
        beta = min(beta, value)
            
        return value
    
    def _copy_player(self, player):
        """Creates a copy of the player for simulation."""
        from .player import Player
        new_player = Player(player.health, player.max_health)
        return new_player
        
    def _copy_npc(self, npc):
        """Creates a copy of the NPC for simulation."""
        from .npc import NPC
        new_npc = NPC(npc.health, npc.name, npc.max_health)
        return new_npc
        
    def _apply_action(self, action, player, npc):
        """Applies the effect of an NPC action on the game state."""
        if action == NPCAction.ATTACK:
            # NPC attacks player
            player.take_damage(10)  # Standard NPC damage
        elif action == NPCAction.DEFEND:
            # NPC defends - takes less damage next turn and heals slightly
            npc.heal(5)  # Small healing from defensive posture
        elif action == NPCAction.FLEE:
            # NPC tries to flee - if successful, it avoids damage next turn
            # In minimax simulation, we'll assume it has limited success
            npc.heal(2)  # Small benefit from fleeing
            
    def get_action_description(self, action, npc_name):
        """Returns a narrative description of the NPC's chosen action."""
        if action == NPCAction.ATTACK:
            return f"The {npc_name} lunges forward with an aggressive attack!"
        elif action == NPCAction.DEFEND:
            return f"The {npc_name} takes a defensive stance, preparing for your next move."
        elif action == NPCAction.FLEE:
            return f"The {npc_name} attempts to flee from the battle!"
        return f"The {npc_name} seems confused about what to do next."
class NPC:
    def __init__(self, health, name, max_health, npc_type="enemy", strength=5, disposition="hostile"):
        self.health = health
        self.name = name
        self.max_health = max_health
        self.is_defending = False
        self.is_fleeing = False
        self.last_action = None
        # New attributes for Milestone 3
        self.npc_type = npc_type        # "enemy", "merchant", "quest_giver", etc.
        self.strength = strength         # Used for combat calculations
        self.disposition = disposition   # "hostile", "neutral", "friendly"
        self.inventory = []              # For merchants or loot
        self.quest_info = None           # For quest-giving NPCs

    def take_damage(self, damage, attacker_strength=0):
        # Apply strength modifier to damage
        modifier = max(-5, min(5, attacker_strength - self.strength))
        modified_damage = damage + modifier
        
        # Apply reduced damage if the NPC is defending
        actual_damage = modified_damage // 2 if self.is_defending else modified_damage
        
        # Ensure damage is at least 1
        actual_damage = max(1, actual_damage)
        
        self.health -= actual_damage
        if self.health < 0:
            self.health = 0
        return actual_damage
        
    def heal(self, amount):
        """Heals the NPC by the specified amount."""
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
            
    def set_action(self, action):
        """Sets the NPC's current action from the AI Strategies module."""
        from .ai_strategies import NPCAction
        
        self.last_action = action
        
        # Reset action states
        self.is_defending = False
        self.is_fleeing = False
        
        # Set new action state
        if action == NPCAction.DEFEND:
            self.is_defending = True
        elif action == NPCAction.FLEE:
            self.is_fleeing = True
            
    def get_dialogue_disposition(self):
        """
        Returns the NPC's disposition for dialogue generation.
        Can be influenced by current health and other factors.
        """
        # If health is low, disposition may shift toward hostile
        if self.health < self.max_health * 0.3 and self.disposition != "friendly":
            return "hostile"
        return self.disposition
        
    def add_to_inventory(self, item):
        """Add an item to NPC's inventory."""
        self.inventory.append(item)
        
    def set_quest_info(self, quest_type, description, reward=None):
        """Set information for a quest this NPC can give."""
        self.quest_info = {
            "type": quest_type,
            "description": description,
            "reward": reward,
            "completed": False
        }
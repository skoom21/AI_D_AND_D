class Player:
    def __init__(self, health, max_health, strength=10):
        self.health = health
        self.max_health = max_health
        # New attributes for Milestone 3
        self.strength = strength     # Used for combat calculations
        self.inventory = []          # Player's items
        self.completed_quests = []   # Track completed quests
        self.active_quests = []      # Track active quests

    def take_damage(self, damage, attacker_strength=0):
        # Apply strength difference as a modifier
        modifier = max(-5, min(5, attacker_strength - self.strength))
        modified_damage = damage + modifier
        
        # Ensure damage is at least 1
        actual_damage = max(1, modified_damage)
        
        self.health -= actual_damage
        if self.health < 0:
            self.health = 0
        return actual_damage

    def heal(self, amount):
        self.health += amount
        if self.health > self.max_health:
            self.health = self.max_health
            
    def add_to_inventory(self, item):
        """Add an item to player's inventory."""
        self.inventory.append(item)
        
    def add_quest(self, quest):
        """Add a new quest to active quests."""
        self.active_quests.append(quest)
        
    def complete_quest(self, quest_id):
        """Mark a quest as completed and move it to completed_quests."""
        for i, quest in enumerate(self.active_quests):
            if quest.get('id') == quest_id:
                completed_quest = self.active_quests.pop(i)
                completed_quest['completed'] = True
                self.completed_quests.append(completed_quest)
                return True
        return False
        
    def attack_roll(self):
        """Perform an attack roll using D&D-style mechanics."""
        from .ai_strategies import roll_dice
        # Base attack roll is d20 + strength modifier
        strength_modifier = self.strength // 2 - 5  # Similar to D&D (+0 at 10 STR)
        attack_roll = roll_dice(20, 1, strength_modifier)
        return attack_roll
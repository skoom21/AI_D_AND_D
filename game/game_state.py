from enum import Enum, auto

class GameState(Enum):
    PLAYING = auto()
    GAME_OVER = auto()
    VICTORY = auto()

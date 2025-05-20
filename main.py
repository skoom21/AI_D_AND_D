import pygame
from enum import Enum, auto
import logging  # Import logging module
import os  # For path creation

from game.game import Game
from game.game_state import GameState

# Application Screen States
class AppScreen(Enum):
    LOADING = auto()
    MAIN_MENU = auto()
    SETTINGS = auto()  # New settings screen state
    INTRO = auto()
    GAMEPLAY = auto()
    OUTRO_VICTORY = auto()
    OUTRO_GAMEOVER = auto()

# Initialize Pygame
pygame.init()
pygame.mixer.init()  # For potential sound effects later

# --- Logger Setup ---
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE_GAME = os.path.join(LOG_DIR, "game_activity.log")
LOG_FILE_ERROR = os.path.join(LOG_DIR, "errors.log")

# General game logger
logger = logging.getLogger("GameLogger")
logger.setLevel(logging.DEBUG)  # Capture all levels of logs

# File handler for general game activity
fh_game = logging.FileHandler(LOG_FILE_GAME, mode='w')  # 'w' to overwrite log each run, 'a' to append
fh_game.setLevel(logging.INFO)  # Log informational messages and above
formatter_game = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
fh_game.setFormatter(formatter_game)
logger.addHandler(fh_game)

# File handler for errors
fh_error = logging.FileHandler(LOG_FILE_ERROR, mode='w')
fh_error.setLevel(logging.ERROR)  # Log only errors and critical
formatter_error = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(module)s - %(funcName)s - %(message)s')
fh_error.setFormatter(formatter_error)
logger.addHandler(fh_error)

logger.info("Logging initialized. Application starting.")

# Get system display info for responsive sizing
info = pygame.display.Info()
SYSTEM_WIDTH, SYSTEM_HEIGHT = info.current_w, info.current_h

# Screen settings - default values, will be updated based on system
# Use system's current resolution as the base/default
BASE_WIDTH, BASE_HEIGHT = SYSTEM_WIDTH, SYSTEM_HEIGHT
SCREEN_WIDTH = min(int(SYSTEM_WIDTH * 0.8), BASE_WIDTH)
SCREEN_HEIGHT = min(int(SYSTEM_HEIGHT * 0.8), BASE_HEIGHT)

# --- Game Settings Variables ---
SUPPORTED_RESOLUTIONS = [(800, 600), (1024, 768), (1280, 720), (1600, 900), (1920, 1080)]
try:
    current_resolution_index = SUPPORTED_RESOLUTIONS.index((SCREEN_WIDTH, SCREEN_HEIGHT))
except ValueError:
    try:
        current_resolution_index = SUPPORTED_RESOLUTIONS.index((BASE_WIDTH, BASE_HEIGHT))
    except ValueError:
        current_resolution_index = 0
        SCREEN_WIDTH, SCREEN_HEIGHT = SUPPORTED_RESOLUTIONS[current_resolution_index]

master_volume = 1.0  # Range 0.0 to 1.0
music_volume = 0.3   # Range 0.0 to 1.0 (initial value from main)
sfx_volume = 0.7     # Range 0.0 to 1.0 (initial value from play_sound default)
fullscreen_enabled = True
# --- End Game Settings Variables ---

# Make the screen resizable
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Dungeon Text - Ai Driven Fanatasy RPG")

# Load and set the game icon
assets_path = "assets"
game_icon = pygame.image.load(os.path.join(assets_path, "images", "game_logo.png"))
pygame.display.set_icon(game_icon)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
DARK_GREY = (50, 50, 50)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)  # For highlights or links
GOLD = (255, 215, 0)
CYAN = (0, 255, 255)
LIGHT_GREY = (200, 200, 200)
DARKER_GREY = (30, 30, 30)
PANEL_BG = (40, 40, 45)

# Define colors for health and strength bars
HEALTH_BAR_FG = (0, 255, 0)  # Green
HEALTH_BAR_BG = (50, 0, 0)   # Dark Red
STRENGTH_BAR_FG = (0, 0, 255) # Blue
STRENGTH_BAR_BG = (0, 0, 50)  # Dark Blue

# --- Sound Assets ---
SOUND_DIR = os.path.join("assets", "sounds")
IMAGE_DIR = os.path.join("assets", "images")  # For background images

game_sounds = {}
background_music = None
background_image = None

def load_assets():
    """Loads all game sounds and background image."""
    global background_music, background_image, game_sounds
    logger.info("Loading assets...")

    # Load background image
    try:
        img_path = os.path.join(IMAGE_DIR, "background_main.png")  # Example image
        if os.path.exists(img_path):
            background_image = pygame.image.load(img_path).convert()
            logger.info(f"Loaded background image: {img_path}")
        else:
            logger.warning(f"Background image not found: {img_path}")
    except pygame.error as e:
        logger.error(f"Error loading background image: {e}")

    # Load sounds
    sound_files = {
        "menu_navigate": "menu_navigate.wav",
        "menu_select": "menu_select.wav",
        "typewriter_char": "typewriter_char.wav",
        "quest_new": "quest_new.wav",
        "quest_complete": "quest_complete.wav",
        "player_action": "player_action.wav",  # Generic action sound
        "error": "error.wav"  # For invalid actions
    }
    for sound_name, file_name in sound_files.items():
        path = os.path.join(SOUND_DIR, file_name)
        if os.path.exists(path):
            try:
                game_sounds[sound_name] = pygame.mixer.Sound(path)
                logger.info(f"Loaded sound: {file_name} as {sound_name}")
            except pygame.error as e:
                logger.error(f"Error loading sound {file_name}: {e}")
                game_sounds[sound_name] = None
        else:
            logger.warning(f"Sound file not found: {path}. {sound_name} will be silent.")
            game_sounds[sound_name] = None

    # Load background music
    music_path_mp3 = os.path.join(SOUND_DIR, "background_music.mp3")
    music_path_ogg = os.path.join(SOUND_DIR, "background_music.ogg")
    
    music_loaded_successfully = False

    # Try MP3 first
    if os.path.exists(music_path_mp3):
        logger.info(f"Attempting to load background music: {music_path_mp3}")
        try:
            pygame.mixer.music.load(music_path_mp3)
            background_music = music_path_mp3 # Store path to indicate it's loaded
            music_loaded_successfully = True
            logger.info(f"Successfully loaded background music: {music_path_mp3}")
        except pygame.error as e:
            logger.error(f"Error loading MP3 background music {music_path_mp3}: {e}")
            # If MP3 fails, and OGG exists, we'll try OGG next
            if os.path.exists(music_path_ogg):
                logger.info(f"MP3 loading failed. Attempting to load OGG fallback: {music_path_ogg}")
            else:
                logger.warning("MP3 loading failed, and no OGG fallback found.")
    
    # If MP3 didn't load or didn't exist, try OGG
    if not music_loaded_successfully and os.path.exists(music_path_ogg):
        logger.info(f"Attempting to load background music: {music_path_ogg}")
        try:
            pygame.mixer.music.load(music_path_ogg)
            background_music = music_path_ogg
            music_loaded_successfully = True
            logger.info(f"Successfully loaded background music: {music_path_ogg}")
        except pygame.error as e:
            logger.error(f"Error loading OGG background music {music_path_ogg}: {e}")

    if not music_loaded_successfully:
        logger.warning(f"Background music file not found or could not be loaded (checked for .mp3 and .ogg).")
        background_music = None
        
    logger.info("Asset loading complete.")

def play_sound(sound_name, volume=None):  # Modified to accept optional volume
    """Plays a sound from the game_sounds dictionary if it exists."""
    if sound_name in game_sounds and game_sounds[sound_name]:
        sound = game_sounds[sound_name]
        effective_volume = volume if volume is not None else (sfx_volume * master_volume)
        sound.set_volume(effective_volume)
        sound.play()
    else:
        logger.debug(f"Attempted to play sound '{sound_name}', but it was not loaded.")

# Function to calculate scaled font sizes
def get_scaled_font_size(base_size):
    scale_factor = min(SCREEN_WIDTH / BASE_WIDTH, SCREEN_HEIGHT / BASE_HEIGHT)
    return max(int(base_size * scale_factor), 10)  # Minimum size of 10

# Font - will be updated when screen is resized
PRIMARY_FONT_NAME = "Consolas"
FALLBACK_FONT_NAME = "monospace"
font_small = None
font_medium = None 
font_large = None
font_title = None

def update_fonts():
    global font_small, font_medium, font_large, font_title
    try:
        font_small = pygame.font.SysFont(PRIMARY_FONT_NAME, get_scaled_font_size(20))
        font_medium = pygame.font.SysFont(PRIMARY_FONT_NAME, get_scaled_font_size(24))
        font_large = pygame.font.SysFont(PRIMARY_FONT_NAME, get_scaled_font_size(36))
        font_title = pygame.font.SysFont(PRIMARY_FONT_NAME, get_scaled_font_size(48))
    except pygame.error:
        logger.warning(f"Font {PRIMARY_FONT_NAME} not found, using {FALLBACK_FONT_NAME}.")
        font_small = pygame.font.SysFont(FALLBACK_FONT_NAME, get_scaled_font_size(20))
        font_medium = pygame.font.SysFont(FALLBACK_FONT_NAME, get_scaled_font_size(24))
        font_large = pygame.font.SysFont(FALLBACK_FONT_NAME, get_scaled_font_size(36))
        font_title = pygame.font.SysFont(FALLBACK_FONT_NAME, get_scaled_font_size(48))

# Initialize fonts
update_fonts()

# Global flags for typewriter state, primarily for coordinating with main loop
typewriter_is_busy = False  # True if typewriter_effect is currently running for a line

# Function to scale UI elements when screen size changes
def update_ui_layout():
    global NARRATIVE_RECT, OPTIONS_RECT, STATS_RECT, CHAR_INFO_RECT
    
    # Calculate margins and padding based on screen size
    h_margin = int(SCREEN_WIDTH * 0.05)  # 5% horizontal margin
    v_margin = int(SCREEN_HEIGHT * 0.05)  # 5% vertical margin
    padding = int(min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.02)  # 2% padding
    
    # Define main UI panel areas
    narrative_height = int(SCREEN_HEIGHT * 0.45)  # 45% of screen height for narrative
    options_height = int(SCREEN_HEIGHT * 0.25)  # 25% of screen height for options
    stats_height = int(SCREEN_HEIGHT * 0.15)  # 15% of screen height for player stats
    
    # Create UI rectangles with proper spacing
    NARRATIVE_RECT = pygame.Rect(
        h_margin, 
        v_margin, 
        SCREEN_WIDTH - (2 * h_margin), 
        narrative_height
    )
    
    OPTIONS_RECT = pygame.Rect(
        h_margin,
        NARRATIVE_RECT.bottom + padding,
        SCREEN_WIDTH - (2 * h_margin),
        options_height
    )
    
    CHAR_INFO_RECT = pygame.Rect(
        h_margin,
        OPTIONS_RECT.bottom + padding,
        SCREEN_WIDTH - (2 * h_margin),
        stats_height
    )
    
    STATS_RECT = pygame.Rect(
        h_margin,
        CHAR_INFO_RECT.bottom + padding,
        SCREEN_WIDTH - (2 * h_margin),
        v_margin - padding
    )

# Initialize UI layout
update_ui_layout()

# Helper function to draw a themed panel
def draw_panel(surface, rect, color=PANEL_BG, border_color=GREY, border_width=2, alpha=220, border_radius=5):
    # Create a surface with per-pixel alpha
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    # Fill with semi-transparent color
    panel.fill((color[0], color[1], color[2], alpha))
    # Draw border with rounded corners
    pygame.draw.rect(panel, border_color, (0, 0, rect.width, rect.height), border_width, border_radius=border_radius)
    # Blit to main surface
    surface.blit(panel, rect)

# Function to draw a health/stat bar
def draw_stat_bar(surface, rect, current, maximum, fg_color, bg_color, text=None, font=None, text_color=WHITE):
    # Draw background
    pygame.draw.rect(surface, bg_color, rect)
    
    # Calculate fill width based on current/max ratio
    if maximum > 0:  # Prevent division by zero
        fill_width = int((current / maximum) * rect.width)
        fill_rect = pygame.Rect(rect.left, rect.top, fill_width, rect.height)
        pygame.draw.rect(surface, fg_color, fill_rect)
    
    # Add border
    pygame.draw.rect(surface, GREY, rect, 1)
    
    # Add text if provided
    if text and font:
        text_surf = font.render(text, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        surface.blit(text_surf, text_rect)

def render_text_wrapped(surface, text, font, color, rect, aa=True, bkg=None):
    """Renders text with word wrapping to fit within a given pygame.Rect."""
    # First draw the panel background
    draw_panel(surface, rect, border_radius=10)
    
    # Adjust rect for padding
    padding = int(min(rect.width, rect.height) * 0.05)
    inner_rect = pygame.Rect(
        rect.left + padding,
        rect.top + padding,
        rect.width - (padding * 2),
        rect.height - (padding * 2)
    )
    
    y = inner_rect.top
    line_spacing = font.get_linesize()

    # Handle multiline text with \n
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if paragraph == "":  # Empty line
            y += line_spacing
            continue
            
        lines = []
        words = paragraph.split(' ')
        current_line = []

        for word in words:
            current_line.append(word)
            line_width, _ = font.size(' '.join(current_line))
            if line_width > inner_rect.width:
                if len(current_line) > 1:
                    current_line.pop()  # Remove the word that made it too long
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # If a single word is too long, keep it and move on
                    lines.append(' '.join(current_line))
                    current_line = []

        if current_line:  # Add any remaining words
            lines.append(' '.join(current_line))

        for line in lines:
            if y + line_spacing > inner_rect.bottom:
                # Show ellipsis if text is cut off
                ellipsis = font.render("...", aa, color)
                surface.blit(ellipsis, (inner_rect.left, inner_rect.bottom - line_spacing))
                break
                
            if bkg:
                img = font.render(line, aa, color, bkg)
            else:
                img = font.render(line, aa, color)
                
            # Left align text within the inner rectangle
            surface.blit(img, (inner_rect.left, y))
            y += line_spacing
            
        # Add extra spacing between paragraphs
        y += int(line_spacing * 0.3)
        
    return y

def typewriter_effect(surface, text, font, color, rect, speed=15, game_instance=None):
    """Displays text with a typewriter effect. Clears the rect area first.
    Calls game_instance.on_typewriter_line_completed() if game_instance is provided.
    Returns True if animation completed/skipped, False if interrupted by QUIT.
    """
    global typewriter_is_busy
    typewriter_is_busy = True
    
    # Handle None text
    if text is None:
        text = "..."
    
    draw_panel(surface, rect, border_radius=10)  # Initial panel draw
    padding = int(min(rect.width, rect.height) * 0.05)
    inner_rect = pygame.Rect(
        rect.left + padding,
        rect.top + padding,
        rect.width - (padding * 2),
        rect.height - (padding * 2)
    )

    words = text.split(' ')
    lines_to_render = []
    current_line_words = []
    line_spacing = font.get_linesize()

    for word in words:
        temp_line_words = current_line_words + [word]
        line_width, _ = font.size(' '.join(temp_line_words))
        if line_width > inner_rect.width and current_line_words:
            lines_to_render.append(' '.join(current_line_words))
            current_line_words = [word]
        else:
            current_line_words.append(word)
    if current_line_words:
        lines_to_render.append(' '.join(current_line_words))
    
    if not lines_to_render and text.strip():  # Handle case where text is very short but not empty
        lines_to_render.append(text.strip())

    rendered_lines_surfaces = []
    current_y = inner_rect.top
    skip_animation = False
    animation_fully_completed = True  # Assume completion unless quit

    for line_idx, line_text_to_type in enumerate(lines_to_render):
        if current_y + line_spacing > inner_rect.bottom:
            # Show ellipsis if text is cut off (only if there are more lines than fit)
            if line_idx < len(lines_to_render) - 1:
                ellipsis_surf = font.render("...", True, color)
                surface.blit(ellipsis_surf, (inner_rect.right - ellipsis_surf.get_width() - 5, inner_rect.bottom - line_spacing))
            break  # Stop if no more space

        typed_chars_for_current_line = ""
        for char_idx, char_to_type in enumerate(line_text_to_type):
            if skip_animation:
                typed_chars_for_current_line = line_text_to_type  # Complete the current line text
                break 
                
            typed_chars_for_current_line += char_to_type
            if char_idx % 3 == 0:  # Reduce sound frequency
                play_sound("typewriter_char", volume=0.2 * master_volume * sfx_volume)

            # Redraw the panel for each frame to clear previous cursor/text state
            draw_panel(surface, rect, border_radius=10)

            temp_blit_y = inner_rect.top
            for prev_line_surf in rendered_lines_surfaces:  # Blit fully completed lines
                surface.blit(prev_line_surf, (inner_rect.left, temp_blit_y))
                temp_blit_y += line_spacing
            
            current_line_surf = font.render(typed_chars_for_current_line, True, color)
            surface.blit(current_line_surf, (inner_rect.left, current_y))  # Blit current typing line

            if (pygame.time.get_ticks() // 500) % 2 == 0:  # Blinking cursor
                cursor_pos = (inner_rect.left + current_line_surf.get_width() + 2, current_y)
                cursor_height = font.get_height()
                pygame.draw.line(surface, color, cursor_pos, 
                                (cursor_pos[0], cursor_pos[1] + cursor_height - 2), 2)
            
            pygame.display.update(rect)  # Update only the text rect
            pygame.time.wait(speed)

            for event_tw in pygame.event.get():  # Minimal event handling during typing
                if event_tw.type == pygame.QUIT:
                    logger.warning("Quit event during typewriter effect.")
                    animation_fully_completed = False
                    pygame.quit()  # Ensure pygame quits properly
                    import sys
                    sys.exit()
                elif event_tw.type == pygame.KEYDOWN:
                    if event_tw.key == pygame.K_SPACE or event_tw.key == pygame.K_RETURN:
                        logger.info("Typewriter skipped by player.")
                        skip_animation = True
                        play_sound("menu_select", volume=sfx_volume * master_volume) 
                        break  # Break from char loop
            if not animation_fully_completed: break  # If quit, break from char loop
        
        if not animation_fully_completed: break  # If quit, break from line loop

        # Current line is fully typed or skipped
        completed_line_surf = font.render(line_text_to_type, True, color)  # Render the full line
        rendered_lines_surfaces.append(completed_line_surf)
        current_y += line_spacing
        
        if skip_animation:  # If skipped, break from rendering further lines
            break

    # Final redraw of the fully typed/skipped text within the rect
    draw_panel(surface, rect, border_radius=10)
    temp_blit_y = inner_rect.top
    for final_line_surf in rendered_lines_surfaces:
        surface.blit(final_line_surf, (inner_rect.left, temp_blit_y))
        temp_blit_y += line_spacing
    pygame.display.update(rect)

    typewriter_is_busy = False
    if game_instance and animation_fully_completed:  # Only call callback if animation wasn't quit
        game_instance.on_typewriter_line_completed()
    
    return animation_fully_completed

# The rest of the code remains unchanged.
game = None
current_app_screen = AppScreen.LOADING
menu_selection = 0
settings_menu_selection = 0  # For navigating settings screen options
SETTINGS_OPTIONS = [
    "Resolution", 
    "Fullscreen", 
    "Master Volume", 
    "Music Volume", 
    "SFX Volume", 
    "Apply", 
    "Back to Main Menu"
]


def display_loading_screen():
    screen.fill(BLACK)  # Dark background
    logo_image = pygame.image.load(os.path.join(assets_path, "images", "game_logo.png"))
    logo_image = pygame.transform.scale(logo_image, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))  # Scale logo
    logo_rect = logo_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))

    # Fade in
    for alpha in range(0, 256, 5):  # Faster fade
        logo_image.set_alpha(alpha)
        screen.fill(BLACK)
        screen.blit(logo_image, logo_rect)
        pygame.display.flip()
        pygame.time.wait(30)  # Animation speed

    pygame.time.wait(1000)  # Hold logo

    # Fade out
    for alpha in range(255, -1, -5):  # Faster fade
        logo_image.set_alpha(alpha)
        screen.fill(BLACK)
        screen.blit(logo_image, logo_rect)
        pygame.display.flip()
        pygame.time.wait(30)  # Animation speed

    logger.info("Logo animation complete.")


MENU_OPTIONS = ["Start New Game", "Settings", "Quit"]


def display_main_menu():
    screen.fill(DARK_GREY)
    if background_image:
        scaled_bg = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((DARK_GREY[0], DARK_GREY[1], DARK_GREY[2], 150))
        screen.blit(overlay, (0, 0))
    
    # Draw a decorative header panel
    header_rect = pygame.Rect(
        int(SCREEN_WIDTH * 0.1),
        int(SCREEN_HEIGHT * 0.1),
        int(SCREEN_WIDTH * 0.8),
        int(SCREEN_HEIGHT * 0.2)
    )
    draw_panel(screen, header_rect, color=DARKER_GREY, border_color=GREEN, border_width=3, border_radius=10)
    
    # Draw a decorative background panel for menu options
    menu_panel_rect = pygame.Rect(
        int(SCREEN_WIDTH * 0.2),
        int(SCREEN_HEIGHT * 0.4),
        int(SCREEN_WIDTH * 0.6),
        int(SCREEN_HEIGHT * 0.4)
    )
    draw_panel(screen, menu_panel_rect, alpha=180, border_radius=10)
    
    # Title with shadow effect
    shadow_offset = max(2, int(get_scaled_font_size(3)))
    title_text = "Dungeon Text"  # Changed
    shadow_surf = font_title.render(title_text, True, BLACK)
    title_surf = font_title.render(title_text, True, GREEN)
    
    shadow_rect = shadow_surf.get_rect(center=(header_rect.centerx + shadow_offset, header_rect.centery + shadow_offset))
    title_rect = title_surf.get_rect(center=(header_rect.centerx, header_rect.centery))
    
    screen.blit(shadow_surf, shadow_rect)
    screen.blit(title_surf, title_rect)

    # Subtitle
    subtitle_text = "Ai Driven Fanatasy RPG"  # Changed
    subtitle = font_medium.render(subtitle_text, True, LIGHT_GREY)
    subtitle_rect = subtitle.get_rect(midtop=(header_rect.centerx, title_rect.bottom + 10))
    screen.blit(subtitle, subtitle_rect)

    # Menu options with hover effect
    option_spacing = max(40, int(SCREEN_HEIGHT * 0.07))
    for i, option in enumerate(MENU_OPTIONS):
        # Prepare text with different styling for selected option
        if i == menu_selection:
            # Selected option
            color = BLUE
            option_font = font_large
            # Draw highlight box
            option_box_rect = pygame.Rect(
                menu_panel_rect.left + 20,
                menu_panel_rect.top + 20 + (i * option_spacing),
                menu_panel_rect.width - 40,
                option_spacing - 10
            )
            draw_panel(screen, option_box_rect, color=DARKER_GREY, border_color=color, border_width=3, alpha=230, border_radius=8)
        else:
            # Unselected option
            color = WHITE
            option_font = font_medium
        
        # Render and position the text
        text_surf = option_font.render(option, True, color)
        text_rect = text_surf.get_rect(
            midleft=(
                menu_panel_rect.left + 40,
                menu_panel_rect.top + 20 + (i * option_spacing) + option_spacing//2
            )
        )
        screen.blit(text_surf, text_rect)
    
    # Draw controls hint at bottom
    controls_text = "↑/↓: Navigate   ENTER: Select   ESC: Exit"
    controls_surf = font_small.render(controls_text, True, GREY)
    controls_rect = controls_surf.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20))
    screen.blit(controls_surf, controls_rect)
    
    pygame.display.flip()


def display_settings_screen():
    """Displays the settings screen and handles settings adjustments."""
    global settings_menu_selection, current_resolution_index, fullscreen_enabled
    global master_volume, music_volume, sfx_volume, SCREEN_WIDTH, SCREEN_HEIGHT, screen
    
    screen.fill(DARK_GREY)
    if background_image:
        scaled_bg = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((DARK_GREY[0], DARK_GREY[1], DARK_GREY[2], 180)) # Darker overlay for settings
        screen.blit(overlay, (0, 0))

    # Settings panel
    settings_panel_rect = pygame.Rect(
        int(SCREEN_WIDTH * 0.15),
        int(SCREEN_HEIGHT * 0.1),
        int(SCREEN_WIDTH * 0.7),
        int(SCREEN_HEIGHT * 0.8)
    )
    draw_panel(screen, settings_panel_rect, color=DARKER_GREY, border_color=BLUE, border_width=3, alpha=220, border_radius=10)

    # Title
    title_surf = font_large.render("Settings", True, WHITE)
    title_rect = title_surf.get_rect(center=(settings_panel_rect.centerx, settings_panel_rect.top + 50))
    screen.blit(title_surf, title_rect)

    option_spacing = max(45, int(settings_panel_rect.height * 0.08))
    start_y = title_rect.bottom + 50

    for i, option_text in enumerate(SETTINGS_OPTIONS):
        color = WHITE
        option_font = font_medium
        
        display_text = option_text
        current_value_text = ""

        if option_text == "Resolution":
            current_value_text = f"{SUPPORTED_RESOLUTIONS[current_resolution_index][0]} x {SUPPORTED_RESOLUTIONS[current_resolution_index][1]}"
        elif option_text == "Fullscreen":
            current_value_text = "On" if fullscreen_enabled else "Off"
        elif option_text == "Master Volume":
            current_value_text = f"{int(master_volume * 100)}%"
        elif option_text == "Music Volume":
            current_value_text = f"{int(music_volume * 100)}%"
        elif option_text == "SFX Volume":
            current_value_text = f"{int(sfx_volume * 100)}%"

        if current_value_text:
            display_text = f"{option_text}: < {current_value_text} >"
            
        if i == settings_menu_selection:
            color = BLUE
            option_font = font_large # Slightly larger for selected

        text_surf = option_font.render(display_text, True, color)
        text_rect = text_surf.get_rect(
            midleft=(
                settings_panel_rect.left + 50,
                start_y + (i * option_spacing)
            )
        )
        screen.blit(text_surf, text_rect)

    # Controls hint
    controls_text = "↑/↓: Navigate   ←/→: Change Value   ENTER: Select/Toggle   ESC: Back"
    controls_surf = font_small.render(controls_text, True, LIGHT_GREY)
    controls_rect = controls_surf.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20))
    screen.blit(controls_surf, controls_rect)
    
    pygame.display.flip()


INTRO_TEXT = [
    "In a realm shrouded in ancient magic and lingering shadows...",
    "You awaken with a hazy memory, a sturdy resolve, and a path unknown.",
    "Your adventure begins now. What choices will you make?"
]
current_intro_line = 0


def display_intro():
    global current_intro_line, current_app_screen
    
    screen.fill(DARK_GREY)
    if background_image:
        scaled_bg = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((DARK_GREY[0], DARK_GREY[1], DARK_GREY[2], 120))
        screen.blit(overlay, (0, 0))
    
    # Draw a decorative frame for the intro text
    intro_panel = pygame.Rect(
        int(SCREEN_WIDTH * 0.1), 
        int(SCREEN_HEIGHT * 0.2), 
        int(SCREEN_WIDTH * 0.8), 
        int(SCREEN_HEIGHT * 0.5)
    )
    
    # Check if we're at the end of intro text
    if current_intro_line >= len(INTRO_TEXT):
        current_app_screen = AppScreen.GAMEPLAY
        logger.info("End of intro reached, transitioning to gameplay")
        return
    
    # Track completion state for the current line
    if not hasattr(display_intro, 'line_completed'):
        display_intro.line_completed = False
    
    # Get the current text to display
    current_text = INTRO_TEXT[current_intro_line]
    
    # If the line animation hasn't completed, run the typewriter effect
    if not display_intro.line_completed:
        # The typewriter_effect function handles the animation and returns whether it was skipped
        was_skipped = typewriter_effect(screen, current_text, font_medium, WHITE, intro_panel, speed=30)
        display_intro.line_completed = True
    else:
        # Just render the text normally if already completed
        render_text_wrapped(screen, current_text, font_medium, WHITE, intro_panel)
    
    # Display navigation prompts in a nice panel
    prompt_panel = pygame.Rect(
        int(SCREEN_WIDTH * 0.2),
        int(SCREEN_HEIGHT * 0.75),
        int(SCREEN_WIDTH * 0.6),
        int(SCREEN_HEIGHT * 0.15)
    )
    draw_panel(screen, prompt_panel, border_color=BLUE, border_radius=8)
    
    # Different prompt text based on animation state
    if display_intro.line_completed:
        prompt_text = "Press ENTER to continue, SPACE to skip intro"
    else:
        prompt_text = "Press SPACE to skip animation"
    
    prompt_surf = font_medium.render(prompt_text, True, WHITE)
    prompt_rect = prompt_surf.get_rect(center=(prompt_panel.centerx, prompt_panel.centery))
    screen.blit(prompt_surf, prompt_rect)
    
    # Show progress indicator with a visual bar
    progress_width = int(SCREEN_WIDTH * 0.3)
    progress_rect = pygame.Rect(
        (SCREEN_WIDTH - progress_width) // 2,
        int(SCREEN_HEIGHT * 0.9),
        progress_width,
        20
    )
    
    # Draw progress bar background
    pygame.draw.rect(screen, DARKER_GREY, progress_rect)
    
    # Calculate fill width based on current progress
    fill_width = int((current_intro_line / len(INTRO_TEXT)) * progress_rect.width)
    fill_rect = pygame.Rect(progress_rect.left, progress_rect.top, fill_width, progress_rect.height)
    pygame.draw.rect(screen, GREEN, fill_rect)
    
    # Add border
    pygame.draw.rect(screen, GREY, progress_rect, 1)
    
    # Add text indicator
    progress_text = f"{current_intro_line + 1}/{len(INTRO_TEXT)}"
    text_surf = font_small.render(progress_text, True, WHITE)
    text_rect = text_surf.get_rect(center=progress_rect.center)
    screen.blit(text_surf, text_rect)
    
    pygame.display.flip()


def display_outro(message_lines):
    screen.fill(DARK_GREY)
    if background_image:
        scaled_bg = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((DARK_GREY[0], DARK_GREY[1], DARK_GREY[2], 100))
        screen.blit(overlay, (0, 0))
    
    # Create a panel for the outro message
    outro_panel = pygame.Rect(
        int(SCREEN_WIDTH * 0.1),
        int(SCREEN_HEIGHT * 0.2),
        int(SCREEN_WIDTH * 0.8),
        int(SCREEN_HEIGHT * 0.5)
    )
    
    border_color = GREEN if current_app_screen == AppScreen.OUTRO_VICTORY else RED
    draw_panel(screen, outro_panel, color=DARKER_GREY, border_color=border_color, border_width=3, border_radius=10)
    
    # Display message lines with nice formatting
    y_offset = outro_panel.top + 80
    
    for i, line in enumerate(message_lines):
        # Apply different styling to first line (title)
        if i == 0:
            font_color = GREEN if current_app_screen == AppScreen.OUTRO_VICTORY else RED
            text_surf = font_large.render(line, True, font_color)
        else:
            text_surf = font_medium.render(line, True, WHITE)
        
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
        screen.blit(text_surf, text_rect)
        y_offset += 60
    
    # Display navigation options
    prompt_panel = pygame.Rect(
        int(SCREEN_WIDTH * 0.25),
        int(SCREEN_HEIGHT * 0.75),
        int(SCREEN_WIDTH * 0.5),
        int(SCREEN_HEIGHT * 0.1)
    )
    draw_panel(screen, prompt_panel, border_color=BLUE, border_radius=8)
    
    prompt_text = font_medium.render("Press Q to quit or ENTER/M for Main Menu", True, WHITE)
    prompt_rect = prompt_text.get_rect(center=prompt_panel.center)
    screen.blit(prompt_text, prompt_rect)
    
    pygame.display.flip()


NARRATIVE_RECT = pygame.Rect(50, 50, SCREEN_WIDTH - 100, SCREEN_HEIGHT // 2 - 50)
OPTIONS_RECT = pygame.Rect(50, SCREEN_HEIGHT // 2 + 50, SCREEN_WIDTH - 100, 150)
STATS_RECT = pygame.Rect(50, SCREEN_HEIGHT - 70, SCREEN_WIDTH - 100, 50)


def display_gameplay():
    global game, current_app_screen
    
    # Initialize game if needed
    if not game:
        game = Game()
        logger.info("New game instance created")
        if game.game_state == GameState.PLAYING:
            game.play_sound_event = "quest_new"  # Use game's sound event system

    screen.fill(DARK_GREY)
    if background_image:
        scaled_bg = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        screen.blit(scaled_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((DARK_GREY[0], DARK_GREY[1], DARK_GREY[2], 100))
        screen.blit(overlay, (0, 0))

    if game.is_generating_text:
        # Display a loading indicator
        loading_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        loading_overlay.fill((0, 0, 0, 150)) # Semi-transparent black overlay
        screen.blit(loading_overlay, (0,0))

        loading_text_str = "AI is thinking..."
        loading_surf = font_large.render(loading_text_str, True, WHITE)
        loading_rect = loading_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        
        # Simple animation for loading text (e.g., pulsing dots)
        num_dots = (pygame.time.get_ticks() // 500) % 4
        animated_loading_text = loading_text_str + "." * num_dots
        animated_surf = font_large.render(animated_loading_text, True, WHITE)
        animated_rect = animated_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen.blit(animated_surf, animated_rect)
        
    else:
        narrative_lines, options = game.get_display_text()

        # If typewriter is not busy, render text normally.
        # If typewriter IS busy, it handles its own drawing within NARRATIVE_RECT.
        # The main loop will call typewriter_effect if game.awaiting_typewriter_completion is true.
        # So, display_gameplay just needs to render the current narrative if typewriter is not active.
        if not typewriter_is_busy:
            # Filter out None values and convert all items to strings to prevent errors
            clean_narrative = [str(line) for line in narrative_lines if line is not None]
            render_text_wrapped(screen, "\n".join(clean_narrative), font_small, WHITE, NARRATIVE_RECT)
        # Else: typewriter_effect is handling the narrative panel drawing.

        # Display the options panel
        draw_panel(screen, OPTIONS_RECT, border_color=BLUE, border_radius=10)
        
        # Show options only if we're in playing state and not generating text
        if game.game_state == GameState.PLAYING and options:
            option_height = font_medium.get_linesize() + 10
            for i, opt in enumerate(options):
                # Draw option background with highlight effect for visual separation
                option_rect_item = pygame.Rect(
                    OPTIONS_RECT.left + 20,
                    OPTIONS_RECT.top + 20 + (i * option_height),
                    OPTIONS_RECT.width - 40,
                    option_height
                )
                
                draw_panel(screen, option_rect_item, color=(60, 60, 65), border_color=GREY, border_width=1, alpha=200, border_radius=5)
                
                # Draw option number in a circle
                circle_radius = option_height // 2 - 2
                circle_center = (option_rect_item.left + circle_radius + 2, option_rect_item.centery)
                pygame.draw.circle(screen, BLUE, circle_center, circle_radius)
                pygame.draw.circle(screen, WHITE, circle_center, circle_radius, 1)
                
                # Option number
                num_surf = font_medium.render(str(i+1), True, WHITE)
                num_rect = num_surf.get_rect(center=circle_center)
                screen.blit(num_surf, num_rect)
                
                # Option text
                text_surf = font_medium.render(opt, True, WHITE)
                text_rect = text_surf.get_rect(
                    midleft=(option_rect_item.left + circle_radius*2 + 10, option_rect_item.centery)
                )
                screen.blit(text_surf, text_rect)

    # This part is outside the "else" so it always shows, even during loading, if desired.
    # Create character info panel for player and NPC info
    draw_panel(screen, CHAR_INFO_RECT, border_color=GREEN, border_radius=10)
    
    # Display current quest if available
    if game.current_quest:
        quest_text = game.current_quest.get('description', 'None')
        quest_type = game.current_quest.get('type')
        quest_color = GREEN
        if quest_type:
            # Color code by quest type
            if quest_type.name == 'DEFEAT':
                quest_color = RED
            elif quest_type.name == 'TALK':
                quest_color = BLUE
            elif quest_type.name == 'FIND':
                quest_color = GOLD
    else:
        quest_text = "None"
        quest_color = GREEN
    
    # Make sure quest_text is a string
    if quest_text is None:
        quest_text = "None"
    
    # Quest panel
    quest_panel_height = int(SCREEN_HEIGHT * 0.06)
    quest_panel = pygame.Rect(
        NARRATIVE_RECT.left,
        NARRATIVE_RECT.bottom + 5,
        NARRATIVE_RECT.width,
        quest_panel_height
    )
    draw_panel(screen, quest_panel, alpha=200, border_radius=8)
    
    # Quest title
    quest_title = font_small.render("CURRENT QUEST:", True, WHITE)
    screen.blit(quest_title, (quest_panel.left + 10, quest_panel.top + 5))
    
    # Quest text
    quest_surf = font_medium.render(quest_text, True, quest_color)
    quest_text_x = quest_panel.left + quest_title.get_width() + 20
    quest_text_y = quest_panel.top + (quest_panel.height - quest_surf.get_height()) // 2
    screen.blit(quest_surf, (quest_text_x, quest_text_y))

    # Character information panel
    padding = int(CHAR_INFO_RECT.height * 0.1)
    bar_height = int((CHAR_INFO_RECT.height - (padding * 3)) / 2)
    
    # Player information section
    player_section_width = CHAR_INFO_RECT.width // 2 - padding
    
    # Player label
    player_label = font_medium.render("PLAYER", True, GREEN)
    player_label_rect = player_label.get_rect(
        topleft=(CHAR_INFO_RECT.left + padding, CHAR_INFO_RECT.top + padding)
    )
    screen.blit(player_label, player_label_rect)
    
    # Player health bar
    health_bar_rect = pygame.Rect(
        CHAR_INFO_RECT.left + padding,
        player_label_rect.bottom + 5,
        player_section_width,
        bar_height
    )
    
    health_text = f"Health: {game.player.health}/{game.player.max_health}"
    draw_stat_bar(
        screen, health_bar_rect, 
        game.player.health, game.player.max_health,
        HEALTH_BAR_FG, HEALTH_BAR_BG, 
        health_text, font_small
    )
    
    # Player strength bar
    strength_bar_rect = pygame.Rect(
        CHAR_INFO_RECT.left + padding,
        health_bar_rect.bottom + 5,
        player_section_width,
        bar_height
    )
    
    strength_text = f"Strength: {game.player.strength}"
    draw_stat_bar(
        screen, strength_bar_rect,
        game.player.strength, game.player.strength,  # Max = current for display
        STRENGTH_BAR_FG, STRENGTH_BAR_BG,
        strength_text, font_small
    )
    
    # NPC information section (if available)
    if game.current_npc:
        # Determine NPC color based on type
        npc_color = RED  # Default for enemies
        if game.current_npc.npc_type == "merchant":
            npc_color = CYAN
        elif game.current_npc.npc_type == "quest_giver":
            npc_color = GOLD
        
        # NPC name and type
        npc_label = font_medium.render(
            f"{game.current_npc.name} ({game.current_npc.npc_type.capitalize()})",
            True, npc_color
        )
        npc_label_rect = npc_label.get_rect(
            topleft=(CHAR_INFO_RECT.centerx + padding, CHAR_INFO_RECT.top + padding)
        )
        screen.blit(npc_label, npc_label_rect)
        
        # NPC health bar
        npc_health_bar_rect = pygame.Rect(
            CHAR_INFO_RECT.centerx + padding,
            npc_label_rect.bottom + 5,
            player_section_width,
            bar_height
        )
        
        npc_health_text = f"Health: {game.current_npc.health}/{game.current_npc.max_health}"
        draw_stat_bar(
            screen, npc_health_bar_rect,
            game.current_npc.health, game.current_npc.max_health,
            HEALTH_BAR_FG, HEALTH_BAR_BG,
            npc_health_text, font_small
        )
        
        # NPC strength bar
        npc_strength_bar_rect = pygame.Rect(
            CHAR_INFO_RECT.centerx + padding,
            npc_health_bar_rect.bottom + 5,
            player_section_width,
            bar_height
        )
        
        npc_strength_text = f"Strength: {game.current_npc.strength}"
        draw_stat_bar(
            screen, npc_strength_bar_rect,
            game.current_npc.strength, game.current_npc.strength,  # Max = current for display
            STRENGTH_BAR_FG, STRENGTH_BAR_BG,
            npc_strength_text, font_small
        )
    
    # Show options only if we're in playing state
    if game.game_state == GameState.PLAYING:
        help_panel_rect = pygame.Rect(
            SCREEN_WIDTH // 4,
            SCREEN_HEIGHT - 40,
            SCREEN_WIDTH // 2,
            30
        )
        draw_panel(screen, help_panel_rect, alpha=150, border_radius=5)
        
        # Modify help text if AI is thinking
        if game.is_generating_text:
            help_text_str = "AI is thinking... (Q to Menu)"
        else:
            help_text_str = "Press 1-3 to select an option. Press Q to quit to menu."
        
        help_text = font_small.render(help_text_str, True, WHITE)
        help_rect = help_text.get_rect(center=help_panel_rect.center)
        screen.blit(help_text, help_rect)
    
    pygame.display.flip()


def main():
    global current_app_screen, menu_selection, settings_menu_selection, game, current_intro_line, SCREEN_WIDTH, SCREEN_HEIGHT, screen
    global current_resolution_index, fullscreen_enabled, master_volume, music_volume, sfx_volume, typewriter_is_busy
    logger.info("Main function started.")

    # Load assets at the beginning
    load_assets()

    # Start background music if loaded
    if background_music and pygame.mixer.music.get_busy() == 0:
        try:
            pygame.mixer.music.play(-1, fade_ms=2000)  # Play indefinitely, fade in over 2 seconds
            pygame.mixer.music.set_volume(music_volume * master_volume)  # Use combined volume
            logger.info("Background music started.")
        except pygame.error as e:
            logger.error(f"Could not start background music: {e}")

    clock = pygame.time.Clock()
    running = True

    # Track key state for continuous inputs
    key_repeat_delay = 150  # milliseconds before key repeats
    key_repeat_interval = 100  # milliseconds between repeats
    pygame.key.set_repeat(key_repeat_delay, key_repeat_interval)

    try:
        while running:
            # Event handling
            events = pygame.event.get()  # Get all events once per frame
            for event in events:
                if event.type == pygame.QUIT:
                    logger.info("Quit event received. Shutting down.")
                    running = False
                    break

                # Handle window resizing
                if event.type == pygame.VIDEORESIZE:
                    SCREEN_WIDTH, SCREEN_HEIGHT = event.size
                    # Add constraints to minimum window size
                    SCREEN_WIDTH = max(SCREEN_WIDTH, BASE_WIDTH // 2) 
                    SCREEN_HEIGHT = max(SCREEN_HEIGHT, BASE_HEIGHT // 2)
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                    update_fonts()  # Update font sizes based on new screen dimensions
                    update_ui_layout()  # Update UI layout based on new screen dimensions
                    logger.info(f"Screen resized to {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

                if event.type == pygame.KEYDOWN:
                    logger.debug(f"Keydown event: {pygame.key.name(event.key)} ({event.key}) in screen: {current_app_screen.name}")
                    
                    # Global key handling (works in any screen)
                    if event.key == pygame.K_ESCAPE:
                        # ESC goes back to main menu from any screen except outro
                        if current_app_screen not in [AppScreen.MAIN_MENU, AppScreen.OUTRO_VICTORY, AppScreen.OUTRO_GAMEOVER]:
                            current_app_screen = AppScreen.MAIN_MENU
                            logger.info("ESC pressed, returning to main menu")
                            # Reset intro line and completion if returning to menu from intro
                            if current_app_screen == AppScreen.INTRO:
                                current_intro_line = 0
                                if hasattr(display_intro, 'line_completed'):
                                    display_intro.line_completed = False
                            continue

                    # Screen-specific key handling
                    if current_app_screen == AppScreen.MAIN_MENU:
                        if event.key == pygame.K_UP:
                            menu_selection = (menu_selection - 1) % len(MENU_OPTIONS)
                            play_sound("menu_navigate")
                            logger.info(f"Menu selection changed: {MENU_OPTIONS[menu_selection]}")
                        elif event.key == pygame.K_DOWN:
                            menu_selection = (menu_selection + 1) % len(MENU_OPTIONS)
                            play_sound("menu_navigate")
                            logger.info(f"Menu selection changed: {MENU_OPTIONS[menu_selection]}")
                        elif event.key == pygame.K_RETURN:
                            play_sound("menu_select")
                            logger.info(f"Menu option selected: {MENU_OPTIONS[menu_selection]}")
                            if MENU_OPTIONS[menu_selection] == "Start New Game":
                                current_app_screen = AppScreen.INTRO
                                current_intro_line = 0  # Reset intro
                                # Reset the line completion flag for intro
                                if hasattr(display_intro, 'line_completed'):
                                    display_intro.line_completed = False
                                game = None  # Reset game object for new game
                                logger.info("Starting new game, transitioning to INTRO screen.")
                            elif MENU_OPTIONS[menu_selection] == "Settings":
                                current_app_screen = AppScreen.SETTINGS
                                settings_menu_selection = 0  # Reset settings selection
                                logger.info("Navigating to Settings screen.")
                            elif MENU_OPTIONS[menu_selection] == "Options":
                                logger.info("Options selected - not implemented yet.")
                                pass
                            elif event.key == pygame.K_q:
                                logger.info("Quick quit from main menu.")
                                running = False

                    elif current_app_screen == AppScreen.INTRO:
                        if event.key == pygame.K_RETURN:
                            current_intro_line += 1
                            play_sound("menu_select")
                            # Reset the line completion flag for the next line
                            if hasattr(display_intro, 'line_completed'):
                                display_intro.line_completed = False
                            logger.info(f"Intro progressed to line: {current_intro_line}")
                            # If we've reached the end of intro text, transition to gameplay
                            if current_intro_line >= len(INTRO_TEXT):
                                current_app_screen = AppScreen.GAMEPLAY
                                logger.info("Intro complete, transitioning to GAMEPLAY.")
                        elif event.key == pygame.K_SPACE:
                            # Skip button - go straight to gameplay
                            current_app_screen = AppScreen.GAMEPLAY
                            play_sound("menu_select")
                            game = None  # Make sure we start with a fresh game
                            logger.info("Intro skipped with SPACE, transitioning to GAMEPLAY.")
                        elif event.key == pygame.K_q:
                            current_app_screen = AppScreen.MAIN_MENU
                            logger.info("Quit from intro, returning to main menu.")

                    elif current_app_screen == AppScreen.SETTINGS:
                        if event.key == pygame.K_UP:
                            settings_menu_selection = (settings_menu_selection - 1) % len(SETTINGS_OPTIONS)
                            play_sound("menu_navigate")
                        elif event.key == pygame.K_DOWN:
                            settings_menu_selection = (settings_menu_selection + 1) % len(SETTINGS_OPTIONS)
                            play_sound("menu_navigate")
                        elif event.key == pygame.K_LEFT:
                            selected_setting = SETTINGS_OPTIONS[settings_menu_selection]
                            if selected_setting == "Resolution":
                                current_resolution_index = (current_resolution_index - 1) % len(SUPPORTED_RESOLUTIONS)
                                play_sound("menu_navigate")
                            elif selected_setting == "Master Volume":
                                master_volume = max(0.0, round(master_volume - 0.1, 1))
                                pygame.mixer.music.set_volume(music_volume * master_volume)  # Update immediately
                                play_sound("menu_navigate", master_volume * sfx_volume)  # Play sound with new volume
                            elif selected_setting == "Music Volume":
                                music_volume = max(0.0, round(music_volume - 0.1, 1))
                                pygame.mixer.music.set_volume(music_volume * master_volume)  # Update immediately
                                play_sound("menu_navigate")
                            elif selected_setting == "SFX Volume":
                                sfx_volume = max(0.0, round(sfx_volume - 0.1, 1))
                                play_sound("menu_navigate", master_volume * sfx_volume)  # Play sound with new volume
                        elif event.key == pygame.K_RIGHT:
                            selected_setting = SETTINGS_OPTIONS[settings_menu_selection]
                            if selected_setting == "Resolution":
                                current_resolution_index = (current_resolution_index + 1) % len(SUPPORTED_RESOLUTIONS)
                                play_sound("menu_navigate")
                            elif selected_setting == "Master Volume":
                                master_volume = min(1.0, round(master_volume + 0.1, 1))
                                pygame.mixer.music.set_volume(music_volume * master_volume)
                                play_sound("menu_navigate", master_volume * sfx_volume)
                            elif selected_setting == "Music Volume":
                                music_volume = min(1.0, round(music_volume + 0.1, 1))
                                pygame.mixer.music.set_volume(music_volume * master_volume)
                                play_sound("menu_navigate")
                            elif selected_setting == "SFX Volume":
                                sfx_volume = min(1.0, round(sfx_volume + 0.1, 1))
                                play_sound("menu_navigate", master_volume * sfx_volume)
                        elif event.key == pygame.K_RETURN:
                            selected_setting = SETTINGS_OPTIONS[settings_menu_selection]
                            play_sound("menu_select")
                            if selected_setting == "Fullscreen":
                                fullscreen_enabled = not fullscreen_enabled
                            elif selected_setting == "Apply":
                                SCREEN_WIDTH, SCREEN_HEIGHT = SUPPORTED_RESOLUTIONS[current_resolution_index]
                                flags = pygame.RESIZABLE
                                if fullscreen_enabled:
                                    flags |= pygame.FULLSCREEN
                                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
                                update_fonts()
                                update_ui_layout()
                                logger.info(f"Applied settings: Resolution {SCREEN_WIDTH}x{SCREEN_HEIGHT}, Fullscreen: {fullscreen_enabled}")
                            elif selected_setting == "Back to Main Menu":
                                current_app_screen = AppScreen.MAIN_MENU
                                logger.info("Returning to Main Menu from Settings.")
                        elif event.key == pygame.K_ESCAPE:
                            current_app_screen = AppScreen.MAIN_MENU
                            play_sound("menu_select")
                            logger.info("Returning to Main Menu from Settings (ESC).")
                            
                    elif current_app_screen == AppScreen.GAMEPLAY:
                        if not game:  # Ensure game is initialized if somehow skipped intro
                            logger.warning("Game object was None when entering GAMEPLAY screen. Initializing now.")
                            game = Game()
                            if game.game_state == GameState.PLAYING and game.current_npc:
                                game.ai_dm.update_quest() # This might trigger NLP
                            logger.info("New game instance created for GAMEPLAY screen.")
                        
                        if game and game.game_state == GameState.PLAYING:
                            # If AI is generating text, only allow quit or dialogue advancement if applicable
                            if game.is_generating_text:
                                if event.key == pygame.K_q:
                                    logger.info("Quit from gameplay screen while AI is thinking.")
                                    current_app_screen = AppScreen.MAIN_MENU
                                # Potentially allow skipping typewriter even if AI is thinking in background for next step
                                elif (event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER or event.key == pygame.K_SPACE) and \
                                     game.active_dialogue_npc and game.awaiting_typewriter_completion and typewriter_is_busy:
                                    logger.info(f"GAMEPLAY (AI thinking): Key {pygame.key.name(event.key)} to skip typewriter.")
                                    pass # The typewriter loop will catch this
                                else:
                                    logger.debug(f"Key {pygame.key.name(event.key)} ignored while AI is generating text.")
                                continue # Skip other gameplay inputs if AI is busy

                            # Check for dialogue advancement keys first (if not generating text)
                            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER or event.key == pygame.K_SPACE:  # Added K_SPACE
                                if game.active_dialogue_npc and \
                                   game.dialogue_requires_player_advance and \
                                   not game.awaiting_typewriter_completion:
                                    logger.info(f"GAMEPLAY: Key {pygame.key.name(event.key)} detected to advance dialogue.")  # Clarified log
                                    game.player_advance_dialogue_key()
                                else:
                                    logger.info(f"GAMEPLAY: Key {pygame.key.name(event.key)} pressed, but conditions not met for dialogue advance.")
                            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                                choice = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}.get(event.key)
                                logger.info(f"Player input in gameplay: {choice}")  # This log is from main.py
                                play_sound("player_action")
                                game.handle_input(choice)  # game.handle_input will log if it's ignored
                                if game.last_action_led_to_quest_complete:
                                    play_sound("quest_complete")
                                    game.last_action_led_to_quest_complete = False
                                if game.last_action_led_to_new_quest:
                                    play_sound("quest_new")
                                    game.last_action_led_to_new_quest = False
                            elif event.key == pygame.K_q:
                                logger.info("Quit from gameplay screen.")
                                current_app_screen = AppScreen.MAIN_MENU

                    elif current_app_screen in [AppScreen.OUTRO_VICTORY, AppScreen.OUTRO_GAMEOVER]:
                        if event.key == pygame.K_q:
                            logger.info("Quit from outro screen.")
                            play_sound("menu_select")
                            running = False
                        elif event.key == pygame.K_m or event.key == pygame.K_RETURN:
                            current_app_screen = AppScreen.MAIN_MENU
                            play_sound("menu_select")
                            game = None  # Clear the game state
                            logger.info("Returning to Main Menu from outro screen.")

            # --- Sound Event Handling ---
            if game and game.play_sound_event:
                sound_to_play = None
                vol = sfx_volume * master_volume
                if game.play_sound_event == "dialogue_start": sound_to_play = "menu_select"
                elif game.play_sound_event == "dialogue_advance": sound_to_play = "menu_navigate"
                elif game.play_sound_event == "dialogue_end": sound_to_play = "menu_select"
                elif game.play_sound_event == "quest_new": sound_to_play = "quest_new"
                elif game.play_sound_event == "quest_complete": sound_to_play = "quest_complete"
                
                if sound_to_play:
                    play_sound(sound_to_play, volume=vol)
                game.play_sound_event = None  # Consume the event
            
            # --- Game Logic for starting typewriter ---
            # This must be AFTER event handling and BEFORE drawing,
            # so typewriter_is_busy is correctly set for the display_gameplay call.
            if current_app_screen == AppScreen.GAMEPLAY and game:
                if game.awaiting_typewriter_completion and not typewriter_is_busy:
                    if game.narrative: 
                        current_dialogue_line = game.narrative[0] 
                        logger.debug(f"Main loop initiating typewriter for: {current_dialogue_line}")
                        # This call is blocking for the duration of the line typing/skip
                        if not typewriter_effect(screen, current_dialogue_line, font_small, WHITE, NARRATIVE_RECT, speed=30, game_instance=game):
                            running = False  # Typewriter effect was quit
                            logger.info("Exiting due to quit during typewriter effect.")

            # --- Screen Drawing ---
            previous_app_screen = current_app_screen  # For logging screen transitions
            
            if current_app_screen == AppScreen.LOADING:
                display_loading_screen()
                current_app_screen = AppScreen.MAIN_MENU

            elif current_app_screen == AppScreen.MAIN_MENU:
                display_main_menu()

            elif current_app_screen == AppScreen.SETTINGS:  # New case for settings screen
                display_settings_screen()

            elif current_app_screen == AppScreen.INTRO:
                display_intro()

            elif current_app_screen == AppScreen.GAMEPLAY:
                display_gameplay()

            elif current_app_screen == AppScreen.OUTRO_VICTORY:
                display_outro(["Victory Achieved!", "The realm is safe, for now."])

            elif current_app_screen == AppScreen.OUTRO_GAMEOVER:
                display_outro(["Game Over", "Your journey ends here."])

            # Handle screen transitions
            if previous_app_screen != current_app_screen:
                logger.info(f"App screen changed from {previous_app_screen.name} to {current_app_screen.name}")
                if current_app_screen == AppScreen.INTRO and hasattr(display_intro, 'line_completed'):
                    display_intro.line_completed = False
                previous_app_screen = current_app_screen 

            # Cap at 30 FPS
            clock.tick(30)
            
    except Exception as e:
        logger.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
    finally:
        logger.info("Application shutting down.")
        pygame.quit()


if __name__ == "__main__":
    try:
        logger.info("Application __main__ started.")
        main()
    except SystemExit:
        logger.info("Pygame quit normally or system exit called.")
    except Exception as e:
        logger.critical(f"Unhandled exception at top level: {e}", exc_info=True)
        print(f"A critical error occurred. Please check {LOG_FILE_ERROR} for details.")
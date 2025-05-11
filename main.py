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
BASE_WIDTH, BASE_HEIGHT = 1280, 720
SCREEN_WIDTH = min(int(SYSTEM_WIDTH * 0.8), BASE_WIDTH)
SCREEN_HEIGHT = min(int(SYSTEM_HEIGHT * 0.8), BASE_HEIGHT)

# Make the screen resizable
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Text-Based AI D&D RPG - Enhanced Edition")

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

# UI Theme
HEALTH_BAR_BG = (80, 0, 0)
HEALTH_BAR_FG = (220, 30, 30)
STRENGTH_BAR_BG = (0, 50, 80)
STRENGTH_BAR_FG = (30, 100, 220)

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
def draw_panel(surface, rect, color=PANEL_BG, border_color=GREY, border_width=2, alpha=220):
    # Create a surface with per-pixel alpha
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    # Fill with semi-transparent color
    panel.fill((color[0], color[1], color[2], alpha))
    # Draw border
    pygame.draw.rect(panel, border_color, (0, 0, rect.width, rect.height), border_width)
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
    draw_panel(surface, rect)
    
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

def typewriter_effect(surface, text, font, color, rect, speed=15, sound=None):
    """Displays text with a typewriter effect. Clears the rect area first."""
    # First draw the panel background
    draw_panel(surface, rect)
    
    # Adjust rect for padding
    padding = int(min(rect.width, rect.height) * 0.05)
    inner_rect = pygame.Rect(
        rect.left + padding,
        rect.top + padding,
        rect.width - (padding * 2),
        rect.height - (padding * 2)
    )

    words = text.split(' ')
    lines_to_render = []  # This will hold the strings for each line
    current_line_words = []
    line_spacing = font.get_linesize()

    # Calculate lines based on inner_rect width
    for word in words:
        temp_line_words = current_line_words + [word]
        line_width, _ = font.size(' '.join(temp_line_words))
        if line_width > inner_rect.width and current_line_words:  # if adding word exceeds width and there are words in current_line
            lines_to_render.append(' '.join(current_line_words))
            current_line_words = [word]
        else:
            current_line_words.append(word)
    if current_line_words:  # Add any remaining words
        lines_to_render.append(' '.join(current_line_words))

    rendered_lines_surfaces = []  # Store surfaces of fully typed lines
    current_y = inner_rect.top
    
    # Allow skipping the typing animation
    skip_animation = False

    for line_idx, line_text in enumerate(lines_to_render):
        if current_y + line_spacing > inner_rect.bottom:  # Check if there's space for the new line
            break

        typed_chars_for_current_line = ""
        for char_idx, char_to_type in enumerate(line_text):
            if skip_animation:
                # If animation is skipped, jump to the fully typed text
                break
                
            typed_chars_for_current_line += char_to_type

            # Redraw the panel for each frame
            draw_panel(surface, rect)

            # Blit previously completed lines
            temp_blit_y = inner_rect.top
            for prev_line_surf in rendered_lines_surfaces:
                surface.blit(prev_line_surf, (inner_rect.left, temp_blit_y))
                temp_blit_y += line_spacing

            # Render and blit the current line being typed (at its correct y position)
            current_line_surf = font.render(typed_chars_for_current_line, True, color)
            surface.blit(current_line_surf, (inner_rect.left, current_y))

            # Add a blinking cursor at the end of the current line
            if (pygame.time.get_ticks() // 500) % 2 == 0:  # Blink every 500ms
                cursor_pos = (inner_rect.left + current_line_surf.get_width() + 2, current_y)
                cursor_height = font.get_height()
                pygame.draw.line(surface, color, cursor_pos, 
                                (cursor_pos[0], cursor_pos[1] + cursor_height - 2), 2)

            pygame.display.update(rect)  # Update only the text rect for efficiency
            pygame.time.wait(speed)

            # Event handling during typing to prevent freeze
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.warning("Quit event during typewriter effect.")
                    pygame.quit()
                    import sys
                    sys.exit()
                # Skip animation on SPACE or RETURN
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    skip_animation = True
                    break

        # If animation was skipped, render the full line immediately
        if skip_animation:
            typed_chars_for_current_line = line_text
        
        # Current line is fully typed, store its fully rendered surface
        completed_line_surf = font.render(line_text, True, color)
        rendered_lines_surfaces.append(completed_line_surf)
        current_y += line_spacing  # Move to next line position
    
    # If we skipped the animation, make sure all text is visible
    if skip_animation:
        # Redraw everything for the final state
        draw_panel(surface, rect)
        temp_blit_y = inner_rect.top
        for completed_line_surf in rendered_lines_surfaces:
            surface.blit(completed_line_surf, (inner_rect.left, temp_blit_y))
            temp_blit_y += line_spacing
        pygame.display.update(rect)

    # Final state of the rect is now drawn.
    return skip_animation  # Return whether the animation was skipped

# The rest of the code remains unchanged.
game = None
current_app_screen = AppScreen.LOADING
menu_selection = 0


def display_loading_screen():
    screen.fill(DARK_GREY)
    loading_text = font_large.render("Loading...", True, WHITE)
    text_rect = loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
    screen.blit(loading_text, text_rect)
    pygame.display.flip()
    pygame.time.wait(2000)


MENU_OPTIONS = ["Start New Game", "Options", "Quit"]


def display_main_menu():
    screen.fill(DARK_GREY)
    
    # Draw a decorative header panel
    header_rect = pygame.Rect(
        int(SCREEN_WIDTH * 0.1),
        int(SCREEN_HEIGHT * 0.1),
        int(SCREEN_WIDTH * 0.8),
        int(SCREEN_HEIGHT * 0.2)
    )
    draw_panel(screen, header_rect, color=DARKER_GREY, border_color=GREEN, border_width=3)
    
    # Draw a decorative background panel for menu options
    menu_panel_rect = pygame.Rect(
        int(SCREEN_WIDTH * 0.2),
        int(SCREEN_HEIGHT * 0.4),
        int(SCREEN_WIDTH * 0.6),
        int(SCREEN_HEIGHT * 0.4)
    )
    draw_panel(screen, menu_panel_rect, alpha=180)
    
    # Title with shadow effect
    shadow_offset = max(2, int(get_scaled_font_size(3)))
    title_text = "Text RPG Adventure"
    shadow_surf = font_title.render(title_text, True, BLACK)
    title_surf = font_title.render(title_text, True, GREEN)
    
    shadow_rect = shadow_surf.get_rect(center=(header_rect.centerx + shadow_offset, header_rect.centery + shadow_offset))
    title_rect = title_surf.get_rect(center=(header_rect.centerx, header_rect.centery))
    
    screen.blit(shadow_surf, shadow_rect)
    screen.blit(title_surf, title_rect)

    # Subtitle
    subtitle = font_medium.render("AI-powered D&D Adventure", True, LIGHT_GREY)
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
            option_box = pygame.Rect(
                menu_panel_rect.left + 20,
                menu_panel_rect.top + 20 + (i * option_spacing),
                menu_panel_rect.width - 40,
                option_spacing - 10
            )
            pygame.draw.rect(screen, DARKER_GREY, option_box, border_radius=5)
            pygame.draw.rect(screen, color, option_box, 2, border_radius=5)
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


INTRO_TEXT = [
    "In a realm shrouded in ancient magic and lingering shadows...",
    "You awaken with a hazy memory, a sturdy resolve, and a path unknown.",
    "Your adventure begins now. What choices will you make?"
]
current_intro_line = 0


def display_intro():
    global current_intro_line, current_app_screen
    
    screen.fill(DARK_GREY)
    
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
    draw_panel(screen, prompt_panel, border_color=BLUE)
    
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
    
    # Create a panel for the outro message
    outro_panel = pygame.Rect(
        int(SCREEN_WIDTH * 0.1),
        int(SCREEN_HEIGHT * 0.2),
        int(SCREEN_WIDTH * 0.8),
        int(SCREEN_HEIGHT * 0.5)
    )
    
    border_color = GREEN if current_app_screen == AppScreen.OUTRO_VICTORY else RED
    draw_panel(screen, outro_panel, color=DARKER_GREY, border_color=border_color, border_width=3)
    
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
    draw_panel(screen, prompt_panel, border_color=BLUE)
    
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

    screen.fill(DARK_GREY)

    # Get the latest text content from the game
    narrative, options = game.get_display_text()

    # Render the narrative text with proper wrapping
    render_text_wrapped(screen, "\n".join(narrative), font_small, WHITE, NARRATIVE_RECT)

    # Display the options panel
    draw_panel(screen, OPTIONS_RECT, border_color=BLUE)
    
    # Create character info panel for player and NPC info
    draw_panel(screen, CHAR_INFO_RECT, border_color=GREEN)
    
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
    
    # Quest panel
    quest_panel_height = int(SCREEN_HEIGHT * 0.06)
    quest_panel = pygame.Rect(
        NARRATIVE_RECT.left,
        NARRATIVE_RECT.bottom + 5,
        NARRATIVE_RECT.width,
        quest_panel_height
    )
    draw_panel(screen, quest_panel, alpha=200)
    
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
        game.player.strength, game.player.strength, # Max = current for display
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
            game.current_npc.strength, game.current_npc.strength, # Max = current for display
            STRENGTH_BAR_FG, STRENGTH_BAR_BG,
            npc_strength_text, font_small
        )
    
    # Show options only if we're in playing state
    if game.game_state == GameState.PLAYING and options:
        option_height = font_medium.get_linesize() + 10
        for i, opt in enumerate(options):
            # Draw option background with highlight effect for visual separation
            option_rect = pygame.Rect(
                OPTIONS_RECT.left + 20,
                OPTIONS_RECT.top + 20 + (i * option_height),
                OPTIONS_RECT.width - 40,
                option_height
            )
            
            # Draw subtle highlight for option background
            highlight_color = (60, 60, 65)  # Slightly lighter than panel background
            pygame.draw.rect(screen, highlight_color, option_rect, border_radius=3)
            pygame.draw.rect(screen, GREY, option_rect, 1, border_radius=3)
            
            # Draw option number in a circle
            circle_radius = option_height // 2 - 2
            circle_center = (option_rect.left + circle_radius + 2, option_rect.centery)
            pygame.draw.circle(screen, BLUE, circle_center, circle_radius)
            pygame.draw.circle(screen, WHITE, circle_center, circle_radius, 1)
            
            # Option number
            num_surf = font_medium.render(str(i+1), True, WHITE)
            num_rect = num_surf.get_rect(center=circle_center)
            screen.blit(num_surf, num_rect)
            
            # Option text
            text_surf = font_medium.render(opt, True, WHITE)
            text_rect = text_surf.get_rect(
                midleft=(option_rect.left + circle_radius*2 + 10, option_rect.centery)
            )
            screen.blit(text_surf, text_rect)
    
    # Check for game state changes and update app screen accordingly
    if game.game_state == GameState.GAME_OVER:
        logger.info("Game state changed to GAME_OVER, transitioning to outro screen")
        current_app_screen = AppScreen.OUTRO_GAMEOVER
    elif game.game_state == GameState.VICTORY:
        logger.info("Game state changed to VICTORY, transitioning to victory screen")
        current_app_screen = AppScreen.OUTRO_VICTORY
    
    # Instructions for player at the bottom
    if game.game_state == GameState.PLAYING:
        help_panel = pygame.Rect(
            SCREEN_WIDTH // 4,
            SCREEN_HEIGHT - 40,
            SCREEN_WIDTH // 2,
            30
        )
        draw_panel(screen, help_panel, alpha=150)
        
        help_text = font_small.render("Press 1-3 to select an option. Press Q to quit.", True, WHITE)
        help_rect = help_text.get_rect(center=help_panel.center)
        screen.blit(help_text, help_rect)
    
    pygame.display.flip()


def main():
    global current_app_screen, menu_selection, game, current_intro_line, SCREEN_WIDTH, SCREEN_HEIGHT
    logger.info("Main function started.")

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
                            logger.info(f"Menu selection changed: {MENU_OPTIONS[menu_selection]}")
                        elif event.key == pygame.K_DOWN:
                            menu_selection = (menu_selection + 1) % len(MENU_OPTIONS)
                            logger.info(f"Menu selection changed: {MENU_OPTIONS[menu_selection]}")
                        elif event.key == pygame.K_RETURN:
                            logger.info(f"Menu option selected: {MENU_OPTIONS[menu_selection]}")
                            if MENU_OPTIONS[menu_selection] == "Start New Game":
                                current_app_screen = AppScreen.INTRO
                                current_intro_line = 0  # Reset intro
                                # Reset the line completion flag for intro
                                if hasattr(display_intro, 'line_completed'):
                                    display_intro.line_completed = False
                                game = None  # Reset game object for new game
                                logger.info("Starting new game, transitioning to INTRO screen.")
                            elif MENU_OPTIONS[menu_selection] == "Options":
                                logger.info("Options selected - not implemented yet.")
                                pass
                            elif MENU_OPTIONS[menu_selection] == "Quit":
                                logger.info("Quit selected from menu.")
                                running = False
                        elif event.key == pygame.K_q:
                            logger.info("Quick quit from main menu.")
                            running = False

                    elif current_app_screen == AppScreen.INTRO:
                        if event.key == pygame.K_RETURN:
                            current_intro_line += 1
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
                            game = None  # Make sure we start with a fresh game
                            logger.info("Intro skipped with SPACE, transitioning to GAMEPLAY.")
                        elif event.key == pygame.K_q:
                            current_app_screen = AppScreen.MAIN_MENU
                            logger.info("Quit from intro, returning to main menu.")

                    elif current_app_screen == AppScreen.GAMEPLAY:
                        if not game:  # Ensure game is initialized if somehow skipped intro
                            logger.warning("Game object was None when entering GAMEPLAY screen. Initializing now.")
                            game = Game()
                            if game.game_state == GameState.PLAYING and game.current_npc:
                                game.ai_dm.update_quest()
                            logger.info("New game instance created for GAMEPLAY screen.")
                        if game and game.game_state == GameState.PLAYING:
                            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                                choice = {pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3}.get(event.key)
                                logger.info(f"Player input in gameplay: {choice}")
                                game.handle_input(choice)
                            elif event.key == pygame.K_q:
                                logger.info("Quit from gameplay screen.")
                                current_app_screen = AppScreen.MAIN_MENU
                                # Don't quit the application, just return to menu

                    elif current_app_screen in [AppScreen.OUTRO_VICTORY, AppScreen.OUTRO_GAMEOVER]:
                        if event.key == pygame.K_q:
                            logger.info("Quit from outro screen.")
                            running = False
                        elif event.key == pygame.K_m or event.key == pygame.K_RETURN:
                            current_app_screen = AppScreen.MAIN_MENU
                            game = None  # Clear the game state
                            logger.info("Returning to Main Menu from outro screen.")

            # Screen rendering based on state
            previous_app_screen = current_app_screen  # For logging screen transitions
            
            if current_app_screen == AppScreen.LOADING:
                display_loading_screen()
                current_app_screen = AppScreen.MAIN_MENU

            elif current_app_screen == AppScreen.MAIN_MENU:
                display_main_menu()

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
                # If transitioning to a different screen, reset line completion for intro
                if current_app_screen == AppScreen.INTRO and hasattr(display_intro, 'line_completed'):
                    display_intro.line_completed = False
                # Moved previous_app_screen update here to correctly log transitions
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
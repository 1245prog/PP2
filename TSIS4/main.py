from __future__ import annotations

import json
from pathlib import Path

import pygame

import db
from config import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    FPS,
    SETTINGS_FILE,
    DEFAULT_SETTINGS,
    BACKGROUND_COLOR,
    PANEL_COLOR,
    TEXT_COLOR,
    COLOR_STEP,
    clamp,
)
from game import SnakeGame, Button

SETTINGS_PATH = Path(SETTINGS_FILE)

def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            if isinstance(data, dict):
                settings.update(data)
            if "snake_color" in settings and isinstance(settings["snake_color"], list) and len(settings["snake_color"]) == 3:
                settings["snake_color"] = [clamp(v) for v in settings["snake_color"]]
            return settings
        except (json.JSONDecodeError, OSError):
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict):
    SETTINGS_PATH.write_text(json.dumps(settings, indent=4, ensure_ascii=False), encoding="utf-8")

class App:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
            self.sound_available = True
        except pygame.error:
            self.sound_available = False

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("TSIS 4 Snake")
        self.clock = pygame.time.Clock()

        self.font_big = pygame.font.SysFont(None, 54)
        self.font = pygame.font.SysFont(None, 32)
        self.font_small = pygame.font.SysFont(None, 24)

        self.settings = load_settings()
        self.db_ready = db.init_db()

        self.state = "menu"
        self.username_input = ""
        self.error_message = ""

        self.game: SnakeGame | None = None
        self.leaderboard_rows = []
        self.saved_game_result = False

        self.make_buttons()
        self.refresh_leaderboard()
        self.apply_sound_setting()

    def apply_sound_setting(self):
        if not self.sound_available:
            return
        if not bool(self.settings.get("sound", True)):
            pygame.mixer.music.stop()

    def make_buttons(self):
        self.play_btn = Button(pygame.Rect(220, 260, 200, 44), "Play")
        self.leaderboard_btn = Button(pygame.Rect(220, 316, 200, 44), "Leaderboard")
        self.settings_btn = Button(pygame.Rect(220, 372, 200, 44), "Settings")
        self.quit_btn = Button(pygame.Rect(220, 428, 200, 44), "Quit")

        self.back_btn = Button(pygame.Rect(20, 580, 120, 38), "Back")
        self.save_back_btn = Button(pygame.Rect(470, 580, 150, 38), "Save & Back")
        self.retry_btn = Button(pygame.Rect(180, 420, 120, 44), "Retry")
        self.menu_btn = Button(pygame.Rect(320, 420, 120, 44), "Main Menu")

        self.grid_toggle_btn = Button(pygame.Rect(220, 130, 200, 38), "Toggle Grid")
        self.sound_toggle_btn = Button(pygame.Rect(220, 180, 200, 38), "Toggle Sound")

        self.r_minus = Button(pygame.Rect(220, 250, 38, 34), "-")
        self.r_plus = Button(pygame.Rect(390, 250, 38, 34), "+")
        self.g_minus = Button(pygame.Rect(220, 294, 38, 34), "-")
        self.g_plus = Button(pygame.Rect(390, 294, 38, 34), "+")
        self.b_minus = Button(pygame.Rect(220, 338, 38, 34), "-")
        self.b_plus = Button(pygame.Rect(390, 338, 38, 34), "+")

    def refresh_leaderboard(self):
        self.leaderboard_rows = db.get_leaderboard(10)

    def start_game(self):
        username = self.username_input.strip()
        if not username:
            self.error_message = "Enter a username first."
            return

        personal_best = db.get_personal_best(username)
        self.game = SnakeGame(self.settings, username, personal_best)
        self.game.start(pygame.time.get_ticks())
        self.saved_game_result = False
        self.state = "game"
        self.error_message = ""

    def save_current_settings(self):
        save_settings(self.settings)
        self.apply_sound_setting()

    def draw_text_center(self, text: str, y: int, font=None, color=TEXT_COLOR):
        font = font or self.font
        surface = font.render(text, True, color)
        self.screen.blit(surface, surface.get_rect(center=(WINDOW_WIDTH // 2, y)))

    def draw_label(self, text: str, x: int, y: int, font=None, color=TEXT_COLOR):
        font = font or self.font
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def handle_menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.username_input = self.username_input[:-1]
            elif event.key == pygame.K_RETURN:
                self.start_game()
            else:
                if len(self.username_input) < 20 and event.unicode.isprintable():
                    self.username_input += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.play_btn.clicked(pos):
                self.start_game()
            elif self.leaderboard_btn.clicked(pos):
                self.refresh_leaderboard()
                self.state = "leaderboard"
            elif self.settings_btn.clicked(pos):
                self.state = "settings"
            elif self.quit_btn.clicked(pos):
                raise SystemExit

    def handle_leaderboard_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.back_btn.clicked(event.pos):
                self.state = "menu"

    def handle_settings_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.grid_toggle_btn.clicked(pos):
                self.settings["grid_overlay"] = not bool(self.settings.get("grid_overlay", True))
            elif self.sound_toggle_btn.clicked(pos):
                self.settings["sound"] = not bool(self.settings.get("sound", True))
            elif self.r_minus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[0] = clamp(rgb[0] - COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.r_plus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[0] = clamp(rgb[0] + COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.g_minus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[1] = clamp(rgb[1] - COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.g_plus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[1] = clamp(rgb[1] + COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.b_minus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[2] = clamp(rgb[2] - COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.b_plus.clicked(pos):
                rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
                rgb[2] = clamp(rgb[2] + COLOR_STEP)
                self.settings["snake_color"] = rgb
            elif self.save_back_btn.clicked(pos):
                self.save_current_settings()
                self.state = "menu"
            elif self.back_btn.clicked(pos):
                self.state = "menu"

    def handle_game_over_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.retry_btn.clicked(pos):
                self.start_game()
            elif self.menu_btn.clicked(pos):
                self.state = "menu"

    def handle_game_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.game.set_direction((0, -1))
            elif event.key == pygame.K_DOWN:
                self.game.set_direction((0, 1))
            elif event.key == pygame.K_LEFT:
                self.game.set_direction((-1, 0))
            elif event.key == pygame.K_RIGHT:
                self.game.set_direction((1, 0))

    def update_game(self):
        if not self.game:
            return

        now = pygame.time.get_ticks()
        self.game.update(now)

        if self.game.game_over and not self.saved_game_result:
            final_score = self.game.final_score()
            level_reached = self.game.level_reached()

            if self.db_ready:
                db.save_game_session(self.game.username, final_score, level_reached)
                self.game.personal_best = db.get_personal_best(self.game.username)
            else:
                self.error_message = "Database is not connected. Check config.py and PostgreSQL."

            self.refresh_leaderboard()
            self.saved_game_result = True
            self.state = "game_over"

    def draw_menu(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_text_center("TSIS 4 Snake", 110, self.font_big)
        self.draw_text_center("Enter username before starting", 155, self.font)

        box = pygame.Rect(170, 190, 300, 42)
        pygame.draw.rect(self.screen, (45, 50, 58), box, border_radius=10)
        pygame.draw.rect(self.screen, (220, 220, 220), box, 2, border_radius=10)
        name_surface = self.font.render(self.username_input + "|", True, TEXT_COLOR)
        self.screen.blit(name_surface, (box.x + 10, box.y + 8))

        if self.error_message:
            self.draw_text_center(self.error_message, 235, self.font_small, (255, 120, 120))

        mouse_pos = pygame.mouse.get_pos()
        self.play_btn.draw(self.screen, self.font, mouse_pos)
        self.leaderboard_btn.draw(self.screen, self.font, mouse_pos)
        self.settings_btn.draw(self.screen, self.font, mouse_pos)
        self.quit_btn.draw(self.screen, self.font, mouse_pos)

        self.draw_text_center("Press Enter to start", 490, self.font_small, (180, 180, 180))

    def draw_leaderboard(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_text_center("Leaderboard", 42, self.font_big)

        header = self.font_small.render("Rank   Username          Score   Level   Date", True, (220, 220, 220))
        self.screen.blit(header, (48, 92))

        y = 130
        for idx, row in enumerate(self.leaderboard_rows, start=1):
            date_value = row["played_at"]
            date_str = date_value.strftime("%Y-%m-%d %H:%M") if hasattr(date_value, "strftime") else str(date_value)
            line = f"{idx:<5} {row['username'][:15]:<16} {row['score']:<7} {row['level_reached']:<6} {date_str}"
            surf = self.font_small.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (48, y))
            y += 33

        mouse_pos = pygame.mouse.get_pos()
        self.back_btn.draw(self.screen, self.font, mouse_pos)

    def draw_settings(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_text_center("Settings", 42, self.font_big)

        self.grid_toggle_btn.text = f"Grid overlay: {'ON' if self.settings.get('grid_overlay', True) else 'OFF'}"
        self.sound_toggle_btn.text = f"Sound: {'ON' if self.settings.get('sound', True) else 'OFF'}"

        mouse_pos = pygame.mouse.get_pos()
        self.grid_toggle_btn.draw(self.screen, self.font, mouse_pos)
        self.sound_toggle_btn.draw(self.screen, self.font, mouse_pos)

        rgb = list(self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"]))
        color_box = pygame.Rect(470, 238, 120, 120)
        pygame.draw.rect(self.screen, tuple(rgb), color_box, border_radius=12)
        pygame.draw.rect(self.screen, (220, 220, 220), color_box, 2, border_radius=12)

        channel_rows = [
            ("R", 250, rgb[0], self.r_minus, self.r_plus),
            ("G", 294, rgb[1], self.g_minus, self.g_plus),
            ("B", 338, rgb[2], self.b_minus, self.b_plus),
        ]
        for label, y, value, minus_btn, plus_btn in channel_rows:
            self.draw_label(f"{label}: {value}", 275, y + 4, self.font)
            minus_btn.draw(self.screen, self.font, mouse_pos)
            plus_btn.draw(self.screen, self.font, mouse_pos)

        self.back_btn.draw(self.screen, self.font, mouse_pos)
        self.save_back_btn.draw(self.screen, self.font, mouse_pos)

    def draw_game(self):
        self.screen.fill(BACKGROUND_COLOR)
        if self.game:
            self.game.draw(self.screen)

        now = pygame.time.get_ticks()
        hud = self.game.hud_lines(now) if self.game else []
        y = 8
        for line in hud:
            surf = self.font_small.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (8, y))
            y += 22

        if self.game:
            info = self.font_small.render(f"Length: {len(self.game.snake)}", True, TEXT_COLOR)
            self.screen.blit(info, (8, y))

    def draw_game_over(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_text_center("Game Over", 84, self.font_big)

        if self.game:
            stats = self.game.game_over_stats()
            lines = [
                f"Username: {stats['username']}",
                f"Final score: {stats['score']}",
                f"Level reached: {stats['level']}",
                f"Personal best: {stats['personal_best']}",
            ]
            y = 170
            for line in lines:
                surf = self.font.render(line, True, TEXT_COLOR)
                self.screen.blit(surf, surf.get_rect(center=(WINDOW_WIDTH // 2, y)))
                y += 46

        mouse_pos = pygame.mouse.get_pos()
        self.retry_btn.draw(self.screen, self.font, mouse_pos)
        self.menu_btn.draw(self.screen, self.font, mouse_pos)

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

                if self.state == "menu":
                    self.handle_menu_event(event)
                elif self.state == "leaderboard":
                    self.handle_leaderboard_event(event)
                elif self.state == "settings":
                    self.handle_settings_event(event)
                elif self.state == "game":
                    self.handle_game_event(event)
                elif self.state == "game_over":
                    self.handle_game_over_event(event)

            if self.state == "game":
                self.update_game()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "leaderboard":
                self.draw_leaderboard()
            elif self.state == "settings":
                self.draw_settings()
            elif self.state == "game":
                self.draw_game()
            elif self.state == "game_over":
                self.draw_game_over()

            pygame.display.flip()
            self.clock.tick(FPS)

def main():
    App().run()

if __name__ == "__main__":
    main()

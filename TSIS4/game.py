from __future__ import annotations

from dataclasses import dataclass
from collections import deque
import random
from typing import Optional

import pygame

from config import (
    CELL_SIZE,
    GRID_HEIGHT,
    GRID_WIDTH,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    DEFAULT_SETTINGS,
    BACKGROUND_COLOR,
    GRID_COLOR,
    TEXT_COLOR,
    FOOD_COLORS,
    TIMED_FOOD_COLOR,
    POISON_COLOR,
    SPEED_BOOST_COLOR,
    SLOW_MOTION_COLOR,
    SHIELD_COLOR,
    FOOD_LEVEL_STEP,
    INITIAL_MOVE_DELAY_MS,
    MIN_MOVE_DELAY_MS,
    MOVE_DELAY_DECREASE_PER_LEVEL,
    FOOD_POINTS_CHOICES,
    TIMED_FOOD_TTL_MS,
    POISON_TTL_MS,
    POWERUP_TTL_MS,
    SPEED_BOOST_MS,
    SLOW_MOTION_MS,
    POWERUP_SPAWN_MIN_MS,
    POWERUP_SPAWN_MAX_MS,
    TIMED_FOOD_SPAWN_MIN_MS,
    TIMED_FOOD_SPAWN_MAX_MS,
    POISON_SPAWN_MIN_MS,
    POISON_SPAWN_MAX_MS,
    OBSTACLE_MIN_LEVEL,
    OBSTACLE_BASE_COUNT,
    OBSTACLE_MAX_COUNT,
    OBSTACLE_RETRY_LIMIT,
    COLOR_STEP,
    clamp,
)

Vec = tuple[int, int]

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)


def cell_to_rect(cell: Vec) -> pygame.Rect:
    return pygame.Rect(cell[0] * CELL_SIZE, cell[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)


@dataclass
class FoodItem:
    kind: str
    cell: Vec
    points: int
    color: tuple[int, int, int]
    spawned_at: int
    ttl_ms: Optional[int] = None

    def rect(self) -> pygame.Rect:
        return cell_to_rect(self.cell)


@dataclass
class PowerUpItem:
    kind: str
    cell: Vec
    color: tuple[int, int, int]
    spawned_at: int
    ttl_ms: int = POWERUP_TTL_MS

    def rect(self) -> pygame.Rect:
        return cell_to_rect(self.cell)


class Button:
    def __init__(self, rect: pygame.Rect, text: str):
        self.rect = rect
        self.text = text

    def draw(self, screen: pygame.Surface, font: pygame.font.Font, mouse_pos: tuple[int, int]):
        from config import BUTTON_COLOR, BUTTON_HOVER_COLOR, BUTTON_TEXT_COLOR

        color = BUTTON_HOVER_COLOR if self.rect.collidepoint(mouse_pos) else BUTTON_COLOR
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (20, 20, 20), self.rect, 2, border_radius=10)
        label = font.render(self.text, True, BUTTON_TEXT_COLOR)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


class SnakeGame:
    def __init__(self, settings: dict, username: str, personal_best: int = 0):
        self.settings = {**DEFAULT_SETTINGS, **(settings or {})}
        self.username = username.strip() or "Player"
        self.personal_best = int(personal_best)

        self.reset()

    def reset(self):
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.snake: list[Vec] = [(GRID_WIDTH // 2, GRID_HEIGHT // 2), (GRID_WIDTH // 2 - 1, GRID_HEIGHT // 2), (GRID_WIDTH // 2 - 2, GRID_HEIGHT // 2)]
        self.grow_pending = 0

        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.game_over = False
        self.game_over_reason = ""
        self.saved_to_db = False

        self.obstacles: set[Vec] = set()

        self.regular_food: Optional[FoodItem] = None
        self.timed_food: Optional[FoodItem] = None
        self.poison_food: Optional[FoodItem] = None
        self.field_powerup: Optional[PowerUpItem] = None

        self.active_powerup: Optional[str] = None
        self.powerup_started_at = 0
        self.powerup_ends_at = 0
        self.shield_available = False

        self.base_move_delay_ms = INITIAL_MOVE_DELAY_MS
        self.last_move_at = 0
        self.next_timed_food_spawn_at = 0
        self.next_poison_spawn_at = 0
        self.next_powerup_spawn_at = 0

    def start(self, now_ms: int):
        self.last_move_at = now_ms
        self.next_timed_food_spawn_at = now_ms + random.randint(TIMED_FOOD_SPAWN_MIN_MS, TIMED_FOOD_SPAWN_MAX_MS)
        self.next_poison_spawn_at = now_ms + random.randint(POISON_SPAWN_MIN_MS, POISON_SPAWN_MAX_MS)
        self.next_powerup_spawn_at = now_ms + random.randint(POWERUP_SPAWN_MIN_MS, POWERUP_SPAWN_MAX_MS)
        self.regular_food = self._spawn_food("regular", now_ms)
        self._maybe_generate_obstacles(now_ms)

    @property
    def snake_color(self) -> tuple[int, int, int]:
        rgb = self.settings.get("snake_color", DEFAULT_SETTINGS["snake_color"])
        if isinstance(rgb, list) and len(rgb) == 3:
            return (clamp(rgb[0]), clamp(rgb[1]), clamp(rgb[2]))
        return tuple(DEFAULT_SETTINGS["snake_color"])  # type: ignore[return-value]

    def set_snake_color(self, rgb: tuple[int, int, int]):
        self.settings["snake_color"] = [clamp(rgb[0]), clamp(rgb[1]), clamp(rgb[2])]

    def occupied_cells(self) -> set[Vec]:
        cells = set(self.snake) | self.obstacles
        for item in (self.regular_food, self.timed_food, self.poison_food, self.field_powerup):
            if item is not None:
                cells.add(item.cell)
        return cells

    def free_cells(self) -> list[Vec]:
        occupied = self.occupied_cells()
        return [(x, y) for y in range(GRID_HEIGHT) for x in range(GRID_WIDTH) if (x, y) not in occupied]

    def _random_free_cell(self) -> Optional[Vec]:
        cells = self.free_cells()
        return random.choice(cells) if cells else None

    def _spawn_food(self, kind: str, now_ms: int) -> Optional[FoodItem]:
        cell = self._random_free_cell()
        if cell is None:
            return None

        if kind == "regular":
            points = random.choice(FOOD_POINTS_CHOICES)
            return FoodItem(kind="regular", cell=cell, points=points, color=FOOD_COLORS[points], spawned_at=now_ms, ttl_ms=None)

        if kind == "timed":
            points = random.choice((2, 3))
            return FoodItem(kind="timed", cell=cell, points=points, color=TIMED_FOOD_COLOR, spawned_at=now_ms, ttl_ms=TIMED_FOOD_TTL_MS)

        if kind == "poison":
            return FoodItem(kind="poison", cell=cell, points=0, color=POISON_COLOR, spawned_at=now_ms, ttl_ms=POISON_TTL_MS)

        return None

    def _spawn_powerup(self, now_ms: int) -> Optional[PowerUpItem]:
        cell = self._random_free_cell()
        if cell is None:
            return None

        kind = random.choice(["speed", "slow", "shield"])
        color = {
            "speed": SPEED_BOOST_COLOR,
            "slow": SLOW_MOTION_COLOR,
            "shield": SHIELD_COLOR,
        }[kind]
        return PowerUpItem(kind=kind, cell=cell, color=color, spawned_at=now_ms)

    def _obstacles_safe(self, candidate: set[Vec]) -> bool:
        blocked = set(candidate) | set(self.snake[1:])
        start = self.snake[0]

        q = deque([start])
        seen = {start}

        while q:
            x, y = q.popleft()
            if x in (0, GRID_WIDTH - 1) or y in (0, GRID_HEIGHT - 1):
                return True

            for dx, dy in (UP, DOWN, LEFT, RIGHT):
                nx, ny = x + dx, y + dy
                n = (nx, ny)
                if not (0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT):
                    continue
                if n in blocked or n in seen:
                    continue
                seen.add(n)
                q.append(n)

        return False

    def _respawn_overlapping_items(self, now_ms: int):
        if self.regular_food and self.regular_food.cell in self.obstacles:
            self.regular_food = self._spawn_food("regular", now_ms)
        if self.timed_food and self.timed_food.cell in self.obstacles:
            self.timed_food = None
            self.next_timed_food_spawn_at = now_ms + random.randint(TIMED_FOOD_SPAWN_MIN_MS, TIMED_FOOD_SPAWN_MAX_MS)
        if self.poison_food and self.poison_food.cell in self.obstacles:
            self.poison_food = None
            self.next_poison_spawn_at = now_ms + random.randint(POISON_SPAWN_MIN_MS, POISON_SPAWN_MAX_MS)
        if self.field_powerup and self.field_powerup.cell in self.obstacles:
            self.field_powerup = None
            self.next_powerup_spawn_at = now_ms + random.randint(POWERUP_SPAWN_MIN_MS, POWERUP_SPAWN_MAX_MS)

    def _maybe_generate_obstacles(self, now_ms: int):
        if self.level < OBSTACLE_MIN_LEVEL:
            return

        count = min(OBSTACLE_BASE_COUNT + (self.level - OBSTACLE_MIN_LEVEL), OBSTACLE_MAX_COUNT)

        for _ in range(OBSTACLE_RETRY_LIMIT):
            candidate = set()
            available = [
                (x, y)
                for y in range(1, GRID_HEIGHT - 1)
                for x in range(1, GRID_WIDTH - 1)
                if (x, y) not in set(self.snake)
            ]
            if len(available) < count:
                return

            while len(candidate) < count:
                candidate.add(random.choice(available))

            if self._obstacles_safe(candidate):
                self.obstacles = candidate
                self._respawn_overlapping_items(now_ms)
                return

    def set_direction(self, direction: Vec):
        if direction == (-self.direction[0], -self.direction[1]):
            return
        self.next_direction = direction

    def _current_move_delay(self) -> int:
        delay = max(MIN_MOVE_DELAY_MS, self.base_move_delay_ms - (self.level - 1) * MOVE_DELAY_DECREASE_PER_LEVEL)
        if self.active_powerup == "speed":
            delay = max(40, int(delay / 1.5))
        elif self.active_powerup == "slow":
            delay = min(250, int(delay * 1.4))
        return delay

    def _remaining_powerup_seconds(self, now_ms: int) -> int:
        if self.active_powerup in ("speed", "slow"):
            return max(0, (self.powerup_ends_at - now_ms + 999) // 1000)
        return 0

    def _maybe_spawn_timed_food(self, now_ms: int):
        if self.timed_food is None and now_ms >= self.next_timed_food_spawn_at:
            self.timed_food = self._spawn_food("timed", now_ms)

    def _maybe_spawn_poison_food(self, now_ms: int):
        if self.poison_food is None and now_ms >= self.next_poison_spawn_at:
            self.poison_food = self._spawn_food("poison", now_ms)

    def _maybe_spawn_powerup(self, now_ms: int):
        if self.field_powerup is None and self.active_powerup is None and now_ms >= self.next_powerup_spawn_at:
            self.field_powerup = self._spawn_powerup(now_ms)

    def _expire_foods(self, now_ms: int):
        if self.timed_food and self.timed_food.ttl_ms is not None and now_ms - self.timed_food.spawned_at >= self.timed_food.ttl_ms:
            self.timed_food = None
            self.next_timed_food_spawn_at = now_ms + random.randint(TIMED_FOOD_SPAWN_MIN_MS, TIMED_FOOD_SPAWN_MAX_MS)

        if self.poison_food and self.poison_food.ttl_ms is not None and now_ms - self.poison_food.spawned_at >= self.poison_food.ttl_ms:
            self.poison_food = None
            self.next_poison_spawn_at = now_ms + random.randint(POISON_SPAWN_MIN_MS, POISON_SPAWN_MAX_MS)

        if self.field_powerup and now_ms - self.field_powerup.spawned_at >= self.field_powerup.ttl_ms:
            self.field_powerup = None
            self.next_powerup_spawn_at = now_ms + random.randint(POWERUP_SPAWN_MIN_MS, POWERUP_SPAWN_MAX_MS)

    def _expire_active_powerup(self, now_ms: int):
        if self.active_powerup in ("speed", "slow") and now_ms >= self.powerup_ends_at:
            self.active_powerup = None
            self.powerup_ends_at = 0
            self.powerup_started_at = 0

    def _level_up_if_needed(self, now_ms: int):
        new_level = 1 + self.food_eaten // FOOD_LEVEL_STEP
        if new_level > self.level:
            self.level = new_level
            self.base_move_delay_ms = max(MIN_MOVE_DELAY_MS, self.base_move_delay_ms - MOVE_DELAY_DECREASE_PER_LEVEL)
            self._maybe_generate_obstacles(now_ms)

    def _eat_regular_food(self, now_ms: int):
        if self.regular_food and self.snake[0] == self.regular_food.cell:
            self.score += self.regular_food.points
            self.grow_pending += 1
            self.food_eaten += 1
            self.regular_food = self._spawn_food("regular", now_ms)
            self._level_up_if_needed(now_ms)

    def _eat_timed_food(self, now_ms: int):
        if self.timed_food and self.snake[0] == self.timed_food.cell:
            self.score += self.timed_food.points
            self.grow_pending += 1
            self.food_eaten += 1
            self.timed_food = None
            self.next_timed_food_spawn_at = now_ms + random.randint(TIMED_FOOD_SPAWN_MIN_MS, TIMED_FOOD_SPAWN_MAX_MS)
            self._level_up_if_needed(now_ms)

    def _eat_poison_food(self, now_ms: int):
        if self.poison_food and self.snake[0] == self.poison_food.cell:
            self.poison_food = None
            self.next_poison_spawn_at = now_ms + random.randint(POISON_SPAWN_MIN_MS, POISON_SPAWN_MAX_MS)
            for _ in range(2):
                if len(self.snake) > 1:
                    self.snake.pop()
            if len(self.snake) <= 1:
                self.game_over = True
                self.game_over_reason = "Poison food"

    def _collect_powerup(self, now_ms: int):
        if self.field_powerup and self.snake[0] == self.field_powerup.cell:
            if self.field_powerup.kind == "speed":
                self.active_powerup = "speed"
                self.powerup_started_at = now_ms
                self.powerup_ends_at = now_ms + SPEED_BOOST_MS
            elif self.field_powerup.kind == "slow":
                self.active_powerup = "slow"
                self.powerup_started_at = now_ms
                self.powerup_ends_at = now_ms + SLOW_MOTION_MS
            elif self.field_powerup.kind == "shield":
                self.active_powerup = "shield"
                self.powerup_started_at = now_ms
                self.powerup_ends_at = 0
                self.shield_available = True

            self.field_powerup = None
            self.next_powerup_spawn_at = now_ms + random.randint(POWERUP_SPAWN_MIN_MS, POWERUP_SPAWN_MAX_MS)

    def _collision_hits(self, cell: Vec) -> bool:
        if cell in self.obstacles:
            return True
        x, y = cell
        if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
            return True
        body = self.snake[:-1] if self.grow_pending == 0 else self.snake
        if cell in body[1:]:
            return True
        return False

    def _consume_shield(self):
        self.active_powerup = None
        self.powerup_ends_at = 0
        self.powerup_started_at = 0
        self.shield_available = False

    def _move_snake(self, now_ms: int):
        self.direction = self.next_direction

        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        if self._collision_hits(new_head):
            if self.active_powerup == "shield" and self.shield_available:
                self._consume_shield()
                return
            self.game_over = True
            self.game_over_reason = "Collision"
            return

        self.snake.insert(0, new_head)

        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.snake.pop()

        self._eat_regular_food(now_ms)
        if self.game_over:
            return
        self._eat_timed_food(now_ms)
        if self.game_over:
            return
        self._eat_poison_food(now_ms)
        if self.game_over:
            return
        self._collect_powerup(now_ms)

        if self.snake[0] in self.snake[1:]:
            if self.active_powerup == "shield" and self.shield_available:
                self._consume_shield()
                return
            self.game_over = True
            self.game_over_reason = "Self collision"

    def update(self, now_ms: int):
        if self.game_over:
            return

        self._expire_foods(now_ms)
        self._expire_active_powerup(now_ms)
        self._maybe_spawn_timed_food(now_ms)
        self._maybe_spawn_poison_food(now_ms)
        self._maybe_spawn_powerup(now_ms)

        if now_ms - self.last_move_at >= self._current_move_delay():
            self.last_move_at = now_ms
            self._move_snake(now_ms)

            if len(self.snake) <= 1 and not self.game_over:
                self.game_over = True
                self.game_over_reason = "Snake too short"

    def final_score(self) -> int:
        return int(self.score)

    def level_reached(self) -> int:
        return int(self.level)

    def draw_grid(self, screen: pygame.Surface):
        if not self.settings.get("grid_overlay", True):
            return
        for x in range(0, WINDOW_WIDTH, CELL_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, CELL_SIZE):
            pygame.draw.line(screen, GRID_COLOR, (0, y), (WINDOW_WIDTH, y))

    def _draw_food(self, screen: pygame.Surface, item: FoodItem, outline=(255, 255, 255), poison=False):
        rect = item.rect()
        center = rect.center
        radius = CELL_SIZE // 2 - 2
        pygame.draw.circle(screen, item.color, center, radius)
        pygame.draw.circle(screen, outline, center, radius, 2)
        if not poison:
            font = pygame.font.SysFont(None, 18)
            text = font.render(str(item.points), True, (20, 20, 20))
            screen.blit(text, text.get_rect(center=center))

    def _draw_powerup(self, screen: pygame.Surface, item: PowerUpItem):
        rect = item.rect()
        pygame.draw.rect(screen, item.color, rect, border_radius=5)
        pygame.draw.rect(screen, (15, 15, 15), rect, 2, border_radius=5)
        font = pygame.font.SysFont(None, 16)
        label = {"speed": "S", "slow": "L", "shield": "H"}[item.kind]
        text = font.render(label, True, (20, 20, 20))
        screen.blit(text, text.get_rect(center=rect.center))

    def draw(self, screen: pygame.Surface):
        self.draw_grid(screen)

        for cell in self.obstacles:
            r = cell_to_rect(cell)
            pygame.draw.rect(screen, (90, 90, 100), r, border_radius=4)
            pygame.draw.rect(screen, (45, 45, 52), r, 2, border_radius=4)

        if self.regular_food:
            self._draw_food(screen, self.regular_food)
        if self.timed_food:
            self._draw_food(screen, self.timed_food, outline=(255, 220, 120))
        if self.poison_food:
            self._draw_food(screen, self.poison_food, outline=(160, 0, 0), poison=True)

        if self.field_powerup:
            self._draw_powerup(screen, self.field_powerup)

        for i, cell in enumerate(self.snake):
            rect = cell_to_rect(cell)
            if i == 0:
                color = tuple(min(255, int(c * 1.15)) for c in self.snake_color)
            else:
                color = self.snake_color
            pygame.draw.rect(screen, color, rect, border_radius=5)
            pygame.draw.rect(screen, (15, 15, 15), rect, 1, border_radius=5)

    def hud_lines(self, now_ms: int) -> list[str]:
        lines = [
            f"Score: {self.score}",
            f"Level: {self.level}",
            f"Best: {self.personal_best}",
        ]
        if self.active_powerup == "speed":
            lines.append(f"Power-up: Speed Boost ({self._remaining_powerup_seconds(now_ms)}s)")
        elif self.active_powerup == "slow":
            lines.append(f"Power-up: Slow Motion ({self._remaining_powerup_seconds(now_ms)}s)")
        elif self.active_powerup == "shield":
            lines.append("Power-up: Shield (next collision blocked)")
        return lines

    def game_over_stats(self) -> dict[str, int | str]:
        return {
            "score": int(self.score),
            "level": int(self.level),
            "personal_best": int(self.personal_best),
            "username": self.username,
            "reason": self.game_over_reason,
        }

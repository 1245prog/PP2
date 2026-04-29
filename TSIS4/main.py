import json
import random
import pygame
from db import init_db, save_result, top10, personal_best

pygame.init()
W, H, CELL = 800, 600, 20
screen = pygame.display.set_mode((W, H))
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 28)
small = pygame.font.SysFont("arial", 20)

with open("settings.json", "r", encoding="utf-8") as f:
    settings = json.load(f)

state = "menu"
menu_idx = 0
username = ""

snake = [(10, 10), (9, 10), (8, 10)]
dir_xy = (1, 0)
food = None
food_expire = 0
food_value = 1
poison = None
power = None
power_spawn = 0
active_power = None
active_until = 0
shield = False
score = 0
level = 1
best = 0
obstacles = set()


def spawn_free():
    while True:
        p = (random.randint(1, W // CELL - 2), random.randint(1, H // CELL - 2))
        if p not in snake and p not in obstacles:
            return p


def build_obstacles(level_now):
    obs = set()
    if level_now < 3:
        return obs
    target = min(30, level_now * 6)
    head = snake[0]
    while len(obs) < target:
        p = (random.randint(2, W // CELL - 3), random.randint(2, H // CELL - 3))
        if abs(p[0] - head[0]) + abs(p[1] - head[1]) < 5:
            continue
        if p not in snake:
            obs.add(p)
    return obs


def reset_game():
    global snake, dir_xy, food, food_expire, food_value, poison, power, power_spawn
    global active_power, active_until, shield, score, level, obstacles
    snake = [(10, 10), (9, 10), (8, 10)]
    dir_xy = (1, 0)
    food = spawn_free()
    food_expire = pygame.time.get_ticks() + 5000
    food_value = random.choice([1, 2, 3])
    poison = spawn_free()
    power = None
    power_spawn = 0
    active_power = None
    active_until = 0
    shield = False
    score = 0
    level = 1
    obstacles = set()


init_db()
running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if state == "menu":
                if e.key == pygame.K_UP:
                    menu_idx = (menu_idx - 1) % 4
                elif e.key == pygame.K_DOWN:
                    menu_idx = (menu_idx + 1) % 4
                elif e.key == pygame.K_RETURN:
                    if menu_idx == 0 and username.strip():
                        best = personal_best(username)
                        reset_game()
                        state = "play"
                    elif menu_idx == 1:
                        state = "leader"
                    elif menu_idx == 2:
                        state = "settings"
                    else:
                        running = False
                elif e.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                elif e.unicode.isprintable() and len(username) < 16:
                    username += e.unicode
            elif state == "play":
                if e.key == pygame.K_UP and dir_xy != (0, 1):
                    dir_xy = (0, -1)
                elif e.key == pygame.K_DOWN and dir_xy != (0, -1):
                    dir_xy = (0, 1)
                elif e.key == pygame.K_LEFT and dir_xy != (1, 0):
                    dir_xy = (-1, 0)
                elif e.key == pygame.K_RIGHT and dir_xy != (-1, 0):
                    dir_xy = (1, 0)
            elif state in {"leader", "game_over"} and e.key == pygame.K_ESCAPE:
                state = "menu"
            elif state == "settings":
                if e.key == pygame.K_g:
                    settings["grid"] = not settings["grid"]
                elif e.key == pygame.K_s:
                    settings["sound"] = not settings["sound"]
                elif e.key == pygame.K_c:
                    settings["snake_color"] = [random.randint(0, 255) for _ in range(3)]
                elif e.key == pygame.K_ESCAPE:
                    with open("settings.json", "w", encoding="utf-8") as f:
                        json.dump(settings, f, indent=2)
                    state = "menu"

    screen.fill((15, 15, 20))

    if state == "menu":
        opts = ["Play", "Leaderboard", "Settings", "Quit"]
        screen.blit(font.render("Snake", True, (255, 255, 255)), (360, 80))
        screen.blit(small.render("Username: " + username, True, (240, 220, 0)), (280, 140))
        for i, o in enumerate(opts):
            c = (255, 220, 0) if i == menu_idx else (220, 220, 220)
            screen.blit(font.render(o, True, c), (320, 220 + i * 70))
    elif state == "leader":
        screen.blit(font.render("Top 10", True, (255, 255, 255)), (340, 50))
        rows = top10()
        for i, r in enumerate(rows):
            line = f"{i+1}. {r[0]} | {r[1]} | L{r[2]} | {r[3].strftime('%Y-%m-%d')}"
            screen.blit(small.render(line, True, (220, 220, 220)), (130, 110 + i * 40))
        screen.blit(small.render("Esc: Back", True, (255, 220, 0)), (340, 540))
    elif state == "settings":
        lines = [
            f"Grid (G): {'On' if settings['grid'] else 'Off'}",
            f"Sound (S): {'On' if settings['sound'] else 'Off'}",
            f"Color (C): {settings['snake_color']}",
            "Esc: Save & Back"
        ]
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, (230, 230, 230)), (160, 180 + i * 70))
    elif state == "play":
        now = pygame.time.get_ticks()
        if now > food_expire:
            food = spawn_free()
            food_expire = now + 5000
            food_value = random.choice([1, 2, 3])
        if not poison or random.random() < 0.005:
            poison = spawn_free()
        if not power and now - power_spawn > 5000:
            power = (random.choice(["speed", "slow", "shield"]), spawn_free(), now + 8000)
            power_spawn = now
        if power and now > power[2]:
            power = None
        if active_power in {"speed", "slow"} and now > active_until:
            active_power = None

        nx = snake[0][0] + dir_xy[0]
        ny = snake[0][1] + dir_xy[1]
        next_head = (nx, ny)

        dead_collision = nx < 0 or ny < 0 or nx >= W // CELL or ny >= H // CELL or next_head in snake or next_head in obstacles
        if dead_collision:
            if shield:
                shield = False
            else:
                save_result(username, score, level)
                best = max(best, score)
                state = "game_over"
        if state == "play":
            snake.insert(0, next_head)
            grew = False
            if next_head == food:
                score += food_value * 10
                grew = True
                food = spawn_free()
                food_expire = now + 5000
                food_value = random.choice([1, 2, 3])
                if score // 50 + 1 > level:
                    level = score // 50 + 1
                    obstacles = build_obstacles(level)
            if poison and next_head == poison:
                if len(snake) <= 3:
                    save_result(username, score, level)
                    best = max(best, score)
                    state = "game_over"
                else:
                    snake = snake[:-2]
                    poison = spawn_free()
            if power and next_head == power[1]:
                if power[0] == "speed":
                    active_power = "speed"
                    active_until = now + 5000
                    shield = False
                elif power[0] == "slow":
                    active_power = "slow"
                    active_until = now + 5000
                    shield = False
                else:
                    shield = True
                    active_power = "shield"
                power = None
            if not grew:
                snake.pop()

        if settings["grid"]:
            for x in range(0, W, CELL):
                pygame.draw.line(screen, (30, 30, 35), (x, 0), (x, H))
            for y in range(0, H, CELL):
                pygame.draw.line(screen, (30, 30, 35), (0, y), (W, y))

        for b in obstacles:
            pygame.draw.rect(screen, (100, 100, 100), (b[0] * CELL, b[1] * CELL, CELL, CELL))
        for i, s in enumerate(snake):
            col = tuple(settings["snake_color"]) if i == 0 else (50, 180, 50)
            pygame.draw.rect(screen, col, (s[0] * CELL, s[1] * CELL, CELL, CELL))
        pygame.draw.rect(screen, (255, 180, 0), (food[0] * CELL, food[1] * CELL, CELL, CELL))
        if poison:
            pygame.draw.rect(screen, (120, 0, 0), (poison[0] * CELL, poison[1] * CELL, CELL, CELL))
        if power:
            pc = (0, 255, 255) if power[0] == "speed" else (255, 255, 0) if power[0] == "slow" else (0, 200, 255)
            pygame.draw.rect(screen, pc, (power[1][0] * CELL, power[1][1] * CELL, CELL, CELL))

        txt = f"Score:{score} Level:{level} Best:{best} Power:{active_power or 'none'}"
        screen.blit(small.render(txt, True, (255, 255, 255)), (10, 10))
    elif state == "game_over":
        screen.blit(font.render("Game Over", True, (255, 100, 100)), (300, 200))
        screen.blit(font.render(f"Score: {score}", True, (230, 230, 230)), (300, 270))
        screen.blit(font.render(f"Level: {level}", True, (230, 230, 230)), (300, 320))
        screen.blit(font.render(f"Best: {best}", True, (230, 230, 230)), (300, 370))
        screen.blit(small.render("Esc: Main Menu", True, (255, 220, 0)), (330, 450))

    pygame.display.flip()
    fps = 12
    if state == "play":
        if active_power == "speed":
            fps = 18
        elif active_power == "slow":
            fps = 8
        else:
            fps = min(22, 10 + level)
    clock.tick(fps)

pygame.quit()

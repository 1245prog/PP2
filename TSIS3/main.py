import random
import time
import pygame
from racer import Entity, spawn_safe, collides, LANES_X
from persistence import load_settings, save_settings, load_leaderboard, save_score
from ui import menu, draw_hud

pygame.init()
screen = pygame.display.set_mode((600, 700))
clock = pygame.time.Clock()
font = pygame.font.SysFont("arial", 30)
small = pygame.font.SysFont("arial", 22)

settings = load_settings()
state = "username"
username = ""
menu_items = ["Play", "Leaderboard", "Settings", "Quit"]
menu_idx = 0
leader_idx = 0

player_lane = 1
player = Entity(player_lane, 560, "player")
traffic = []
obstacles = []
powerups = []
coins = 0
distance = 0
score = 0
shield = False
nitro_until = 0
repair = 0
run_over = False
spawn_tick = 0


def reset_game():
    global player_lane, player, traffic, obstacles, powerups, coins, distance, score
    global shield, nitro_until, repair, run_over, spawn_tick
    player_lane = 1
    player = Entity(player_lane, 560, "player")
    traffic = []
    obstacles = []
    powerups = []
    coins = 0
    distance = 0
    score = 0
    shield = False
    nitro_until = 0
    repair = 0
    run_over = False
    spawn_tick = 0


running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if state == "username":
                if e.key == pygame.K_RETURN and username.strip():
                    state = "menu"
                elif e.key == pygame.K_BACKSPACE:
                    username = username[:-1]
                else:
                    username += e.unicode
            elif state == "menu":
                if e.key == pygame.K_UP:
                    menu_idx = (menu_idx - 1) % len(menu_items)
                elif e.key == pygame.K_DOWN:
                    menu_idx = (menu_idx + 1) % len(menu_items)
                elif e.key == pygame.K_RETURN:
                    choice = menu_items[menu_idx]
                    if choice == "Play":
                        reset_game()
                        state = "play"
                    elif choice == "Leaderboard":
                        state = "leaderboard"
                    elif choice == "Settings":
                        state = "settings"
                    else:
                        running = False
            elif state == "settings":
                if e.key == pygame.K_s:
                    settings["sound"] = not settings["sound"]
                elif e.key == pygame.K_c:
                    settings["car_color"] = random.choice(["red", "blue", "green", "yellow"])
                elif e.key == pygame.K_d:
                    settings["difficulty"] = random.choice(["easy", "normal", "hard"])
                elif e.key == pygame.K_ESCAPE:
                    save_settings(settings)
                    state = "menu"
            elif state == "play":
                if e.key == pygame.K_LEFT:
                    player_lane = max(0, player_lane - 1)
                    player.x = LANES_X[player_lane]
                elif e.key == pygame.K_RIGHT:
                    player_lane = min(2, player_lane + 1)
                    player.x = LANES_X[player_lane]
            elif state in {"game_over", "leaderboard"} and e.key == pygame.K_ESCAPE:
                state = "menu"

    screen.fill((40, 40, 40))

    if state == "username":
        txt = small.render("Enter username and press Enter:", True, (255, 255, 255))
        screen.blit(txt, (130, 280))
        screen.blit(font.render(username, True, (255, 220, 0)), (130, 330))
    elif state == "menu":
        menu(screen, "Racer", menu_items, font, menu_idx)
    elif state == "settings":
        lines = [
            f"Sound (S): {'On' if settings['sound'] else 'Off'}",
            f"Car color (C): {settings['car_color']}",
            f"Difficulty (D): {settings['difficulty']}",
            "Esc: Save & Back"
        ]
        for i, line in enumerate(lines):
            screen.blit(small.render(line, True, (255, 255, 255)), (120, 220 + i * 50))
    elif state == "leaderboard":
        board = load_leaderboard()
        screen.blit(font.render("Top 10", True, (255, 255, 255)), (240, 60))
        for i, item in enumerate(board):
            line = f"{i+1}. {item['name']} | {item['score']} | {item['distance']}"
            screen.blit(small.render(line, True, (220, 220, 220)), (120, 130 + i * 45))
        screen.blit(small.render("Esc: Back", True, (255, 220, 0)), (240, 620))
    elif state == "play":
        speed = 7
        if settings["difficulty"] == "easy":
            speed = 6
        elif settings["difficulty"] == "hard":
            speed = 9
        if time.time() < nitro_until:
            speed += 4
        pygame.draw.rect(screen, (80, 80, 80), (120, 0, 360, 700))
        now = pygame.time.get_ticks()
        if now - spawn_tick > max(300, 1100 - distance // 8):
            spawn_tick = now
            roll = random.random()
            if roll < 0.45:
                traffic.append(spawn_safe(player_lane, "traffic"))
            elif roll < 0.75:
                obstacles.append(spawn_safe(player_lane, random.choice(["oil", "barrier", "pothole"])))
            else:
                kind = random.choice(["nitro", "shield", "repair"])
                powerups.append(spawn_safe(player_lane, kind))
        for lst in [traffic, obstacles, powerups]:
            for obj in lst:
                obj.y += speed
        traffic = [t for t in traffic if t.y < 760]
        obstacles = [o for o in obstacles if o.y < 760]
        powerups = [p for p in powerups if p.y < 760]

        car_color = {"red": (255, 0, 0), "blue": (0, 100, 255), "green": (0, 200, 0), "yellow": (240, 240, 0)}[settings["car_color"]]
        pygame.draw.rect(screen, car_color, player.rect)

        for t in traffic:
            pygame.draw.rect(screen, (200, 200, 200), t.rect)
            if collides(player, t):
                if shield:
                    shield = False
                    traffic.remove(t)
                    break
                run_over = True
        for o in list(obstacles):
            color = (0, 0, 0) if o.kind == "oil" else (180, 120, 20)
            pygame.draw.rect(screen, color, o.rect)
            if collides(player, o):
                if o.kind == "oil":
                    player_lane = random.randint(0, 2)
                    player.x = LANES_X[player_lane]
                    obstacles.remove(o)
                elif repair > 0:
                    repair -= 1
                    obstacles.remove(o)
                elif shield:
                    shield = False
                    obstacles.remove(o)
                else:
                    run_over = True
        for p in list(powerups):
            color = (0, 255, 255) if p.kind == "nitro" else (255, 255, 0) if p.kind == "shield" else (0, 255, 0)
            pygame.draw.rect(screen, color, p.rect)
            if collides(player, p):
                if p.kind == "nitro":
                    nitro_until = time.time() + 4
                    shield = False
                    repair = 0
                elif p.kind == "shield":
                    shield = True
                    nitro_until = 0
                    repair = 0
                else:
                    repair = 1
                    nitro_until = 0
                    shield = False
                powerups.remove(p)

        distance += speed
        coins += 1 if random.random() < 0.03 else 0
        score = coins * 10 + distance // 4 + (40 if shield else 0) + (30 if repair else 0)
        power_text = "Nitro" if time.time() < nitro_until else "Shield" if shield else "Repair" if repair else "None"
        draw_hud(screen, small, score, distance, coins, power_text)
        if run_over:
            save_score({"name": username, "score": int(score), "distance": int(distance)})
            state = "game_over"
    elif state == "game_over":
        screen.blit(font.render("Game Over", True, (255, 80, 80)), (200, 220))
        screen.blit(small.render(f"Score: {int(score)}", True, (255, 255, 255)), (230, 300))
        screen.blit(small.render(f"Distance: {int(distance)}", True, (255, 255, 255)), (230, 340))
        screen.blit(small.render("Esc: Main Menu", True, (255, 220, 0)), (210, 420))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

import pygame
from racer import RacerGame, CAR_COLORS
from ui import Button, ToggleButton, OptionButton, BIG_FONT, FONT, SMALL_FONT
from persistence import load_settings, save_settings, save_score, load_leaderboard

WIDTH, HEIGHT = 500, 700

pygame.init()
try:
    pygame.mixer.init()
    MIXER_OK = True
except pygame.error:
    MIXER_OK = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TSIS 3 Racer")
clock = pygame.time.Clock()

# Absolute-path image loading in the required format
car_base = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\mycar.png")
enemy_img = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\elsecar.png")
cone_img = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\cone.png")

nitro_icon = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\nitro.png")
shield_icon = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\shield.png")
repair_icon = pygame.image.load(r"C:\Study\PP2\TSIS\TSIS3\assets\repair.png")

car_base = pygame.transform.scale(car_base, (60, 100))
enemy_img = pygame.transform.scale(enemy_img, (60, 100))
cone_img = pygame.transform.scale(cone_img, (50, 50))
nitro_icon = pygame.transform.scale(nitro_icon, (30, 30))
shield_icon = pygame.transform.scale(shield_icon, (30, 30))
repair_icon = pygame.transform.scale(repair_icon, (30, 30))

settings = load_settings()


def tint_car_image(base_img, color_name):
    img = base_img.copy().convert_alpha()
    color = CAR_COLORS.get(color_name, CAR_COLORS["blue"])
    overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    overlay.fill((*color, 95))
    img.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return img


def safe_start_music():
    if not MIXER_OK:
        return
    if settings.get("sound", True):
        try:
            pygame.mixer.music.load(r"C:\Study\PP2\TSIS\TSIS3\assets\track1.wav")
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass


def stop_music():
    if MIXER_OK:
        pygame.mixer.music.stop()


# state
state = "name"
player_name = ""

# assets dependent on settings
car_img = tint_car_image(car_base, settings.get("car_color", "blue"))
icons = {"nitro": nitro_icon, "shield": shield_icon, "repair": repair_icon}

game = RacerGame(car_img, enemy_img, cone_img, icons, settings)

# buttons
menu_play = Button(150, 180, 200, 55, "Play")
menu_leader = Button(150, 250, 200, 55, "Leaderboard")
menu_settings = Button(150, 320, 200, 55, "Settings")
menu_quit = Button(150, 390, 200, 55, "Quit")

settings_sound = ToggleButton(120, 170, 260, 50, "Sound", settings.get("sound", True))
car_buttons = [
    OptionButton(120, 250, 110, 45, "Blue"),
    OptionButton(250, 250, 110, 45, "Red"),
    OptionButton(120, 305, 110, 45, "Green"),
    OptionButton(250, 305, 110, 45, "Yellow"),
]
diff_buttons = [
    OptionButton(120, 385, 90, 45, "Easy"),
    OptionButton(210, 385, 110, 45, "Normal"),
    OptionButton(330, 385, 90, 45, "Hard"),
]
settings_back = Button(150, 500, 200, 55, "Back")

leader_back = Button(150, 610, 200, 45, "Back")

retry_btn = Button(120, 410, 120, 50, "Retry")
menu_btn = Button(260, 410, 120, 50, "Main Menu")


def rebuild_car_image():
    return tint_car_image(car_base, settings.get("car_color", "blue"))


def restart_game():
    global car_img, game
    car_img = rebuild_car_image()
    game = RacerGame(car_img, enemy_img, cone_img, icons, settings)


running = True
while running:
    screen.fill((24, 24, 28))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN and state == "name":
            if event.key == pygame.K_BACKSPACE:
                player_name = player_name[:-1]
            elif event.key == pygame.K_RETURN:
                if player_name.strip():
                    state = "menu"
            else:
                if len(player_name) < 12 and event.unicode.isprintable() and event.unicode != "\r":
                    player_name += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if state == "menu":
                if menu_play.clicked(event.pos):
                    restart_game()
                    state = "game"
                    safe_start_music()
                elif menu_leader.clicked(event.pos):
                    state = "leaderboard"
                elif menu_settings.clicked(event.pos):
                    state = "settings"
                elif menu_quit.clicked(event.pos):
                    running = False

            elif state == "settings":
                if settings_sound.clicked(event.pos):
                    settings_sound.value = not settings_sound.value
                    settings["sound"] = settings_sound.value
                    save_settings(settings)
                    if settings["sound"]:
                        safe_start_music()
                    else:
                        stop_music()

                for b in car_buttons:
                    if b.clicked(event.pos):
                        settings["car_color"] = b.text.lower()
                        save_settings(settings)
                        car_img = rebuild_car_image()

                for b in diff_buttons:
                    if b.clicked(event.pos):
                        settings["difficulty"] = b.text.lower()
                        save_settings(settings)

                if settings_back.clicked(event.pos):
                    state = "menu"

            elif state == "leaderboard":
                if leader_back.clicked(event.pos):
                    state = "menu"

            elif state == "game_over":
                if retry_btn.clicked(event.pos):
                    restart_game()
                    state = "game"
                    safe_start_music()
                elif menu_btn.clicked(event.pos):
                    state = "menu"

    # NAME ENTRY
    if state == "name":
        title = BIG_FONT.render("Enter your name", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 170)))

        box = pygame.Rect(90, 280, 320, 55)
        pygame.draw.rect(screen, (55, 55, 55), box, border_radius=10)
        pygame.draw.rect(screen, (220, 220, 220), box, 2, border_radius=10)
        name_txt = FONT.render(player_name + "|", True, (255, 255, 255))
        screen.blit(name_txt, (box.x + 12, box.y + 11))

        hint = SMALL_FONT.render("Press Enter to continue", True, (190, 190, 190))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 360)))

    # MAIN MENU
    elif state == "menu":
        title = BIG_FONT.render("TSIS 3 Racer", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 88)))

        player = SMALL_FONT.render(f"Player: {player_name}", True, (210, 210, 210))
        screen.blit(player, (18, 18))

        menu_play.draw(screen)
        menu_leader.draw(screen)
        menu_settings.draw(screen)
        menu_quit.draw(screen)

    # SETTINGS
    elif state == "settings":
        title = BIG_FONT.render("Settings", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 90)))

        settings_sound.value = settings.get("sound", True)
        settings_sound.draw(screen)

        label1 = SMALL_FONT.render("Car color", True, (255, 255, 255))
        screen.blit(label1, (120, 225))
        for b in car_buttons:
            b.draw(screen, active=(settings.get("car_color", "blue") == b.text.lower()))

        label2 = SMALL_FONT.render("Difficulty", True, (255, 255, 255))
        screen.blit(label2, (120, 360))
        for b in diff_buttons:
            b.draw(screen, active=(settings.get("difficulty", "normal") == b.text.lower()))

        settings_back.draw(screen)

    # LEADERBOARD
    elif state == "leaderboard":
        title = BIG_FONT.render("Leaderboard", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 60)))

        board = load_leaderboard()
        header = SMALL_FONT.render("Rank   Name           Score   Distance   Coins", True, (220, 220, 220))
        screen.blit(header, (25, 115))

        y = 150
        for idx, row in enumerate(board[:10], start=1):
            line = SMALL_FONT.render(
                f"{idx:<5} {row.get('name', '-')[:12]:<14} {row.get('score', 0):<7} {row.get('distance', 0):<10} {row.get('coins', 0)}",
                True,
                (255, 255, 255)
            )
            screen.blit(line, (25, y))
            y += 34

        leader_back.draw(screen)

    # GAME
    elif state == "game":
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            game.car.x -= 6
        if keys[pygame.K_RIGHT]:
            game.car.x += 6

        if game.car.x < 0:
            game.car.x = 0
        if game.car.x > WIDTH - game.car.width:
            game.car.x = WIDTH - game.car.width

        status = game.update()
        if status == "gameover":
            final_score = game.final_score()
            save_score(player_name or "Player", final_score, int(game.distance), game.coins_total)
            state = "game_over"
            stop_music()

        game.draw(screen)

        hud1 = SMALL_FONT.render(f"Coins: {game.coins_total}", True, (255, 255, 255))
        hud2 = SMALL_FONT.render(f"Distance: {int(game.distance)}", True, (255, 255, 255))
        hud3 = SMALL_FONT.render(f"Score: {game.final_score()}", True, (255, 255, 255))
        hud4 = SMALL_FONT.render(f"Lives: {game.lives}", True, (255, 255, 255))
        screen.blit(hud1, (10, 8))
        screen.blit(hud2, (10, 30))
        screen.blit(hud3, (10, 52))
        screen.blit(hud4, (10, 74))

        if game.active_powerup == "nitro":
            pt = SMALL_FONT.render(f"Power-up: Nitro ({max(0, game.powerup_timer // 60)}s)", True, (255, 255, 170))
            screen.blit(pt, (WIDTH - pt.get_width() - 10, 8))
        elif game.active_powerup == "shield":
            pt = SMALL_FONT.render(f"Power-up: Shield ({max(0, game.powerup_timer // 60)}s)", True, (255, 255, 170))
            screen.blit(pt, (WIDTH - pt.get_width() - 10, 8))

    # GAME OVER
    elif state == "game_over":
        title = BIG_FONT.render("Game Over", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 80)))

        final_score = game.final_score()
        stats = [
            f"Score: {final_score}",
            f"Distance: {int(game.distance)}",
            f"Coins: {game.coins_total}",
            f"Lives: {game.lives}",
        ]
        for i, text in enumerate(stats):
            line = FONT.render(text, True, (255, 255, 255))
            screen.blit(line, (130, 180 + i * 48))

        retry_btn.draw(screen)
        menu_btn.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()

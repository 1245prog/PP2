import pygame


def draw_center(screen, text, y, font, color=(255, 255, 255)):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(screen.get_width() // 2, y))
    screen.blit(surf, rect)


def menu(screen, title, options, font, selected):
    screen.fill((20, 20, 30))
    draw_center(screen, title, 120, font)
    for i, opt in enumerate(options):
        color = (255, 220, 0) if i == selected else (200, 200, 200)
        draw_center(screen, opt, 220 + i * 60, font, color)


def draw_hud(screen, font, score, distance, coins, power_text):
    line = f"Score: {score}  Distance: {distance}  Coins: {coins}  Power: {power_text}"
    screen.blit(font.render(line, True, (255, 255, 255)), (10, 10))

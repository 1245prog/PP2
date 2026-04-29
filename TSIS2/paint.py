import pygame
from datetime import datetime
from tools import draw_shape, flood_fill

pygame.init()
W, H = 1200, 800
TOOLBAR_H = 90
screen = pygame.display.set_mode((W, H))
canvas = pygame.Surface((W, H - TOOLBAR_H))
canvas.fill((255, 255, 255))
font = pygame.font.SysFont("arial", 20)
clock = pygame.time.Clock()

colors = [(0, 0, 0), (255, 0, 0), (0, 128, 0), (0, 0, 255), (255, 165, 0), (128, 0, 128)]
tools = ["pencil", "line", "rect", "circle", "square", "right_triangle", "eq_triangle", "rhombus", "eraser", "fill", "text"]
size_map = {"1": 2, "2": 5, "3": 10}

selected_color = (0, 0, 0)
selected_tool = "pencil"
brush_size = 2
drawing = False
start_pos = None
last_pos = None
snapshot = None
text_mode = False
text_pos = (0, 0)
text_buffer = ""


def draw_ui():
    pygame.draw.rect(screen, (230, 230, 230), (0, H - TOOLBAR_H, W, TOOLBAR_H))
    for i, c in enumerate(colors):
        r = pygame.Rect(10 + i * 40, H - 80, 30, 30)
        pygame.draw.rect(screen, c, r)
        if c == selected_color:
            pygame.draw.rect(screen, (0, 0, 0), r, 2)
    for i, t in enumerate(tools):
        r = pygame.Rect(280 + i * 83, H - 80, 80, 30)
        pygame.draw.rect(screen, (255, 255, 255), r)
        pygame.draw.rect(screen, (0, 0, 0), r, 2 if t == selected_tool else 1)
        screen.blit(font.render(t, True, (0, 0, 0)), (r.x + 4, r.y + 6))
    s = font.render(f"Brush:{brush_size}px  Keys 1/2/3  Ctrl+S Save", True, (0, 0, 0))
    screen.blit(s, (10, H - 40))


running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_1:
                brush_size = size_map["1"]
            elif e.key == pygame.K_2:
                brush_size = size_map["2"]
            elif e.key == pygame.K_3:
                brush_size = size_map["3"]
            elif e.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                name = datetime.now().strftime("canvas_%Y%m%d_%H%M%S.png")
                pygame.image.save(canvas, name)
            if text_mode:
                if e.key == pygame.K_RETURN:
                    text_mode = False
                elif e.key == pygame.K_ESCAPE:
                    text_mode = False
                    text_buffer = ""
                elif e.key == pygame.K_BACKSPACE:
                    text_buffer = text_buffer[:-1]
                else:
                    text_buffer += e.unicode
        elif e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = e.pos
            if my >= H - TOOLBAR_H:
                for i, c in enumerate(colors):
                    if pygame.Rect(10 + i * 40, H - 80, 30, 30).collidepoint(e.pos):
                        selected_color = c
                for i, t in enumerate(tools):
                    if pygame.Rect(280 + i * 83, H - 80, 80, 30).collidepoint(e.pos):
                        selected_tool = t
            else:
                cx, cy = mx, my
                drawing = True
                start_pos = (cx, cy)
                last_pos = (cx, cy)
                snapshot = canvas.copy()
                if selected_tool == "fill":
                    flood_fill(canvas, cx, cy, selected_color)
                    drawing = False
                elif selected_tool == "text":
                    text_mode = True
                    text_pos = (cx, cy)
                    text_buffer = ""
                    drawing = False
        elif e.type == pygame.MOUSEMOTION and drawing:
            mx, my = e.pos
            if my < H - TOOLBAR_H:
                if selected_tool == "pencil":
                    pygame.draw.line(canvas, selected_color, last_pos, (mx, my), brush_size)
                    last_pos = (mx, my)
                elif selected_tool == "eraser":
                    pygame.draw.line(canvas, (255, 255, 255), last_pos, (mx, my), brush_size * 2)
                    last_pos = (mx, my)
                else:
                    canvas.blit(snapshot, (0, 0))
                    draw_shape(canvas, selected_tool, selected_color, start_pos, (mx, my), brush_size)
        elif e.type == pygame.MOUSEBUTTONUP and drawing:
            drawing = False
    screen.fill((200, 200, 200))
    screen.blit(canvas, (0, 0))
    if text_mode and text_buffer:
        preview = canvas.copy()
        preview.blit(font.render(text_buffer, True, selected_color), text_pos)
        screen.blit(preview, (0, 0))
    elif text_mode and not text_buffer:
        pygame.draw.line(screen, selected_color, text_pos, (text_pos[0], text_pos[1] + 24), 2)
    if not text_mode and text_buffer:
        canvas.blit(font.render(text_buffer, True, selected_color), text_pos)
        text_buffer = ""
    draw_ui()
    pygame.display.flip()
    clock.tick(60)

pygame.quit()

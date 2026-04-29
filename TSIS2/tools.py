import pygame
from collections import deque


def draw_shape(surface, tool, color, start, end, width):
    x1, y1 = start
    x2, y2 = end
    rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
    if tool == "line":
        pygame.draw.line(surface, color, start, end, width)
    elif tool == "rect":
        pygame.draw.rect(surface, color, rect, width)
    elif tool == "circle":
        r = int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5)
        pygame.draw.circle(surface, color, start, r, width)
    elif tool == "square":
        side = max(rect.width, rect.height)
        sq = pygame.Rect(rect.x, rect.y, side, side)
        pygame.draw.rect(surface, color, sq, width)
    elif tool == "right_triangle":
        pts = [(x1, y2), (x1, y1), (x2, y2)]
        pygame.draw.polygon(surface, color, pts, width)
    elif tool == "eq_triangle":
        h = int(abs(x2 - x1) * 0.866)
        pts = [(x1, y1), (x2, y1), ((x1 + x2) // 2, y1 - h)]
        pygame.draw.polygon(surface, color, pts, width)
    elif tool == "rhombus":
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        pts = [(cx, y1), (x2, cy), (cx, y2), (x1, cy)]
        pygame.draw.polygon(surface, color, pts, width)


def flood_fill(surface, x, y, new_color):
    w, h = surface.get_size()
    target = surface.get_at((x, y))
    if target == new_color:
        return
    q = deque([(x, y)])
    while q:
        px, py = q.popleft()
        if px < 0 or py < 0 or px >= w or py >= h:
            continue
        if surface.get_at((px, py)) != target:
            continue
        surface.set_at((px, py), new_color)
        q.append((px + 1, py))
        q.append((px - 1, py))
        q.append((px, py + 1))
        q.append((px, py - 1))

import random
import pygame

LANES_X = [170, 300, 430]
ROAD_TOP = 0
ROAD_BOTTOM = 700


class Entity:
    def __init__(self, lane, y, kind, speed=6):
        self.lane = lane
        self.x = LANES_X[lane]
        self.y = y
        self.kind = kind
        self.speed = speed
        self.w = 60
        self.h = 100 if kind in {"traffic", "player"} else 50

    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)


def spawn_safe(lane_blocked, kind):
    free = [i for i in range(3) if i != lane_blocked]
    lane = random.choice(free)
    return Entity(lane, -120, kind)


def collides(a, b):
    return a.rect.colliderect(b.rect)

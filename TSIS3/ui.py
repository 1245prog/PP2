import pygame

pygame.font.init()
FONT = pygame.font.SysFont(None, 34)
BIG_FONT = pygame.font.SysFont(None, 54)
SMALL_FONT = pygame.font.SysFont(None, 26)


class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text

    def draw(self, screen, bg=(70, 70, 70), fg=(255, 255, 255)):
        pygame.draw.rect(screen, bg, self.rect, border_radius=10)
        pygame.draw.rect(screen, (25, 25, 25), self.rect, 2, border_radius=10)
        txt = FONT.render(self.text, True, fg)
        screen.blit(txt, txt.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class ToggleButton(Button):
    def __init__(self, x, y, w, h, text, value=False):
        super().__init__(x, y, w, h, text)
        self.value = value

    def draw(self, screen):
        bg = (70, 140, 70) if self.value else (140, 70, 70)
        label = f"{self.text}: {'ON' if self.value else 'OFF'}"
        pygame.draw.rect(screen, bg, self.rect, border_radius=10)
        pygame.draw.rect(screen, (25, 25, 25), self.rect, 2, border_radius=10)
        txt = FONT.render(label, True, (255, 255, 255))
        screen.blit(txt, txt.get_rect(center=self.rect.center))


class OptionButton(Button):
    def __init__(self, x, y, w, h, text):
        super().__init__(x, y, w, h, text)

    def draw(self, screen, active=False):
        bg = (85, 120, 180) if active else (70, 70, 70)
        super().draw(screen, bg=bg)

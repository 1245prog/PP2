import pygame
import random

WIDTH, HEIGHT = 500, 700
HIT_MARGIN = 10
LANES = [20, 95, 170, 245, 320, 395, 470]

DIFFICULTY_SETTINGS = {
    "easy":   {"traffic_interval": 54, "cone_interval": 108, "coin_interval": 40, "powerup_interval": 180},
    "normal": {"traffic_interval": 40, "cone_interval": 80,  "coin_interval": 32, "powerup_interval": 150},
    "hard":   {"traffic_interval": 30, "cone_interval": 60,  "coin_interval": 26, "powerup_interval": 120},
}

CAR_COLORS = {
    "blue": (80, 140, 255),
    "red": (235, 80, 80),
    "green": (90, 200, 120),
    "yellow": (235, 210, 90),
}


class Coin:
    def __init__(self, x, y, radius, value):
        self.x = x
        self.y = y
        self.radius = radius
        self.value = value
        self.rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)

    def sync_rect(self):
        self.rect.x = self.x - self.radius
        self.rect.y = self.y - self.radius


class PowerUpItem:
    def __init__(self, kind, rect, icon, spawn_frame):
        self.kind = kind
        self.rect = rect
        self.icon = icon
        self.spawn_frame = spawn_frame


class RacerGame:
    def __init__(self, car_img, enemy_img, cone_img, icons, settings):
        self.car_img = car_img
        self.enemy_img = enemy_img
        self.cone_img = pygame.transform.scale(cone_img, (50, 50))
        self.icons = icons
        self.settings = settings

        self.car = pygame.Rect(220, 600, 60, 100)
        self.car_hit = pygame.Rect(230, 610, 40, 80)

        self.traffic = []
        self.cones = []
        self.coins = []
        self.powerups = []

        self.lives = 1
        self.score = 0
        self.coins_total = 0
        self.distance = 0.0

        self.base_speed = 5.0
        self.enemy_speed = 5.0
        self.cone_speed = 5.0
        self.coin_speed = 5.0

        self.active_powerup = None
        self.powerup_timer = 0

        self.frame = 0
        self.level = 0

        self.apply_difficulty(settings.get("difficulty", "normal"))

    def apply_difficulty(self, difficulty):
        self.difficulty = difficulty if difficulty in DIFFICULTY_SETTINGS else "normal"
        cfg = DIFFICULTY_SETTINGS[self.difficulty]
        self.base_traffic_interval = cfg["traffic_interval"]
        self.base_cone_interval = cfg["cone_interval"]
        self.base_coin_interval = cfg["coin_interval"]
        self.base_powerup_interval = cfg["powerup_interval"]

    def sync_hitbox(self):
        self.car_hit.x = self.car.x + HIT_MARGIN
        self.car_hit.y = self.car.y + HIT_MARGIN

    def _lane_x(self, width):
        x = random.choice(LANES) + random.randint(-20, 20)
        return max(0, min(WIDTH - width, x))

    def _overlaps_any(self, rect, items):
        for item in items:
            other = item["hit"] if isinstance(item, dict) else item.rect
            if rect.colliderect(other):
                return True
        return False

    def _speed_mult(self):
        return 1.25 if self.active_powerup == "nitro" else 1.0

    def _distance_mult(self):
        return 2.0 if self.active_powerup == "nitro" else 1.0

    def _shield_active(self):
        return self.active_powerup == "shield" and self.powerup_timer > 0

    def _progressive_scaling(self):
        self.level = int(self.distance // 1200)
        traffic_interval = max(self.base_traffic_interval - self.level * 2, 18)
        cone_interval = max(traffic_interval * 2, 36)
        coin_interval = max(self.base_coin_interval - self.level, 18)
        powerup_interval = max(self.base_powerup_interval - self.level * 2, 90)
        return traffic_interval, cone_interval, coin_interval, powerup_interval

    def spawn_enemy(self):
        for _ in range(25):
            x = self._lane_x(60)
            draw = pygame.Rect(x, -120, 60, 100)
            hit = pygame.Rect(x + HIT_MARGIN, -110, 40, 80)

            if hit.colliderect(self.car_hit):
                continue
            if self._overlaps_any(hit, self.traffic):
                continue
            if self._overlaps_any(hit, self.cones):
                continue

            self.traffic.append({"draw": draw, "hit": hit})
            return

    def spawn_cone(self):
        for _ in range(25):
            x = self._lane_x(50)
            draw = pygame.Rect(x, -50, 50, 50)
            hit = pygame.Rect(x + 12, -38, 26, 26)

            if hit.colliderect(self.car_hit):
                continue
            if self._overlaps_any(hit, self.cones):
                continue
            if self._overlaps_any(hit, self.traffic):
                continue

            self.cones.append({"draw": draw, "hit": hit})
            return

    def spawn_coin(self):
        radius = random.choice([8, 11, 14])
        value = {8: 1, 11: 2, 14: 3}[radius]
        x = random.randint(radius + 8, WIDTH - radius - 8)
        coin = Coin(x, -20, radius, value)
        if coin.rect.colliderect(self.car_hit):
            return
        self.coins.append(coin)

    def spawn_powerup(self, frame):
        kind = random.choice(["nitro", "shield", "repair"])
        icon = self.icons[kind]
        x = self._lane_x(30)
        rect = pygame.Rect(x, -30, 30, 30)

        if rect.colliderect(self.car_hit):
            return
        if self._overlaps_any(rect, self.traffic):
            return
        if self._overlaps_any(rect, self.cones):
            return

        self.powerups.append(PowerUpItem(kind, rect, icon, frame))

    def pickup_powerup(self, kind):
        if kind == "repair":
            self.lives = min(2, self.lives + 1)
            return

        if self.active_powerup is not None:
            return

        if kind == "nitro":
            self.active_powerup = "nitro"
            self.powerup_timer = 240
        elif kind == "shield":
            self.active_powerup = "shield"
            self.powerup_timer = 300

    def _deactivate_timed_powerup(self):
        self.active_powerup = None
        self.powerup_timer = 0

    def _handle_collision_with_life(self, obj_list, obj):
        if self._shield_active():
            self._deactivate_timed_powerup()
            obj_list.remove(obj)
            return True

        if self.lives > 0:
            self.lives -= 1
            obj_list.remove(obj)
            return True

        return False

    def update(self):
        self.frame += 1
        self.sync_hitbox()

        traffic_interval, cone_interval, coin_interval, powerup_interval = self._progressive_scaling()

        self.distance += self.base_speed * self._distance_mult()

        if self.active_powerup in ("nitro", "shield"):
            self.powerup_timer -= 1
            if self.powerup_timer <= 0:
                self._deactivate_timed_powerup()

        if self.frame % traffic_interval == 0:
            self.spawn_enemy()
        if self.frame % cone_interval == 0:
            self.spawn_cone()
        if self.frame % coin_interval == 0:
            self.spawn_coin()
        if self.frame % powerup_interval == 0:
            self.spawn_powerup(self.frame)

        speed_mult = self._speed_mult()
        traffic_step = max(1, int(self.enemy_speed * speed_mult))
        cone_step = max(1, int(self.cone_speed * speed_mult))
        coin_step = max(1, int(self.coin_speed * speed_mult))

        for t in self.traffic[:]:
            t["draw"].y += traffic_step
            t["hit"].y += traffic_step

            if t["draw"].y > HEIGHT:
                self.traffic.remove(t)
                continue

            if t["hit"].colliderect(self.car_hit):
                if not self._handle_collision_with_life(self.traffic, t):
                    return "gameover"

        for c in self.cones[:]:
            c["draw"].y += cone_step
            c["hit"].y += cone_step

            if c["draw"].y > HEIGHT:
                self.cones.remove(c)
                continue

            if c["hit"].colliderect(self.car_hit):
                if not self._handle_collision_with_life(self.cones, c):
                    return "gameover"

        for coin in self.coins[:]:
            coin.y += coin_step
            coin.sync_rect()

            if coin.rect.top > HEIGHT:
                self.coins.remove(coin)
                continue

            if coin.rect.colliderect(self.car_hit):
                self.score += coin.value * 10
                self.coins_total += coin.value
                self.enemy_speed += 0.15
                self.cone_speed += 0.15
                self.coin_speed += 0.15
                self.coins.remove(coin)

        POWERUP_TTL = 360
        for p in self.powerups[:]:
            p.rect.y += coin_step

            if self.frame - p.spawn_frame > POWERUP_TTL:
                self.powerups.remove(p)
                continue

            if p.rect.colliderect(self.car_hit):
                self.pickup_powerup(p.kind)
                self.powerups.remove(p)

        return "running"

    def final_score(self):
        return int(self.score + self.distance // 10 + self.coins_total * 5 + self.lives * 3)

    def draw(self, screen):
        screen.blit(self.car_img, self.car)

        for t in self.traffic:
            screen.blit(self.enemy_img, t["draw"])

        for c in self.cones:
            screen.blit(self.cone_img, c["draw"])

        for coin in self.coins:
            pygame.draw.circle(screen, (255, 215, 0), (coin.x, coin.y), coin.radius)
            pygame.draw.circle(screen, (255, 240, 150), (coin.x - coin.radius // 3, coin.y - coin.radius // 3), max(2, coin.radius // 4))

        for p in self.powerups:
            screen.blit(p.icon, p.rect)

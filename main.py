import pygame
import cv2
from mediapipe.python.solutions import hands as mp_hands
import random
import math
import os
import json
import numpy as np
 
pygame.init()
 
screen = pygame.display.set_mode((1280, 720))
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Fruit Burst")
 
clock = pygame.time.Clock()
FPS = 60
 
 #webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cap.set(cv2.CAP_PROP_FPS, 60)
CAM_W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))    
CAM_H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))   
 
SCALE_X = WIDTH  / CAM_W     
SCALE_Y = HEIGHT / CAM_H     
 
 
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
 
# Finger state
finger_x = WIDTH // 2
finger_y = HEIGHT // 2
 
SMOOTH   = 0.65
_smooth_x = float(finger_x)
_smooth_y = float(finger_y)
 
# Asset loader 
def load_image(path, size=None):
    img = pygame.image.load(path).convert_alpha()
    if size:
        img = pygame.transform.scale(img, size)
    return img
 
BASE = r"C:/Users/Siddhant/OneDrive/Desktop/Game/Fruit Burst"
 
fruit_images = [
    load_image(f"{BASE}/Fruits/apple.png",       (120, 120)),
    load_image(f"{BASE}/Fruits/banana.png",      (120, 120)),
    load_image(f"{BASE}/Fruits/orange.png",      (120, 120)),
    load_image(f"{BASE}/Fruits/watermelon.png",  (120, 120)),
    load_image(f"{BASE}/Fruits/pineapple.png",   (120, 120)),
    load_image(f"{BASE}/Fruits/strawberry.png",  (120, 120)),
    load_image(f"{BASE}/Fruits/kiwi.png",        (120, 120)),
    load_image(f"{BASE}/Fruits/grapes.png",      (120, 120)),
]
 
golden_fruit = load_image(f"{BASE}/Fruits/golden_fruit.png",  (120, 120))
bomb_img     = load_image(f"{BASE}/explosion/bomb.png",       (120, 120))
heart        = load_image(f"{BASE}/UI/heart.png",             (50,  50))
heart_empty  = load_image(f"{BASE}/UI/heart_empty.png",       (50,  50))
crosshair    = load_image(f"{BASE}/UI/crosshair.png",         (70,  70))
finger_glow  = load_image(f"{BASE}/UI/glow_dot.png",         (120, 120))
game_over_img = load_image(f"{BASE}/UI/game over.png")
 
def _load_explosion_set(folder, prefix, ext="png"):
    return [
        load_image(f"{BASE}/explosion/{folder}/{prefix}_frame{i}.{ext}", (200, 200))
        for i in range(1, 6)
    ]
 
explosion_frames = {
    "red":    _load_explosion_set("red",    "Apple"),
    "orange": _load_explosion_set("Orange", "Orange"),
    "green":  _load_explosion_set("green",  "green"),
    "yellow": _load_explosion_set("yellow", "yellow"),
}

score = 0
lives = 3
HITBOX_RADIUS = 25
fruit_spawn_delay = 1200
last_spawn_time   = 0
difficulty_timer  = 0
 
game_state = "menu"
 
HS_FILE = "highscore.json"
high_score = json.load(open(HS_FILE)) if os.path.exists(HS_FILE) else 0
 
def save_highscore():
    with open(HS_FILE, "w") as f:
        json.dump(high_score, f)
 

class Fruit:
    def __init__(self):
        self.image          = random.choice(fruit_images)
        self.x              = random.randint(100, WIDTH - 100)
        self.y              = HEIGHT + 100
        self.vel_y          = random.randint(-24, -18)
        self.vel_x          = random.randint(-4, 4)
        self.angle          = 0
        self.rotation_speed = random.randint(-8, 8)
        self.radius         = 50
        self.explosion_type = random.choice(["red", "orange", "green", "yellow"])
 
    def update(self):
        self.x      += self.vel_x
        self.y      += self.vel_y
        self.vel_y  += 0.45
        self.angle  += self.rotation_speed
 
    def draw(self, surface):
        rotated = pygame.transform.rotate(self.image, self.angle)
        rect    = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)
 
 
class Bomb:
    def __init__(self):
        self.image          = bomb_img
        self.x              = random.randint(100, WIDTH - 100)
        self.y              = HEIGHT + 100
        self.vel_y          = random.randint(-22, -17)
        self.vel_x          = random.randint(-4, 4)
        self.angle          = 0
        self.rotation_speed = random.randint(-10, 10)
        self.radius         = 50
 
    def update(self):
        self.x      += self.vel_x
        self.y      += self.vel_y
        self.vel_y  += 0.45
        self.angle  += self.rotation_speed
 
    def draw(self, surface):
        rotated = pygame.transform.rotate(self.image, self.angle)
        rect    = rotated.get_rect(center=(self.x, self.y))
        surface.blit(rotated, rect)
 
 
class Explosion:
    def __init__(self, x, y, color):
        self.x        = x
        self.y        = y
        self.frames   = explosion_frames[color]
        self.index    = 0
        self.timer    = 0
        self.finished = False
 
    def update(self):
        self.timer += 1
        if self.timer % 4 == 0:
            self.index += 1
            if self.index >= len(self.frames):
                self.finished = True
 
    def draw(self, surface):
        if not self.finished:
            img  = self.frames[self.index]
            rect = img.get_rect(center=(self.x, self.y))
            surface.blit(img, rect)
 
fruits     = []
bombs      = []
explosions = []
 
 
def spawn_object():
    if random.randint(1, 10) == 1:
        bombs.append(Bomb())
    else:
        fruits.append(Fruit())
 
 
def check_collision(x1, y1, x2, y2, radius, extra = 25):
    return math.hypot(x1 - x2, y1 - y2) < (radius + extra)
 
 
def restart_game():
    global score, lives, fruit_spawn_delay, game_state
    score             = 0
    lives             = 3
    fruit_spawn_delay = 1200
    game_state        = "playing"
    fruits.clear()
    bombs.clear()
    explosions.clear()
 
_display_frame = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
 
def update_finger():
    
    global finger_x, finger_y, _smooth_x, _smooth_y
 
    success, frame = cap.read()
    if not success:
        return None
 
   
    frame = cv2.flip(frame, 1)
 
    display = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_LINEAR)
 
    rgb    = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)
 
    if result.multi_hand_landmarks:
        hand = result.multi_hand_landmarks[0]
 
        tip = hand.landmark[8]     
        pip = hand.landmark[6]      
 
        raw_x = ((tip.x * 0.8) + (pip.x * 0.2)) * WIDTH
        raw_y = ((tip.y * 0.8) + (pip.y * 0.2)) * HEIGHT
 
        _smooth_x += SMOOTH * (raw_x - _smooth_x)
        _smooth_y += SMOOTH * (raw_y - _smooth_y)
 
        finger_x = int(_smooth_x)
        finger_y = int(_smooth_y)
        HITBOX_RADIUS = 25
 
    return display   
 
def draw_webcam_background(display_bgr):
 
    rgb = cv2.cvtColor(display_bgr, cv2.COLOR_BGR2RGB)
    pygame.surfarray.blit_array(screen, rgb.transpose(1, 0, 2))
 
# Fonts
font       = pygame.font.SysFont("Arial", 40, True)
big_font   = pygame.font.SysFont("Arial", 90, True)
button_font = pygame.font.SysFont("Arial", 48, True)
title_font  = pygame.font.SysFont("Arial", 70, True)
 

def _load_emoji_font(size):
    for name in ("Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"):
        try:
            f = pygame.font.SysFont(name, size)
            if f is not None:
                return f
        except Exception:
            continue
    return pygame.font.SysFont("Arial", size, True)
 
emoji_font_lg = _load_emoji_font(60)
emoji_font_md = _load_emoji_font(36)
emoji_font_sm = _load_emoji_font(28)
 

BUTTON_RECT = pygame.Rect(0, 0, 300, 100)
BUTTON_RECT.center = (WIDTH // 2, HEIGHT // 2 + 120)
 
def draw_start_button(surface, hovered):
    base_color  = (255, 60, 60) if not hovered else (255, 100, 100)
    glow_rect   = BUTTON_RECT.inflate(16, 16)
 
    if hovered:
        glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 80, 80, 90), glow.get_rect(), border_radius=28)
        surface.blit(glow, glow_rect.topleft)
 
    pygame.draw.rect(surface, base_color, BUTTON_RECT, border_radius=22)
    pygame.draw.rect(surface, (255, 255, 255), BUTTON_RECT, 4, border_radius=22)
 
    label = button_font.render("START", True, (255, 255, 255))
    surface.blit(label, label.get_rect(center=BUTTON_RECT.center))
 

FRUIT_EMOJIS = ["🍎", "🍌", "🍉", "🍊", "🍍", "🍇", "🍓", "🥝", "✨", "🔥", "💥"]
 
class FloatingEmoji:
    def __init__(self):
        self.reset(random.randint(0, HEIGHT))
 
    def reset(self, y=None):
        self.char  = random.choice(FRUIT_EMOJIS)
        self.x     = random.randint(0, WIDTH)
        self.y     = y if y is not None else HEIGHT + random.randint(0, 200)
        self.speed = random.uniform(0.6, 2.0)
        self.sway  = random.uniform(0.5, 2.0)
        self.phase = random.uniform(0, math.tau)
        size       = random.choice([28, 36, 48])
        self.font  = emoji_font_sm if size == 28 else (emoji_font_md if size == 36 else emoji_font_lg)
        self.alpha = random.randint(120, 220)
 
    def update(self):
        self.phase += 0.03
        self.y     -= self.speed
        if self.y < -60:
            self.reset()
 
    def draw(self, surface):
        x = self.x + math.sin(self.phase) * 20 * self.sway
        surf = self.font.render(self.char, True, (255, 255, 255))
        surf.set_alpha(self.alpha)
        surface.blit(surf, (x, self.y))
 
menu_emojis = [FloatingEmoji() for _ in range(18)]
 
def draw_menu(surface, hovered):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(140)
    overlay.fill((10, 10, 20))
    surface.blit(overlay, (0, 0))
 
    for e in menu_emojis:
        e.update()
        e.draw(surface)
 
    title = title_font.render("FRUIT BURST", True, (255, 215, 0))
    surface.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 140)))
 
    deco = emoji_font_lg.render("🍉 🍎 🍌 🍊 🍇", True, (255, 255, 255))
    surface.blit(deco, deco.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
 
    subtitle = font.render("Use your finger to pop the fruit — avoid the bombs!", True, (230, 230, 230))
    surface.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 5)))
 
    draw_start_button(surface, hovered)
 
    hint = font.render("Click START or hover your finger over it", True, (200, 200, 200))
    surface.blit(hint, hint.get_rect(center=(WIDTH // 2, BUTTON_RECT.bottom + 45)))
 

running = True
_button_hover_timer = 0
HOVER_TO_START_FRAMES = 45  # ~0.75s of hovering the finger over the button to start
 
while running:
    clock.tick(FPS)
 
    mouse_click = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_click = True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_SPACE and game_state == "menu":
                game_state = "playing"
            if game_state == "gameover" and event.key == pygame.K_r:
                restart_game()

    frame = update_finger()
    if frame is not None:
        draw_webcam_background(frame)
 
    current_time = pygame.time.get_ticks()
 

    if game_state == "menu":
        hovered = BUTTON_RECT.collidepoint(finger_x, finger_y) or BUTTON_RECT.collidepoint(pygame.mouse.get_pos())
 
        if hovered:
            _button_hover_timer += 1
        else:
            _button_hover_timer = 0
 
        if mouse_click and BUTTON_RECT.collidepoint(pygame.mouse.get_pos()):
            game_state = "playing"
            _button_hover_timer = 0
        elif _button_hover_timer >= HOVER_TO_START_FRAMES:
            game_state = "playing"
            _button_hover_timer = 0
 
        draw_menu(screen, hovered)
 
        # Show the finger pointer 
        screen.blit(finger_glow, finger_glow.get_rect(center=(finger_x, finger_y)))
        screen.blit(crosshair, crosshair.get_rect(center=(finger_x, finger_y)))
 
        pygame.display.flip()
        continue
 

    if game_state == "playing":
 
        # Spawn
        if current_time - last_spawn_time > fruit_spawn_delay:
            spawn_object()
            last_spawn_time = current_time
 
        # Difficulty ramp
        difficulty_timer += 1
        if difficulty_timer > 600:
            difficulty_timer  = 0
            fruit_spawn_delay = max(300, fruit_spawn_delay - 50)
 
        # Fruits
        for fruit in fruits[:]:
            fruit.update()
            fruit.draw(screen)
 
            if check_collision(finger_x, finger_y, fruit.x, fruit.y, fruit.radius):
                score += 1
                explosions.append(Explosion(fruit.x, fruit.y, fruit.explosion_type))
                fruits.remove(fruit)
                continue
 
            if fruit.y > HEIGHT + 150:
                lives -= 1
                fruits.remove(fruit)
 
        # Bombs
        for bomb in bombs[:]:
            bomb.update()
            bomb.draw(screen)
 
            if check_collision(finger_x, finger_y, bomb.x, bomb.y, bomb.radius):
                lives -= 1
                bombs.remove(bomb)
                continue
 
            if bomb.y > HEIGHT + 150:
                bombs.remove(bomb)
 
        # Explosions
        for exp in explosions[:]:
            exp.update()
            exp.draw(screen)
            if exp.finished:
                explosions.remove(exp)
 
        # Game over trigger
        if lives <= 0:
            game_state = "gameover"
            if score > high_score:
                high_score = score
                save_highscore()
 

 
    # Finger glow
    screen.blit(finger_glow, finger_glow.get_rect(center=(finger_x, finger_y)))
 
    # Crosshair
    screen.blit(crosshair, crosshair.get_rect(center=(finger_x, finger_y)))
 
    # Score (with a little fruit emoji accent)
    score_emoji = emoji_font_sm.render("🍓", True, (255, 255, 255))
    screen.blit(score_emoji, (20, 15))
    screen.blit(font.render(f"Score : {score}",      True, (255, 255, 255)), (55, 20))
 
    best_emoji = emoji_font_sm.render("🏆", True, (255, 255, 255))
    screen.blit(best_emoji, (20, 65))
    screen.blit(font.render(f"Best  : {high_score}", True, (255, 255,   0)), (55, 70))
 
    # Lives
    for i in range(3):
        img = heart if i < lives else heart_empty
        screen.blit(img, (WIDTH - 200 + i * 60, 20))
 
    # Game Over overlay
    if game_state == "gameover":
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        screen.blit(overlay, (0, 0))
 
        for e in menu_emojis:
            e.update()
            e.draw(screen)
 
        skull = emoji_font_lg.render("💀", True, (255, 255, 255))
        screen.blit(skull, skull.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 200)))
 
        title = big_font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 120)))
 
        screen.blit(
            font.render(f"Final Score : {score}", True, (255, 255, 255)),
            (WIDTH // 2 - 150, HEIGHT // 2)
        )
        screen.blit(
            font.render(f"Best Score  : {high_score}", True, (255, 215, 0)),
            (WIDTH // 2 - 150, HEIGHT // 2 + 55)
        )
        screen.blit(
            font.render("Press R to Restart", True, (255, 255, 0)),
            (WIDTH // 2 - 170, HEIGHT // 2 + 120)
        )
 
    pygame.display.flip()
 
 
cap.release()
cv2.destroyAllWindows()
pygame.quit()
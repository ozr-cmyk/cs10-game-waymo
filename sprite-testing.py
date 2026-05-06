import random
import arcade
import os

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_COIN = 0.3
COIN_COUNT = 50

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Traffic Dodge Game"


# --- Safe loader ---
def load_texture_safe(path, fallback):
    return path if os.path.exists(path) else fallback


# --- Entity Types ---
ENTITY_TYPES = [
    {
        "name": "car",
        "texture": load_texture_safe("car.png", ":resources:images/items/coinGold.png"),
        "speed": 6
    },
    {
        "name": "cyclist",
        "texture": load_texture_safe("cyclist.png", ":resources:images/items/gemBlue.png"),
        "speed": 4
    },
    {
        "name": "pedestrian",
        "texture": load_texture_safe("pedestrian.png", ":resources:images/items/gemRed.png"),
        "speed": 2
    },
    {
        "name": "cat",
        "texture": load_texture_safe("cat.png", ":resources:images/items/star.png"),
        "speed": None  # special behavior
    },
]


class MovingEntity(arcade.Sprite):
    def __init__(self, data):
        super().__init__(data["texture"], scale=SPRITE_SCALING_COIN)

        self.name = data["name"]
        self.base_speed = data["speed"]

        self.change_timer = random.uniform(1.0, 3.0)

        self.pick_direction()

    def get_speed(self):
        # Cat has variable speed
        if self.name == "cat":
            return random.uniform(2, 4)  # between pedestrian (2) and cyclist (4)
        return self.base_speed

    def pick_direction(self):
        speed = self.get_speed()

        direction = random.choice(["up", "down", "left", "right"])

        if direction == "up":
            self.change_x = 0
            self.change_y = speed
        elif direction == "down":
            self.change_x = 0
            self.change_y = -speed
        elif direction == "left":
            self.change_x = -speed
            self.change_y = 0
        else:
            self.change_x = speed
            self.change_y = 0

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Bounce
        if self.left < 0 or self.right > WINDOW_WIDTH:
            self.change_x *= -1
        if self.bottom < 0 or self.top > WINDOW_HEIGHT:
            self.change_y *= -1

        # Change direction
        self.change_timer -= delta_time
        if self.change_timer <= 0:
            self.pick_direction()
            self.change_timer = random.uniform(1.0, 3.0)

    def draw_label(self):
        arcade.draw_text(
            self.name,
            self.center_x,
            self.top + 5,
            arcade.color.WHITE,
            10,
            anchor_x="center"
        )


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.player_list = None
        self.entity_list = None
        self.player_sprite = None

        self.background = None

        self.target_x = 0
        self.target_y = 0

        self.game_over = False

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()

        # Background
        bg_path = load_texture_safe(
            "bgimage.png",
            ":resources:images/backgrounds/abstract_1.jpg"
        )
        self.background = arcade.load_texture(bg_path)

        # Player
        player_path = load_texture_safe(
            "waymo.avif",
            ":resources:images/animated_characters/female_person/femalePerson_idle.png"
        )

        self.player_sprite = arcade.Sprite(player_path, SPRITE_SCALING_PLAYER)
        self.player_sprite.center_x = 50
        self.player_sprite.center_y = 50
        self.player_list.append(self.player_sprite)

        self.target_x = 50
        self.target_y = 50

        # Entities
        for _ in range(COIN_COUNT):
            data = random.choice(ENTITY_TYPES)
            entity = MovingEntity(data)

            entity.center_x = random.randrange(WINDOW_WIDTH)
            entity.center_y = random.randrange(WINDOW_HEIGHT)

            self.entity_list.append(entity)

    def on_draw(self):
        self.clear()

        arcade.draw_texture_rect(
            self.background,
            arcade.rect.XYWH(
                WINDOW_WIDTH / 2,
                WINDOW_HEIGHT / 2,
                WINDOW_WIDTH,
                WINDOW_HEIGHT
            )
        )

        self.entity_list.draw()
        self.player_list.draw()

        # Draw labels
        for entity in self.entity_list:
            entity.draw_label()

        if self.game_over:
            arcade.draw_text(
                "GAME OVER",
                WINDOW_WIDTH / 2,
                WINDOW_HEIGHT / 2,
                arcade.color.RED,
                40,
                anchor_x="center"
            )

    def on_mouse_motion(self, x, y, dx, dy):
        self.target_x = x
        self.target_y = y

    def on_update(self, delta_time):
        if self.game_over:
            return

        self.entity_list.update(delta_time)

        # Player movement
        speed = 5
        dx = self.target_x - self.player_sprite.center_x
        dy = self.target_y - self.player_sprite.center_y

        dist = (dx**2 + dy**2) ** 0.5
        if dist > 0:
            dx /= dist
            dy /= dist

        self.player_sprite.center_x += dx * speed
        self.player_sprite.center_y += dy * speed

        # Collision = freeze
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.entity_list
        ):
            self.game_over = True

    def on_key_press(self, key, modifiers):
        if key == arcade.key.R:
            self.setup()
            self.game_over = False


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.set_mouse_cursor_visible(False)

    game = GameView()
    game.setup()
    window.show_view(game)

    arcade.run()


if __name__ == "__main__":
    main()

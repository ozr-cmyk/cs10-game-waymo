import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_ENTITY = 0.3
ENTITY_COUNT = 4
PLAYER_SPEED = 420

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Stable Traffic Variants Game"


# --- Variants (SAFE VERSION) ---
CAR = {
    "name": "car",
    "texture": "car.png",
    "speed": 240
}

CYCLIST = {
    "name": "cyclist",
    "texture": "cyclist.png",
    "speed": 180
}

PEDESTRIAN = {
    "name": "pedestrian",
    "texture": "pedestrian.png",
    "speed": 120
}

CAT = {
    "name": "cat",
    "texture": "cat.png",
    "speed_min": 120,
    "speed_max": 220
}

ENTITY_TYPES = [CAR, CYCLIST, PEDESTRIAN, CAT]


class MovingEntity(arcade.Sprite):
    def __init__(self, config):
        super().__init__(config["texture"], SPRITE_SCALING_ENTITY)

        self.config = config
        self.name = config["name"]

        self.timer = random.uniform(1.0, 3.0)
        self.set_direction()

    def get_speed(self):
        if self.name == "cat":
            return random.uniform(self.config["speed_min"], self.config["speed_max"])
        return self.config["speed"]

    def set_direction(self):
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

    def update(self, delta_time):
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time

        if self.left < 0:
            self.left = 0
            self.change_x *= -1
        elif self.right > WINDOW_WIDTH:
            self.right = WINDOW_WIDTH
            self.change_x *= -1

        if self.bottom < 0:
            self.bottom = 0
            self.change_y *= -1
        elif self.top > WINDOW_HEIGHT:
            self.top = WINDOW_HEIGHT
            self.change_y *= -1

        self.timer -= delta_time
        if self.timer <= 0:
            self.set_direction()
            self.timer = random.uniform(1.0, 3.0)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()

        self.background = arcade.load_texture("bgimage.png")

        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            SPRITE_SCALING_PLAYER
        )

        self.player_sprite.center_x = 50
        self.player_sprite.center_y = 50

        self.player_list.append(self.player_sprite)

        for _ in range(ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)

            entity = MovingEntity(config)
            entity.center_x = random.randrange(WINDOW_WIDTH)
            entity.center_y = random.randrange(WINDOW_HEIGHT)

            self.entity_list.append(entity)

        self.game_over = False

    def on_draw(self):
        self.clear()

        arcade.draw_texture_rect(
            self.background,
            arcade.rect.XYWH(WINDOW_WIDTH/2, WINDOW_HEIGHT/2,
                             WINDOW_WIDTH, WINDOW_HEIGHT)
        )

        self.entity_list.draw()
        self.player_list.draw()

        if self.game_over:
            arcade.draw_text(
                "GAME OVER",
                WINDOW_WIDTH/2,
                WINDOW_HEIGHT/2,
                arcade.color.RED,
                40,
                anchor_x="center"
            )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.D:
            self.right_pressed = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False

    def on_update(self, delta_time):
        if self.game_over:
            return

        self.entity_list.update(delta_time)

        dx = 0
        dy = 0

        if self.up_pressed:
            dy += PLAYER_SPEED * delta_time
        if self.down_pressed:
            dy -= PLAYER_SPEED * delta_time
        if self.left_pressed:
            dx -= PLAYER_SPEED * delta_time
        if self.right_pressed:
            dx += PLAYER_SPEED * delta_time

        self.player_sprite.center_x += dx
        self.player_sprite.center_y += dy

        if self.player_sprite.left < 0:
            self.player_sprite.left = 0
        elif self.player_sprite.right > WINDOW_WIDTH:
            self.player_sprite.right = WINDOW_WIDTH

        if self.player_sprite.bottom < 0:
            self.player_sprite.bottom = 0
        elif self.player_sprite.top > WINDOW_HEIGHT:
            self.player_sprite.top = WINDOW_HEIGHT

        if arcade.check_for_collision_with_list(self.player_sprite, self.entity_list):
            self.game_over = True


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()

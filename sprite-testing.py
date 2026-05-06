import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.3
SPRITE_SCALING_COIN = 0.5
COIN_COUNT = 50

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Working Coin Variants (No Errors)"


# Built-in Arcade textures (these ALWAYS exist)
COIN_TYPES = [
    {"texture": ":resources:images/items/coinGold.png", "speed": 1},
    {"texture": ":resources:images/items/gemBlue.png", "speed": 2},
    {"texture": ":resources:images/items/gemRed.png", "speed": 3},
    {"texture": ":resources:images/items/star.png", "speed": 5},
]


class Coin(arcade.Sprite):
    def __init__(self, texture, scale, speed):
        super().__init__(texture, scale=scale)

        self.speed = speed
        self.change_timer = random.uniform(1.0, 3.0)
        self.pick_direction()

    def pick_direction(self):
        direction = random.choice(["up", "down", "left", "right"])

        if direction == "up":
            self.change_x = 0
            self.change_y = self.speed
        elif direction == "down":
            self.change_x = 0
            self.change_y = -self.speed
        elif direction == "left":
            self.change_x = -self.speed
            self.change_y = 0
        else:  # right
            self.change_x = self.speed
            self.change_y = 0

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Bounce off walls
        if self.left < 0 or self.right > WINDOW_WIDTH:
            self.change_x *= -1
        if self.bottom < 0 or self.top > WINDOW_HEIGHT:
            self.change_y *= -1

        # Occasionally change direction
        self.change_timer -= delta_time
        if self.change_timer <= 0:
            self.pick_direction()
            self.change_timer = random.uniform(1.0, 3.0)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.player_list = None
        self.coin_list = None
        self.player_sprite = None

        self.target_x = 0
        self.target_y = 0

        self.game_over = False

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()

        # Player (built-in image)
        self.player_sprite = arcade.Sprite(
            ":resources:images/animated_characters/female_person/femalePerson_idle.png",
            scale=SPRITE_SCALING_PLAYER
        )
        self.player_sprite.center_x = 100
        self.player_sprite.center_y = 100
        self.player_list.append(self.player_sprite)

        self.target_x = 100
        self.target_y = 100

        # Coins (variants)
        for _ in range(COIN_COUNT):
            coin_type = random.choice(COIN_TYPES)

            coin = Coin(
                coin_type["texture"],
                SPRITE_SCALING_COIN,
                coin_type["speed"]
            )

            coin.center_x = random.randrange(WINDOW_WIDTH)
            coin.center_y = random.randrange(WINDOW_HEIGHT)

            self.coin_list.append(coin)

    def on_draw(self):
        self.clear()

        self.coin_list.draw()
        self.player_list.draw()

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

        self.coin_list.update(delta_time)

        # Smooth movement
        speed = 5
        dx = self.target_x - self.player_sprite.center_x
        dy = self.target_y - self.player_sprite.center_y

        distance = (dx**2 + dy**2) ** 0.5
        if distance > 0:
            dx /= distance
            dy /= distance

        self.player_sprite.center_x += dx * speed
        self.player_sprite.center_y += dy * speed

        # Collision = freeze game
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.coin_list
        ):
            self.game_over = True

    def on_key_press(self, key, modifiers):
        # Press R to restart
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

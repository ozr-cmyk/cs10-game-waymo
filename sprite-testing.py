import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_COIN = 0.3
COIN_COUNT = 10

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Linear Coins + Freeze on Hit"


class Coin(arcade.Sprite):
    def __init__(self, filename, scale):
        super().__init__(filename, scale=scale)

        self.speed = random.randint(1, 4)
        self.pick_new_direction()

        self.change_timer = random.uniform(1.0, 3.0)

    def pick_new_direction(self):
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
        elif direction == "right":
            self.change_x = self.speed
            self.change_y = 0

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        # Bounce off edges
        if self.left < 0 or self.right > WINDOW_WIDTH:
            self.change_x *= -1
        if self.bottom < 0 or self.top > WINDOW_HEIGHT:
            self.change_y *= -1

        # Randomly change direction
        self.change_timer -= delta_time
        if self.change_timer <= 0:
            self.pick_new_direction()
            self.change_timer = random.uniform(1.0, 3.0)


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.player_sprite = None
        self.player_list = None
        self.coin_list = None

        self.background = None

        self.target_x = 0
        self.target_y = 0

        self.game_over = False

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()

        self.background = arcade.load_texture("bgimage.png")

        # Player
        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            scale=SPRITE_SCALING_PLAYER
        )
        self.player_sprite.position = (50, 50)
        self.player_list.append(self.player_sprite)

        self.target_x = 50
        self.target_y = 50

        # Coins
        for _ in range(COIN_COUNT):
            coin = Coin(
                ":resources:images/items/coinGold.png",
                SPRITE_SCALING_COIN
            )
            coin.center_x = random.randrange(WINDOW_WIDTH)
            coin.center_y = random.randrange(WINDOW_HEIGHT)
            self.coin_list.append(coin)

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
            return  # 🔒 Freeze everything

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

        # --- Collision = freeze game ---
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.coin_list
        ):
            self.game_over = True


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.set_mouse_cursor_visible(False)

    game = GameView()
    game.setup()
    window.show_view(game)

    arcade.run()


if __name__ == "__main__":
    main()

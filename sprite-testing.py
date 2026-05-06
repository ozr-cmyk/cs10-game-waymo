import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_COIN = 0.3
COIN_COUNT = 50

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Blocking Coins + Score Penalty"


class Coin(arcade.Sprite):
    def __init__(self, filename, scale):
        super().__init__(filename, scale=scale)

        self.change_x = random.uniform(-2, 2)
        self.change_y = random.uniform(-2, 2)
        self.change_timer = random.uniform(0.5, 2.0)

    def update(self, delta_time: float = 1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        self.change_timer -= delta_time
        if self.change_timer <= 0:
            self.change_x += random.uniform(-1.5, 1.5)
            self.change_y += random.uniform(-1.5, 1.5)
            self.change_timer = random.uniform(0.5, 2.0)

        # small randomness
        self.change_x += random.uniform(-0.1, 0.1)
        self.change_y += random.uniform(-0.1, 0.1)

        # clamp speed
        max_speed = 4
        self.change_x = max(-max_speed, min(self.change_x, max_speed))
        self.change_y = max(-max_speed, min(self.change_y, max_speed))

        # bounce off screen edges
        if self.left < 0 or self.right > WINDOW_WIDTH:
            self.change_x *= -1
        if self.bottom < 0 or self.top > WINDOW_HEIGHT:
            self.change_y *= -1


class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.player_sprite = None
        self.player_list = None
        self.coin_list = None

        self.score = 0
        self.score_text = None

        self.background = None

        # mouse target
        self.target_x = 0
        self.target_y = 0

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.coin_list = arcade.SpriteList()

        # Background (make sure file exists)
        self.background = arcade.load_texture("bgimage.png")

        self.score = 0
        self.score_text = arcade.Text(
            f"Score: {self.score}",
            10, 20,
            arcade.color.WHITE,
            14
        )

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
        self.score_text.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        self.target_x = x
        self.target_y = y

    def on_update(self, delta_time):
        self.coin_list.update(delta_time)

        # --- Smooth movement toward mouse ---
        speed = 5

        dx = self.target_x - self.player_sprite.center_x
        dy = self.target_y - self.player_sprite.center_y

        distance = (dx**2 + dy**2) ** 0.5
        if distance > 0:
            dx /= distance
            dy /= distance

        # --- Move X ---
        self.player_sprite.center_x += dx * speed
        if arcade.check_for_collision_with_list(self.player_sprite, self.coin_list):
            self.player_sprite.center_x -= dx * speed  # undo

        # --- Move Y ---
        self.player_sprite.center_y += dy * speed
        if arcade.check_for_collision_with_list(self.player_sprite, self.coin_list):
            self.player_sprite.center_y -= dy * speed  # undo

        # --- Score penalty on touch ---
        hit_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.coin_list
        )

        for coin in hit_list:
            coin.remove_from_sprite_lists()
            self.score -= 1  # subtract points

        self.score_text.text = f"Score: {self.score}"


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.set_mouse_cursor_visible(False)

    game = GameView()
    game.setup()
    window.show_view(game)

    arcade.run()


if __name__ == "__main__":
    main()

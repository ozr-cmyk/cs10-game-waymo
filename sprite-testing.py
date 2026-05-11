import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_ENTITY = 0.3
ENTITY_COUNT = 4
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Stable Traffic Variants Game"
GRID_SIZE = 40
GRID_COLS = WINDOW_WIDTH // GRID_SIZE
GRID_ROWS = WINDOW_HEIGHT // GRID_SIZE
PLAYER_TILES_PER_SECOND = 8


# --- Variants (SAFE VERSION) ---
CAR = {
    "name": "car",
    "texture": "car.png",
    "speed": 4
}

CYCLIST = {
    "name": "cyclist",
    "texture": "cyclist.png",
    "speed": 3
}

PEDESTRIAN = {
    "name": "pedestrian",
    "texture": "pedestrian.png",
    "speed": 2
}

CAT = {
    "name": "cat",
    "texture": "cat.png",
    "speed_min": 2,
    "speed_max": 4
}

ENTITY_TYPES = [CAR, CYCLIST, PEDESTRIAN, CAT]


def grid_to_center(grid_x, grid_y):
    return (
        grid_x * GRID_SIZE + GRID_SIZE / 2,
        grid_y * GRID_SIZE + GRID_SIZE / 2,
    )


class MovingEntity(arcade.Sprite):
    def __init__(self, config):
        super().__init__(config["texture"], SPRITE_SCALING_ENTITY)

        self.config = config
        self.name = config["name"]
        self.grid_x = 0
        self.grid_y = 0
        self.direction = random.choice(["up", "down", "left", "right"])
        self.step_timer = 0.0

    def get_speed(self):
        if self.name == "cat":
            return random.uniform(self.config["speed_min"], self.config["speed_max"])
        return self.config["speed"]

    def set_direction(self):
        self.direction = random.choice(["up", "down", "left", "right"])

    def sync_to_grid(self):
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)

    def step(self):
        next_x = self.grid_x
        next_y = self.grid_y

        if self.direction == "up":
            next_y += 1
        elif self.direction == "down":
            next_y -= 1
        elif self.direction == "left":
            next_x -= 1
        else:
            next_x += 1

        if next_x < 0 or next_x >= GRID_COLS:
            self.direction = "left" if self.direction == "right" else "right"
            next_x = self.grid_x + (-1 if self.direction == "left" else 1)

        if next_y < 0 or next_y >= GRID_ROWS:
            self.direction = "down" if self.direction == "up" else "up"
            next_y = self.grid_y + (-1 if self.direction == "down" else 1)

        self.grid_x = max(0, min(GRID_COLS - 1, next_x))
        self.grid_y = max(0, min(GRID_ROWS - 1, next_y))
        self.sync_to_grid()

    def update(self, delta_time):
        self.step_timer += delta_time
        step_interval = 1.0 / self.get_speed()

        while self.step_timer >= step_interval:
            self.step_timer -= step_interval
            self.step()

        self.sync_to_grid()


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.player_grid_x = 0
        self.player_grid_y = 0
        self.player_step_timer = 0.0

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()

        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            SPRITE_SCALING_PLAYER
        )

        self.player_grid_x = 1
        self.player_grid_y = 1
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )

        self.player_list.append(self.player_sprite)

        for _ in range(ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)

            entity = MovingEntity(config)
            entity.grid_x = random.randrange(GRID_COLS)
            entity.grid_y = random.randrange(GRID_ROWS)
            entity.sync_to_grid()

            self.entity_list.append(entity)

        self.game_over = False

    def on_draw(self):
        self.clear()

        arcade.draw_lbwh_rectangle_filled(
            0,
            0,
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
            arcade.color.DARK_GREEN,
        )
        self.draw_streets()

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

    def draw_streets(self):
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                center_x, center_y = grid_to_center(col, row)
                left = center_x - (GRID_SIZE - 2) / 2
                bottom = center_y - (GRID_SIZE - 2) / 2
                arcade.draw_lbwh_rectangle_filled(
                    left,
                    bottom,
                    GRID_SIZE - 2,
                    GRID_SIZE - 2,
                    arcade.color.DARK_SLATE_GRAY,
                )
                arcade.draw_lbwh_rectangle_outline(
                    left,
                    bottom,
                    GRID_SIZE - 2,
                    GRID_SIZE - 2,
                    arcade.color.DIM_GRAY,
                    1,
                )
                arcade.draw_line(
                    center_x - GRID_SIZE * 0.18,
                    center_y,
                    center_x + GRID_SIZE * 0.18,
                    center_y,
                    arcade.color.LIGHT_GRAY,
                    1,
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

    def move_player(self, dx, dy):
        self.player_grid_x = max(0, min(GRID_COLS - 1, self.player_grid_x + dx))
        self.player_grid_y = max(0, min(GRID_ROWS - 1, self.player_grid_y + dy))
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )

    def get_player_direction(self):
        if self.up_pressed:
            return 0, 1
        if self.down_pressed:
            return 0, -1
        if self.left_pressed:
            return -1, 0
        if self.right_pressed:
            return 1, 0
        return 0, 0

    def on_update(self, delta_time):
        if self.game_over:
            return

        self.entity_list.update(delta_time)

        if not (self.up_pressed or self.down_pressed or self.left_pressed or self.right_pressed):
            self.player_step_timer = 0.0
            return

        self.player_step_timer += delta_time
        player_step_interval = 1.0 / PLAYER_TILES_PER_SECOND
        move_x, move_y = self.get_player_direction()

        while self.player_step_timer >= player_step_interval and (move_x or move_y):
            self.player_step_timer -= player_step_interval
            self.move_player(move_x, move_y)
            move_x, move_y = self.get_player_direction()

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

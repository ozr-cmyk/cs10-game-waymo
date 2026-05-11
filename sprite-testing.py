import random
import arcade

# --- Constants ---
SPRITE_SCALING_PLAYER = 0.03
SPRITE_SCALING_ENTITY = 0.3
ENTITY_COUNT = 4
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Stable Traffic Variants Game"
PLAYER_TILES_PER_SECOND = 8
GRID_BACKGROUND_ALPHA = 160
STREET_FILL_ALPHA = 165
BLOCK_FILL_ALPHA = 195
STREET_OUTLINE_ALPHA = 180
BLOCK_OUTLINE_ALPHA = 210

# Bottom row first. "#" tiles line up with the drawn street grid.
STREET_TILE_ROWS = (
    "################################",
    "..#.....#......#....#.....#...##",
    "..#.....#......#.....#.....#...#",
    "..#.....#......#.....###########",
    "################################",
    "..#.....#..##..#...........#...#",
    "..#.....#.###..#...........#...#",
    "..#.######...################..#",
    "..#.....#......#.....#.....#...#",
    "..#.....#......#.....#.....#...#",
    "################################",
    "..#.....#......#.....#.....#...#",
    "..#.....#......#.....#.....#...#",
    "######################...#######",
    "..#.....#......#.....#.....#...#",
    "..#.....#......#.....#.....#...#",
    "..#.....#......#.....#.....#...#",
    "################################",
)

GRID_COLS = len(STREET_TILE_ROWS[0])
GRID_ROWS = len(STREET_TILE_ROWS)
GRID_CELL_WIDTH = WINDOW_WIDTH / GRID_COLS
GRID_CELL_HEIGHT = WINDOW_HEIGHT / GRID_ROWS

DIRECTION_DELTAS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}


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
        grid_x * GRID_CELL_WIDTH + GRID_CELL_WIDTH / 2,
        grid_y * GRID_CELL_HEIGHT + GRID_CELL_HEIGHT / 2,
    )


def with_alpha(color, alpha):
    return (color.r, color.g, color.b, alpha)


def is_street_tile(grid_x, grid_y):
    if not (0 <= grid_x < GRID_COLS and 0 <= grid_y < GRID_ROWS):
        return False
    return STREET_TILE_ROWS[grid_y][grid_x] == "#"


def random_street_tile():
    street_tiles = [
        (grid_x, grid_y)
        for grid_y, row in enumerate(STREET_TILE_ROWS)
        for grid_x, tile in enumerate(row)
        if tile == "#"
    ]
    return random.choice(street_tiles)


def street_neighbors(grid_x, grid_y):
    neighbors = []

    for direction, (dx, dy) in DIRECTION_DELTAS.items():
        next_x = grid_x + dx
        next_y = grid_y + dy
        if is_street_tile(next_x, next_y):
            neighbors.append((direction, next_x, next_y))

    return neighbors


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
        dx, dy = DIRECTION_DELTAS[self.direction]
        next_x = self.grid_x + dx
        next_y = self.grid_y + dy

        if not is_street_tile(next_x, next_y):
            valid_neighbors = street_neighbors(self.grid_x, self.grid_y)
            if not valid_neighbors:
                self.sync_to_grid()
                return

            self.direction, next_x, next_y = random.choice(valid_neighbors)

        self.grid_x = next_x
        self.grid_y = next_y
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
        self.background_list = arcade.SpriteList()

    def setup(self):
        self.background_list = arcade.SpriteList()
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()

        background_sprite = arcade.Sprite("grid.png")
        background_sprite.center_x = WINDOW_WIDTH / 2
        background_sprite.center_y = WINDOW_HEIGHT / 2
        background_sprite.width = WINDOW_WIDTH
        background_sprite.height = WINDOW_HEIGHT
        background_sprite.alpha = GRID_BACKGROUND_ALPHA
        self.background_list.append(background_sprite)

        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            SPRITE_SCALING_PLAYER
        )

        self.player_grid_x, self.player_grid_y = random_street_tile()
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )

        self.player_list.append(self.player_sprite)

        for _ in range(ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)

            entity = MovingEntity(config)
            entity.grid_x, entity.grid_y = random_street_tile()
            entity.sync_to_grid()

            self.entity_list.append(entity)

        self.game_over = False

    def on_draw(self):
        self.clear()

        self.background_list.draw()
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
                left = center_x - (GRID_CELL_WIDTH - 2) / 2
                bottom = center_y - (GRID_CELL_HEIGHT - 2) / 2
                if is_street_tile(col, row):
                    fill_color = with_alpha(arcade.color.DARK_SLATE_GRAY, STREET_FILL_ALPHA)
                    outline_color = with_alpha(arcade.color.DIM_GRAY, STREET_OUTLINE_ALPHA)
                else:
                    fill_color = with_alpha(arcade.color.LIGHT_CORAL, BLOCK_FILL_ALPHA)
                    outline_color = with_alpha(arcade.color.DARK_RED, BLOCK_OUTLINE_ALPHA)

                arcade.draw_lbwh_rectangle_filled(
                    left,
                    bottom,
                    GRID_CELL_WIDTH - 2,
                    GRID_CELL_HEIGHT - 2,
                    fill_color,
                )
                arcade.draw_lbwh_rectangle_outline(
                    left,
                    bottom,
                    GRID_CELL_WIDTH - 2,
                    GRID_CELL_HEIGHT - 2,
                    outline_color,
                    1,
                )
                arcade.draw_line(
                    center_x - GRID_CELL_WIDTH * 0.18,
                    center_y,
                    center_x + GRID_CELL_WIDTH * 0.18,
                    center_y,
                    arcade.color.LIGHT_GRAY if is_street_tile(col, row) else arcade.color.DARK_RED,
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
        next_x = self.player_grid_x + dx
        next_y = self.player_grid_y + dy

        if not is_street_tile(next_x, next_y):
            return

        self.player_grid_x = next_x
        self.player_grid_y = next_y
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

import random
from functools import lru_cache
import arcade
from PIL import Image

# --- Constants ---
ENTITY_COUNT = 4
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Stable Traffic Variants Game"
PLAYER_TILES_PER_SECOND = 8
STOPLIGHT_PHASE_SECONDS = 7.0
STREET_FILL_ALPHA = 165
BLOCK_FILL_ALPHA = 195
STREET_OUTLINE_ALPHA = 180
BLOCK_OUTLINE_ALPHA = 210

STREET_TILE_ROWS = (
    "################################",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "################################",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "..##############################",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "################################",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "################################",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "..#.....#......#.....#.....#....",
    "################################",
)

GRID_COLS = len(STREET_TILE_ROWS[0])
GRID_ROWS = len(STREET_TILE_ROWS)
GRID_CELL_WIDTH = WINDOW_WIDTH / GRID_COLS
GRID_CELL_HEIGHT = WINDOW_HEIGHT / GRID_ROWS
TWO_TILE_SIZE = min(GRID_CELL_WIDTH, GRID_CELL_HEIGHT) * 2

DIRECTION_DELTAS = {
    "up": (0, 1),
    "down": (0, -1),
    "left": (-1, 0),
    "right": (1, 0),
}

DIRECTION_ANGLES = {
    "right": {"right": 90, "up": 0, "left": 270, "down": 180},
    "left": {"left": 270, "down": 180, "right": 90, "up": 0},
}

OPPOSITE_DIRECTION = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}

CAR = {
    "name": "car",
    "texture": "car.png",
    "speed": 4,
    "facing": "left",
}

CYCLIST = {
    "name": "cyclist",
    "texture": "cyclist.png",
    "speed": 3,
    "facing": "right",
}

PEDESTRIAN = {
    "name": "pedestrian",
    "texture": "pedestrian.png",
    "speed": 2,
    "facing": "right",
}

CAT = {
    "name": "cat",
    "texture": "cat.png",
    "speed_min": 2,
    "speed_max": 4,
    "facing": "left",
}

ENTITY_TYPES = [CAR, CYCLIST, PEDESTRIAN, CAT]
RED_LIGHT_ENTITIES = {"car", "cyclist", "pedestrian"}
TURN_WEIGHT = 2.0

# --- Helper functions ---
def grid_to_center(grid_x, grid_y):
    return (
        grid_x * GRID_CELL_WIDTH + GRID_CELL_WIDTH / 2,
        grid_y * GRID_CELL_HEIGHT + GRID_CELL_HEIGHT / 2,
    )

@lru_cache(maxsize=None)
def sprite_scale_to_two_tiles(texture_path):
    with Image.open(texture_path) as image:
        widest_side = max(image.size)
    return TWO_TILE_SIZE / widest_side

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

def direction_to_angle(direction, facing):
    return DIRECTION_ANGLES[facing][direction]

def choose_direction_with_turn_bias(current_direction, options):
    if len(options) <= 1:
        return options[0]
    weighted_options = []
    for option in options:
        direction = option[0]
        weight = TURN_WEIGHT if direction != current_direction else 1.0
        weighted_options.extend([option] * int(weight * 2))
    return random.choice(weighted_options)

# --- MovingEntity class ---
class MovingEntity(arcade.Sprite):
    def __init__(self, config):
        super().__init__(config["texture"], sprite_scale_to_two_tiles(config["texture"]))
        self.config = config
        self.name = config["name"]
        self.facing = config["facing"]
        self.grid_x = 0
        self.grid_y = 0
        self.direction = random.choice(["up", "down", "left", "right"])
        self.step_timer = 0.0
        self.angle = direction_to_angle(self.direction, self.facing)

    def get_speed(self):
        if self.name == "cat":
            return random.uniform(self.config["speed_min"], self.config["speed_max"])
        return self.config["speed"]

    def sync_to_grid(self):
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)

    def step(self):
        neighbors = street_neighbors(self.grid_x, self.grid_y)
        if neighbors:
            self.direction, self.grid_x, self.grid_y = choose_direction_with_turn_bias(self.direction, neighbors)
            self.angle = direction_to_angle(self.direction, self.facing)
        self.sync_to_grid()

    def update(self, delta_time):
        self.step_timer += delta_time
        step_interval = 1.0 / self.get_speed()
        while self.step_timer >= step_interval:
            self.step_timer -= step_interval
            self.step()

# --- Client class ---
class Client(arcade.Sprite):
    VOICELINES = [
        "It's taking a while...",
        "Maybe I should have taken an über...",
        "Hurry up, please!",
        "This is taking too long!",
    ]
    def __init__(self, player_grid_pos):
        super().__init__("client.png", sprite_scale_to_two_tiles("client.png"))
        # Spawn far from player
        while True:
            self.grid_x, self.grid_y = random_street_tile()
            px, py = player_grid_pos
            if abs(self.grid_x - px) + abs(self.grid_y - py) > 5:
                break
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)
        self.chat_text = ""
        self.chat_timer = 0.0
        self.time_since_spawn = 0.0
        self.next_voiceline_time = 1.0

    def update(self, delta_time):
        self.time_since_spawn += delta_time
        self.chat_timer = max(0, self.chat_timer - delta_time)
        if self.time_since_spawn >= self.next_voiceline_time:
            if self.chat_text == "":
                self.chat_text = "i need a waymo"
                self.chat_timer = 3.0
                self.next_voiceline_time = self.time_since_spawn + random.uniform(3, 6)
            else:
                self.chat_text = random.choice(Client.VOICELINES)
                self.chat_timer = 3.0
                self.next_voiceline_time = self.time_since_spawn + random.uniform(3, 6)

    def draw_chat(self):
        if self.chat_timer > 0:
            arcade.draw_rectangle_filled(
                self.center_x,
                self.center_y + 40,
                len(self.chat_text) * 10,
                24,
                arcade.color.WHITE_SMOKE
            )
            arcade.draw_text(
                self.chat_text,
                self.center_x - len(self.chat_text) * 5,
                self.center_y + 32,
                arcade.color.BLACK,
                12
            )

# --- GameView class ---
class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.player_grid_x = 0
        self.player_grid_y = 0
                self.player_step_timer = 0.0
        self.stoplight_timer = random.uniform(0.0, STOPLIGHT_PHASE_SECONDS * 2)

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()
        self.client_list = arcade.SpriteList()

        # Player sprite
        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            sprite_scale_to_two_tiles("waymo.avif")
        )
        self.player_grid_x = 0
        self.player_grid_y = 0
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x, self.player_grid_y
        )
        self.player_sprite.angle = direction_to_angle("left", "left")
        self.player_list.append(self.player_sprite)

        # Spawn other entities
        available_tiles = random_street_tiles(excluded={(self.player_grid_x, self.player_grid_y)})
        for grid_x, grid_y in random.sample(available_tiles, ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)
            entity = MovingEntity(config)
            entity.grid_x, entity.grid_y = grid_x, grid_y
            entity.sync_to_grid()
            self.entity_list.append(entity)

        # Spawn client
        self.client = Client((self.player_grid_x, self.player_grid_y))
        self.client_list.append(self.client)

    def on_draw(self):
        self.clear()
        self.draw_streets()
        self.entity_list.draw()
        self.player_list.draw()
        self.client_list.draw()

        # Draw client chat bubbles
        for client in self.client_list:
            client.draw_chat()

    def draw_streets(self):
        for col in range(GRID_COLS):
            for row in range(GRID_ROWS):
                center_x, center_y = grid_to_center(col, row)
                left = center_x - (GRID_CELL_WIDTH - 2) / 2
                bottom = center_y - (GRID_CELL_HEIGHT - 2) / 2
                if is_street_tile(col, row):
                    fill_color = arcade.color.DARK_SLATE_GRAY
                    outline_color = arcade.color.DIM_GRAY
                else:
                    fill_color = arcade.color.LIGHT_CORAL
                    outline_color = arcade.color.DARK_RED
                arcade.draw_rectangle_filled(
                    center_x, center_y, GRID_CELL_WIDTH - 2, GRID_CELL_HEIGHT - 2, fill_color
                )
                arcade.draw_rectangle_outline(
                    center_x, center_y, GRID_CELL_WIDTH - 2, GRID_CELL_HEIGHT - 2, outline_color, 1
                )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W: self.up_pressed = True
        if key == arcade.key.S: self.down_pressed = True
        if key == arcade.key.A: self.left_pressed = True
        if key == arcade.key.D: self.right_pressed = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W: self.up_pressed = False
        if key == arcade.key.S: self.down_pressed = False
        if key == arcade.key.A: self.left_pressed = False
        if key == arcade.key.D: self.right_pressed = False

    def get_player_direction(self):
        dx = 0
        dy = 0
        if self.up_pressed: dy = 1
        if self.down_pressed: dy = -1
        if self.left_pressed: dx = -1
        if self.right_pressed: dx = 1
        return dx, dy

    def move_player(self, dx, dy):
        next_x = self.player_grid_x + dx
        next_y = self.player_grid_y + dy
        if not is_street_tile(next_x, next_y):
            return
        self.player_grid_x = next_x
        self.player_grid_y = next_y
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x, self.player_grid_y
        )
        # Update player angle
        if dx > 0: direction = "right"
        elif dx < 0: direction = "left"
        elif dy > 0: direction = "up"
        elif dy < 0: direction = "down"
        else: direction = "left"
        self.player_sprite.angle = direction_to_angle(direction, "left")

    def on_update(self, delta_time):
        # Update player movement
        dx, dy = self.get_player_direction()
        self.player_step_timer += delta_time
        step_interval = 1.0 / PLAYER_TILES_PER_SECOND
        while self.player_step_timer >= step_interval:
            self.player_step_timer -= step_interval
            self.move_player(dx, dy)

        # Update entities
        for entity in self.entity_list:
            entity.update(delta_time)

        # Update client
        for client in self.client_list:
            client.update(delta_time)

# --- Run the game ---
def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game_view = GameView()
    game_view.setup()
    window.show_view(game_view)
    arcade.run()

if __name__ == "__main__":
    main()

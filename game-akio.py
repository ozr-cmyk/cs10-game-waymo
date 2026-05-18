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
GRID_CELL_WIDTH = 40
GRID_CELL_HEIGHT = 40
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
GRID_ROWS = len(STREET_TILE_ROWS)
GRID_COLS = len(STREET_TILE_ROWS[0])

# --- Entities ---
CAR = {"name": "car", "texture": "car.png", "speed": 4, "facing": "left"}
CYCLIST = {"name": "cyclist", "texture": "cyclist.png", "speed": 3, "facing": "right"}
PEDESTRIAN = {"name": "pedestrian", "texture": "pedestrian.png", "speed": 2, "facing": "right"}
CAT = {"name": "cat", "texture": "cat.png", "speed_min": 2, "speed_max": 4, "facing": "left"}
ENTITY_TYPES = [CAR, CYCLIST, PEDESTRIAN, CAT]

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

def random_street_tile(exclude=None):
    exclude = exclude or set()
    street_tiles = [
        (x, y)
        for y, row in enumerate(STREET_TILE_ROWS)
        for x, tile in enumerate(row)
        if tile == "#" and (x, y) not in exclude
    ]
    return random.choice(street_tiles)

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
        self.angle = 0

    def get_speed(self):
        if self.name == "cat":
            return random.uniform(self.config["speed_min"], self.config["speed_max"])
        return self.config["speed"]

    def sync_to_grid(self):
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)

    def step(self):
        # Simple random movement
        neighbors = []
        for d, (dx, dy) in DIRECTION_DELTAS.items():
            nx, ny = self.grid_x + dx, self.grid_y + dy
            if is_street_tile(nx, ny):
                neighbors.append((d, nx, ny))
        if neighbors:
            self.direction, self.grid_x, self.grid_y = random.choice(neighbors)
        self.angle = DIRECTION_ANGLES[self.facing][self.direction]
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

# --- GameView ---
class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.left_pressed = self.right_pressed = self.up_pressed = self.down_pressed = False
        self.player_grid_x = 0
        self.player_grid_y = 0
        self.player_step_timer = 0.0

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()
        self.client_list = arcade.SpriteList()

        # Player
        self.player_sprite = arcade.Sprite("waymo.avif", sprite_scale_to_two_tiles("waymo.avif"))
        self.player_grid_x = 0
        self.player_grid_y = 0
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x, self.player_grid_y
        )
        self.player_sprite.angle = 0
        self.player_list.append(self.player_sprite)

        # Entities
        available_tiles = random_street_tile(exclude={(self.player_grid_x, self.player_grid_y)})
        for _ in range(ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)
            entity = MovingEntity(config)
            entity.grid_x, entity.grid_y = random_street_tile(exclude={(self.player_grid_x, self.player_grid_y)})
            entity.sync_to_grid()
            self.entity_list.append(entity)

        # Client
        self.client = Client((self.player_grid_x, self.player_grid_y))
        self.client_list.append(self.client)

    def on_draw(self):
        self.clear()
        self.draw_streets()
        self.entity_list.draw()
        self.player_list.draw()
        self.client_list.draw()
        for client in self.client_list:
            client.draw_chat()

    def draw_streets(self):
        for y, row in enumerate(STREET_TILE_ROWS):
            for x, tile in enumerate(row):
                center_x, center_y = grid_to_center(x, y)
                color = arcade.color.DARK_SLATE_GRAY if tile == "#" else arcade.color.LIGHT_CORAL
                arcade.draw_rectangle_filled(
                    center_x,
                    center_y,
                    GRID_CELL_WIDTH,
                    GRID_CELL_HEIGHT,
                    color
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
        dx = dy = 0
        if self.up_pressed: dy = 1
        if self.down_pressed: dy = -1
        if self.left_pressed: dx = -1
        if self.right_pressed: dx = 1
        return dx, dy

    def move_player(self, dx, dy):
        next_x = self.player_grid_x + dx
        next_y = self.player_grid_y + dy
        if not is_street_tile(next_x, next_y): return
        self.player_grid_x = next_x
        self.player_grid_y = next_y
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(next_x, next_y)

    def on_update(self, delta_time):
        # Player movement
        dx, dy = self.get_player_direction()
        self.player_step_timer += delta_time
        step_interval = 1.0 / PLAYER_TILES_PER_SECOND
        while self.player_step_timer >= step_interval:
            self.player_step_timer -= step_interval
            self.move_player(dx, dy)

        # Entities
        for entity in self.entity_list:
            entity.update(delta_time)

        # Client
        for client in self.client_list:
            client.update(delta_time)

# --- Run ---
def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()

if __name__ == "__main__":
    main()

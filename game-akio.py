import random
from collections import deque
from functools import lru_cache
import arcade
from PIL import Image

# --- Constants ---
ENTITY_COUNT = 4
TRAFFIC_OBSTACLE_TEXTURE = "Traffic!.png"
TRAFFIC_OBSTACLE_TILE_SIZE = 8
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Stable Traffic Variants Game"
WAYMO_TILES_PER_SECOND = 4
STOPLIGHT_PHASE_SECONDS = 7.0
STREET_FILL_ALPHA = 165
BLOCK_FILL_ALPHA = 195
STREET_OUTLINE_ALPHA = 180
BLOCK_OUTLINE_ALPHA = 210

# Bottom row first. "#" tiles line up with the drawn street grid.
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

# Arcade uses degrees, with 0 pointing to the right and positive angles rotating counterclockwise.
DIRECTION_ANGLES = {
    "right": {"right": 90, "up": 0, "left": 270, "down": 180},
    "left": {"left": 270, "down": 180, "right": 90, "up": 0},
}
OPPOSITE_DIRECTION = {"up": "down", "down": "up", "left": "right", "right": "left"}

# --- Variants (SAFE VERSION) ---
CAR = {"name": "car", "texture": "car.png", "speed": 4, "facing": "left"}
CYCLIST = {"name": "cyclist", "texture": "cyclist.png", "speed": 3, "facing": "right"}
PEDESTRIAN = {"name": "pedestrian", "texture": "pedestrian.png", "speed": 2, "facing": "right"}
CAT = {"name": "cat", "texture": "cat.png", "speed_min": 2, "speed_max": 4, "facing": "left"}
ENTITY_TYPES = [CAR, CYCLIST, PEDESTRIAN, CAT]
RED_LIGHT_ENTITIES = {"car", "cyclist", "pedestrian"}
TURN_WEIGHT = 2.0

START_TILE = (0, 0)
GOAL_TILE = (GRID_COLS - 1, GRID_ROWS - 1)

# --- Client configuration ---
CLIENT = {
    "name": "client",
    "texture": "pedestrian.png",
    "messages": ["I need a Waymo", "It's taking a while", "I should've taken an Uber"],
    "facing": "right",
}


# ----------------- Utility Functions -----------------
def grid_to_center(grid_x, grid_y):
    return (
        grid_x * GRID_CELL_WIDTH + GRID_CELL_WIDTH / 2,
        grid_y * GRID_CELL_HEIGHT + GRID_CELL_HEIGHT / 2,
    )


def with_alpha(color, alpha):
    return (color.r, color.g, color.b, alpha)


@lru_cache(maxsize=None)
def sprite_scale_to_two_tiles(texture_path):
    with Image.open(texture_path) as image:
        widest_side = max(image.size)
        return TWO_TILE_SIZE / widest_side


def is_street_tile(grid_x, grid_y):
    if not (0 <= grid_x < GRID_COLS and 0 <= grid_y < GRID_ROWS):
        return False
    return STREET_TILE_ROWS[grid_y][grid_x] == "#"


def random_street_tiles(excluded=None):
    excluded = excluded or set()
    return [
        (grid_x, grid_y)
        for grid_y, row in enumerate(STREET_TILE_ROWS)
        for grid_x, tile in enumerate(row)
        if tile == "#" and (grid_x, grid_y) not in excluded
    ]


def street_neighbors(grid_x, grid_y):
    neighbors = []
    for direction, (dx, dy) in DIRECTION_DELTAS.items():
        next_x = grid_x + dx
        next_y = grid_y + dy
        if is_street_tile(next_x, next_y):
            neighbors.append((direction, next_x, next_y))
    return neighbors


def shortest_route_between_tiles(start_tile, goal_tile):
    """Breadth-first search for shortest path along street tiles."""
    if not is_street_tile(*start_tile) or not is_street_tile(*goal_tile):
        return []

    queue = deque([start_tile])
    came_from = {start_tile: None}

    while queue:
        current_x, current_y = queue.popleft()
        if (current_x, current_y) == goal_tile:
            break
        for _, next_x, next_y in street_neighbors(current_x, current_y):
            next_tile = (next_x, next_y)
            if next_tile in came_from:
                continue
            came_from[next_tile] = (current_x, current_y)
            queue.append(next_tile)

    if goal_tile not in came_from:
        return []

    # Reconstruct path
    route = []
    current_tile = goal_tile
    while current_tile is not None:
        route.append(current_tile)
        current_tile = came_from[current_tile]
    route.reverse()
    return route


def direction_to_angle(direction, facing):
    return DIRECTION_ANGLES[facing][direction]


# ----------------- Moving Entity -----------------
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

    def step(self, occupied_tiles=None, stoplight_lookup=None, stoplight_timer=None):
        blocked_tiles = set(occupied_tiles or ())
        blocked_tiles.discard((self.grid_x, self.grid_y))
        dx, dy = DIRECTION_DELTAS[self.direction]
        next_x = self.grid_x + dx
        next_y = self.grid_y + dy
        if is_street_tile(next_x, next_y) and (next_x, next_y) not in blocked_tiles:
            candidate_direction = self.direction
            candidate_x = next_x
            candidate_y = next_y
        else:
            valid_neighbors = [
                (direction, nx, ny)
                for direction, nx, ny in street_neighbors(self.grid_x, self.grid_y)
                if (nx, ny) not in blocked_tiles and direction != OPPOSITE_DIRECTION[self.direction]
            ]
            if valid_neighbors:
                candidate_direction, candidate_x, candidate_y = random.choice(valid_neighbors)
            else:
                self.sync_to_grid()
                return

        self.direction = candidate_direction
        self.grid_x = candidate_x
        self.grid_y = candidate_y
        self.angle = direction_to_angle(self.direction, self.facing)
        self.sync_to_grid()

    def update(self, delta_time, occupied_tiles=None, stoplight_lookup=None, stoplight_timer=None):
        self.step_timer += delta_time
        step_interval = 1.0 / self.get_speed()
        while self.step_timer >= step_interval:
            self.step_timer -= step_interval
            self.step(occupied_tiles, stoplight_lookup, stoplight_timer)


# ----------------- Client (stationary) -----------------
class Client(arcade.Sprite):
    def __init__(self, config):
        super().__init__(config["texture"], sprite_scale_to_two_tiles(config["texture"]))
        self.name = config["name"]
        self.grid_x, self.grid_y = random.choice(random_street_tiles())
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)


# ----------------- Waymo autopilot -----------------
class Waymo(MovingEntity):
    def __init__(self, config, client):
        super().__init__(config)
        self.client = client
        self.autopilot = True
        self.route = []
        self.route_index = 0
        self.player_step_timer = 0.0
        self.refresh_route_from_player()

    def refresh_route_from_player(self):
        if self.client is None:
            self.route = []
            return
        current_tile = (self.grid_x, self.grid_y)
        goal_tile = (self.client.grid_x, self.client.grid_y)
        if current_tile == goal_tile:
            self.route = []
            self.route_index = 0
            return
        self.route = shortest_route_between_tiles(current_tile, goal_tile)
        self.route_index = 0

    def advance_route(self):
        if not self.route or self.route_index >= len(self.route) - 1:
            self.route = []
            self.route_index = 0
            return
        next_tile = self.route[self.route_index + 1]
        dx = next_tile[0] - self.grid_x
        dy = next_tile[1] - self.grid_y
        self.grid_x += dx
        self.grid_y += dy
        self.angle = direction_to_angle(self.direction, self.facing)
        self.center_x, self.center_y = grid_to_center(self.grid_x, self.grid_y)
        if (self.grid_x, self.grid_y) == next_tile:
            self.route_index += 1

    def update(self, delta_time):
        if self.autopilot:
            self.player_step_timer += delta_time
            player_step_interval = 1.0 / WAYMO_TILES_PER_SECOND
            while self.player_step_timer >= player_step_interval:
                self.player_step_timer -= player_step_interval
                if self.route:
                    self.advance_route()

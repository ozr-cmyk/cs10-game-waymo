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


def random_street_tile():
    street_tiles = [
        (grid_x, grid_y)
        for grid_y, row in enumerate(STREET_TILE_ROWS)
        for grid_x, tile in enumerate(row)
        if tile == "#"
    ]
    return random.choice(street_tiles)


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


def is_intersection_tile(grid_x, grid_y):
    return (
        is_street_tile(grid_x, grid_y)
        and is_street_tile(grid_x - 1, grid_y)
        and is_street_tile(grid_x + 1, grid_y)
        and is_street_tile(grid_x, grid_y - 1)
        and is_street_tile(grid_x, grid_y + 1)
    )


def draw_stoplight(grid_x, grid_y, state="red"):
    center_x, center_y = grid_to_center(grid_x, grid_y)

    pole_height = GRID_CELL_HEIGHT * 1.8
    pole_width = GRID_CELL_WIDTH * 0.08
    housing_width = GRID_CELL_WIDTH * 0.32
    housing_height = GRID_CELL_HEIGHT * 0.95
    light_radius = min(GRID_CELL_WIDTH, GRID_CELL_HEIGHT) * 0.11

    pole_color = arcade.color.DARK_SLATE_GRAY
    housing_color = arcade.color.BLACK
    inactive_color = arcade.color.DIM_GRAY
    active_colors = {
        "red": arcade.color.RED,
        "green": arcade.color.GREEN,
    }

    pole_left = center_x - pole_width / 2
    pole_bottom = center_y - GRID_CELL_HEIGHT * 0.25 - pole_height / 2
    arcade.draw_lbwh_rectangle_filled(pole_left, pole_bottom, pole_width, pole_height, pole_color)

    housing_left = center_x - housing_width / 2
    housing_bottom = center_y + GRID_CELL_HEIGHT * 0.35 - housing_height / 2
    arcade.draw_lbwh_rectangle_filled(housing_left, housing_bottom, housing_width, housing_height, housing_color)

    light_offsets = (0.22, 0.0, -0.22)
    light_states = ("red", "yellow", "green")

    for offset, light_state in zip(light_offsets, light_states):
        light_color = active_colors[light_state] if light_state == state else inactive_color
        arcade.draw_circle_filled(center_x, housing_bottom + housing_height / 2 + (housing_height * offset), light_radius, light_color)


def build_stoplights():
    stoplights = []
    intersection_count = 0

    for grid_y in range(GRID_ROWS):
        for grid_x in range(GRID_COLS):
            if not is_intersection_tile(grid_x, grid_y):
                continue

            if intersection_count % 3 == 0:
                stoplights.append(
                    {
                        "grid_x": grid_x,
                        "grid_y": grid_y,
                        "phase_offset": random.uniform(0.0, STOPLIGHT_PHASE_SECONDS * 2),
                    }
                )

            intersection_count += 1

    return stoplights


def draw_stoplights_every_third_intersection(stoplights, timer):
    for stoplight in stoplights:
        state = "green" if int((timer + stoplight["phase_offset"]) / STOPLIGHT_PHASE_SECONDS) % 2 else "red"
        draw_stoplight(stoplight["grid_x"], stoplight["grid_y"], state=state)


def build_stoplight_lookup(stoplights):
    return {(stoplight["grid_x"], stoplight["grid_y"]): stoplight for stoplight in stoplights}


def stoplight_state_for_tile(grid_x, grid_y, stoplight_lookup, timer):
    stoplight = stoplight_lookup.get((grid_x, grid_y))
    if stoplight is None:
        return None

    return "green" if int((timer + stoplight["phase_offset"]) / STOPLIGHT_PHASE_SECONDS) % 2 else "red"


class MovingEntity(arcade.Sprite):
    def __init__(self, config):
        super().__init__(config["texture"], sprite_scale_to_two_tiles(config["texture"]))

        self.config = config
        self.name = config["name"]
        self.facing = config["f

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
DELIVERY_TIME_LIMIT_SECONDS = 30.0
RED_LIGHT_PENALTY_SECONDS = 2.0
CLIENT_BONUS_SECONDS = 3.0
CLIENT_BONUS_THRESHOLD_SECONDS = 10.0
HUD_BADGE_SECONDS = 1.2
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

OPPOSITE_DIRECTION = {
    "up": "down",
    "down": "up",
    "left": "right",
    "right": "left",
}


# --- Variants (SAFE VERSION) ---
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
START_TILE = (0, 0)
GOAL_TILE = (GRID_COLS - 1, GRID_ROWS - 1)
DESTINATION_TEXTURE = "star.png"
DESTINATION_MIN_DISTANCE_TILES = 15

# --- Client configuration ---
CLIENT = {
    "name": "client",
    "texture": "pedestrian.png",
    "messages": ["I need a Waymo", "It's taking a while", "I should've taken an Uber"],
    "facing": "right",
}


def grid_to_center(grid_x, grid_y):
    return (
        grid_x * GRID_CELL_WIDTH + GRID_CELL_WIDTH / 2,
        grid_y * GRID_CELL_HEIGHT + GRID_CELL_HEIGHT / 2,
    )


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def clamp_center_to_window(center_x, center_y, width=0.0, height=0.0):
    """Keep a drawn object fully inside the visible window."""
    half_width = width / 2
    half_height = height / 2
    return (
        clamp(center_x, half_width, WINDOW_WIDTH - half_width),
        clamp(center_y, half_height, WINDOW_HEIGHT - half_height),
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


def route_distance_between_tiles(start_tile, goal_tile):
    route = shortest_route_between_tiles(start_tile, goal_tile)
    if not route:
        return None
    return len(route) - 1


def random_destination_tile(start_tile, minimum_distance=DESTINATION_MIN_DISTANCE_TILES, excluded=None):
    excluded = set(excluded or ())
    excluded.add(start_tile)

    eligible_tiles = []
    farthest_tiles = []
    farthest_distance = -1

    for tile in random_street_tiles(excluded=excluded):
        distance = route_distance_between_tiles(start_tile, tile)
        if distance is None:
            continue

        if distance >= minimum_distance:
            eligible_tiles.append(tile)

        if distance > farthest_distance:
            farthest_distance = distance
            farthest_tiles = [tile]
        elif distance == farthest_distance:
            farthest_tiles.append(tile)

    if eligible_tiles:
        return random.choice(eligible_tiles)

    if farthest_tiles:
        return random.choice(farthest_tiles)

    return None


def adjacent_street_tiles(tile):
    grid_x, grid_y = tile
    adjacent_tiles = []

    for dx, dy in DIRECTION_DELTAS.values():
        next_tile = (grid_x + dx, grid_y + dy)
        if is_street_tile(*next_tile):
            adjacent_tiles.append(next_tile)

    return adjacent_tiles


def is_corner_tile(tile):
    return tile in {
        (0, 0),
        (0, GRID_ROWS - 1),
        (GRID_COLS - 1, 0),
        (GRID_COLS - 1, GRID_ROWS - 1),
    }


def street_neighbors(grid_x, grid_y):
    neighbors = []

    for direction, (dx, dy) in DIRECTION_DELTAS.items():
        next_x = grid_x + dx
        next_y = grid_y + dy
        if is_street_tile(next_x, next_y):
            neighbors.append((direction, next_x, next_y))

    return neighbors


def shortest_route_between_tiles(start_tile, goal_tile):
    """Return the shortest street route between two grid tiles.

    Because every street step costs the same, breadth-first search gives us the
    optimal route in number of tiles.
    """
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

    route = []
    current_tile = goal_tile
    while current_tile is not None:
        route.append(current_tile)
        current_tile = came_from[current_tile]

    route.reverse()
    return route


def direction_to_angle(direction, facing):
    return DIRECTION_ANGLES[facing][direction]


def choose_direction_with_turn_bias(current_direction, options):
    """Prefer turning over continuing straight by 100% when both are possible."""
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
    """Draw a simple stoplight on top of the street grid."""
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

    stoplight_width = max(pole_width, housing_width)
    stoplight_height = pole_height + GRID_CELL_HEIGHT * 0.825
    center_x, center_y = clamp_center_to_window(
        center_x,
        center_y,
        stoplight_width,
        stoplight_height,
    )

    pole_left = center_x - pole_width / 2
    pole_bottom = center_y - GRID_CELL_HEIGHT * 0.25 - pole_height / 2
    arcade.draw_lbwh_rectangle_filled(
        pole_left,
        pole_bottom,
        pole_width,
        pole_height,
        pole_color,
    )

    housing_left = center_x - housing_width / 2
    housing_bottom = center_y + GRID_CELL_HEIGHT * 0.35 - housing_height / 2
    arcade.draw_lbwh_rectangle_filled(
        housing_left,
        housing_bottom,
        housing_width,
        housing_height,
        housing_color,
    )

    light_offsets = (0.22, 0.0, -0.22)
    light_states = ("red", "yellow", "green")

    for offset, light_state in zip(light_offsets, light_states):
        light_color = active_colors[light_state] if light_state == state else inactive_color
        arcade.draw_circle_filled(
            center_x,
            housing_bottom + housing_height / 2 + (housing_height * offset),
            light_radius,
            light_color,
        )


def build_stoplights():
    """Return the street intersections that should get stoplights."""
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
    """Place stoplights on every third intersection tile."""
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


def draw_route(route):
    """Render the planned route as a thin line over the street grid."""
    if len(route) < 2:
        return

    route_color = (70, 230, 255, 180)
    node_color = (70, 230, 255, 220)

    for start_tile, end_tile in zip(route, route[1:]):
        start_x, start_y = grid_to_center(*start_tile)
        end_x, end_y = grid_to_center(*end_tile)
        arcade.draw_line(start_x, start_y, end_x, end_y, route_color, 4)

    for grid_x, grid_y in route[::4]:
        center_x, center_y = grid_to_center(grid_x, grid_y)
        arcade.draw_circle_filled(center_x, center_y, min(GRID_CELL_WIDTH, GRID_CELL_HEIGHT) * 0.08, node_color)


def draw_timer_graphic(
    seconds_remaining,
    seconds_total=DELIVERY_TIME_LIMIT_SECONDS,
    badge_text=None,
    badge_fill_color=(176, 28, 28, 235),
):
    """Draw the delivery countdown in the top-right corner."""
    panel_width = 230
    panel_height = 72
    margin = 18
    right = WINDOW_WIDTH - margin
    top = WINDOW_HEIGHT - margin
    center_x = right - panel_width / 2
    center_y = top - panel_height / 2
    center_x, center_y = clamp_center_to_window(
        center_x,
        center_y,
        panel_width,
        panel_height,
    )
    left = center_x - panel_width / 2
    bottom = center_y - panel_height / 2

    progress = 0.0 if seconds_total <= 0 else max(0.0, min(1.0, seconds_remaining / seconds_total))
    if progress > 0.5:
        fill_color = arcade.color.LIGHT_GREEN
    elif progress > 0.2:
        fill_color = arcade.color.GOLD
    else:
        fill_color = arcade.color.ORANGE_RED

    icon_x = left + 28
    icon_y = center_y
    arcade.draw_circle_outline(icon_x, icon_y, 15, arcade.color.WHITE, 2)
    arcade.draw_line(icon_x, icon_y, icon_x, icon_y + 7, arcade.color.WHITE, 2)
    arcade.draw_line(icon_x, icon_y, icon_x + 5, icon_y - 3, arcade.color.WHITE, 2)

    bar_left = left + 52
    bar_bottom = bottom + 18
    bar_width = panel_width - 72
    bar_height = 16
    arcade.draw_lbwh_rectangle_filled(
        left,
        bottom,
        panel_width,
        panel_height,
        (20, 24, 34, 210),
    )
    arcade.draw_lbwh_rectangle_outline(
        left,
        bottom,
        panel_width,
        panel_height,
        arcade.color.WHITE,
        2,
    )

    arcade.draw_lbwh_rectangle_filled(
        bar_left,
        bar_bottom,
        bar_width,
        bar_height,
        (255, 255, 255, 45),
    )
    arcade.draw_lbwh_rectangle_filled(
        bar_left,
        bar_bottom,
        bar_width * progress,
        bar_height,
        fill_color,
    )
    arcade.draw_lbwh_rectangle_outline(
        bar_left,
        bar_bottom,
        bar_width,
        bar_height,
        arcade.color.WHITE,
        1,
    )

    time_text = f"{max(0, int(seconds_remaining + 0.999))}s"
    arcade.draw_text(
        time_text,
        left + 52,
        bottom + 38,
        arcade.color.WHITE,
        18,
        bold=True,
    )
    arcade.draw_text(
        "TO DESTINATION",
        left + 52,
        bottom + 18,
        arcade.color.LIGHT_GRAY,
        9,
    )

    if badge_text:
        badge_width = 42
        badge_height = 28
        badge_center_x = left - 10 - badge_width / 2
        badge_center_y = bottom + panel_height / 2
        badge_center_x, badge_center_y = clamp_center_to_window(
            badge_center_x,
            badge_center_y,
            badge_width,
            badge_height,
        )
        badge_left = badge_center_x - badge_width / 2
        badge_bottom = badge_center_y - badge_height / 2

        arcade.draw_lbwh_rectangle_filled(
            badge_left,
            badge_bottom,
            badge_width,
            badge_height,
            badge_fill_color,
        )
        arcade.draw_lbwh_rectangle_outline(
            badge_left,
            badge_bottom,
            badge_width,
            badge_height,
            arcade.color.WHITE,
            2,
        )
        arcade.draw_text(
            badge_text,
            badge_left,
            badge_bottom + 3,
            arcade.color.WHITE,
            18,
            bold=True,
            width=badge_width,
            align="center",
        )


def choose_traffic_obstacle_tile(route, excluded=None, goal_tile=None):
    """Pick a route tile for the traffic obstacle, favoring the middle of the path."""
    excluded = excluded or set()
    if goal_tile is not None and is_corner_tile(goal_tile):
        excluded.update(adjacent_street_tiles(goal_tile))

    if len(route) <= 10:
        return None

    preferred_tiles = [tile for tile in route[10:-1] if tile not in excluded]
    if len(preferred_tiles) >= 3:
        middle_tiles = preferred_tiles[1:-1]
        if middle_tiles:
            preferred_tiles = middle_tiles

    if not preferred_tiles:
        return None

    return random.choice(preferred_tiles)


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

    def set_direction(self):
        self.direction = random.choice(["up", "down", "left", "right"])
        self.angle = direction_to_angle(self.direction, self.facing)

    def sync_to_grid(self):
        center_x, center_y = grid_to_center(self.grid_x, self.grid_y)
        self.center_x, self.center_y = clamp_center_to_window(
            center_x,
            center_y,
            self.width,
            self.height,
        )

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
                (direction, neighbor_x, neighbor_y)
                for direction, neighbor_x, neighbor_y in street_neighbors(self.grid_x, self.grid_y)
                if (neighbor_x, neighbor_y) not in blocked_tiles
                and direction != OPPOSITE_DIRECTION[self.direction]
            ]

            if valid_neighbors:
                candidate_direction, candidate_x, candidate_y = choose_direction_with_turn_bias(
                    self.direction,
                    valid_neighbors,
                )
            else:
                reverse_direction = OPPOSITE_DIRECTION[self.direction]
                reverse_dx, reverse_dy = DIRECTION_DELTAS[reverse_direction]
                reverse_x = self.grid_x + reverse_dx
                reverse_y = self.grid_y + reverse_dy
                if is_street_tile(reverse_x, reverse_y) and (reverse_x, reverse_y) not in blocked_tiles:
                    candidate_direction = reverse_direction
                    candidate_x = reverse_x
                    candidate_y = reverse_y
                else:
                    self.sync_to_grid()
                    return

        if stoplight_lookup is not None and stoplight_timer is not None and self.name in RED_LIGHT_ENTITIES:
            current_state = stoplight_state_for_tile(
                self.grid_x,
                self.grid_y,
                stoplight_lookup,
                stoplight_timer,
            )
            next_state = stoplight_state_for_tile(
                candidate_x,
                candidate_y,
                stoplight_lookup,
                stoplight_timer,
            )
            if current_state == "red" or next_state == "red":
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

        self.sync_to_grid()


class Client(arcade.Sprite):
    """Stationary pedestrian that cycles through chat messages."""

    def __init__(self, config):
        super().__init__(config["texture"], sprite_scale_to_two_tiles(config["texture"]))
        self.name = config["name"]
        self.facing = config["facing"]
        self.grid_x = 0
        self.grid_y = 0
        self.messages = config["messages"]
        self.chat_timer = 0.0
        self.current_index = 0

    def sync_to_grid(self):
        center_x, center_y = grid_to_center(self.grid_x, self.grid_y)
        self.center_x, self.center_y = clamp_center_to_window(
            center_x,
            center_y,
            self.width,
            self.height,
        )

    def update(self, delta_time, *args, **kwargs):
        self.chat_timer += delta_time
        if self.chat_timer >= 5.0:
            self.chat_timer = 0.0
            self.current_index = (self.current_index + 1) % len(self.messages)

    def draw_chat(self):
        arcade.draw_text(
            self.messages[self.current_index],
            self.center_x,
            self.center_y + GRID_CELL_HEIGHT * 0.7,
            arcade.color.WHITE,
            12,
            anchor_x="center",
        )

# Add a Title Card / Instructions Screen
class TitleView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK

    def on_show_view(self):
        arcade.set_background_color(self.background_color)

    def on_draw(self):
        self.clear()

        import math

        # Animated dark gradient background
        arcade.draw_lrbt_rectangle_filled(
            0,
            WINDOW_WIDTH,
            0,
            WINDOW_HEIGHT,
            (8, 10, 20),
        )


        # Neon glow background circles
        for i in range(25):
            x = (i * 97) % WINDOW_WIDTH
            y = (i * 53 + int(self.window.time * 20 if hasattr(self.window, "time") else 0)) % WINDOW_HEIGHT

            arcade.draw_circle_filled(
                x,
                y,
                60 + (i % 4) * 20,
                (40, 140, 255, 18),
            )

    # Animated title glow
        pulse = 1.0 + 0.05 * math.sin(self.window.time * 3)

    # Outer glow
        arcade.draw_text(
            "STABLE TRAFFIC VARIANTS",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT - 150,
            (60, 180, 255, 80),
            int(52 * pulse),
            anchor_x="center",
            bold=True,
        )

    # Main title
        arcade.draw_text(
            "Waymo Simulator",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT - 150,
            arcade.color.WHITE,
            42,
            anchor_x="center",
            bold=True,
        )

    # Subtitle
        arcade.draw_text(
            "By Akio and Oz",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT - 195,
            arcade.color.LIGHT_GRAY,
            18,
            anchor_x="center",
            italic=True,
        )

    # Main instruction panel
        panel_width = 720
        panel_height = 420

        panel_left = WINDOW_WIDTH / 2 - panel_width / 2
        panel_bottom = WINDOW_HEIGHT / 2 - panel_height / 2 - 30

    # Glass panel
        arcade.draw_lbwh_rectangle_filled(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (18, 24, 38, 210),
        )

        arcade.draw_lbwh_rectangle_outline(
            panel_left,
            panel_bottom,
            panel_width,
            panel_height,
            (90, 180, 255),
            3,
        )

        instructions = [
            ("MISSION", arcade.color.YELLOW, 28),
            ("Pick up passengers and deliver them before time runs out.", arcade.color.WHITE, 18),

            ("", arcade.color.WHITE, 18),

            ("CONTROLS", arcade.color.YELLOW, 28),
            ("W  A  S  D   → Move", arcade.color.WHITE, 18),
            ("SPACE        → Stop / Resume", arcade.color.WHITE, 18),

            ("", arcade.color.WHITE, 18),

            ("RULES", arcade.color.YELLOW, 28),
            ("• Avoid moving traffic", arcade.color.WHITE, 18),
            ("• Red lights deduct 2 seconds", arcade.color.WHITE, 18),
            ("• Traffic obstacles deduct 5 seconds", arcade.color.WHITE, 18),

            ("", arcade.color.WHITE, 18),

            ("PRESS ENTER TO START", arcade.color.LIME_GREEN, 26),
        ]

        text_y = panel_bottom + panel_height - 60

        for text, color, size in instructions:
            arcade.draw_text(
                text,
                WINDOW_WIDTH / 2,
                text_y,
                color,
                size,
                anchor_x="center",
                bold=(size >= 26),
            )

            text_y -= 34

    # Decorative moving road lines
        road_y = 70

        for i in range(20):
            offset = (self.window.time* 250) % 80

            x = i * 80 + offset

            arcade.draw_lrbt_rectangle_filled(
                x - 20,
                x + 20,
                road_y - 3,
                road_y + 3,
                arcade.color.GOLD,
            )

    # Bottom hint
        arcade.draw_text(
            "Built with Python + Arcade",
            WINDOW_WIDTH / 2,
            20,
            (160, 160, 160),
            12,
            anchor_x="center",
        )
    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            warning_view = WarningView()
        self.window.show_view(warning_view)

class WarningView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK
        self.animation_time = 0.0

    def on_show_view(self):
        arcade.set_background_color(self.background_color)

    def on_update(self, delta_time):
        self.animation_time += delta_time

    def on_draw(self):
        self.clear()

        import math

        # Background
        arcade.draw_lrbt_rectangle_filled(
            0,
            WINDOW_WIDTH,
            0,
            WINDOW_HEIGHT,
            (15, 8, 8),
        )

        # Pulsing red glow
        glow_radius = 90 + 10 * math.sin(self.animation_time * 2)

        arcade.draw_circle_filled(
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT - 120,
            glow_radius,
            (255, 50, 50, 40),
        )

        # WARNING title
        arcade.draw_text(
            "WARNING",
            WINDOW_WIDTH / 2,
            WINDOW_HEIGHT - 145,
            arcade.color.WHITE,
            48,
            anchor_x="center",
            bold=True,
        )

        # Main warning panel
        panel_width = 860
        panel_height = 320

        left = WINDOW_WIDTH / 2 - panel_width / 2
        bottom = WINDOW_HEIGHT / 2 - panel_height / 2

        arcade.draw_lbwh_rectangle_filled(
            left,
            bottom,
            panel_width,
            panel_height,
            (30, 20, 20, 220),
        )

        arcade.draw_lbwh_rectangle_outline(
            left,
            bottom,
            panel_width,
            panel_height,
            arcade.color.RED,
            4,
        )

        lines = [
            "This game simulates unstable autonomous driving behavior.",
            "",
            "Waymo vehicles may:",
            "• Run red lights",
            "• Crash into moving traffic",
            "• Ignore obstacles",
            "• Behave unpredictably",
            "",
            "Drive carefully and reach the destination before time expires.",
        ]

        start_y = bottom + panel_height - 60

        for i, line in enumerate(lines):

            color = arcade.color.WHITE
            size = 20

            if "Waymo vehicles may" in line:
                color = arcade.color.YELLOW
                size = 24

            if "Run red lights" in line or "Crash into moving traffic" in line:
                color = arcade.color.ORANGE_RED

            arcade.draw_text(
                line,
                WINDOW_WIDTH / 2,
                start_y - i * 32,
                color,
                size,
                anchor_x="center",
            )

        # Flashing continue text
        if int(self.animation_time * 2) % 2 == 0:
            arcade.draw_text(
                "PRESS ENTER TO START",
                WINDOW_WIDTH / 2,
                90,
                arcade.color.YELLOW,
                28,
                anchor_x="center",
                bold=True,
            )

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ENTER:
            game_view = GameView()
            game_view.setup()
            self.window.show_view(game_view)

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.stop_pressed = False
        self.player_grid_x = START_TILE[0]
        self.player_grid_y = START_TILE[1]
        self.player_step_timer = 0.0
        self.stoplight_timer = random.uniform(0.0, STOPLIGHT_PHASE_SECONDS * 2)
        self.time_limit_seconds = DELIVERY_TIME_LIMIT_SECONDS
        self.time_remaining_seconds = DELIVERY_TIME_LIMIT_SECONDS
        self.route = []
        self.route_index = 0
        self.autopilot = True
        self.pending_direction = None
        self.route_goal_tile = GOAL_TILE
        self.client = None
        self.client_picked_up = False
        self.client_list = arcade.SpriteList()
        self.destination_tile = None
        self.destination = None
        self.destination_list = arcade.SpriteList()
        self.traffic_obstacle = None
        self.traffic_obstacle_list = arcade.SpriteList()
        self.traffic_obstacle_tile = None
        self.victory = False
        self.elapsed_seconds = 0.0
        self.hud_badge_timer = 0.0
        self.hud_badge_text = None
        self.hud_badge_fill_color = (176, 28, 28, 235)

    def on_show_view(self):
        arcade.set_background_color(self.background_color)

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()
        self.client_list = arcade.SpriteList()
        self.traffic_obstacle_list = arcade.SpriteList()
        self.destination_tile = None
        self.destination = None
        self.destination_list = arcade.SpriteList()
        self.client = None
        self.client_picked_up = False
        self.route_goal_tile = GOAL_TILE
        self.traffic_obstacle = None
        self.traffic_obstacle_tile = None
        self.victory = False
        self.time_remaining_seconds = self.time_limit_seconds
        self.elapsed_seconds = 0.0
        self.hud_badge_timer = 0.0
        self.hud_badge_text = None
        self.hud_badge_fill_color = (176, 28, 28, 235)

        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            sprite_scale_to_two_tiles("waymo.avif")
        )

        # Always start the player in the bottom-left street tile.
        self.player_grid_x, self.player_grid_y = START_TILE
        player_center_x, player_center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )
        self.player_sprite.center_x, self.player_sprite.center_y = clamp_center_to_window(
            player_center_x,
            player_center_y,
            self.player_sprite.width,
            self.player_sprite.height,
        )
        self.client_list.append(self.client)
        self.client_picked_up = False
        occupied_tiles.add(client_tile)

        self.player_list.append(self.player_sprite)

        player_origin = (self.player_grid_x, self.player_grid_y)

        available_tiles = [
            tile
            for tile in random_street_tiles(excluded={player_origin})
            if route_distance_between_tiles(player_origin, tile) is not None
            and route_distance_between_tiles(player_origin, tile) >= 10
        ]

        for grid_x, grid_y in random.sample(available_tiles, ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)

            entity = MovingEntity(config)
            entity.grid_x, entity.grid_y = grid_x, grid_y
            entity.sync_to_grid()

            self.entity_list.append(entity)

        occupied_tiles = {(self.player_grid_x, self.player_grid_y)}
        occupied_tiles.update((entity.grid_x, entity.grid_y) for entity in self.entity_list)

        client_tile = random.choice(random_street_tiles(excluded=occupied_tiles))
        self.client = Client(CLIENT)
        self.client.grid_x, self.client.grid_y = client_tile
        self.client.sync_to_grid()
        self.client_list.append(self.client)
        self.client_picked_up = False
        occupied_tiles.add(client_tile)
        # Initial guide line leads to the client
        self.route_goal_tile = client_tile
        self.route = shortest_route_between_tiles(
            (self.player_grid_x, self.player_grid_y),
            self.route_goal_tile,
        )
        self.route_index = 0

        if len(self.route) >= 2:
            first_step_x = self.route[1][0] - self.route[0][0]
            first_step_y = self.route[1][1] - self.route[0][1]

            if first_step_x > 0:
                initial_direction = "right"
            elif first_step_x < 0:
                initial_direction = "left"
            elif first_step_y > 0:
                initial_direction = "up"
            else:
                initial_direction = "down"

            self.player_sprite.angle = direction_to_angle(initial_direction, "left")
        else:
            self.player_sprite.angle = direction_to_angle("left", "left")

        self.refresh_route_from_player()
        self.traffic_obstacle_tile = choose_traffic_obstacle_tile(
            self.route,
            excluded=occupied_tiles,
            goal_tile=self.route_goal_tile,
        )
        if self.traffic_obstacle_tile is not None:
            base_scale = sprite_scale_to_two_tiles(TRAFFIC_OBSTACLE_TEXTURE)
            self.traffic_obstacle = arcade.Sprite(
                TRAFFIC_OBSTACLE_TEXTURE,
                base_scale * (TRAFFIC_OBSTACLE_TILE_SIZE / 2),
            )
            obstacle_center_x, obstacle_center_y = grid_to_center(
                *self.traffic_obstacle_tile
            )
            self.traffic_obstacle.center_x, self.traffic_obstacle.center_y = clamp_center_to_window(
                obstacle_center_x,
                obstacle_center_y,
                self.traffic_obstacle.width,
                self.traffic_obstacle.height,
            )
            self.traffic_obstacle_list.append(self.traffic_obstacle)

        self.stoplights = build_stoplights()
        self.stoplight_lookup = build_stoplight_lookup(self.stoplights)
        self.game_over = False

    def refresh_route_from_player(self):
        current_tile = (self.player_grid_x, self.player_grid_y)

        if not self.route:
            self.route = shortest_route_between_tiles(current_tile, self.route_goal_tile)
            self.route_index = 0
            return

        if current_tile in self.route:
            self.route_index = self.route.index(current_tile)
            return

        self.route = shortest_route_between_tiles(current_tile, self.route_goal_tile)
        self.route_index = 0

    def should_show_traffic_obstacle(self):
        if self.traffic_obstacle is None or not self.route:
            return False

        if self.traffic_obstacle_tile not in self.route:
            return False

        obstacle_index = self.route.index(self.traffic_obstacle_tile)
        tiles_until_hit = obstacle_index - self.route_index

        if tiles_until_hit < 0:
            return False

        seconds_until_hit = tiles_until_hit / WAYMO_TILES_PER_SECOND
        return seconds_until_hit <= 2.0

    def advance_route(self):
        if not self.route or self.route_index >= len(self.route) - 1:
            return

        next_tile = self.route[self.route_index + 1]
        current_tile = self.route[self.route_index]
        dx = next_tile[0] - current_tile[0]
        dy = next_tile[1] - current_tile[1]

        self.move_player(dx, dy)
        if (self.player_grid_x, self.player_grid_y) == next_tile:
            self.route_index += 1
        self.refresh_route_from_player()

    def on_draw(self):
        self.clear()

        self.draw_streets()
        draw_route(self.route[self.route_index:])
        draw_stoplights_every_third_intersection(self.stoplights, self.stoplight_timer)

        self.client_list.draw()
        if self.client is not None:
            self.client.draw_chat()

        if self.client_picked_up:
            self.destination_list.draw()

        if self.should_show_traffic_obstacle():
            self.traffic_obstacle_list.draw()

        self.entity_list.draw()
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

        if self.victory:
            arcade.draw_text(
                "VICTORY",
                WINDOW_WIDTH / 2,
                WINDOW_HEIGHT / 2,
                arcade.color.GREEN,
                56,
                anchor_x="center",
                anchor_y="center",
            )

        draw_timer_graphic(
            self.time_remaining_seconds,
            self.time_limit_seconds,
            badge_text=self.hud_badge_text if self.hud_badge_timer > 0.0 else None,
            badge_fill_color=self.hud_badge_fill_color,
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
        # Restart game after game over or victory
        if (self.game_over or self.victory) and key == arcade.key.SPACE:
            self.setup()
            return
        if key == arcade.key.SPACE:
            self.stop_pressed = not self.stop_pressed
            self.player_step_timer = 0.0
            return

        if key == arcade.key.W:
            self.stop_pressed = False
            self.up_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (0, 1)
        elif key == arcade.key.S:
            self.stop_pressed = False
            self.down_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (0, -1)
        elif key == arcade.key.A:
            self.stop_pressed = False
            self.left_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (-1, 0)
        elif key == arcade.key.D:
            self.stop_pressed = False
            self.right_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (1, 0)

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
        current_tile = (self.player_grid_x, self.player_grid_y)
        next_x = self.player_grid_x + dx
        next_y = self.player_grid_y + dy

        if not is_street_tile(next_x, next_y):
            return

        self.player_grid_x = next_x
        self.player_grid_y = next_y
        if dx > 0:
            direction = "right"
        elif dx < 0:
            direction = "left"
        elif dy > 0:
            direction = "up"
        else:
            direction = "down"
        self.player_sprite.angle = direction_to_angle(direction, "left")
        player_center_x, player_center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )
        self.player_sprite.center_x, self.player_sprite.center_y = clamp_center_to_window(
            player_center_x,
            player_center_y,
            self.player_sprite.width,
            self.player_sprite.height,
        )
        self.refresh_route_from_player()

        if self.stoplight_lookup is not None and self.time_remaining_seconds > 0:
            next_tile = (self.player_grid_x, self.player_grid_y)
            current_state = stoplight_state_for_tile(
                current_tile[0],
                current_tile[1],
                self.stoplight_lookup,
                self.stoplight_timer,
            )
            next_state = stoplight_state_for_tile(
                next_tile[0],
                next_tile[1],
                self.stoplight_lookup,
                self.stoplight_timer,
            )
            if current_state == "red" or next_state == "red":
                self.time_remaining_seconds = max(
                    0.0,
                    self.time_remaining_seconds - RED_LIGHT_PENALTY_SECONDS,
                )
                self.hud_badge_text = "-2"
                self.hud_badge_fill_color = (176, 28, 28, 235)
                self.hud_badge_timer = HUD_BADGE_SECONDS
                if self.time_remaining_seconds <= 0.0:
                    self.game_over = True

        if (self.player_grid_x, self.player_grid_y) == self.route_goal_tile:
            self.victory = True

    def start_delivery_route(self):
        self.destination_tile = None
        self.destination = None
        self.destination_list = arcade.SpriteList()

        occupied_tiles = {
            (entity.grid_x, entity.grid_y)
            for entity in self.entity_list
        }
        current_tile = (self.player_grid_x, self.player_grid_y)
        destination_tile = random_destination_tile(current_tile, excluded=occupied_tiles)

        if destination_tile is None:
            # Initial route now leads to the client instead of the final goal
            self.route_goal_tile = client_tile
            self.route = shortest_route_between_tiles(START_TILE, self.route_goal_tile)
            self.route_index = 0
            return

        self.destination_tile = destination_tile
        self.destination = arcade.Sprite(
            DESTINATION_TEXTURE,
            sprite_scale_to_two_tiles(DESTINATION_TEXTURE),
        )
        self.destination.grid_x, self.destination.grid_y = destination_tile
        destination_center_x, destination_center_y = grid_to_center(
            *destination_tile
        )
        self.destination.center_x, self.destination.center_y = clamp_center_to_window(
            destination_center_x,
            destination_center_y,
            self.destination.width,
            self.destination.height,
        )
        self.destination_list.append(self.destination)
        self.route_goal_tile = destination_tile
        self.route = shortest_route_between_tiles(current_tile, self.route_goal_tile)
        self.route_index = 0

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

    def maybe_pick_up_client(self):
        if self.client is None or self.client_picked_up:
            return

        if arcade.check_for_collision(self.player_sprite, self.client):
            if self.elapsed_seconds < CLIENT_BONUS_THRESHOLD_SECONDS:
                self.time_remaining_seconds += CLIENT_BONUS_SECONDS
                self.hud_badge_text = "+3"
                self.hud_badge_fill_color = (34, 139, 34, 235)
                self.hud_badge_timer = HUD_BADGE_SECONDS
            self.client_picked_up = True
            self.client_list = arcade.SpriteList()
            self.client = None
            self.start_delivery_route()

    def on_update(self, delta_time):
        if self.game_over or self.victory:
            return

        self.elapsed_seconds += delta_time
        self.stoplight_timer += delta_time
        occupied_tiles = {
            (entity.grid_x, entity.grid_y)
            for entity in self.entity_list
        }
        for entity in self.entity_list:
            entity.update(delta_time, occupied_tiles, self.stoplight_lookup, self.stoplight_timer)

        if self.client is not None:
            self.client.update(delta_time)

        if self.stop_pressed:
            self.player_step_timer = 0.0
        elif self.autopilot and self.route:
            self.player_step_timer += delta_time
            player_step_interval = 1.0 / WAYMO_TILES_PER_SECOND

            while self.player_step_timer >= player_step_interval:
                self.player_step_timer -= player_step_interval
                move_x, move_y = self.pending_direction or self.get_player_direction()
                if move_x or move_y:
                    self.move_player(move_x, move_y)
                else:
                    self.advance_route()
        else:
            if not (self.up_pressed or self.down_pressed or self.left_pressed or self.right_pressed):
                self.player_step_timer = 0.0
                return

            self.player_step_timer += delta_time
            player_step_interval = 1.0 / WAYMO_TILES_PER_SECOND
            move_x, move_y = self.get_player_direction()

            while self.player_step_timer >= player_step_interval and (move_x or move_y):
                self.player_step_timer -= player_step_interval
                self.move_player(move_x, move_y)
                move_x, move_y = self.get_player_direction()

        self.maybe_pick_up_client()

        if arcade.check_for_collision_with_list(self.player_sprite, self.entity_list):
            self.game_over = True

        if (
            self.traffic_obstacle is not None
            and arcade.check_for_collision(self.player_sprite, self.traffic_obstacle)
        ):
            # Deduct 5 seconds instead of losing instantly
            self.time_remaining_seconds = max(
                0.0,
                self.time_remaining_seconds - 5.0,
            )

            # Show HUD penalty badge
            self.hud_badge_text = "-5"
            self.hud_badge_fill_color = (176, 28, 28, 235)
            self.hud_badge_timer = HUD_BADGE_SECONDS

            # Remove obstacle after hit so it only penalizes once
            self.traffic_obstacle_list.remove(self.traffic_obstacle)
            self.traffic_obstacle = None
            self.traffic_obstacle_tile = None

            # End game only if timer reaches zero
            if self.time_remaining_seconds <= 0.0:
                self.game_over = True

        if self.hud_badge_timer > 0.0:
            self.hud_badge_timer = max(0.0, self.hud_badge_timer - delta_time)

        if not self.victory:
            self.time_remaining_seconds = max(0.0, self.time_remaining_seconds - delta_time)
            if self.time_remaining_seconds <= 0.0:
                self.game_over = True


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)

    title_view = TitleView()
    window.show_view(title_view)

    arcade.run()



if __name__ == "__main__":
    main()

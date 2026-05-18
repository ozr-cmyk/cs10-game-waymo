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


def choose_traffic_obstacle_tile(route, excluded=None):
    """Pick a route tile for the traffic obstacle, favoring the middle of the path."""
    excluded = excluded or set()
    if len(route) < 3:
        return None

    preferred_tiles = [tile for tile in route[1:-1] if tile not in excluded]
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


class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.background_color = arcade.color.BLACK
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.player_grid_x = START_TILE[0]
        self.player_grid_y = START_TILE[1]
        self.player_step_timer = 0.0
        self.stoplight_timer = random.uniform(0.0, STOPLIGHT_PHASE_SECONDS * 2)
        self.route = []
        self.route_index = 0
        self.autopilot = True
        self.pending_direction = None
        self.traffic_obstacle = None
        self.traffic_obstacle_list = arcade.SpriteList()
        self.traffic_obstacle_tile = None

    def on_show_view(self):
        arcade.set_background_color(self.background_color)

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.entity_list = arcade.SpriteList()
        self.traffic_obstacle_list = arcade.SpriteList()
        self.traffic_obstacle = None
        self.traffic_obstacle_tile = None

        self.player_sprite = arcade.Sprite(
            "waymo.avif",
            sprite_scale_to_two_tiles("waymo.avif")
        )

        # Always start the player in the bottom-left street tile.
        self.player_grid_x, self.player_grid_y = START_TILE
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )
        self.route = shortest_route_between_tiles(START_TILE, GOAL_TILE)
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

        self.player_list.append(self.player_sprite)

        available_tiles = random_street_tiles(excluded={(self.player_grid_x, self.player_grid_y)})
        for grid_x, grid_y in random.sample(available_tiles, ENTITY_COUNT):
            config = random.choice(ENTITY_TYPES)

            entity = MovingEntity(config)
            entity.grid_x, entity.grid_y = grid_x, grid_y
            entity.sync_to_grid()

            self.entity_list.append(entity)

        occupied_tiles = {(self.player_grid_x, self.player_grid_y)}
        occupied_tiles.update((entity.grid_x, entity.grid_y) for entity in self.entity_list)
        self.traffic_obstacle_tile = choose_traffic_obstacle_tile(self.route, excluded=occupied_tiles)
        if self.traffic_obstacle_tile is not None:
            base_scale = sprite_scale_to_two_tiles(TRAFFIC_OBSTACLE_TEXTURE)
            self.traffic_obstacle = arcade.Sprite(
                TRAFFIC_OBSTACLE_TEXTURE,
                base_scale * (TRAFFIC_OBSTACLE_TILE_SIZE / 2),
            )
            self.traffic_obstacle.center_x, self.traffic_obstacle.center_y = grid_to_center(
                *self.traffic_obstacle_tile
            )
            self.traffic_obstacle_list.append(self.traffic_obstacle)

        self.stoplights = build_stoplights()
        self.stoplight_lookup = build_stoplight_lookup(self.stoplights)
        self.game_over = False

    def refresh_route_from_player(self):
        current_tile = (self.player_grid_x, self.player_grid_y)

        if not self.route:
            self.route = shortest_route_between_tiles(current_tile, GOAL_TILE)
            self.route_index = 0
            return

        if current_tile in self.route:
            self.route_index = self.route.index(current_tile)
            return

        self.route = shortest_route_between_tiles(current_tile, GOAL_TILE)
        self.route_index = 0

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

        self.traffic_obstacle_list.draw()

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
            self.player_step_timer = 0.0
            self.pending_direction = (0, 1)
        elif key == arcade.key.S:
            self.down_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (0, -1)
        elif key == arcade.key.A:
            self.left_pressed = True
            self.player_step_timer = 0.0
            self.pending_direction = (-1, 0)
        elif key == arcade.key.D:
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
        self.player_sprite.center_x, self.player_sprite.center_y = grid_to_center(
            self.player_grid_x,
            self.player_grid_y,
        )
        self.refresh_route_from_player()

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

        self.stoplight_timer += delta_time
        occupied_tiles = {
            (entity.grid_x, entity.grid_y)
            for entity in self.entity_list
        }
        for entity in self.entity_list:
            entity.update(delta_time, occupied_tiles, self.stoplight_lookup, self.stoplight_timer)

        if self.autopilot and self.route:
            self.player_step_timer += delta_time
            player_step_interval = 1.0 / WAYMO_TILES_PER_SECOND

            while self.player_step_timer >= player_step_interval:
                self.player_step_timer -= player_step_interval
                move_x, move_y = self.pending_direction or self.get_player_direction()
                if move_x or move_y:
                    self.move_player(move_x, move_y)
                    self.pending_direction = None
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

        if arcade.check_for_collision_with_list(self.player_sprite, self.entity_list):
            self.game_over = True

        if self.traffic_obstacle is not None and arcade.check_for_collision(
            self.player_sprite,
            self.traffic_obstacle,
        ):
            self.game_over = True


def main():
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()

import arcade

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "WASD Movement (Arcade)"

PLAYER_SPEED = 5


class MyGame(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)

        self.player = None
        self.scene = None

        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

    def setup(self):
        # Create a sprite list (scene)
        self.scene = arcade.Scene()

        self.player = arcade.Sprite("sinead.jpeg", scale=1.0)
        self.player.center_x = 50
        self.player.center_y = 50

        # Add to scene
        self.scene.add_sprite("Player", self.player)

    def on_draw(self):
        self.clear()
        self.scene.draw()  # <-- draw everything through the scene

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

    def on_update(self, delta_time):
        dx = 0
        dy = 0

        if self.up_pressed:
            dy += PLAYER_SPEED
        if self.down_pressed:
            dy -= PLAYER_SPEED
        if self.left_pressed:
            dx -= PLAYER_SPEED
        if self.right_pressed:
            dx += PLAYER_SPEED

        self.player.center_x += dx
        self.player.center_y += dy


def main():
    game = MyGame()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()

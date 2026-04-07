"""
GUI for Dots and Boxes

"""

import sys

import pygame

from client import GameClient

# -------- CONFIG --------

WIDTH, HEIGHT = 800, 700
BOX_SIZE = 80
MARGIN = 100

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
BLUE = (50, 50, 200)

# ------------------------


class GUI:
    def __init__(self, client):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Dots and Boxes")

        self.client = client

        # Game data
        self.state = None
        self.grid_size = None
        self.player_number = None

        # Connect callbacks
        client.on_assign = self.on_assign
        client.on_start = self.on_start
        client.on_state_update = self.on_update
        client.on_game_over = self.on_game_over

    # -------- CALLBACKS --------

    def on_assign(self, player, grid_size):
        print("Assigned:", player)
        self.player_number = player
        self.grid_size = grid_size

    def on_start(self, state):
        print("Game started")
        self.state = state

    def on_update(self, state):
        self.state = state

    def on_game_over(self, state, winner):
        self.state = state
        print("Winner:", winner)

    # -------- DRAW --------

    def draw(self):
        self.screen.fill(WHITE)

        if self.state is None or self.grid_size is None:
            self.draw_text("Waiting for opponent...", 250, 300)
            pygame.display.flip()
            return

        self.draw_text("DOTS AND BOXES", 250, 20, size=48)

        scores = self.state["scores"]
        self.draw_text(f"P1: {scores['1']}   P2: {scores['2']}", 280, 80)

        turn = self.state["current_turn"]
        self.draw_text(f"Turn: Player {turn}", 300, 120)

        self.draw_board()

        pygame.display.flip()

    def draw_board(self):
        g = self.grid_size
        start_x = MARGIN
        start_y = 150

        # Draw dots
        for r in range(g + 1):
            for c in range(g + 1):
                x = start_x + c * BOX_SIZE
                y = start_y + r * BOX_SIZE
                pygame.draw.circle(self.screen, BLACK, (x, y), 5)

        # Draw horizontal lines
        for r, c in self.state["horizontal_lines"]:
            x1 = start_x + c * BOX_SIZE
            y1 = start_y + r * BOX_SIZE
            x2 = x1 + BOX_SIZE
            pygame.draw.line(self.screen, RED, (x1, y1), (x2, y1), 4)

        # Draw vertical lines
        for r, c in self.state["vertical_lines"]:
            x1 = start_x + c * BOX_SIZE
            y1 = start_y + r * BOX_SIZE
            y2 = y1 + BOX_SIZE
            pygame.draw.line(self.screen, BLUE, (x1, y1), (x1, y2), 4)

    def draw_text(self, text, x, y, size=36):
        font = pygame.font.SysFont(None, size)
        img = font.render(text, True, BLACK)
        self.screen.blit(img, (x, y))

    # -------- INPUT --------

    def handle_click(self, pos):
        if self.state is None:
            return

        if self.state["current_turn"] != self.player_number:
            return

        g = self.grid_size
        start_x = MARGIN
        start_y = 150

        mx, my = pos

        # Horizontal
        for r in range(g + 1):
            for c in range(g):
                rect = pygame.Rect(
                    start_x + c * BOX_SIZE,
                    start_y + r * BOX_SIZE - 5,
                    BOX_SIZE,
                    10,
                )
                if rect.collidepoint(mx, my):
                    self.client.send_move("H", r, c)
                    return

        # Vertical
        for r in range(g):
            for c in range(g + 1):
                rect = pygame.Rect(
                    start_x + c * BOX_SIZE - 5,
                    start_y + r * BOX_SIZE,
                    10,
                    BOX_SIZE,
                )
                if rect.collidepoint(mx, my):
                    self.client.send_move("V", r, c)
                    return

    # -------- MAIN LOOP --------

    def run(self):
        clock = pygame.time.Clock()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(pygame.mouse.get_pos())

            self.draw()
            clock.tick(60)


# -------- RUN --------

if __name__ == "__main__":
    client = GameClient("127.0.0.1", 5050)
    client.connect()

    gui = GUI(client)
    gui.run()

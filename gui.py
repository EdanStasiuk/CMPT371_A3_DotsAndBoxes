"""
gui.py - Dots and Boxes Pygame GUI
CMPT 371 - Assignment 3

A polished graphical interface for the Dots and Boxes game.
Connects to the server via the GameClient class and renders the board
using Pygame. No changes to client.py, server.py, or game_state.py required.

Usage:
    python gui.py [server_ip]

    Defaults to 127.0.0.1 if no IP is provided.

Design aesthetic: Clean dark board with neon dot accents, smooth hover
highlights, and animated box fills. Inspired by arcade/retro-digital boards.

Citations: GenAI (Claude) was used to completely create this Graphical User Interface
as permitted by the Assignment 3 guidelines.
Only minor adjustments were made to make for an exceptional interface design
"""

import sys
import threading
import time

import pygame

from client import GameClient

# ── Networking ────────────────────────────────────────────────────────────────
# Get server IP from command line argument, or use localhost if none provided
HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = 5050

# ── Colours ───────────────────────────────────────────────────────────────────
BG_COLOR = (15, 17, 26)  # Deep navy background
GRID_COLOR = (40, 44, 60)  # Subtle dot/grid colour
DOT_COLOR = (220, 220, 230)  # Bright white dots
LINE_DRAWN_P1 = (80, 200, 255)  # Player 1 edge: electric blue
LINE_DRAWN_P2 = (255, 100, 130)  # Player 2 edge: hot coral
LINE_HOVER = (180, 180, 200)  # Ghost line on hover
BOX_P1 = (80, 200, 255, 55)  # Translucent blue fill
BOX_P2 = (255, 100, 130, 55)  # Translucent coral fill
SCORE_BG_P1 = (20, 50, 80)
SCORE_BG_P2 = (80, 25, 40)
TEXT_COLOR = (220, 220, 230)
DIM_TEXT = (120, 120, 150)
ACCENT_P1 = (80, 200, 255)
ACCENT_P2 = (255, 100, 130)
WIN_OVERLAY = (10, 12, 20, 210)

# ── Layout constants ──────────────────────────────────────────────────────────
WINDOW_W = 820  # width
WINDOW_H = 700  #
BOARD_MARGIN_TOP = 130  # Space above the board for the scoreboard
BOARD_PADDING = 60  # Padding from left/right window edges to board
CELL_SIZE = 100  # Pixels per cell (scales with grid; recalculated)
DOT_RADIUS = 7
LINE_WIDTH = 6
LINE_HIT_WIDTH = 16  # Invisible hit-box width for click detection
DOT_Z = 10  # Dots drawn on top (z-ordering via draw order)

FPS = 60


def compute_layout(grid_size: int):
    """
    Compute board geometry so it always fits the window nicely.

    Returns a dict with:
        cell     - pixel size of one cell
        x0, y0   - pixel coords of top-left dot
        board_px - total pixel width/height of the board
    """
    available_w = WINDOW_W - 2 * BOARD_PADDING
    available_h = WINDOW_H - BOARD_MARGIN_TOP - BOARD_PADDING
    cell = min(available_w // grid_size, available_h // grid_size)
    board_px = cell * grid_size
    x0 = (WINDOW_W - board_px) // 2
    y0 = BOARD_MARGIN_TOP
    return {"cell": cell, "x0": x0, "y0": y0, "board_px": board_px}


def dot_pos(layout, row, col):
    """Return screen (x, y) for the dot at grid position (row, col)."""
    return (
        layout["x0"] + col * layout["cell"],
        layout["y0"] + row * layout["cell"],
    )


def h_line_rect(layout, row, col):
    """
    Return the pygame.Rect of the horizontal edge between dots
    (row, col) and (row, col+1).
    """
    x, y = dot_pos(layout, row, col)
    c = layout["cell"]
    return pygame.Rect(x, y - LINE_HIT_WIDTH // 2, c, LINE_HIT_WIDTH)


def v_line_rect(layout, row, col):
    """
    Return the pygame.Rect of the vertical edge between dots
    (row, col) and (row+1, col).
    """
    x, y = dot_pos(layout, row, col)
    c = layout["cell"]
    return pygame.Rect(x - LINE_HIT_WIDTH // 2, y, LINE_HIT_WIDTH, c)


# ── Box animation helper ──────────────────────────────────────────────────────


class BoxAnimation:
    """Tracks a short fade-in animation when a new box is claimed."""

    DURATION = 0.35  # seconds

    def __init__(self, row, col, player):
        self.row = row
        self.col = col
        self.player = player
        self.start = time.time()

    @property
    def alpha(self):
        """Current alpha 0-55 during fade-in, 55 after complete."""
        elapsed = time.time() - self.start
        t = min(elapsed / self.DURATION, 1.0)
        return int(t * 55)

    @property
    def done(self):
        return time.time() - self.start >= self.DURATION


# ── Main GUI class ────────────────────────────────────────────────────────────


class DotsAndBoxesGUI:
    """
    Pygame-based graphical interface for Dots and Boxes.

    Lifecycle:
        gui = DotsAndBoxesGUI()
        gui.run()   ← blocks until the window is closed
    """

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Dots & Boxes — CMPT 371")
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pygame.time.Clock()

        # ── Fonts ──
        self.font_title = pygame.font.SysFont("Courier New", 28, bold=True)
        self.font_score = pygame.font.SysFont("Courier New", 22, bold=True)
        self.font_status = pygame.font.SysFont("Courier New", 16)
        self.font_big = pygame.font.SysFont("Courier New", 48, bold=True)
        self.font_sub = pygame.font.SysFont("Courier New", 22)

        # ── Network client ──
        self.client = GameClient(HOST, PORT)
        self._register_callbacks()

        # ── Game state (written by network thread, read by render thread) ──
        self.state_lock = threading.Lock()
        self.game_state = None  # Latest state dict from server
        self.player_number = None  # Our player (1 or 2)
        self.grid_size = None
        self.layout = None
        self.game_over = False
        self.winner = None
        self.waiting = True  # True until both players connect
        self.error_msg = ""  # Transient error from server
        self.error_timer = 0.0

        # ── Rendering helpers ──
        self.hover_edge = None  # (orientation, row, col) or None
        self.box_animations = []  # List[BoxAnimation]
        self.known_boxes = {}  # Tracks boxes seen so far for animations

        # ── Connect (non-blocking) ──
        self.client.connect()

    # ── Callback registration ─────────────────────────────────────────────────

    def _register_callbacks(self):
        """Wire GameClient callbacks to GUI state updates."""
        self.client.on_assign = self._on_assign
        self.client.on_start = self._on_start
        self.client.on_state_update = self._on_state_update
        self.client.on_game_over = self._on_game_over
        self.client.on_error = self._on_error

    def _on_assign(self, player, grid_size):
        with self.state_lock:
            self.player_number = player
            self.grid_size = grid_size
            self.layout = compute_layout(grid_size)

    def _on_start(self, state):
        with self.state_lock:
            self.game_state = state
            self.waiting = False

    def _on_state_update(self, state):
        with self.state_lock:
            self._trigger_new_box_animations(state)
            self.game_state = state

    def _on_game_over(self, state, winner):
        with self.state_lock:
            self._trigger_new_box_animations(state)
            self.game_state = state
            self.game_over = True
            self.winner = winner

    def _on_error(self, message):
        with self.state_lock:
            self.error_msg = message
            self.error_timer = time.time()

    def _trigger_new_box_animations(self, new_state):
        """
        Compare new_state's boxes to self.known_boxes and spawn animations
        for any boxes that just appeared. Must be called while holding state_lock.
        """
        new_boxes = new_state.get("boxes", {})
        for key, player in new_boxes.items():
            if key not in self.known_boxes:
                r, c = (int(x) for x in key.split(","))
                self.box_animations.append(BoxAnimation(r, c, player))
        self.known_boxes = dict(new_boxes)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """Main Pygame event + render loop."""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self._update_hover(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            self._draw()

        self.client.disconnect()
        pygame.quit()

    # ── Input helpers ─────────────────────────────────────────────────────────

    def _is_my_turn(self):
        """Return True if the current game state shows it's our turn."""
        if self.game_state is None or self.player_number is None:
            return False
        return self.game_state.get("current_turn") == self.player_number

    def _update_hover(self, mouse_pos):
        """
        Detect which edge (if any) the mouse is hovering over and store it.
        Only highlights edges when it's the local player's turn.
        """
        with self.state_lock:
            if self.layout is None or not self._is_my_turn() or self.game_over:
                self.hover_edge = None
                return
            gs = self.grid_size
            h_lines = set(tuple(e) for e in self.game_state.get("horizontal_lines", []))
            v_lines = set(tuple(e) for e in self.game_state.get("vertical_lines", []))

        # Check horizontal edges
        for row in range(gs + 1):
            for col in range(gs):
                if (row, col) in h_lines:
                    continue
                rect = h_line_rect(self.layout, row, col)
                if rect.collidepoint(mouse_pos):
                    self.hover_edge = ("H", row, col)
                    return

        # Check vertical edges
        for row in range(gs):
            for col in range(gs + 1):
                if (row, col) in v_lines:
                    continue
                rect = v_line_rect(self.layout, row, col)
                if rect.collidepoint(mouse_pos):
                    self.hover_edge = ("V", row, col)
                    return

        self.hover_edge = None

    def _handle_click(self, mouse_pos):
        """Send a move to the server when the player clicks a valid edge."""
        with self.state_lock:
            if (
                self.layout is None
                or not self._is_my_turn()
                or self.game_over
                or self.game_state is None
            ):
                return
            gs = self.grid_size
            h_lines = set(tuple(e) for e in self.game_state.get("horizontal_lines", []))
            v_lines = set(tuple(e) for e in self.game_state.get("vertical_lines", []))

        # Check horizontal edges
        for row in range(gs + 1):
            for col in range(gs):
                if (row, col) in h_lines:
                    continue
                rect = h_line_rect(self.layout, row, col)
                if rect.collidepoint(mouse_pos):
                    self.client.send_move("H", row, col)
                    return

        # Check vertical edges
        for row in range(gs):
            for col in range(gs + 1):
                if (row, col) in v_lines:
                    continue
                rect = v_line_rect(self.layout, row, col)
                if rect.collidepoint(mouse_pos):
                    self.client.send_move("V", row, col)
                    return

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw(self):
        """Master draw call: background → board → UI → overlays."""
        self.screen.fill(BG_COLOR)

        with self.state_lock:
            state = self.game_state
            layout = self.layout
            gs = self.grid_size
            player = self.player_number
            waiting = self.waiting
            game_over = self.game_over
            winner = self.winner
            error_msg = self.error_msg
            error_timer = self.error_timer
            animations = list(self.box_animations)

        # Clean up finished animations (safe outside lock)
        self.box_animations = [a for a in self.box_animations if not a.done]

        if waiting or layout is None:
            self._draw_waiting(player)
        else:
            self._draw_header(state, player, gs)
            self._draw_board(state, layout, gs, animations)
            self._draw_status(state, player, error_msg, error_timer)

        if game_over:
            self._draw_game_over(state, winner, player)

        pygame.display.flip()

    def _draw_waiting(self, player):
        """Shown while waiting for the second player to connect."""
        if player is None:
            msg = "Connecting to server..."
        else:
            msg = f"You are Player {player}"
            msg2 = "Waiting for opponent to join..."
            surf = self.font_score.render(msg2, True, DIM_TEXT)
            self.screen.blit(
                surf,
                surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 40)),
            )

        surf = self.font_title.render(msg, True, TEXT_COLOR)
        self.screen.blit(
            surf,
            surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2)),
        )

        # Animated ellipsis dots
        t = int(time.time() * 2) % 4
        dots = "." * t
        dot_surf = self.font_status.render(dots, True, DIM_TEXT)
        self.screen.blit(
            dot_surf,
            dot_surf.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 80)),
        )

    def _draw_header(self, state, player, gs):
        """Draw scoreboard at the top of the window."""
        # ── Title ──
        title = self.font_title.render("DOTS & BOXES", True, TEXT_COLOR)
        self.screen.blit(title, title.get_rect(center=(WINDOW_W // 2, 28)))

        if state is None:
            return

        scores = state.get("scores", {"1": 0, "2": 0})
        s1 = scores.get("1", scores.get(1, 0))
        s2 = scores.get("2", scores.get(2, 0))
        total = gs * gs
        turn = state.get("current_turn")

        # ── Player 1 score card (left) ──
        p1_rect = pygame.Rect(BOARD_PADDING, 55, 200, 60)
        pygame.draw.rect(self.screen, SCORE_BG_P1, p1_rect, border_radius=8)
        if player == 1:
            pygame.draw.rect(self.screen, ACCENT_P1, p1_rect, width=2, border_radius=8)
        label1 = self.font_score.render(
            f"{'▶ ' if turn == 1 else '  '}P1  {s1}/{total}", True, ACCENT_P1
        )
        self.screen.blit(label1, label1.get_rect(center=p1_rect.center))

        # ── Player 2 score card (right) ──
        p2_rect = pygame.Rect(WINDOW_W - BOARD_PADDING - 200, 55, 200, 60)
        pygame.draw.rect(self.screen, SCORE_BG_P2, p2_rect, border_radius=8)
        if player == 2:
            pygame.draw.rect(self.screen, ACCENT_P2, p2_rect, width=2, border_radius=8)
        label2 = self.font_score.render(
            f"P2  {s2}/{total}{'  ◀' if turn == 2 else '  '}", True, ACCENT_P2
        )
        self.screen.blit(label2, label2.get_rect(center=p2_rect.center))

    def _draw_status(self, state, player, error_msg, error_timer):
        """Draw a status line below the board."""
        if state is None:
            return

        # Transient error message (fades after 3 seconds)
        if error_msg and (time.time() - error_timer) < 3.0:
            fade = 1.0 - (time.time() - error_timer) / 3.0
            alpha = int(255 * fade)
            surf = self.font_status.render(f"⚠ {error_msg}", True, (255, 80, 80))
            surf.set_alpha(alpha)
            self.screen.blit(surf, surf.get_rect(center=(WINDOW_W // 2, WINDOW_H - 22)))
            return

        turn = state.get("current_turn")
        if turn == player:
            msg = "Your turn — click an edge"
            color = ACCENT_P1 if player == 1 else ACCENT_P2
        else:
            msg = f"Player {turn}'s turn..."
            color = DIM_TEXT

        surf = self.font_status.render(msg, True, color)
        self.screen.blit(surf, surf.get_rect(center=(WINDOW_W // 2, WINDOW_H - 22)))

    def _draw_board(self, state, layout, gs, animations):
        """Draw box fills, edges, hover highlight, and dots."""
        if state is None:
            return

        h_lines = set(tuple(e) for e in state.get("horizontal_lines", []))
        v_lines = set(tuple(e) for e in state.get("vertical_lines", []))
        boxes = state.get("boxes", {})
        cell = layout["cell"]

        # ── Box fills (with ongoing animations) ──
        anim_keys = {(a.row, a.col): a for a in animations}

        # Draw settled boxes
        box_surf = pygame.Surface((cell - 4, cell - 4), pygame.SRCALPHA)
        for key, player in boxes.items():
            r, c = (int(x) for x in key.split(","))
            if (r, c) in anim_keys:
                continue  # Still animating; drawn below
            color = (
                (*LINE_DRAWN_P1[:3], 55) if player == 1 else (*LINE_DRAWN_P2[:3], 55)
            )
            box_surf.fill(color)
            x, y = dot_pos(layout, r, c)
            self.screen.blit(box_surf, (x + 2, y + 2))

        # Draw animating boxes
        for anim in animations:
            alpha = anim.alpha
            anim_box = pygame.Surface((cell - 4, cell - 4), pygame.SRCALPHA)
            base = LINE_DRAWN_P1[:3] if anim.player == 1 else LINE_DRAWN_P2[:3]
            anim_box.fill((*base, alpha))
            x, y = dot_pos(layout, anim.row, anim.col)
            self.screen.blit(anim_box, (x + 2, y + 2))

        # ── Box owner labels (P1 / P2) ──
        for key, player in boxes.items():
            r, c = (int(x) for x in key.split(","))
            color = ACCENT_P1 if player == 1 else ACCENT_P2
            label = self.font_status.render(f"P{player}", True, color)
            x, y = dot_pos(layout, r, c)
            cx = x + cell // 2
            cy = y + cell // 2
            self.screen.blit(label, label.get_rect(center=(cx, cy)))

        # ── Hover ghost edge ──
        if self.hover_edge:
            orient, hr, hc = self.hover_edge
            if orient == "H":
                x1, y1 = dot_pos(layout, hr, hc)
                x2, y2 = dot_pos(layout, hr, hc + 1)
            else:
                x1, y1 = dot_pos(layout, hr, hc)
                x2, y2 = dot_pos(layout, hr + 1, hc)
            pygame.draw.line(self.screen, LINE_HOVER, (x1, y1), (x2, y2), LINE_WIDTH)

        # ── Drawn horizontal edges ──
        for row, col in h_lines:
            player_who = self._edge_owner(boxes, "H", row, col, gs)
            color = LINE_DRAWN_P1 if player_who == 1 else LINE_DRAWN_P2
            x1, y1 = dot_pos(layout, row, col)
            x2, y2 = dot_pos(layout, row, col + 1)
            pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), LINE_WIDTH)

        # ── Drawn vertical edges ──
        for row, col in v_lines:
            player_who = self._edge_owner(boxes, "V", row, col, gs)
            color = LINE_DRAWN_P1 if player_who == 1 else LINE_DRAWN_P2
            x1, y1 = dot_pos(layout, row, col)
            x2, y2 = dot_pos(layout, row + 1, col)
            pygame.draw.line(self.screen, color, (x1, y1), (x2, y2), LINE_WIDTH)

        # ── Dots (drawn last, always on top) ──
        for row in range(gs + 1):
            for col in range(gs + 1):
                x, y = dot_pos(layout, row, col)
                pygame.draw.circle(self.screen, DOT_COLOR, (x, y), DOT_RADIUS)

    def _edge_owner(self, boxes, orient, row, col, gs):
        """
        Determine which player drew a specific edge by checking adjacent boxes.
        Falls back to player 1 if unable to determine (visual fallback only).

        This is a best-effort heuristic for coloring edges — the authoritative
        owner is stored server-side.
        """
        if orient == "H":
            candidates = [(row - 1, col), (row, col)]
        else:
            candidates = [(row, col - 1), (row, col)]

        for br, bc in candidates:
            if 0 <= br < gs and 0 <= bc < gs:
                key = f"{br},{bc}"
                if key in boxes:
                    return boxes[key]
        return 1  # Default colour (visual fallback)

    def _draw_game_over(self, state, winner, player):
        """Draw a semi-transparent overlay announcing the game result."""
        overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
        overlay.fill(WIN_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        if winner == "tie":
            headline = "IT'S A TIE!"
            color = TEXT_COLOR
        elif winner == player:
            headline = "YOU WIN!"
            color = ACCENT_P1 if player == 1 else ACCENT_P2
        else:
            headline = "YOU LOSE"
            color = DIM_TEXT

        big = self.font_big.render(headline, True, color)
        self.screen.blit(big, big.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 - 40)))

        if state:
            scores = state.get("scores", {})
            s1 = scores.get("1", scores.get(1, 0))
            s2 = scores.get("2", scores.get(2, 0))
            sub_text = f"Final score — P1: {s1}  |  P2: {s2}"
        else:
            sub_text = ""

        sub = self.font_sub.render(sub_text, True, DIM_TEXT)
        self.screen.blit(sub, sub.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 30)))

        hint = self.font_status.render("Press ESC to exit", True, DIM_TEXT)
        self.screen.blit(
            hint, hint.get_rect(center=(WINDOW_W // 2, WINDOW_H // 2 + 80))
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    gui = DotsAndBoxesGUI()
    gui.run()

# This GUI was created with the assistance of GenAI (Claude) as permitted by the Assignment 3 guidelines.
# Only minor adjustments were made to make for an exceptional interface design.

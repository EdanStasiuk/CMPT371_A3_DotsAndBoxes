"""
game_state.py - Dots and Boxes Game State
CMPT 371 - Assignment 3

Contains the GameState class which manages all game logic:
  - Tracking drawn edges (horizontal and vertical)
  - Detecting completed boxes
  - Scoring and turn management
  - Serialization for sending over the network

Both the server (authoritative) and client (for local rendering)
can import this module.
"""

from __future__ import annotations

from typing import Any


class GameState:
    """
    Holds the complete state of a Dots and Boxes game.

    The board is represented as two sets of edges:
      - horizontal_lines: set of (row, col) where row in 0..grid_size,
                                                   col in 0..grid_size-1
      - vertical_lines:   set of (row, col) where row in 0..grid_size-1,
                                                   col in 0..grid_size

    A box at (row, col) is complete when all 4 of its edges are drawn:
      top    = horizontal (row,   col)
      bottom = horizontal (row+1, col)
      left   = vertical   (row,   col)
      right  = vertical   (row,   col+1)
    """

    def __init__(self, grid_size: int) -> None:
        self.grid_size: int = grid_size
        self.horizontal_lines: set[tuple[int, int]] = (
            set()
        )  # (row, col) pairs for horizontal edges
        self.vertical_lines: set[tuple[int, int]] = (
            set()
        )  # (row, col) pairs for vertical edges
        self.boxes: dict[tuple[int, int], int] = (
            {}
        )  # (row, col) -> player number (1 or 2)
        self.scores: dict[int, int] = {1: 0, 2: 0}
        self.current_turn: int = 1  # Player 1 goes first

    def apply_move(self, move: dict[str, Any]) -> int:
        """
        Apply a move to the game state.

        Args:
            move (dict): {
                "orientation": "H" or "V",
                "row": int,
                "col": int
            }

        Returns:
            int: Number of new boxes claimed by this move (0 or more).
                 If > 0, the same player gets another turn.
                 Returns -1 if the move is invalid (edge already drawn).
        """
        orientation = move["orientation"]
        row = move["row"]
        col = move["col"]

        # Validate the edge hasn't already been drawn
        if orientation == "H":
            if (row, col) in self.horizontal_lines:
                return -1  # Invalid: already drawn
            self.horizontal_lines.add((row, col))
        else:  # "V"
            if (row, col) in self.vertical_lines:
                return -1  # Invalid: already drawn
            self.vertical_lines.add((row, col))

        # Check if any new boxes were completed by this move
        new_boxes = self._check_new_boxes(orientation, row, col)

        # Award boxes to the current player
        for box in new_boxes:
            self.boxes[box] = self.current_turn
            self.scores[self.current_turn] += 1

        # Switch turns only if no new boxes were claimed
        if len(new_boxes) == 0:
            self.current_turn = 2 if self.current_turn == 1 else 1

        return len(new_boxes)

    def _check_new_boxes(
        self, orientation: str, row: int, col: int
    ) -> list[tuple[int, int]]:
        """
        After placing an edge, determine which adjacent boxes (if any) are now complete.

        A horizontal edge at (row, col) borders:
          - The box above: (row-1, col)
          - The box below: (row,   col)

        A vertical edge at (row, col) borders:
          - The box to the left:  (row, col-1)
          - The box to the right: (row, col)

        Returns:
            list of (row, col) tuples for newly completed boxes.
        """
        completed = []

        if orientation == "H":
            candidates = [(row - 1, col), (row, col)]
        else:  # "V"
            candidates = [(row, col - 1), (row, col)]

        for br, bc in candidates:
            if self._is_valid_box(br, bc) and self._is_box_complete(br, bc):
                completed.append((br, bc))

        return completed

    def _is_valid_box(self, row: int, col: int) -> bool:
        """Check if (row, col) is within the grid bounds."""
        return 0 <= row < self.grid_size and 0 <= col < self.grid_size

    def _is_box_complete(self, row: int, col: int) -> bool:
        """Check if the box at (row, col) has all 4 edges drawn."""
        top = (row, col) in self.horizontal_lines
        bottom = (row + 1, col) in self.horizontal_lines
        left = (row, col) in self.vertical_lines
        right = (row, col + 1) in self.vertical_lines
        return top and bottom and left and right

    def is_game_over(self) -> bool:
        """The game ends when all boxes have been claimed."""
        return len(self.boxes) == self.grid_size * self.grid_size

    def get_winner(self) -> int | str:
        """
        Returns:
            int or str: 1, 2, or "tie"
        """
        if self.scores[1] > self.scores[2]:
            return 1
        if self.scores[2] > self.scores[1]:
            return 2
        return "tie"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full game state to a JSON-safe dict for broadcasting."""
        return {
            "horizontal_lines": list(self.horizontal_lines),
            "vertical_lines": list(self.vertical_lines),
            "boxes": {f"{r},{c}": p for (r, c), p in self.boxes.items()},
            "scores": self.scores,
            "current_turn": self.current_turn,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        """
        Reconstruct a GameState from a dict received over the network.
        Useful for the client to maintain a local copy of the state.

        Args:
            data (dict): A dict previously produced by to_dict(), plus "grid_size".

        Returns:
            GameState
        """
        state = cls(data["grid_size"])
        state.horizontal_lines = set(tuple(e) for e in data["horizontal_lines"])
        state.vertical_lines = set(tuple(e) for e in data["vertical_lines"])
        state.boxes = {
            tuple(int(x) for x in k.split(",")): v for k, v in data["boxes"].items()
        }
        state.scores = {int(k): v for k, v in data["scores"].items()}
        state.current_turn = data["current_turn"]
        return state

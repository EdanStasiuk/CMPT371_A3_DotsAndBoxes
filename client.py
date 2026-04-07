"""
client.py - Dots and Boxes TCP Client
CMPT 371 - Assignment 3

The client connects to the server, receives game state updates, and sends
moves on behalf of the local player. It is designed to be GUI-agnostic:
the GameClient class communicates via callbacks so your GUI layer can
simply register handlers and call send_move() without touching sockets.

Architecture: Client-Server (TCP)
  - Client connects to the server by IP and port
  - Receives: "assign", "start", "state_update", "game_over", "error"
  - Sends:    move messages when it's the local player's turn
"""

import json
import socket
import sys
import threading
from typing import Callable

# ---- Configuration -------------------------

HOST = "127.0.0.1"  # Default to localhost; override via command-line arg
PORT = 5050

# ---- Client --------------------------------


class GameClient:
    """
    Manages the TCP connection to the Dots and Boxes server.

    GUI Integration:
        Register callbacks before calling connect():
            client.on_assign       = lambda player, grid_size: ...
            client.on_start        = lambda state: ...
            client.on_state_update = lambda state: ...
            client.on_game_over    = lambda state, winner: ...
            client.on_error        = lambda message: ...

        To send a move:
            client.send_move("H", row, col)  # horizontal edge
            client.send_move("V", row, col)  # vertical edge

    All callbacks are invoked from the receiver thread.
    """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

        # Local state mirrored from the server
        self.player_number = None  # 1 or 2, assigned by server
        self.grid_size = None
        self.game_state = None  # Latest state dict from server

        # Callbacks
        # fmt: off
        self.on_assign:       Callable[[int, int], None] | None = None
        self.on_start:        Callable[[dict], None] | None = None
        self.on_state_update: Callable[[dict], None] | None = None
        self.on_game_over:    Callable[[dict, int | str], None] | None = None
        self.on_error:        Callable[[str], None] | None = None
        # fmt: on

    def connect(self):
        """
        Establish a TCP connection to the server and start the receiver thread.
        Blocks until the connection is made, then returns immediately.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"[CLIENT] Connected to server at {self.host}:{self.port}")

        # Start background thread to listen for server messages
        recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        recv_thread.start()

    def send_move(self, orientation, row, col):
        """
        Send a move to the server.

        Args:
            orientation (str): "H" for horizontal, "V" for vertical.
            row (int): Row index of the edge.
            col (int): Column index of the edge.

        Edge coordinate system:
            Horizontal edge (row, col): the top edge of box (row, col),
                                        bottom edge of box (row-1, col).
            Vertical edge   (row, col): the left edge of box (row, col),
                                        right edge of box (row, col-1).

            row and col for horizontal: row in 0..grid_size, col in 0..grid_size-1
            row and col for vertical:   row in 0..grid_size-1, col in 0..grid_size
        """
        self._send(
            {
                "type": "move",
                "move": {"orientation": orientation, "row": row, "col": col},
            }
        )

    def disconnect(self):
        """Close the connection to the server."""
        if self.sock:
            self.sock.close()
            print("[CLIENT] Disconnected from server.")

    # ---- Internal Functions ---------------

    def _receive_loop(self):
        """
        Continuously read messages from the server and dispatch to callbacks.
        Runs in a background thread.
        """
        while True:
            data = self._recv()
            if data is None:
                print("[CLIENT] Connection to server lost.")
                break
            self._handle_message(data)

    def _handle_message(self, data):
        """
        Route an incoming server message to the appropriate callback.

        Message types:
            assign       - Server assigns player number and grid size.
            start        - Both players connected; game begins.
            state_update - A move was made; here's the new state.
            game_over    - All boxes filled; here's the final state and winner.
            error        - Something went wrong (invalid move, wrong turn, etc.)
        """
        msg_type = data.get("type")

        if msg_type == "assign":
            self.player_number = data["player"]
            self.grid_size = data["grid_size"]
            print(
                f"[CLIENT] Assigned as Player {self.player_number} "
                f"on a {self.grid_size}x{self.grid_size} grid."
            )
            if self.on_assign is not None:
                self.on_assign(self.player_number, self.grid_size)

        elif msg_type == "start":
            self.game_state = data["state"]
            print("[CLIENT] Game started!")
            if self.on_start is not None:
                self.on_start(self.game_state)

        elif msg_type == "state_update":
            self.game_state = data["state"]
            current = self.game_state["current_turn"]
            print(f"[CLIENT] State updated. It's Player {current}'s turn.")
            if self.on_state_update is not None:
                self.on_state_update(self.game_state)

        elif msg_type == "game_over":
            self.game_state = data["state"]
            winner = data["winner"]
            print(f"[CLIENT] Game over! Winner: {winner}")
            if self.on_game_over is not None:
                self.on_game_over(self.game_state, winner)

        elif msg_type == "error":
            message = data.get("message", "Unknown error.")
            print(f"[CLIENT] Server error: {message}")
            if self.on_error is not None:
                self.on_error(message)

        else:
            print(f"[CLIENT] Unknown message type: {msg_type}")

    def _send(self, data):
        """
        Send a JSON-encoded, length-prefixed message to the server.
        Length prefix is 4 bytes big-endian.
        """
        try:
            payload = json.dumps(data).encode("utf-8")
            length = len(payload).to_bytes(4, byteorder="big")
            self.sock.sendall(length + payload)
        except Exception as e:
            print(f"[CLIENT] Send error: {e}")

    def _recv(self):
        """
        Receive a length-prefixed JSON message from the server.

        Returns:
            dict or None if the connection was closed.
        """
        try:
            raw_len = self._recv_exact(4)
            if raw_len is None:
                return None
            msg_len = int.from_bytes(raw_len, byteorder="big")

            raw_data = self._recv_exact(msg_len)
            if raw_data is None:
                return None

            return json.loads(raw_data.decode("utf-8"))
        except Exception as e:
            print(f"[CLIENT] Recv error: {e}")
            return None

    def _recv_exact(self, num_bytes):
        """
        Read exactly num_bytes from the socket, handling partial TCP reads.

        Returns:
            bytes or None if the connection closed mid-read.
        """
        buf = b""
        while len(buf) < num_bytes:
            chunk = self.sock.recv(num_bytes - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf


# ---- Entry Point --------------------------

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else HOST
    client = GameClient(host, PORT)
    client.connect()

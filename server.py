"""
server.py - Dots and Boxes TCP Server
CMPT 371 - Assignment 3

The server manages the game state and acts as the authority for all moves.
It accepts exactly 2 clients, assigns them player numbers, and relays moves
between them while enforcing turn order and win detection.

Architecture: Client-Server (TCP)
  - Server listens for 2 incoming connections
  - Once both players are connected, the game begins
  - Players alternate sending moves; server validates and broadcasts state
  - Server detects game over and announces the winner

Documentation and inline comments were supplemented with the assistance of generative AI (Claude).
"""

import json
import socket
import threading
from typing import Any

from game_state import GameState

# ---- Configuration ------------------------

HOST = "0.0.0.0"  # Listen on all available interfaces
PORT = 5050  # Port clients will connect to
GRID_SIZE = 4  # Number of boxes per row/column (4x4 = 16 boxes total)

# ---- Server --------------------------------


class DotsAndBoxesServer:
    """
    TCP server that manages a 2-player Dots and Boxes game.

    Flow:
      1. Wait for 2 clients to connect.
      2. Send each client their player number.
      3. Receive moves from the active player, validate them, update state.
      4. Broadcast the updated state to both players.
      5. On game over, broadcast the result and close connections.
    """

    def __init__(self, host: str, port: int, grid_size: int) -> None:
        self.host: str = host
        self.port: int = port
        self.game: GameState = GameState(grid_size)
        self.clients: dict[int, socket.socket] = {}  # player_number (1 or 2) -> socket
        self.lock: threading.Lock = threading.Lock()

    def start(self) -> None:
        """Bind, listen, and wait for exactly 2 clients before starting the game."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Allow reuse of the address immediately after server restarts
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(2)

        print(f"[SERVER] Listening on {self.host}:{self.port}")
        print("[SERVER] Waiting for 2 players...")

        player_num = 1
        while len(self.clients) < 2:
            conn, addr = server_socket.accept()
            self.clients[player_num] = conn
            print(f"[SERVER] Player {player_num} connected from {addr}")

            # Immediately tell the client which player they are
            self._send(
                conn,
                {
                    "type": "assign",
                    "player": player_num,
                    "grid_size": self.game.grid_size,
                },
            )

            player_num += 1

        print("[SERVER] Both players connected. Starting game!")
        self._broadcast({"type": "start", "state": self.game.to_dict()})

        # Handle each client in its own thread
        threads = []
        for pnum, conn in self.clients.items():
            t = threading.Thread(target=self._handle_client, args=(pnum, conn))
            t.daemon = True
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        server_socket.close()
        print("[SERVER] Game over. Server shutting down.")

    def _handle_client(self, player_num: int, conn: socket.socket) -> None:
        """
        Listen for moves from a specific client.
        Only processes moves when it's that player's turn.
        """
        print(f"[SERVER] Listening for moves from Player {player_num}")

        while True:
            try:
                data = self._recv(conn)
                if data is None:
                    print(f"[SERVER] Player {player_num} disconnected.")
                    self._broadcast(
                        {
                            "type": "error",
                            "message": f"Player {player_num} disconnected. Game aborted.",
                        }
                    )
                    break

                if data.get("type") == "move":
                    self._process_move(player_num, data["move"])

            except Exception as e:
                print(f"[SERVER] Error with Player {player_num}: {e}")
                break

    def _process_move(self, player_num: int, move: dict[str, Any]) -> None:
        """
        Validate and apply a move, then broadcast the updated state.
        Ignore the move if it's not the sender's turn.
        """
        with self.lock:
            if self.game.current_turn != player_num:
                # Not this player's turn — send them a rejection
                self._send(
                    self.clients[player_num],
                    {"type": "error", "message": "It's not your turn."},
                )
                return

            result = self.game.apply_move(move)

            if result == -1:
                # Move was invalid (edge already drawn)
                self._send(
                    self.clients[player_num],
                    {"type": "error", "message": "Invalid move: edge already drawn."},
                )
                return

            print(
                f"[SERVER] Player {player_num} played {move}. Boxes claimed: {result}"
            )

            if self.game.is_game_over():
                winner = self.game.get_winner()
                self._broadcast(
                    {
                        "type": "game_over",
                        "state": self.game.to_dict(),
                        "winner": winner,
                    }
                )
                print(f"[SERVER] Game over! Winner: {winner}")
            else:
                self._broadcast({"type": "state_update", "state": self.game.to_dict()})

    def _send(self, conn: socket.socket, data: dict[str, Any]) -> None:
        """
        Send a JSON-encoded message to a single client.
        Messages are length-prefixed (4 bytes) to handle TCP stream boundaries.
        """
        try:
            payload = json.dumps(data).encode("utf-8")
            length = len(payload).to_bytes(4, byteorder="big")
            conn.sendall(length + payload)
        except Exception as e:
            print(f"[SERVER] Send error: {e}")

    def _recv(self, conn: socket.socket) -> dict[str, Any] | None:
        """
        Receive a length-prefixed JSON message from a client.

        Returns:
            dict or None if the connection was closed.
        """
        try:
            # Read the 4-byte length header first
            raw_len = self._recv_exact(conn, 4)
            if raw_len is None:
                return None
            msg_len = int.from_bytes(raw_len, byteorder="big")

            # Read exactly msg_len bytes for the payload
            raw_data = self._recv_exact(conn, msg_len)
            if raw_data is None:
                return None

            return json.loads(raw_data.decode("utf-8"))
        except Exception as e:
            print(f"[SERVER] Recv error: {e}")
            return None

    def _recv_exact(self, conn, num_bytes):
        """
        Read exactly num_bytes from the socket, handling partial reads.

        Returns:
            bytes or None if the connection closed mid-read.
        """
        buf = b""
        while len(buf) < num_bytes:
            chunk = conn.recv(num_bytes - len(buf))
            if not chunk:
                return None
            buf += chunk
        return buf

    def _broadcast(self, data):
        """Send the same message to both connected clients."""
        for conn in self.clients.values():
            self._send(conn, data)


if __name__ == "__main__":
    server = DotsAndBoxesServer(HOST, PORT, GRID_SIZE)
    server.start()

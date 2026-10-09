"""
server.py
=========
High-Performance, Zero-Dependency HTTP Server for Minesweeper.

Uses Python's standard library `http.server.ThreadingHTTPServer` so that:
- Runs instantly on ANY computer without installing any external packages!
- Serves static frontend files (HTML5, CSS3, Vanilla JS).
- Provides RESTful JSON API for game engine operations and database persistence.
"""

import os
import sys
import json
import uuid
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict

from game_engine import MinesweeperGame
from database import DatabaseManager

PORT = int(os.environ.get("PORT", 8000))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# In-memory dictionary of active game sessions: session_id -> MinesweeperGame
sessions: Dict[str, MinesweeperGame] = {}
db = DatabaseManager()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handles requests in separate threads for non-blocking concurrent access."""
    daemon_threads = True


class MinesweeperHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the static frontend and the REST API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data: dict, status_code: int = 200) -> None:
        """Sends a JSON response with appropriate headers and status code."""
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self) -> None:
        """Handles CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handles GET requests (API endpoints and static frontend files)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 1. API: New Game
        if path == "/api/game/new":
            difficulty = query_params.get("difficulty", ["beginner"])[0]
            rows = int(query_params.get("rows", [9])[0])
            cols = int(query_params.get("cols", [9])[0])
            mines = int(query_params.get("mines", [10])[0])

            session_id = str(uuid.uuid4())
            game = MinesweeperGame(difficulty=difficulty, rows=rows, cols=cols, mines=mines)
            sessions[session_id] = game

            state = game.get_state()
            state["sessionId"] = session_id
            self._send_json(state)
            return

        # 2. API: Get Game State
        if path == "/api/game/state":
            session_id = query_params.get("sessionId", [""])[0]
            game = sessions.get(session_id)
            if not game:
                self._send_json({"error": "Session not found"}, 404)
                return
            state = game.get_state()
            state["sessionId"] = session_id
            self._send_json(state)
            return

        # 3. API: Logical Deduction Hint
        if path == "/api/game/hint":
            session_id = query_params.get("sessionId", [""])[0]
            game = sessions.get(session_id)
            if not game:
                self._send_json({"error": "Session not found"}, 404)
                return
            hint = game.get_hint()
            self._send_json(hint)
            return

        # 4. API: Leaderboard
        if path == "/api/leaderboard":
            difficulty = query_params.get("difficulty", ["beginner"])[0]
            limit = int(query_params.get("limit", [10])[0])
            scores = db.get_leaderboard(difficulty=difficulty, limit=limit)
            self._send_json({"difficulty": difficulty, "leaderboard": scores})
            return

        # 5. API: Overall Statistics
        if path == "/api/stats":
            stats = db.get_statistics()
            self._send_json(stats)
            return

        # Fallback to serving static files (index.html, style.css, app.js)
        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        """Handles POST requests (revealing cells, toggling flags, saving scores)."""
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length)
        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        # 1. API: Reveal Cell
        if path == "/api/game/reveal":
            session_id = body.get("sessionId")
            game = sessions.get(session_id)
            if not game:
                self._send_json({"error": "Session not found"}, 404)
                return

            row = int(body.get("row", 0))
            col = int(body.get("col", 0))
            new_state = game.reveal(row, col)
            new_state["sessionId"] = session_id
            self._send_json(new_state)
            return

        # 2. API: Toggle Flag
        if path == "/api/game/flag":
            session_id = body.get("sessionId")
            game = sessions.get(session_id)
            if not game:
                self._send_json({"error": "Session not found"}, 404)
                return

            row = int(body.get("row", 0))
            col = int(body.get("col", 0))
            new_state = game.toggle_flag(row, col)
            new_state["sessionId"] = session_id
            self._send_json(new_state)
            return

        # 3. API: Save Score / Record Game
        if path == "/api/scores":
            player_name = body.get("player_name", "Anonymous")
            difficulty = body.get("difficulty", "beginner")
            time_seconds = int(body.get("time_seconds", 0))
            won = bool(body.get("won", False))
            moves_count = int(body.get("moves_count", 0))

            saved_record = db.record_game(
                player_name=player_name,
                difficulty=difficulty,
                time_seconds=time_seconds,
                won=won,
                moves_count=moves_count,
            )
            # Return updated leaderboard
            updated_leaderboard = db.get_leaderboard(difficulty=difficulty, limit=10)
            self._send_json({
                "saved": saved_record,
                "leaderboard": updated_leaderboard,
            })
            return

        self._send_json({"error": "Endpoint not found"}, 404)


def run_server(port: int = PORT) -> None:
    """Starts the multi-threaded HTTP server with port fallback."""
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ("0.0.0.0", port)
    max_tries = 10
    httpd = None

    for p in range(port, port + max_tries):
        try:
            server_address = ("0.0.0.0", p)
            httpd = ThreadedHTTPServer(server_address, MinesweeperHandler)
            port = p
            break
        except OSError as e:
            if p == port + max_tries - 1:
                raise e
            continue

    print(f"=================================================")
    print(f" Minesweeper Server with Discrete Mathematics Engine")
    print(f" Running at: http://localhost:{port}")
    print(f" Static files served from: {STATIC_DIR}")
    print(f" Database: SQLite ({db.db_path})")
    print(f"=================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()

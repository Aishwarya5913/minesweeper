"""
app.py
======
Production-ready Flask application for Minesweeper.

Compatible with Gunicorn, Render, Railway, Vercel, and PythonAnywhere.
Delegates to the Discrete Mathematics Engine (discrete_math.py), Game Engine
(game_engine.py), and Database Layer (database.py).
"""

import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from game_engine import MinesweeperGame
from database import DatabaseManager

app = Flask(__name__, static_folder="static", static_url_path="")

# In-memory dictionary of active game sessions: session_id -> MinesweeperGame
sessions = {}
db = DatabaseManager()


@app.route("/")
def index():
    """Serves the main game page."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/game/new", methods=["GET"])
def api_new_game():
    """Initializes a new game session."""
    difficulty = request.args.get("difficulty", "beginner")
    rows = int(request.args.get("rows", 9))
    cols = int(request.args.get("cols", 9))
    mines = int(request.args.get("mines", 10))

    session_id = str(uuid.uuid4())
    game = MinesweeperGame(difficulty=difficulty, rows=rows, cols=cols, mines=mines)
    sessions[session_id] = game

    state = game.get_state()
    state["sessionId"] = session_id
    return jsonify(state)


@app.route("/api/game/state", methods=["GET"])
def api_game_state():
    """Retrieves current game state."""
    session_id = request.args.get("sessionId", "")
    game = sessions.get(session_id)
    if not game:
        return jsonify({"error": "Session not found"}), 404

    state = game.get_state()
    state["sessionId"] = session_id
    return jsonify(state)


@app.route("/api/game/reveal", methods=["POST"])
def api_reveal():
    """Reveals a cell."""
    data = request.get_json() or {}
    session_id = data.get("sessionId")
    game = sessions.get(session_id)
    if not game:
        return jsonify({"error": "Session not found"}), 404

    row = int(data.get("row", 0))
    col = int(data.get("col", 0))
    state = game.reveal(row, col)
    state["sessionId"] = session_id
    return jsonify(state)


@app.route("/api/game/flag", methods=["POST"])
def api_flag():
    """Toggles a flag on a cell."""
    data = request.get_json() or {}
    session_id = data.get("sessionId")
    game = sessions.get(session_id)
    if not game:
        return jsonify({"error": "Session not found"}), 404

    row = int(data.get("row", 0))
    col = int(data.get("col", 0))
    state = game.toggle_flag(row, col)
    state["sessionId"] = session_id
    return jsonify(state)


@app.route("/api/game/hint", methods=["GET"])
def api_hint():
    """Returns discrete-math propositional logic deduction hint."""
    session_id = request.args.get("sessionId", "")
    game = sessions.get(session_id)
    if not game:
        return jsonify({"error": "Session not found"}), 404

    hint = game.get_hint()
    return jsonify(hint)


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    """Retrieves top 10 completion times."""
    difficulty = request.args.get("difficulty", "beginner")
    limit = int(request.args.get("limit", 10))
    leaderboard = db.get_leaderboard(difficulty=difficulty, limit=limit)
    return jsonify({"difficulty": difficulty, "leaderboard": leaderboard})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Retrieves global game stats."""
    stats = db.get_statistics()
    return jsonify(stats)


@app.route("/api/scores", methods=["POST"])
def api_save_score():
    """Records completed game session and returns updated leaderboard."""
    data = request.get_json() or {}
    player_name = data.get("player_name", "Anonymous")
    difficulty = data.get("difficulty", "beginner")
    time_seconds = int(data.get("time_seconds", 0))
    won = bool(data.get("won", False))
    moves_count = int(data.get("moves_count", 0))

    saved = db.record_game(
        player_name=player_name,
        difficulty=difficulty,
        time_seconds=time_seconds,
        won=won,
        moves_count=moves_count,
    )
    leaderboard = db.get_leaderboard(difficulty=difficulty, limit=10)
    return jsonify({"saved": saved, "leaderboard": leaderboard})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

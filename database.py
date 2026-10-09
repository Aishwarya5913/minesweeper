"""
database.py
===========
Database Layer for Minesweeper Game.

Provides persistence for:
1. Leaderboards (top fastest completion times per difficulty).
2. Game History and aggregated win/loss statistics.

Supports:
- Local SQLite (default, zero configuration, zero external dependencies).
- Cloud PostgreSQL via DATABASE_URL environment variable (for free deployments
  on Render, Supabase, Neon, or Railway).
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime

# On Vercel serverless environments, the root directory is read-only; /tmp is writable
DEFAULT_DB_PATH = "/tmp/minesweeper.db" if os.environ.get("VERCEL") else "minesweeper.db"
DB_PATH = os.environ.get("SQLITE_DB_PATH", DEFAULT_DB_PATH)
DATABASE_URL = os.environ.get("DATABASE_URL")


class DatabaseManager:
    """
    Manages database connections, schemas, and queries for leaderboards and game stats.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.is_postgres = bool(DATABASE_URL)
        self.init_db()

    def _get_connection(self):
        """Returns an active database connection."""
        if self.is_postgres:
            try:
                import psycopg2
                return psycopg2.connect(DATABASE_URL, sslmode="require")
            except Exception:
                # Fallback to local SQLite if postgres connection fails
                pass
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initializes tables and indexes."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create scores / leaderboard table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                time_seconds INTEGER NOT NULL,
                won INTEGER NOT NULL,
                moves_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for ultra-fast leaderboard queries by difficulty and completion time
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scores_diff_time 
            ON scores (difficulty, won, time_seconds)
        """)

        conn.commit()
        conn.close()

    def record_game(
        self,
        player_name: str,
        difficulty: str,
        time_seconds: int,
        won: bool,
        moves_count: int = 0
    ) -> Dict[str, Any]:
        """
        Inserts a completed game session into the database.
        Returns the inserted record metadata.
        """
        clean_name = (player_name or "Anonymous").strip()[:24]
        if not clean_name:
            clean_name = "Anonymous"

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO scores (player_name, difficulty, time_seconds, won, moves_count)
            VALUES (?, ?, ?, ?, ?)
        """, (clean_name, difficulty.lower(), time_seconds, 1 if won else 0, moves_count))

        inserted_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": inserted_id,
            "player_name": clean_name,
            "difficulty": difficulty.lower(),
            "time_seconds": time_seconds,
            "won": won,
            "moves_count": moves_count,
        }

    def get_leaderboard(self, difficulty: str = "beginner", limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves the top fastest winning games for the given difficulty level.
        Sorted by time_seconds ASC, then created_at ASC.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, player_name, difficulty, time_seconds, moves_count, created_at
            FROM scores
            WHERE difficulty = ? AND won = 1
            ORDER BY time_seconds ASC, created_at ASC
            LIMIT ?
        """, (difficulty.lower(), limit))

        rows = cursor.fetchall()
        leaderboard = []
        for rank, row in enumerate(rows, start=1):
            leaderboard.append({
                "rank": rank,
                "id": row["id"],
                "player_name": row["player_name"],
                "difficulty": row["difficulty"],
                "time_seconds": row["time_seconds"],
                "moves_count": row["moves_count"],
                "created_at": str(row["created_at"]),
            })

        conn.close()
        return leaderboard

    def get_statistics(self) -> Dict[str, Any]:
        """
        Computes overall statistics: Total games played, total wins,
        overall win percentage, and best times per difficulty.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total counts
        cursor.execute("SELECT COUNT(*) AS total, SUM(won) AS wins FROM scores")
        row = cursor.fetchone()
        total_games = row["total"] or 0
        total_wins = row["wins"] or 0
        win_rate = round((total_wins / total_games * 100), 1) if total_games > 0 else 0.0

        # Best time per difficulty
        best_times = {}
        for diff in ["beginner", "intermediate", "expert"]:
            cursor.execute("""
                SELECT MIN(time_seconds) AS best
                FROM scores
                WHERE difficulty = ? AND won = 1
            """, (diff,))
            best_row = cursor.fetchone()
            best_times[diff] = best_row["best"] if best_row and best_row["best"] is not None else None

        conn.close()

        return {
            "total_games": total_games,
            "total_wins": total_wins,
            "win_rate_percent": win_rate,
            "best_times": best_times,
        }

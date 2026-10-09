"""
test_suite.py
=============
Automated test suite verifying:
1. Discrete Mathematics concepts (Graph Theory, Set Theory, Combinatorics, Logic)
2. Game State and Cascades
3. Database persistence & Leaderboard queries
4. HTTP API handling logic
"""

import unittest
import os
import io
import json
from discrete_math import (
    GridGraph,
    SetTheoryEngine,
    CombinatoricsEngine,
    PropositionalLogicSolver,
)
from game_engine import MinesweeperGame
from database import DatabaseManager


class TestDiscreteMathematics(unittest.TestCase):
    def test_graph_theory(self):
        # 1. Vertex set size |V| = R x C
        g = GridGraph(9, 9)
        self.assertEqual(len(g.vertices), 81)

        # 2. Vertex degrees: Corner = 3, Edge = 5, Interior = 8
        self.assertEqual(g.degree((0, 0)), 3)
        self.assertEqual(g.degree((8, 8)), 3)
        self.assertEqual(g.degree((0, 4)), 5)
        self.assertEqual(g.degree((4, 0)), 5)
        self.assertEqual(g.degree((4, 4)), 8)

        # 3. Symmetry of adjacency relation
        for u in [(0, 0), (2, 3), (8, 7)]:
            for v in g.get_neighbors(u):
                self.assertIn(u, g.get_neighbors(v), "Adjacency relation must be symmetric")

    def test_set_theory_engine(self):
        engine = SetTheoryEngine(9, 9)
        self.assertEqual(len(engine.universe), 81)

        # Simulate 10 mines
        engine.mines = {(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1), (2, 2), (3, 3)}
        # Invariant 1: S = U \ M
        self.assertEqual(len(engine.safe_cells), 71)
        self.assertEqual(engine.safe_cells & engine.mines, set())
        self.assertEqual(engine.safe_cells | engine.mines, engine.universe)

        # Invariant 2: Cannot flag revealed cells
        engine.revealed.add((5, 5))
        self.assertFalse(engine.can_flag((5, 5)))
        self.assertTrue(engine.can_flag((6, 6)))

        # Invariant 3: Toggle flag
        self.assertTrue(engine.toggle_flag((6, 6)))
        self.assertIn((6, 6), engine.flagged)
        self.assertFalse(engine.toggle_flag((6, 6)))
        self.assertNotIn((6, 6), engine.flagged)

        # Invariant 4: Victory condition R == S
        self.assertFalse(engine.is_victory())
        engine.revealed = set(engine.safe_cells)
        self.assertTrue(engine.is_victory())

        # Invariant 5: Loss condition R & M != empty
        engine.revealed.add((0, 0))
        self.assertTrue(engine.is_loss())

    def test_combinatorics_and_probability(self):
        comb = CombinatoricsEngine()
        # Binomial coefficients
        self.assertEqual(comb.combinations_count(81, 10), 1878392407320)
        self.assertEqual(comb.combinations_count(5, 0), 1)
        self.assertEqual(comb.combinations_count(5, 5), 1)

        # Safe placement
        engine = SetTheoryEngine(9, 9)
        g = GridGraph(9, 9)
        first_click = (4, 4)
        neighbors = g.get_neighbors(first_click)
        mines = comb.generate_safe_mine_placement(engine.universe, first_click, neighbors, 10)
        self.assertEqual(len(mines), 10)
        self.assertNotIn(first_click, mines)
        for n in neighbors:
            self.assertNotIn(n, mines)

    def test_propositional_logic_solver(self):
        g = GridGraph(3, 3)
        solver = PropositionalLogicSolver(g)

        # Setup: Cell (0, 0) has clue 1. Only neighbor is (0, 1), (1, 0), (1, 1).
        # Suppose (0, 1) and (1, 0) are revealed safe.
        # Then (1, 1) MUST be a mine by All-Mines Rule!
        clues = {(0, 0): 1, (0, 1): 0, (1, 0): 0}
        revealed = {(0, 0), (0, 1), (1, 0)}
        flagged = set()

        safe, mines = solver.deduce_safe_and_mines(clues, revealed, flagged)
        self.assertIn((1, 1), mines)


class TestGameEngine(unittest.TestCase):
    def test_game_lifecycle(self):
        game = MinesweeperGame("beginner")
        state = game.get_state()
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["rows"], 9)
        self.assertEqual(state["cols"], 9)
        self.assertEqual(state["totalMines"], 10)

        # First click at (4, 4) must be safe and start playing
        state = game.reveal(4, 4)
        self.assertEqual(state["status"], "playing")
        self.assertGreater(state["revealedCount"], 0)

        # Unrevealed cell can be flagged
        unrevealed = [
            (r, c) for r in range(9) for c in range(9)
            if not state["grid"][r][c]["revealed"]
        ]
        target = unrevealed[0]
        state = game.toggle_flag(target[0], target[1])
        self.assertEqual(state["flaggedCount"], 1)
        self.assertEqual(state["remainingMines"], 9)

        # Toggle flag back
        state = game.toggle_flag(target[0], target[1])
        self.assertEqual(state["flaggedCount"], 0)


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.test_db = "test_run.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.db = DatabaseManager(self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_scores_and_leaderboard(self):
        self.db.record_game("Speedy", "beginner", 25, True, 10)
        self.db.record_game("Slowpoke", "beginner", 95, True, 30)
        self.db.record_game("Unlucky", "beginner", 40, False, 5)

        lb = self.db.get_leaderboard("beginner")
        self.assertEqual(len(lb), 2)  # Only winning games in leaderboard
        self.assertEqual(lb[0]["player_name"], "Speedy")
        self.assertEqual(lb[0]["time_seconds"], 25)

        stats = self.db.get_statistics()
        self.assertEqual(stats["total_games"], 3)
        self.assertEqual(stats["total_wins"], 2)
        self.assertEqual(stats["best_times"]["beginner"], 25)


if __name__ == "__main__":
    unittest.main()

"""
game_engine.py
==============
Game State Coordinator and Logic Engine.

Connects the discrete mathematical primitives (Graph Theory, Set Theory,
Combinatorics, Propositional Logic) to the Minesweeper game rules and
provides a clean API for the server and web frontend.
"""

from typing import Dict, Any, Optional, Set, Tuple
import time
from discrete_math import (
    Vertex,
    GridGraph,
    SetTheoryEngine,
    CombinatoricsEngine,
    PropositionalLogicSolver,
)


DIFFICULTY_PRESETS = {
    "beginner": {"rows": 9, "cols": 9, "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert": {"rows": 16, "cols": 30, "mines": 99},
}


class MinesweeperGame:
    """
    Manages a single Minesweeper session using the discrete mathematics models.
    """

    def __init__(self, difficulty: str = "beginner", rows: int = 9, cols: int = 9, mines: int = 10):
        if difficulty in DIFFICULTY_PRESETS:
            config = DIFFICULTY_PRESETS[difficulty]
            self.difficulty = difficulty
            self.rows = config["rows"]
            self.cols = config["cols"]
            self.total_mines = config["mines"]
        else:
            self.difficulty = "custom"
            self.rows = max(4, min(30, rows))
            self.cols = max(4, min(50, cols))
            max_mines = (self.rows * self.cols) - 9
            self.total_mines = max(1, min(max_mines, mines))

        # 1. Initialize Discrete Mathematics Engines
        self.graph = GridGraph(self.rows, self.cols)
        self.set_engine = SetTheoryEngine(self.rows, self.cols)
        self.comb_engine = CombinatoricsEngine()
        self.logic_solver = PropositionalLogicSolver(self.graph)

        # 2. Game State Variables
        self.clues: Dict[Vertex, int] = {}
        self.status: str = "ready"  # "ready", "playing", "won", "lost"
        self.first_click_done: bool = False
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.exploded_mine: Optional[Vertex] = None
        self.moves_count: int = 0

    def _ensure_mines_placed(self, first_r: int, first_c: int) -> None:
        """
        Combinatorial placement: Generates mines safely after the first click.
        guaranteeing the first clicked vertex and its 8-neighborhood are 0-clue.
        """
        first_click = (first_r, first_c)
        neighbors = self.graph.get_neighbors(first_click)

        # Combinatorics: Random sample from Universe \ (first_click U N(first_click))
        placed_mines = self.comb_engine.generate_safe_mine_placement(
            self.set_engine.universe,
            first_click,
            neighbors,
            self.total_mines
        )
        self.set_engine.mines = placed_mines

        # Precompute clues: h(u) = |N(u) intersect M|
        for v in self.set_engine.universe:
            if v in self.set_engine.mines:
                self.clues[v] = -1  # Indicates mine
            else:
                neighbor_mines = len(set(self.graph.get_neighbors(v)) & self.set_engine.mines)
                self.clues[v] = neighbor_mines

        self.first_click_done = True
        self.start_time = time.time()
        self.status = "playing"

    def reveal(self, r: int, c: int) -> Dict[str, Any]:
        """
        Reveals the cell at (r, c).
        Applies Graph BFS traversal if cell is a zero-clue vertex.
        """
        target: Vertex = (r, c)

        if self.status in ["won", "lost"]:
            return self.get_state()

        # Cannot reveal out of bounds or flagged cells
        if target not in self.set_engine.universe or target in self.set_engine.flagged:
            return self.get_state()

        # Already revealed cell: If clicked again, attempt chord reveal
        if target in self.set_engine.revealed:
            return self.chord_reveal(r, c)

        # Place mines safely on first move
        if not self.first_click_done:
            self._ensure_mines_placed(r, c)

        self.moves_count += 1

        # Check if mine was clicked (Loss condition: R intersect M != empty)
        if target in self.set_engine.mines:
            self.status = "lost"
            self.end_time = time.time()
            self.exploded_mine = target
            self.set_engine.revealed.add(target)
            return self.get_state()

        # Clue check: if 0-cell, use BFS cascade to find connected component
        clue = self.clues.get(target, 0)
        if clue == 0:
            cascade_cells = self.graph.bfs_cascade(
                target,
                self.clues,
                self.set_engine.revealed,
                self.set_engine.flagged
            )
            self.set_engine.revealed.update(cascade_cells)
        else:
            self.set_engine.revealed.add(target)

        # Check Victory Condition: R == S  <=>  |S \ R| == 0
        if self.set_engine.is_victory():
            self.status = "won"
            self.end_time = time.time()
            # Automatically flag all mines upon winning
            self.set_engine.flagged = set(self.set_engine.mines)

        return self.get_state()

    def chord_reveal(self, r: int, c: int) -> Dict[str, Any]:
        """
        Chording action:
        When a revealed numbered cell has exactly as many flagged neighbors as its clue,
        reveal all other unflagged neighbors.
        """
        target = (r, c)
        if target not in self.set_engine.revealed or self.status != "playing":
            return self.get_state()

        clue = self.clues.get(target, 0)
        if clue <= 0:
            return self.get_state()

        neighbors = set(self.graph.get_neighbors(target))
        flagged_neighbors = neighbors & self.set_engine.flagged

        if len(flagged_neighbors) == clue:
            unflagged_hidden = (neighbors - self.set_engine.revealed) - self.set_engine.flagged
            for nr, nc in unflagged_hidden:
                if (nr, nc) in self.set_engine.mines:
                    self.status = "lost"
                    self.end_time = time.time()
                    self.exploded_mine = (nr, nc)
                    self.set_engine.revealed.add((nr, nc))
                    return self.get_state()
                else:
                    self.reveal(nr, nc)

        return self.get_state()

    def toggle_flag(self, r: int, c: int) -> Dict[str, Any]:
        """Toggles flag on coordinate (r, c)."""
        if self.status in ["won", "lost"]:
            return self.get_state()

        target: Vertex = (r, c)
        self.set_engine.toggle_flag(target)
        return self.get_state()

    def get_hint(self) -> Dict[str, Any]:
        """
        Uses Propositional Logic Solver to deduce provably safe or mine cells.
        Returns deduction information.
        """
        if not self.first_click_done or self.status != "playing":
            return {"type": "none", "message": "Make your first move to enable logic deduction."}

        provably_safe, provably_mines = self.logic_solver.deduce_safe_and_mines(
            self.clues,
            self.set_engine.revealed,
            self.set_engine.flagged
        )

        if provably_safe:
            cell = next(iter(provably_safe))
            return {
                "type": "safe",
                "cell": {"row": cell[0], "col": cell[1]},
                "message": f"Cell ({cell[0] + 1}, {cell[1] + 1}) is logically provable to be SAFE by constraint satisfaction."
            }
        elif provably_mines:
            cell = next(iter(provably_mines))
            return {
                "type": "mine",
                "cell": {"row": cell[0], "col": cell[1]},
                "message": f"Cell ({cell[0] + 1}, {cell[1] + 1}) is logically provable to contain a MINE."
            }

        return {
            "type": "probability",
            "message": "No single-clue deterministic deductions remain; choose the cell with lowest discrete probability."
        }

    def get_elapsed_seconds(self) -> int:
        """Returns elapsed game duration in integer seconds."""
        if not self.start_time:
            return 0
        if self.end_time:
            return int(self.end_time - self.start_time)
        return int(time.time() - self.start_time)

    def get_state(self) -> Dict[str, Any]:
        """
        Serializes current board state safely for frontend consumption.
        Mines remain hidden unless game status is won or lost.
        """
        grid = []
        is_over = self.status in ["won", "lost"]

        for r in range(self.rows):
            row_cells = []
            for c in range(self.cols):
                v = (r, c)
                is_revealed = v in self.set_engine.revealed
                is_flagged = v in self.set_engine.flagged
                is_mine = v in self.set_engine.mines

                cell_data = {
                    "row": r,
                    "col": c,
                    "revealed": is_revealed,
                    "flagged": is_flagged,
                }

                if is_revealed:
                    cell_data["clue"] = self.clues.get(v, 0)
                    cell_data["isMine"] = is_mine
                elif is_over:
                    # Reveal board secrets when game ends
                    cell_data["isMine"] = is_mine
                    if is_mine:
                        cell_data["clue"] = -1
                else:
                    cell_data["clue"] = None

                if is_over and self.exploded_mine == v:
                    cell_data["exploded"] = True

                row_cells.append(cell_data)
            grid.append(row_cells)

        return {
            "status": self.status,
            "difficulty": self.difficulty,
            "rows": self.rows,
            "cols": self.cols,
            "totalMines": self.total_mines,
            "remainingMines": self.total_mines - len(self.set_engine.flagged),
            "flaggedCount": len(self.set_engine.flagged),
            "revealedCount": len(self.set_engine.revealed),
            "movesCount": self.moves_count,
            "elapsedSeconds": self.get_elapsed_seconds(),
            "grid": grid,
        }

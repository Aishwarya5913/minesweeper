"""
discrete_math.py
================
Discrete Mathematics Core Engine for Minesweeper.

This module implements the theoretical foundations of Minesweeper using formal
discrete mathematics concepts:
1. GRAPH THEORY:
   - Undirected Grid Graph G = (V, E)
   - Moore Neighborhood (8-Adjacency)
   - Vertex Degree analysis: deg(v) in {3, 5, 8}
   - Connected Components & Breadth-First Search (BFS) for zero-cascade propagation
2. SET THEORY & BINARY RELATIONS:
   - Coordinate Universe U = { (r, c) | 0 <= r < R, 0 <= c < C }
   - Subsets: Mines (M), Revealed (R), Flagged (F), Safe (S = U \ M)
   - Adjacency Binary Relation R_adj subset of U x U (Symmetric & Irreflexive)
   - Set operations: Cardinality, Unions, Intersections, Relative Complements
   - Victory Condition: R = S  <=>  S \ R = {}
3. COMBINATORICS & DISCRETE PROBABILITY:
   - Combinations C(n, k) = n! / (k! * (n - k)!) for board configurations
   - Guaranteed First-Click Safety via set difference candidate pools
   - Uniform random sampling without replacement
   - Discrete conditional mine probability calculation
4. PROPOSITIONAL LOGIC & CONSTRAINT SATISFACTION:
   - Boolean variables X_v in {0, 1} (1 = mine, 0 = safe)
   - Clue linear constraints: sum_{v in N(u)} X_v = h(u)
   - Inference Rules: All-Mines Rule and All-Safe Rule
"""

from typing import Set, Tuple, List, Dict, Optional
from collections import deque
import math
import random

# Type aliases for mathematical clarity
Vertex = Tuple[int, int]  # An element (row, column) in Universe U
Edge = Tuple[Vertex, Vertex]  # An unordered pair {u, v} in Edge set E


# ==============================================================================
# 1. GRAPH THEORY ENGINE
# ==============================================================================

class GridGraph:
    """
    Represents the Minesweeper board as an undirected finite graph G = (V, E).

    Mathematical Formalism:
    - Vertex Set V = { (r, c) in Z x Z | 0 <= r < R, 0 <= c < C }
    - Edge Set E = { {u, v} in V x V | u != v and max(|u_r - v_r|, |u_c - v_c|) <= 1 }
    - This corresponds to an 8-connected grid graph (Moore neighborhood).
    """

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        # Construct Vertex Set V
        self.vertices: Set[Vertex] = {
            (r, c) for r in range(rows) for c in range(cols)
        }
        # Adjacency List representation: Adj(v) = { u in V | {u, v} in E }
        self.adjacency_list: Dict[Vertex, List[Vertex]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        """Constructs the adjacency list for all vertices in V."""
        # 8 possible directional vectors in discrete 2D space:
        # Delta = { (dr, dc) in {-1, 0, 1}^2 \ {(0, 0)} }
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        for r, c in self.vertices:
            neighbors = []
            for dr, dc in directions:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    neighbors.append((nr, nc))
            self.adjacency_list[(r, c)] = neighbors

    def degree(self, v: Vertex) -> int:
        """
        Returns deg(v), the degree of vertex v.
        In an R x C 8-connected grid:
        - Corners: deg(v) = 3
        - Edges (non-corner): deg(v) = 5
        - Interior: deg(v) = 8
        """
        return len(self.adjacency_list[v])

    def get_neighbors(self, v: Vertex) -> List[Vertex]:
        """Returns the open neighborhood N(v) = { u in V | (v, u) in E }."""
        return self.adjacency_list.get(v, [])

    def bfs_cascade(
        self,
        start_vertex: Vertex,
        clue_function: Dict[Vertex, int],
        already_revealed: Set[Vertex],
        flagged: Set[Vertex]
    ) -> Set[Vertex]:
        """
        Graph Traversal: Breadth-First Search (BFS) to identify connected
        components of zero-clue vertices and their boundary frontier.

        Mathematical concept:
        - Let V_0 = { v in V | clue(v) == 0 } be the set of zero-clue vertices.
        - The cascade discovers the connected component C of V_0 containing start_vertex,
          along with the exterior boundary partial neighborhood:
          Frontier = { u in N(v) | v in C }.
        - The total set to reveal is C union Frontier.
        """
        to_reveal: Set[Vertex] = set()
        queue: deque[Vertex] = deque([start_vertex])
        visited: Set[Vertex] = {start_vertex}

        while queue:
            current = queue.popleft()

            # Cells that are flagged cannot be revealed
            if current in flagged:
                continue

            to_reveal.add(current)

            # If current vertex has clue 0, traverse all adjacent vertices in G
            if clue_function.get(current, 0) == 0:
                for neighbor in self.adjacency_list[current]:
                    if neighbor not in visited and neighbor not in flagged and neighbor not in already_revealed:
                        visited.add(neighbor)
                        queue.append(neighbor)

        return to_reveal


# ==============================================================================
# 2. SET THEORY & BINARY RELATIONS ENGINE
# ==============================================================================

class SetTheoryEngine:
    """
    Manages the state and invariants of the game using formal Set Theory.

    Universe:
      U = { (r, c) | 0 <= r < R, 0 <= c < C }

    Subsets:
      M subset U: Mine coordinates (|M| = k)
      S = U \ M : Safe coordinates (|S| = |U| - k)
      R subset U: Revealed coordinates
      F subset U: Flagged coordinates

    Invariants:
      1. S union M = U and S intersect M = {} (Partition of U)
      2. F intersect R = {} (A revealed cell cannot be flagged)
      3. Victory Condition: R == S  (or S \ R == {})
      4. Loss Condition: R intersect M != {}
    """

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols
        self.universe: Set[Vertex] = {
            (r, c) for r in range(rows) for c in range(cols)
        }
        self.mines: Set[Vertex] = set()
        self.revealed: Set[Vertex] = set()
        self.flagged: Set[Vertex] = set()

    @property
    def safe_cells(self) -> Set[Vertex]:
        """Computes safe cell set S = U \ M (Set Difference)."""
        return self.universe - self.mines

    @property
    def remaining_safe_cells(self) -> Set[Vertex]:
        """Computes remaining unrevealed safe cells: S \ R."""
        return self.safe_cells - self.revealed

    def is_victory(self) -> bool:
        """
        Victory predicate:
        Player wins if and only if all safe cells are revealed:
        R == S  <=>  |S \ R| == 0
        """
        return len(self.remaining_safe_cells) == 0 and not self.is_loss()

    def is_loss(self) -> bool:
        """
        Loss predicate:
        Player loses if and only if any mine is revealed:
        R intersect M != {}
        """
        return len(self.revealed & self.mines) > 0

    def can_flag(self, v: Vertex) -> bool:
        """A cell can only be flagged if v in U \ R (Unrevealed)."""
        return v in self.universe and v not in self.revealed

    def toggle_flag(self, v: Vertex) -> bool:
        """
        Symmetric difference operation on Flagged set F with respect to {v}:
        If v in F: F := F \ {v}
        If v not in F: F := F union {v}
        Returns True if flagged, False if unflagged.
        """
        if not self.can_flag(v):
            return False
        if v in self.flagged:
            self.flagged.remove(v)
            return False
        else:
            self.flagged.add(v)
            return True


# ==============================================================================
# 3. COMBINATORICS & DISCRETE PROBABILITY ENGINE
# ==============================================================================

class CombinatoricsEngine:
    """
    Implements counting, combinatorial configurations, and probability metrics.
    """

    @staticmethod
    def combinations_count(n: int, k: int) -> int:
        """
        Calculates the Binomial Coefficient C(n, k) = n! / (k! * (n - k)!).
        Represents total possible distinct mine placements.
        """
        if k < 0 or k > n:
            return 0
        return math.comb(n, k)

    @staticmethod
    def generate_safe_mine_placement(
        universe: Set[Vertex],
        first_click: Vertex,
        first_click_neighbors: List[Vertex],
        total_mines: int
    ) -> Set[Vertex]:
        """
        Combinatorial Selection:
        Ensures the first click is completely safe and opens a satisfying 0-cell.

        Mathematical Selection Pool:
        Let Protected = { first_click } union N(first_click)
        CandidatePool = Universe \ Protected
        Mines are sampled uniformly at random: M subset CandidatePool with |M| = total_mines.
        """
        protected_set: Set[Vertex] = {first_click} | set(first_click_neighbors)
        candidate_pool: List[Vertex] = list(universe - protected_set)

        # Fallback if board is too small for full protection
        if len(candidate_pool) < total_mines:
            candidate_pool = list(universe - {first_click})

        selected_mines: Set[Vertex] = set(random.sample(candidate_pool, total_mines))
        return selected_mines

    @staticmethod
    def calculate_conditional_mine_probability(
        clue: int,
        unrevealed_neighbors: Set[Vertex],
        flagged_neighbors: Set[Vertex]
    ) -> float:
        """
        Discrete Probability:
        Given revealed vertex u with clue h(u) and flagged neighbors F_u = N(u) intersect F:
        Remaining unplaced mines among unrevealed unflagged neighbors:
        m_rem = h(u) - |F_u|
        Available cells:
        c_avail = |N(u) \ (R union F)|
        Conditional probability of each unrevealed neighbor being a mine:
        P(X_v = 1 | h(u)) = m_rem / c_avail
        """
        remaining_mines = clue - len(flagged_neighbors)
        available_cells = len(unrevealed_neighbors - flagged_neighbors)
        if available_cells <= 0:
            return 0.0
        return max(0.0, min(1.0, remaining_mines / available_cells))


# ==============================================================================
# 4. PROPOSITIONAL LOGIC & CONSTRAINT SATISFACTION (DEDUCTION ENGINE)
# ==============================================================================

class PropositionalLogicSolver:
    """
    Formal Propositional Logic Engine for Minesweeper.

    For every cell v in U, define a Boolean proposition:
      X_v = True   (cell v contains a mine)
      X_v = False  (cell v is safe)

    Linear Pseudo-Boolean Clue Constraint:
      For each revealed cell u in R with clue h(u):
      sum_{v in N(u)} X_v = h(u)

    Deduction Inference Rules:
    1. ALL-MINES RULE (Modus Ponens on boundary equality):
       If |N(u) \ R| == h(u) - |N(u) intersect F| > 0:
       Then for all v in N(u) \ R: X_v = True  (All remaining neighbors are mines!)

    2. ALL-SAFE RULE:
       If h(u) - |N(u) intersect F| == 0:
       Then for all v in N(u) \ (R union F): X_v = False  (All remaining neighbors are safe!)
    """

    def __init__(self, graph: GridGraph):
        self.graph = graph

    def deduce_safe_and_mines(
        self,
        clues: Dict[Vertex, int],
        revealed: Set[Vertex],
        flagged: Set[Vertex]
    ) -> Tuple[Set[Vertex], Set[Vertex]]:
        """
        Applies Propositional Logic deduction rules across all revealed frontier cells.

        Returns:
          (provably_safe_cells, provably_mine_cells)
        """
        provably_safe: Set[Vertex] = set()
        provably_mines: Set[Vertex] = set()

        for u in revealed:
            clue = clues.get(u, 0)
            neighbors = set(self.graph.get_neighbors(u))
            unrevealed = neighbors - revealed
            flagged_neighbors = neighbors & flagged
            hidden_unflagged = unrevealed - flagged

            remaining_mines_needed = clue - len(flagged_neighbors)

            # Rule 1: All remaining unrevealed are mines
            if len(hidden_unflagged) > 0 and len(hidden_unflagged) == remaining_mines_needed:
                provably_mines.update(hidden_unflagged)

            # Rule 2: Clue satisfied -> All remaining unrevealed are safe
            if remaining_mines_needed == 0 and len(hidden_unflagged) > 0:
                provably_safe.update(hidden_unflagged)

        return provably_safe, provably_mines

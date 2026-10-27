
from typing import Set, Tuple, List, Dict, Optional
from collections import deque
import math
import random


class GridGraph:
    

    def __init__(self, rows: int, cols: int):
        self.rows = rows
        self.cols = cols

        self.vertices: Set[Vertex] = {
            (r, c) for r in range(rows) for c in range(cols)
        }

    self.adjacency_list: Dict[Vertex, List[Vertex]] = {}
        self._build_graph()

    def _build_graph(self) -> None:
        
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
        
        return len(self.adjacency_list[v])

    def get_neighbors(self, v: Vertex) -> List[Vertex]:

        return self.adjacency_list.get(v, [])

    def bfs_cascade(
        self,
        start_vertex: Vertex,
        clue_function: Dict[Vertex, int],
        already_revealed: Set[Vertex],
        flagged: Set[Vertex]
    ) -> Set[Vertex]:
      
        to_reveal: Set[Vertex] = set()
        queue: deque[Vertex] = deque([start_vertex])
        visited: Set[Vertex] = {start_vertex}

        while queue:
            current = queue.popleft()

            if current in flagged:
                continue

            to_reveal.add(current)

            if clue_function.get(current, 0) == 0:
                for neighbor in self.adjacency_list[current]:
                    if neighbor not in visited and neighbor not in flagged and neighbor not in already_revealed:
                        visited.add(neighbor)
                        queue.append(neighbor)

        return to_reveal




class SetTheoryEngine:
   
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
        return self.universe - self.mines

    @property
    def remaining_safe_cells(self) -> Set[Vertex]:
        return self.safe_cells - self.revealed

    def is_victory(self) -> bool:
       
        return len(self.remaining_safe_cells) == 0 and not self.is_loss()

    def is_loss(self) -> bool:
        
        return len(self.revealed & self.mines) > 0

    def can_flag(self, v: Vertex) -> bool:
        return v in self.universe and v not in self.revealed

    def toggle_flag(self, v: Vertex) -> bool:
        
        if not self.can_flag(v):
            return False
        if v in self.flagged:
            self.flagged.remove(v)
            return False
        else:
            self.flagged.add(v)
            return True




class CombinatoricsEngine:
   

    @staticmethod
    def combinations_count(n: int, k: int) -> int:
       
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
        
        remaining_mines = clue - len(flagged_neighbors)
        available_cells = len(unrevealed_neighbors - flagged_neighbors)
        if available_cells <= 0:
            return 0.0
        return max(0.0, min(1.0, remaining_mines / available_cells))



class PropositionalLogicSolver:
   

    def __init__(self, graph: GridGraph):
        self.graph = graph

    def deduce_safe_and_mines(
        self,
        clues: Dict[Vertex, int],
        revealed: Set[Vertex],
        flagged: Set[Vertex]
    ) -> Tuple[Set[Vertex], Set[Vertex]]:
       
        provably_safe: Set[Vertex] = set()
        provably_mines: Set[Vertex] = set()

        for u in revealed:
            clue = clues.get(u, 0)
            neighbors = set(self.graph.get_neighbors(u))
            unrevealed = neighbors - revealed
            flagged_neighbors = neighbors & flagged
            hidden_unflagged = unrevealed - flagged

            remaining_mines_needed = clue - len(flagged_neighbors)

            if len(hidden_unflagged) > 0 and len(hidden_unflagged) == remaining_mines_needed:
                provably_mines.update(hidden_unflagged)

            if remaining_mines_needed == 0 and len(hidden_unflagged) > 0:
                provably_safe.update(hidden_unflagged)

        return provably_safe, provably_mines

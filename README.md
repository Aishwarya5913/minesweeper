# 💣 Minesweeper with Discrete Mathematics Engine

A modern, responsive, and elegant Minesweeper web game. Designed for academic and demonstration purposes, this project models the core game mechanics using formal **Discrete Mathematics** in the backend while providing a clean, accessible frontend interface.

The game is styled using the custom 6-color palette from the project specification, includes an in-game **Instructions** guide, connects to a database for a **Global Hall of Fame / Leaderboard**, and can be deployed online **100% for free**.

---

## 🎨 Color Palette Reference

The interface is designed using the exact color palette extracted from the reference image:

| Color Swatch | Hex Code | Role in Design |
| :--- | :--- | :--- |
| **Canary Yellow** | `#FCEA6C` | Primary buttons, victory highlights, flag accents, hint glow |
| **Charcoal Mauve** | `#6F5F69` | Primary typography, headers, borders, dark icons |
| **Medium Lavender** | `#DEC8EE` | Unrevealed cell base, tactile 3D borders, card accents |
| **Pastel Lilac** | `#EEDBF1` | Cell hover states, input borders, board background frame |
| **Lavender Blush** | `#F9E9F4` | Background gradient, modal backgrounds, hover tints |
| **Soft Pearl Mist** | `#FBF0F8` | Page canvas, revealed cell background, clean surfaces |

---

## 📐 Discrete Mathematics in the Backend

As required, discrete mathematics concepts are implemented in the backend (`discrete_math.py`) and code structure, while the frontend maintains a classic Minesweeper experience.

```
                           +----------------------------------------+
                           |           Coordinate Universe          |
                           |   U = { (r, c) | 0 <= r<R, 0 <= c<C }  |
                           +----------------------------------------+
                                         /             \
                                        /               \
                       +-------------------+   +--------------------+
                       |    Graph Theory   |   |     Set Theory     |
                       | G=(V,E), 8-Adj    |   | U = S ∪ M, S ∩ M=∅ |
                       | BFS Cascade Flood |   | Victory: R == S    |
                       +-------------------+   +--------------------+
                                        \               /
                                         \             /
                           +----------------------------------------+
                           |  Combinatorics & Propositional Logic   |
                           |  C(n, k) Mine Pools, Constraint Clues  |
                           |  ∑ X_v = h(u) Deductions (All-Mines/Safe)
                           +----------------------------------------+
```

### 1. Graph Theory ($G = (V, E)$)
* **Vertex Set ($V$):** Each cell is a discrete coordinate pair $v = (r, c)$ in the universe $U$:
  $$V = \{ (r, c) \in \mathbb{Z} \times \mathbb{Z} \mid 0 \le r < R, \; 0 \le c < C \}$$
  Total vertices: $|V| = R \times C$.
* **Edge Set ($E$):** Cells are connected if they are adjacent in the discrete 2D plane (Moore 8-neighborhood):
  $$E = \{ \{(r_1, c_1), (r_2, c_2)\} \subset V \mid \max(|r_1 - r_2|, |c_1 - c_2|) = 1 \}$$
* **Vertex Degree ($\deg(v)$):**
  * Corner vertices: $\deg(v) = 3$
  * Edge vertices (non-corner): $\deg(v) = 5$
  * Interior vertices: $\deg(v) = 8$
* **Connected Components & Breadth-First Search (BFS):**
  When a cell with clue $0$ is uncovered, the game runs a BFS graph traversal on the subgraph of zero-clue vertices:
  $$V_0 = \{ v \in V \mid clue(v) = 0 \}$$
  The cascade discovers the connected component containing the clicked vertex and reveals all boundary vertices (frontier $N(v)$) touching the component.

### 2. Set Theory & Binary Relations
* **Universe:** $U = V = \{ (r, c) \}$.
* **Subsets of $U$:**
  * $M \subset U$: The set of mine coordinates ($|M| = k$).
  * $S = U \setminus M$: The set of safe coordinates.
  * $R \subseteq U$: The set of currently revealed coordinates.
  * $F \subseteq U$: The set of currently flagged coordinates.
* **Set Invariants:**
  * Partition: $S \cup M = U$ and $S \cap M = \emptyset$.
  * Flag Invariant: $F \cap R = \emptyset$ (A revealed cell cannot be flagged).
* **Binary Adjacency Relation ($R_{adj} \subseteq U \times U$):**
  * $(u, v) \in R_{adj} \iff \max(|u_r - v_r|, |u_c - v_c|) = 1$.
  * *Symmetric:* $(u, v) \in R_{adj} \iff (v, u) \in R_{adj}$.
  * *Irreflexive:* $(u, u) \notin R_{adj}$.
* **Neighborhood Function:** $N(u) = \{ v \in U \mid (u, v) \in R_{adj} \}$.
* **Set-Theoretic Victory Condition:**
  $$\text{Victory} \iff R = S \quad (\text{equivalently } |S \setminus R| = 0)$$
* **Loss Condition:**
  $$\text{Loss} \iff R \cap M \neq \emptyset$$

### 3. Combinatorics & Discrete Probability
* **Total Possible Mine Configurations:**
  $$\binom{|U|}{k} = \frac{|U|!}{k!(|U| - k)!}$$
* **Guaranteed First-Click Safety:**
  To ensure the first click $u_0$ is always safe and initiates a satisfying opening cascade, mines are sampled uniformly at random from the candidate pool:
  $$U_{\text{candidates}} = U \setminus (\{u_0\} \cup N(u_0))$$
  Number of valid board openings: $\binom{|U| - (|N(u_0)| + 1)}{k}$.
* **Discrete Conditional Probability:**
  For any unrevealed neighbor $v \in N(u) \setminus (R \cup F)$ of revealed cell $u$ with clue $h(u)$:
  $$P(\text{cell } v \text{ contains a mine} \mid h(u)) = \frac{h(u) - |N(u) \cap F|}{|N(u) \setminus (R \cup F)|}$$

### 4. Propositional Logic & Constraint Satisfaction
* **Boolean Propositional Variables:** For every cell $v \in U$, define $X_v \in \{0, 1\}$ ($1 = \text{mine}$, $0 = \text{safe}$).
* **Linear Pseudo-Boolean Clue Constraints:** For every revealed cell $u \in R$ with clue $h(u)$:
  $$\sum_{v \in N(u)} X_v = h(u)$$
* **Inference Rules (Deduction Engine in `PropositionalLogicSolver`):**
  1. **All-Mines Rule (Modus Ponens):**
     If the number of unrevealed neighbors equals the remaining required mines:
     $$|N(u) \setminus R| = h(u) - |N(u) \cap F| > 0 \implies \bigwedge_{v \in N(u) \setminus R} X_v = 1$$
     *(Every unrevealed neighbor is logically proven to be a mine!)*
  2. **All-Safe Rule:**
     If all required mines for clue $u$ are already flagged:
     $$h(u) - |N(u) \cap F| = 0 \implies \bigwedge_{v \in N(u) \setminus (R \cup F)} \neg X_v$$
     *(Every unrevealed unflagged neighbor is logically proven to be safe!)*

---

## 🗂️ Project Structure

```
dm project/
├── discrete_math.py    # Formal Discrete Mathematics engines (Graph, Set, Combinatorics, Logic)
├── game_engine.py      # Game session coordinator & board state manager
├── database.py         # SQLite / PostgreSQL database layer for leaderboards & statistics
├── server.py           # Zero-dependency, multi-threaded standard library HTTP server
├── app.py              # Flask WSGI web application (for cloud deployments)
├── test_suite.py       # Comprehensive unit tests for all mathematical & game logic
├── requirements.txt    # Cloud deployment dependencies (flask, gunicorn)
├── Procfile            # Deployment process definition
├── render.yaml         # 1-Click free deployment blueprint for Render.com
├── README.md           # Documentation & mathematical explanations
└── static/             # Frontend client assets
    ├── index.html      # Responsive HTML5 layout with Instructions & Leaderboard modals
    ├── style.css       # Custom styling using the exact 6-color palette
    └── app.js          # Controller with Web Audio API, touch support, and REST API calls
```

---

## 🚀 How to Run Locally

You can run this project locally with **zero external dependencies** using Python's built-in standard library!

### Option A: Zero-Dependency Run (Recommended)
```bash
python3 server.py
```
Open your browser at: **`http://localhost:8000`**

### Option B: Run with Flask
```bash
pip install -r requirements.txt
python3 app.py
```
Open your browser at: **`http://localhost:8000`**

### Running the Test Suite
```bash
python3 test_suite.py
```
All unit tests for Graph Theory, Set Theory, Combinatorics, and Propositional Logic will run and report status.

---

## 🗄️ Database Architecture

The database stores player completion times and game statistics.

### Schema
```sql
CREATE TABLE scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL,
    difficulty TEXT NOT NULL,       -- 'beginner', 'intermediate', 'expert'
    time_seconds INTEGER NOT NULL,  -- Completion time
    won INTEGER NOT NULL,           -- 1 for win, 0 for loss
    moves_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scores_diff_time ON scores (difficulty, won, time_seconds);
```

### Supported Databases:
1. **Local SQLite (`minesweeper.db`):** Created automatically on first run without any setup.
2. **Cloud PostgreSQL (Supabase / Neon / Render):** Set the `DATABASE_URL` environment variable:
   ```bash
   export DATABASE_URL="postgresql://user:password@host:port/dbname"
   ```
   The database manager (`database.py`) will automatically connect to your cloud PostgreSQL database!

---

## 🌐 How to Deploy Online for Free

### Method 1: Deploy on Vercel (100% Free - Recommended)
1. Push this folder to a GitHub repository:
   ```bash
   git init
   git add .
   git commit -m "Minesweeper with Discrete Math"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
2. Go to [vercel.com](https://vercel.com) and sign in with your GitHub account (Free).
3. Click **Add New...** $\rightarrow$ **Project**.
4. Select your Minesweeper repository from the list and click **Import**.
5. Vercel automatically detects `vercel.json`, `public/`, and `requirements.txt`.
6. Click **Deploy**!
   Your site will be live in ~30 seconds with a free `.vercel.app` URL!

*(Optional Vercel Database): In your Vercel Dashboard $\rightarrow$ **Storage**, click **Create Database** $\rightarrow$ **Postgres** (or Neon/Supabase), and it will automatically set `DATABASE_URL` for real-time global leaderboards!*

### Method 2: Deploy on Render.com (100% Free)
1. Push this project folder to a free GitHub repository.
2. Go to [render.com](https://render.com) and sign up (Free).
3. Click **New +** $\rightarrow$ **Web Service**.
4. Connect your GitHub repository.
5. Set:
   * **Environment:** `Python 3`
   * **Build Command:** `pip install -r requirements.txt`
   * **Start Command:** `python server.py`
6. Click **Deploy Web Service**! Render will give you a free live URL (e.g., `https://your-minesweeper.onrender.com`).

*(Or use the included `render.yaml` for 1-click blueprint deployment!)*

### Method 3: Deploy on Railway.app
1. Go to [railway.app](https://railway.app).
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Railway automatically detects `Procfile` and `requirements.txt` and deploys your site live.

### Method 3: Free Cloud Database with Supabase
If you want persistent cloud high scores across all users worldwide:
1. Go to [supabase.com](https://supabase.com) and create a free project.
2. In Project Settings $\rightarrow$ Database, copy the **Connection URI** (`postgresql://...`).
3. In your Render or Railway web service settings, add an Environment Variable:
   * Key: `DATABASE_URL`
   * Value: `postgresql://postgres:[YOUR-PASSWORD]@[HOST]:5432/postgres`
4. The game will automatically save all player scores to your Supabase PostgreSQL cloud database!

---

## 🎮 How to Play

Click the **📖 Instructions** button inside the game header at any time for the complete interactive guide:

1. **Left-Click / Tap:** Uncover a covered square.
2. **First Move Protection:** Your first click is guaranteed to be 100% safe.
3. **Numbers (1–8):** Each number tells you how many of the 8 adjacent squares contain a mine.
4. **Right-Click / Flag Mode:** Place or remove a flag 🚩 on suspected mines.
5. **Flag Mode Button:** Mobile & trackpad friendly toggle for easy touch play.
6. **Double-Click (Chord):** Clicking an already satisfied numbered cell reveals all remaining unflagged neighbors.
7. **💡 Hint Button:** Uses backend discrete mathematics (Propositional Logic) to suggest a provably safe cell or mine!
8. **Victory:** Uncover all non-mine cells to win and enter the **🏆 Leaderboard**!

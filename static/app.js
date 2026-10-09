/**
 * app.js
 * ======
 * Unified Frontend Controller & Discrete Mathematics Fallback Engine for Minesweeper.
 *
 * Designed to work seamlessly in TWO execution modes:
 * 1. Online / Full-Stack Mode: Communicates with the Python backend REST API & SQLite/PostgreSQL database.
 * 2. Standalone / File Mode: Runs the exact same Discrete Mathematics models (Graph Theory,
 *    Set Theory, Combinatorics, Propositional Logic) directly in the browser if opened via file://
 *    or when the backend server is offline.
 *
 * Board is rendered IMMEDIATELY upon page load, eliminating any blank screens!
 */

// ==============================================================================
// CLIENT-SIDE DISCRETE MATHEMATICS ENGINE (FALLBACK / STANDALONE)
// ==============================================================================

class LocalDiscreteMathEngine {
  constructor(rows = 9, cols = 9, totalMines = 10, difficulty = 'beginner') {
    this.rows = rows;
    this.cols = cols;
    this.totalMines = totalMines;
    this.difficulty = difficulty;

    // Set Theory: Universe U = { (r, c) }
    this.universe = new Set();
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        this.universe.add(`${r},${c}`);
      }
    }

    // Graph Theory: Adjacency list for 8-connected Moore neighborhood
    this.adjList = new Map();
    this.buildGraph();

    // Sets
    this.mines = new Set();
    this.revealed = new Set();
    this.flagged = new Set();
    this.clues = new Map();

    this.firstClickDone = false;
    this.status = 'ready'; // ready, playing, won, lost
    this.startTime = null;
    this.endTime = null;
    this.explodedMine = null;
    this.movesCount = 0;
  }

  buildGraph() {
    const deltas = [
      [-1, -1], [-1, 0], [-1, 1],
      [0, -1],           [0, 1],
      [1, -1],  [1, 0],  [1, 1]
    ];
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const key = `${r},${c}`;
        const neighbors = [];
        for (const [dr, dc] of deltas) {
          const nr = r + dr;
          const nc = c + dc;
          if (nr >= 0 && nr < this.rows && nc >= 0 && nc < this.cols) {
            neighbors.push(`${nr},${nc}`);
          }
        }
        this.adjList.set(key, neighbors);
      }
    }
  }

  // Combinatorics: Safe first-click mine placement
  ensureMinesPlaced(firstR, firstC) {
    const firstKey = `${firstR},${firstC}`;
    const protectedKeys = new Set([firstKey, ...(this.adjList.get(firstKey) || [])]);

    // Candidate Pool = Universe \ Protected
    let candidatePool = Array.from(this.universe).filter(k => !protectedKeys.has(k));
    if (candidatePool.length < this.totalMines) {
      candidatePool = Array.from(this.universe).filter(k => k !== firstKey);
    }

    // Uniform random sampling without replacement of k mines
    const shuffled = [...candidatePool].sort(() => Math.random() - 0.5);
    this.mines = new Set(shuffled.slice(0, this.totalMines));

    // Precompute Clue Function: h(u) = |N(u) intersect M|
    for (const v of this.universe) {
      if (this.mines.has(v)) {
        this.clues.set(v, -1);
      } else {
        const neighbors = this.adjList.get(v) || [];
        const mineNeighbors = neighbors.filter(n => this.mines.has(n)).length;
        this.clues.set(v, mineNeighbors);
      }
    }

    this.firstClickDone = true;
    this.status = 'playing';
    this.startTime = Date.now();
  }

  // Graph Theory: Breadth-First Search (BFS) for zero-cascade connected component
  bfsCascade(startKey) {
    const toReveal = new Set();
    const queue = [startKey];
    const visited = new Set([startKey]);

    while (queue.length > 0) {
      const current = queue.shift();
      if (this.flagged.has(current)) continue;

      toReveal.add(current);

      if ((this.clues.get(current) || 0) === 0) {
        const neighbors = this.adjList.get(current) || [];
        for (const n of neighbors) {
          if (!visited.has(n) && !this.flagged.has(n) && !this.revealed.has(n)) {
            visited.add(n);
            queue.push(n);
          }
        }
      }
    }
    return toReveal;
  }

  reveal(r, c) {
    const key = `${r},${c}`;
    if (this.status === 'won' || this.status === 'lost') return this.getState();
    if (!this.universe.has(key) || this.flagged.has(key)) return this.getState();

    // First click guarantee
    if (!this.firstClickDone) {
      this.ensureMinesPlaced(r, c);
    }

    this.movesCount++;

    // Loss condition: R intersect M != empty
    if (this.mines.has(key)) {
      this.status = 'lost';
      this.endTime = Date.now();
      this.explodedMine = key;
      this.revealed.add(key);
      return this.getState();
    }

    // Zero-cell cascade
    const clue = this.clues.get(key) || 0;
    if (clue === 0) {
      const cascade = this.bfsCascade(key);
      for (const k of cascade) {
        this.revealed.add(k);
      }
    } else {
      this.revealed.add(key);
    }

    // Set Theory Victory Condition: R == S  (All safe cells revealed)
    const safeCellsCount = this.universe.size - this.mines.size;
    if (this.revealed.size >= safeCellsCount) {
      this.status = 'won';
      this.endTime = Date.now();
      this.flagged = new Set(this.mines); // auto flag
    }

    return this.getState();
  }

  toggleFlag(r, c) {
    const key = `${r},${c}`;
    if (this.status === 'won' || this.status === 'lost') return this.getState();
    if (this.revealed.has(key)) return this.getState();

    if (this.flagged.has(key)) {
      this.flagged.delete(key);
    } else {
      this.flagged.add(key);
    }
    return this.getState();
  }

  // Propositional Logic Solver
  getHint() {
    if (!this.firstClickDone || this.status !== 'playing') {
      return { type: 'none', message: 'Click any square first to start the game!' };
    }

    for (const u of this.revealed) {
      const clue = this.clues.get(u) || 0;
      if (clue <= 0) continue;

      const neighbors = this.adjList.get(u) || [];
      const unrevealed = neighbors.filter(n => !this.revealed.has(n));
      const flaggedNeighbors = neighbors.filter(n => this.flagged.has(n));
      const unflaggedHidden = unrevealed.filter(n => !this.flagged.has(n));

      const remainingMinesNeeded = clue - flaggedNeighbors.length;

      // Rule 1: All remaining unrevealed are mines
      if (unflaggedHidden.length > 0 && unflaggedHidden.length === remainingMinesNeeded) {
        const [hr, hc] = unflaggedHidden[0].split(',').map(Number);
        return {
          type: 'mine',
          cell: { row: hr, col: hc },
          message: `Cell (${hr + 1}, ${hc + 1}) is logically provable to contain a MINE.`
        };
      }

      // Rule 2: Clue satisfied -> All remaining unrevealed are safe
      if (remainingMinesNeeded === 0 && unflaggedHidden.length > 0) {
        const [hr, hc] = unflaggedHidden[0].split(',').map(Number);
        return {
          type: 'safe',
          cell: { row: hr, col: hc },
          message: `Cell (${hr + 1}, ${hc + 1}) is logically provable to be SAFE.`
        };
      }
    }

    return {
      type: 'probability',
      message: 'No single-clue deterministic deductions remain; choose the square with lowest mine probability.'
    };
  }

  getElapsedSeconds() {
    if (!this.startTime) return 0;
    const end = this.endTime || Date.now();
    return Math.floor((end - this.startTime) / 1000);
  }

  getState() {
    const isOver = this.status === 'won' || this.status === 'lost';
    const grid = [];

    for (let r = 0; r < this.rows; r++) {
      const rowCells = [];
      for (let c = 0; c < this.cols; c++) {
        const key = `${r},${c}`;
        const isRevealed = this.revealed.has(key);
        const isFlagged = this.flagged.has(key);
        const isMine = this.mines.has(key);

        const cellData = {
          row: r,
          col: c,
          revealed: isRevealed,
          flagged: isFlagged,
          clue: isRevealed ? this.clues.get(key) : null,
          isMine: isRevealed ? isMine : (isOver ? isMine : false),
          exploded: isOver && this.explodedMine === key
        };
        rowCells.append ? rowCells.append(cellData) : rowCells.push(cellData);
      }
      grid.push(rowCells);
    }

    return {
      status: this.status,
      difficulty: this.difficulty,
      rows: this.rows,
      cols: this.cols,
      totalMines: this.totalMines,
      remainingMines: this.totalMines - this.flagged.size,
      flaggedCount: this.flagged.size,
      revealedCount: this.revealed.size,
      movesCount: this.movesCount,
      elapsedSeconds: this.getElapsedSeconds(),
      grid: grid
    };
  }
}


// ==============================================================================
// MAIN APP CONTROLLER
// ==============================================================================

class MinesweeperApp {
  constructor() {
    this.sessionId = null;
    this.difficulty = 'beginner';
    this.rows = 9;
    this.cols = 9;
    this.totalMines = 10;
    this.grid = [];
    this.status = 'ready';
    this.flagMode = false;
    this.timerInterval = null;
    this.elapsedSeconds = 0;
    this.soundEnabled = true;
    this.audioCtx = null;
    this.isServerConnected = false;
    this.localEngine = null;

    this.cacheElements();
    this.bindEvents();
    this.initAudio();

    // Start immediately and render board!
    this.startNewGame(this.difficulty);
  }

  cacheElements() {
    // Header & Toolbar
    this.boardEl = document.getElementById('board');
    this.difficultySelect = document.getElementById('difficultySelect');
    this.newGameBtn = document.getElementById('newGameBtn');
    this.resetBtn = document.getElementById('resetBtn');
    this.faceEmoji = document.getElementById('faceEmoji');
    this.minesCounter = document.getElementById('minesCounter');
    this.timerCounter = document.getElementById('timerCounter');
    this.flagModeBtn = document.getElementById('flagModeBtn');
    this.flagModeText = document.getElementById('flagModeText');
    this.hintBtn = document.getElementById('hintBtn');
    this.soundToggleBtn = document.getElementById('soundToggleBtn');
    this.soundIcon = document.getElementById('soundIcon');
    this.messageBanner = document.getElementById('messageBanner');
    this.messageText = document.getElementById('messageText');

    // Modals
    this.instructionsBtn = document.getElementById('instructionsBtn');
    this.instructionsModal = document.getElementById('instructionsModal');
    this.closeInstructionsBtn = document.getElementById('closeInstructionsBtn');
    this.gotItBtn = document.getElementById('gotItBtn');

    this.leaderboardBtn = document.getElementById('leaderboardBtn');
    this.leaderboardModal = document.getElementById('leaderboardModal');
    this.closeLeaderboardBtn = document.getElementById('closeLeaderboardBtn');
    this.closeLeaderboardFooterBtn = document.getElementById('closeLeaderboardFooterBtn');
    this.leaderboardTbody = document.getElementById('leaderboardTbody');
    this.tabButtons = document.querySelectorAll('.tab-btn');

    // Stats
    this.statTotalGames = document.getElementById('statTotalGames');
    this.statTotalWins = document.getElementById('statTotalWins');
    this.statWinRate = document.getElementById('statWinRate');

    // Victory Modal
    this.victoryModal = document.getElementById('victoryModal');
    this.victoryTime = document.getElementById('victoryTime');
    this.saveScoreForm = document.getElementById('saveScoreForm');
    this.playerNameInput = document.getElementById('playerNameInput');
    this.skipSaveBtn = document.getElementById('skipSaveBtn');
  }

  bindEvents() {
    // Controls
    this.difficultySelect.addEventListener('change', (e) => {
      this.difficulty = e.target.value;
      this.startNewGame(this.difficulty);
    });

    if (this.newGameBtn) {
      this.newGameBtn.addEventListener('click', () => this.startNewGame(this.difficulty));
    }

    this.resetBtn.addEventListener('click', () => this.startNewGame(this.difficulty));

    this.flagModeBtn.addEventListener('click', () => {
      this.flagMode = !this.flagMode;
      this.flagModeBtn.classList.toggle('active', this.flagMode);
      this.flagModeText.textContent = this.flagMode ? 'ON' : 'OFF';
    });

    this.hintBtn.addEventListener('click', () => this.requestHint());

    this.soundToggleBtn.addEventListener('click', () => {
      this.soundEnabled = !this.soundEnabled;
      this.soundIcon.textContent = this.soundEnabled ? '🔊' : '🔇';
    });

    // Modals
    this.instructionsBtn.addEventListener('click', () => this.openModal(this.instructionsModal));
    this.closeInstructionsBtn.addEventListener('click', () => this.closeModal(this.instructionsModal));
    this.gotItBtn.addEventListener('click', () => this.closeModal(this.instructionsModal));

    this.leaderboardBtn.addEventListener('click', () => {
      this.openModal(this.leaderboardModal);
      this.loadLeaderboard(this.difficulty);
      this.loadOverallStats();
    });
    this.closeLeaderboardBtn.addEventListener('click', () => this.closeModal(this.leaderboardModal));
    this.closeLeaderboardFooterBtn.addEventListener('click', () => this.closeModal(this.leaderboardModal));

    this.tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.tabButtons.forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        const diff = e.target.getAttribute('data-diff');
        this.loadLeaderboard(diff);
      });
    });

    this.saveScoreForm.addEventListener('submit', (e) => this.handleScoreSubmit(e));
    this.skipSaveBtn.addEventListener('click', () => this.closeModal(this.victoryModal));

    window.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-overlay')) {
        this.closeModal(e.target);
      }
    });
  }

  initAudio() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.audioCtx = new AudioCtx();
      }
    } catch (err) {
      console.log('Audio not supported');
    }
  }

  playSound(type) {
    if (!this.soundEnabled || !this.audioCtx) return;
    if (this.audioCtx.state === 'suspended') {
      this.audioCtx.resume();
    }
    const ctx = this.audioCtx;
    const now = ctx.currentTime;

    if (type === 'click') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.05);
      gain.gain.setValueAtTime(0.1, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.05);
    } else if (type === 'flag') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(520, now);
      osc.frequency.setValueAtTime(660, now + 0.04);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.08);
    } else if (type === 'win') {
      const notes = [523.25, 659.25, 783.99, 1046.50];
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + idx * 0.1);
        gain.gain.setValueAtTime(0.15, now + idx * 0.1);
        gain.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.1 + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now + idx * 0.1);
        osc.stop(now + idx * 0.1 + 0.25);
      });
    } else if (type === 'boom') {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(140, now);
      osc.frequency.exponentialRampToValueAtTime(40, now + 0.35);
      gain.gain.setValueAtTime(0.25, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now);
      osc.stop(now + 0.35);
    }
  }

  // ==========================================
  // GAME INITIALIZATION & BOARD RENDERING
  // ==========================================

  getDifficultyConfig(difficulty) {
    if (difficulty === 'intermediate') {
      return { rows: 16, cols: 16, mines: 40, cellSizeVar: 'var(--cell-size-intermediate)' };
    } else if (difficulty === 'expert') {
      return { rows: 16, cols: 30, mines: 99, cellSizeVar: 'var(--cell-size-expert)' };
    }
    return { rows: 9, cols: 9, mines: 10, cellSizeVar: 'var(--cell-size-beginner)' };
  }

  async startNewGame(difficulty = 'beginner') {
    this.stopTimer();
    this.elapsedSeconds = 0;
    this.timerCounter.textContent = '000';
    this.faceEmoji.textContent = '🙂';
    this.hideMessage();

    const config = this.getDifficultyConfig(difficulty);
    this.rows = config.rows;
    this.cols = config.cols;
    this.totalMines = config.mines;
    this.difficulty = difficulty;

    document.documentElement.style.setProperty('--cell-size', config.cellSizeVar);

    // Initialize local Discrete Math Engine immediately so board is rendered right now!
    this.localEngine = new LocalDiscreteMathEngine(this.rows, this.cols, this.totalMines, this.difficulty);
    const localState = this.localEngine.getState();
    this.status = localState.status;
    this.grid = localState.grid;
    this.updateCounters(this.totalMines, 0);

    // RENDER BOARD IMMEDIATELY! NO BLANK SCREENS!
    this.renderBoard();

    // Check if Python backend server is reachable
    try {
      const response = await fetch(`/api/game/new?difficulty=${difficulty}`, { cache: 'no-store' });
      if (response.ok) {
        const data = await response.json();
        this.sessionId = data.sessionId;
        this.status = data.status;
        this.grid = data.grid;
        this.isServerConnected = true;
        this.updateCounters(data.remainingMines, 0);
        this.renderBoard();
        console.log('Connected to Python Backend API & Database.');
      } else {
        this.isServerConnected = false;
      }
    } catch (err) {
      // In file:// mode or server offline
      this.isServerConnected = false;
      console.log('Running in Standalone mode via Local Discrete Math Engine.');
    }
  }

  renderBoard() {
    this.boardEl.innerHTML = '';
    this.boardEl.style.gridTemplateColumns = `repeat(${this.cols}, var(--cell-size))`;
    this.boardEl.style.gridTemplateRows = `repeat(${this.rows}, var(--cell-size))`;

    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const cellData = this.grid[r][c];
        const cellEl = document.createElement('div');
        cellEl.className = 'cell';
        cellEl.dataset.row = r;
        cellEl.dataset.col = c;
        cellEl.setAttribute('role', 'gridcell');

        this.applyCellState(cellEl, cellData);

        // Events
        cellEl.addEventListener('click', (e) => this.handleCellClick(r, c, e));
        cellEl.addEventListener('contextmenu', (e) => {
          e.preventDefault();
          this.handleCellRightClick(r, c);
        });

        // Touch long-press support
        let pressTimer = null;
        cellEl.addEventListener('touchstart', (e) => {
          pressTimer = setTimeout(() => {
            this.handleCellRightClick(r, c);
          }, 450);
        }, { passive: true });
        cellEl.addEventListener('touchend', () => {
          if (pressTimer) clearTimeout(pressTimer);
        });

        // Face feedback on mousedown
        cellEl.addEventListener('mousedown', (e) => {
          if (this.status === 'playing' || this.status === 'ready') {
            if (e.button === 0) this.faceEmoji.textContent = '😮';
          }
        });

        this.boardEl.appendChild(cellEl);
      }
    }

    document.addEventListener('mouseup', () => {
      if (this.status === 'playing' || this.status === 'ready') {
        this.faceEmoji.textContent = '🙂';
      }
    }, { once: true });
  }

  applyCellState(cellEl, cellData) {
    cellEl.className = 'cell';
    cellEl.removeAttribute('data-clue');
    cellEl.textContent = '';

    if (cellData.revealed) {
      cellEl.classList.add('revealed');
      if (cellData.isMine) {
        cellEl.classList.add('mine');
        if (cellData.exploded) cellEl.classList.add('exploded');
      } else if (cellData.clue > 0) {
        cellEl.dataset.clue = cellData.clue;
        cellEl.textContent = cellData.clue;
      }
    } else {
      cellEl.classList.add('covered');
      if (cellData.flagged) {
        cellEl.classList.add('flagged');
      }
      if (this.status === 'lost' && cellData.isMine && !cellData.flagged) {
        cellEl.classList.add('mine');
      }
    }
  }

  updateBoard(newGrid) {
    this.grid = newGrid;
    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        const cellData = this.grid[r][c];
        const cellEl = this.boardEl.querySelector(`[data-row="${r}"][data-col="${c}"]`);
        if (cellEl) {
          this.applyCellState(cellEl, cellData);
        }
      }
    }
  }

  startTimer() {
    if (this.timerInterval) return;
    this.timerInterval = setInterval(() => {
      this.elapsedSeconds++;
      const formatted = String(Math.min(999, this.elapsedSeconds)).padStart(3, '0');
      this.timerCounter.textContent = formatted;
    }, 1000);
  }

  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  updateCounters(remainingMines, time) {
    const formattedMines = String(Math.max(-99, Math.min(999, remainingMines))).padStart(3, '0');
    this.minesCounter.textContent = formattedMines;
    if (time !== undefined && time !== null) {
      this.elapsedSeconds = time;
      this.timerCounter.textContent = String(Math.min(999, time)).padStart(3, '0');
    }
  }

  // ==========================================
  // CLICK INTERACTIONS (REVEAL & FLAG)
  // ==========================================

  async handleCellClick(row, col, event) {
    if (this.status === 'won' || this.status === 'lost') return;

    if (this.flagMode) {
      await this.handleCellRightClick(row, col);
      return;
    }

    const cellData = this.grid[row][col];
    if (cellData.flagged) return;

    if (this.status === 'ready') {
      this.startTimer();
    }

    if (this.isServerConnected) {
      try {
        const response = await fetch('/api/game/reveal', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessionId: this.sessionId, row, col })
        });
        const data = await response.json();
        this.handleStateUpdate(data);
        this.playSound(data.status === 'lost' ? 'boom' : 'click');
        return;
      } catch (err) {
        this.isServerConnected = false;
      }
    }

    // Fallback to local Discrete Math engine
    const localData = this.localEngine.reveal(row, col);
    this.handleStateUpdate(localData);
    this.playSound(localData.status === 'lost' ? 'boom' : 'click');
  }

  async handleCellRightClick(row, col) {
    if (this.status === 'won' || this.status === 'lost') return;
    const cellData = this.grid[row][col];
    if (cellData.revealed) return;

    if (this.isServerConnected) {
      try {
        const response = await fetch('/api/game/flag', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sessionId: this.sessionId, row, col })
        });
        const data = await response.json();
        this.handleStateUpdate(data);
        this.playSound('flag');
        return;
      } catch (err) {
        this.isServerConnected = false;
      }
    }

    // Local engine
    const localData = this.localEngine.toggleFlag(row, col);
    this.handleStateUpdate(localData);
    this.playSound('flag');
  }

  handleStateUpdate(data) {
    this.status = data.status;
    this.updateCounters(data.remainingMines, data.elapsedSeconds);
    this.updateBoard(data.grid);

    if (this.status === 'won') {
      this.stopTimer();
      this.faceEmoji.textContent = '😎';
      this.playSound('win');
      this.showVictoryModal(data.elapsedSeconds);
    } else if (this.status === 'lost') {
      this.stopTimer();
      this.faceEmoji.textContent = '😵';
      this.showMessage('Game Over! You stepped on a mine. Click "Start New Game" to play again!');
    } else {
      this.faceEmoji.textContent = '🙂';
    }
  }

  // ==========================================
  // HINTS & DEDUCTIONS
  // ==========================================

  async requestHint() {
    if (this.status !== 'playing') {
      this.showMessage('Click any square on the board first to start playing!');
      return;
    }

    let data = null;
    if (this.isServerConnected) {
      try {
        const response = await fetch(`/api/game/hint?sessionId=${this.sessionId}`);
        data = await response.json();
      } catch (err) {
        this.isServerConnected = false;
      }
    }

    if (!data) {
      data = this.localEngine.getHint();
    }

    if (data.cell) {
      const { row, col } = data.cell;
      const cellEl = this.boardEl.querySelector(`[data-row="${row}"][data-col="${col}"]`);
      if (cellEl) {
        cellEl.classList.add('hint-highlight');
        setTimeout(() => cellEl.classList.remove('hint-highlight'), 3500);
      }
    }
    this.showMessage(data.message);
  }

  showMessage(msg) {
    this.messageText.textContent = msg;
    this.messageBanner.classList.remove('hidden');
  }

  hideMessage() {
    this.messageBanner.classList.add('hidden');
  }

  // ==========================================
  // MODALS & LEADERBOARD (SERVER + LOCALSTORAGE)
  // ==========================================

  openModal(modalEl) {
    modalEl.classList.remove('hidden');
  }

  closeModal(modalEl) {
    modalEl.classList.add('hidden');
  }

  showVictoryModal(seconds) {
    this.victoryTime.textContent = seconds;
    this.playerNameInput.value = '';
    this.openModal(this.victoryModal);
    this.playerNameInput.focus();
  }

  async handleScoreSubmit(e) {
    e.preventDefault();
    const playerName = this.playerNameInput.value.trim() || 'Anonymous';

    if (this.isServerConnected) {
      try {
        await fetch('/api/scores', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            player_name: playerName,
            difficulty: this.difficulty,
            time_seconds: this.elapsedSeconds,
            won: true,
            moves_count: 0
          })
        });
      } catch (err) {
        console.error(err);
      }
    }

    // Always also persist in local storage as backup
    this.saveLocalScore(playerName, this.difficulty, this.elapsedSeconds);

    this.closeModal(this.victoryModal);
    this.openModal(this.leaderboardModal);
    this.loadLeaderboard(this.difficulty);
    this.loadOverallStats();
  }

  saveLocalScore(playerName, difficulty, timeSeconds) {
    try {
      const scores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[]');
      scores.push({
        player_name: playerName,
        difficulty: difficulty.toLowerCase(),
        time_seconds: timeSeconds,
        created_at: new Date().toISOString().split('T')[0]
      });
      localStorage.setItem('minesweeper_scores', JSON.stringify(scores));
    } catch (err) {}
  }

  getLocalLeaderboard(difficulty) {
    try {
      const scores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[]');
      const filtered = scores
        .filter(s => s.difficulty === difficulty.toLowerCase())
        .sort((a, b) => a.time_seconds - b.time_seconds)
        .slice(0, 10);
      return filtered.map((s, idx) => ({ ...s, rank: idx + 1 }));
    } catch (err) {
      return [];
    }
  }

  async loadLeaderboard(difficulty = 'beginner') {
    this.leaderboardTbody.innerHTML = '<tr><td colspan="5" class="table-empty">Loading records...</td></tr>';
    let records = [];

    if (this.isServerConnected) {
      try {
        const response = await fetch(`/api/leaderboard?difficulty=${difficulty}&limit=10`);
        const data = await response.json();
        records = data.leaderboard || [];
      } catch (err) {
        records = this.getLocalLeaderboard(difficulty);
      }
    } else {
      records = this.getLocalLeaderboard(difficulty);
    }

    if (records.length === 0) {
      this.leaderboardTbody.innerHTML = '<tr><td colspan="5" class="table-empty">No scores yet. Clear the board to be #1!</td></tr>';
      return;
    }

    this.leaderboardTbody.innerHTML = records.map(r => `
      <tr>
        <td><strong>#${r.rank}</strong></td>
        <td>${this.escapeHtml(r.player_name)}</td>
        <td><strong>${r.time_seconds}s</strong></td>
        <td>${r.moves_count || '-'}</td>
        <td>${r.created_at ? r.created_at.split(' ')[0] : 'Today'}</td>
      </tr>
    `).join('');
  }

  async loadOverallStats() {
    let stats = null;
    if (this.isServerConnected) {
      try {
        const response = await fetch('/api/stats');
        stats = await response.json();
      } catch (err) {}
    }

    if (!stats) {
      try {
        const scores = JSON.parse(localStorage.getItem('minesweeper_scores') || '[]');
        stats = {
          total_games: scores.length,
          total_wins: scores.length,
          win_rate_percent: scores.length > 0 ? 100 : 0
        };
      } catch (e) {
        stats = { total_games: 0, total_wins: 0, win_rate_percent: 0 };
      }
    }

    this.statTotalGames.textContent = stats.total_games || 0;
    this.statTotalWins.textContent = stats.total_wins || 0;
    this.statWinRate.textContent = `${stats.win_rate_percent || 0}%`;
  }

  escapeHtml(str) {
    return str.replace(/[&<>'"]/g, 
      tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
  }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
  window.minesweeper = new MinesweeperApp();
});

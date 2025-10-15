#!/usr/bin/env python3
"""
terminal_pokemon_astar.py
Terminal grid + A* demo with file logging.

Run:
    python3 terminal_pokemon_astar.py

Outputs both to the console and to 'terminal_pokemon_astar_output.txt'.

Notes:
- Top-left grid coordinate is (0,0).
- Tile costs: NORMAL=1, MUD=3, WALL=impassable.
- Toggle ANIMATE = True to record/animate A* expansion steps.
"""

import random
import heapq
import time
import os
from datetime import datetime

# --- Config ---
ROWS = 8
COLS = 10
WALL_PROB = 0.18    # probability a tile is a wall
MUD_PROB = 0.12     # probability a tile is mud (higher cost)
SEED = None         # set int for reproducible
ANIMATE = False     # set True to watch expansion animation (slower)
MAX_PLACE_TRIES = 400  # attempts to place start/goal on a generated grid before regenerating

# Output file
OUTFILE = "terminal_pokemon_astar_output.txt"

# Tile types and symbols
TILE_NORMAL = '.'
TILE_WALL = '#'
TILE_MUD = '~'
TILE_POKEBALL = 'P'
TILE_ASH = 'A'
TILE_PATH = '*'

COSTS = {
    TILE_NORMAL: 1,
    TILE_MUD: 3,
}

# --- Utilities ---
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def manhattan(a, b):
    # careful arithmetic per policy (simple but explicit)
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def nowstr():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Simple logger that writes both to console and file (file append)
class Logger:
    def __init__(self, filename):
        self.filename = filename
        # open/overwrite at start
        with open(self.filename, 'w', encoding='utf-8') as f:
            f.write(f"Log start: {nowstr()}\n\n")

    def log(self, message, console=True):
        line = f"{nowstr()} | {message}"
        if console:
            print(message)
        with open(self.filename, 'a', encoding='utf-8') as f:
            f.write(line + "\n")

logger = Logger(OUTFILE)

# --- Grid generation ---
def generate_grid(rows, cols, wall_prob, mud_prob, seed=None):
    # If seed provided, we use it once per generation call
    if seed is not None:
        random.seed(seed)
    grid = [[TILE_NORMAL for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            rnum = random.random()
            if rnum < wall_prob:
                grid[r][c] = TILE_WALL
            else:
                if random.random() < mud_prob:
                    grid[r][c] = TILE_MUD
    return grid

def random_empty_cell(grid):
    rows = len(grid)
    cols = len(grid[0])
    # pick until non-wall
    while True:
        r = random.randrange(rows)
        c = random.randrange(cols)
        if grid[r][c] != TILE_WALL:
            return (r, c)

def ensure_reachable(grid, start, goal):
    # quick BFS to check connectivity ignoring mud cost
    rows = len(grid); cols = len(grid[0])
    q = [start]
    seen = set([start])
    while q:
        cr, cc = q.pop(0)
        if (cr, cc) == goal:
            return True
        for dr, dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = cr+dr, cc+dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if grid[nr][nc] != TILE_WALL and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    q.append((nr,nc))
    return False

# Place Ash and Pokéball on an existing grid (tries multiple times; regenerates grid if impossible)
def place_entities_on_grid(rows, cols, wall_prob, mud_prob, seed=None):
    attempts = 0
    tries_since_regen = 0
    # generate initial grid
    grid = generate_grid(rows, cols, wall_prob, mud_prob, seed)
    while True:
        # try to pick start and goal on non-wall cells
        start = random_empty_cell(grid)
        goal = random_empty_cell(grid)
        if start == goal:
            tries_since_regen += 1
            attempts += 1
            if tries_since_regen > MAX_PLACE_TRIES:
                # regenerate grid and reset tries
                grid = generate_grid(rows, cols, wall_prob, mud_prob, None)
                tries_since_regen = 0
            continue
        if ensure_reachable(grid, start, goal):
            logger.log(f"Placed Ash at {start} and Pokéball at {goal} on existing grid.")
            return grid, start, goal
        else:
            tries_since_regen += 1
            attempts += 1
            if tries_since_regen > MAX_PLACE_TRIES:
                # regenerate grid and reset tries
                logger.log("Could not find reachable start/goal on current grid after many attempts; regenerating grid.")
                grid = generate_grid(rows, cols, wall_prob, mud_prob, None)
                tries_since_regen = 0

# --- A* implementation with optional step recording ---
def astar(grid, start, goal, record_steps=False):
    rows = len(grid); cols = len(grid[0])
    g = {start: 0}
    parent = {}
    open_heap = []
    # priority = f, tie-breaker: g (lower g preferred)
    heapq.heappush(open_heap, (manhattan(start, goal), 0, start))
    open_set = {start}
    closed_set = set()
    steps = []  # each step: snapshot of (open_set, closed_set, current, g)

    while open_heap:
        f, _, current = heapq.heappop(open_heap)
        if current in closed_set:
            continue
        open_set.discard(current)
        closed_set.add(current)

        if record_steps:
            steps.append({
                'current': current,
                'open': set(open_set),
                'closed': set(closed_set),
                'g': g.copy()
            })

        if current == goal:
            # reconstruct path
            path = []
            cur = current
            while cur != start:
                path.append(cur)
                cur = parent[cur]
            path.append(start)
            path.reverse()
            return {'path': path, 'expanded': len(closed_set), 'steps': steps}

        cr, cc = current
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = cr+dr, cc+dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            if grid[nr][nc] == TILE_WALL:
                continue
            neighbor = (nr, nc)
            tentative_g = g[current] + COSTS.get(grid[nr][nc], 1)
            if tentative_g < g.get(neighbor, float('inf')):
                g[neighbor] = tentative_g
                parent[neighbor] = current
                fscore = tentative_g + manhattan(neighbor, goal)
                heapq.heappush(open_heap, (fscore, tentative_g, neighbor))
                open_set.add(neighbor)
    return None  # no path

# --- Rendering ---
def render(grid, start=None, goal=None, path=None, open_set=None, closed_set=None):
    rows = len(grid); cols = len(grid[0])
    out_lines = []
    path_set = set(path) if path else set()
    for r in range(rows):
        row_chars = []
        for c in range(cols):
            pos = (r,c)
            if pos == start:
                ch = TILE_ASH
            elif pos == goal:
                ch = TILE_POKEBALL
            elif pos in path_set and pos != start and pos != goal:
                ch = TILE_PATH
            else:
                ch = grid[r][c]
            # overlay open/closed
            if open_set and pos in open_set and ch not in (TILE_ASH, TILE_POKEBALL, TILE_PATH):
                ch = 'o' if ch != TILE_WALL else ch
            if closed_set and pos in closed_set and ch not in (TILE_ASH, TILE_POKEBALL, TILE_PATH):
                ch = 'x' if ch != TILE_WALL else ch
            row_chars.append(ch)
        out_lines.append(''.join(row_chars))
    return '\n'.join(out_lines)

# Helper to write grid + small description to file
def write_grid_snapshot(filehandle, title, grid, start=None, goal=None, path=None, open_set=None, closed_set=None):
    filehandle.write(f"--- {title} ---\n")
    filehandle.write(render(grid, start=start, goal=goal, path=path, open_set=open_set, closed_set=closed_set) + "\n\n")

# --- Main driver ---
def main():
    if SEED is not None:
        random.seed(SEED)

    logger.log("Starting grid generation and placement phase.", console=True)

    # generate grid once and then place entities (regenerating grid only if placement repeatedly fails)
    grid, start, goal = place_entities_on_grid(ROWS, COLS, WALL_PROB, MUD_PROB, SEED)

    logger.log(f"Grid generated: {ROWS} rows x {COLS} cols. (top-left is (0,0)).", console=True)
    logger.log("Legend: . normal  ~ mud(cost=3)  # wall  A ash  P pokeball  * path", console=True)
    logger.log("Initial grid snapshot (with Ash and Pokéball placed):", console=False)

    # show grid in console
    clear_console()
    print("Grid generated: {}x{}".format(ROWS, COLS))
    print("Legend: . normal  ~ mud(cost=3)  # wall  A ash  P pokeball  * path")
    print()
    print(render(grid, start=start, goal=goal))
    print()
    logger.log(f"Ash (start) coordinate: {start}. Pokéball (goal) coordinate: {goal}.", console=True)

    # log the initial grid with entities into file
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write("\n")
        f.write("Initial grid + entities placement:\n")
        write_grid_snapshot(f, "Initial placement", grid, start=start, goal=goal)

    logger.log("Finding shortest path with A* (Manhattan heuristic)...", console=True)
    res = astar(grid, start, goal, record_steps=ANIMATE)
    if not res:
        logger.log("No path found (unexpected — placement ensures reachability).", console=True)
        return
    path = res['path']
    expanded = res['expanded']
    logger.log(f"Path found. Steps (edges) from start -> goal: {len(path)-1}. Nodes expanded by A*: {expanded}.", console=True)

    # record summary to file
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write(f"\nA* Summary:\n")
        f.write(f"Start: {start}\nGoal: {goal}\nPath length (steps): {len(path)-1}\nNodes expanded: {expanded}\n\n")
        write_grid_snapshot(f, "Final path (A* result)", grid, start=start, goal=goal, path=path)

        # If ANIMATE then log all recorded A* steps (this can be long)
        if ANIMATE:
            f.write("\nA* expansion steps (chronological):\n")
            for i, st in enumerate(res['steps']):
                f.write(f"\nStep {i+1}: current={st['current']}, open_size={len(st['open'])}, closed_size={len(st['closed'])}\n")
                # write a compact snapshot (open as 'o', closed as 'x')
                f.write(render(grid, start=start, goal=goal, path=None, open_set=st['open'], closed_set=st['closed']) + "\n")

        # Write full path coordinates:
        f.write("\nPath coordinates from start -> goal (ordered):\n")
        f.write(", ".join(str(p) for p in path) + "\n\n")

    # Terminal animation (optional)
    print("Path found length (steps): {}, nodes expanded: {}".format(len(path)-1, expanded))
    time.sleep(0.8)

    if ANIMATE:
        logger.log("Animating A* expansion in terminal (also recorded to file).", console=True)
        for st in res['steps']:
            clear_console()
            print("A* animation: current={}, expanded={}".format(st['current'], len(st['closed'])))
            print(render(grid, start=start, goal=goal, path=None, open_set=st['open'], closed_set=st['closed']))
            time.sleep(0.06)
        time.sleep(0.4)

    # final render with path
    clear_console()
    print("Final path (A* result):")
    print(render(grid, start=start, goal=goal, path=path))
    print()
    print("Path coordinates (start -> goal):")
    print(path)
    logger.log("Final path printed to console and saved to file.", console=True)

    # move Ash along the path in terminal (animated) and log each move to file
    print("\nPress Enter to watch Ash walk to the Pokéball...")
    input()
    logger.log("Animating Ash's movement along the path (recorded moves follow).", console=True)
    with open(OUTFILE, 'a', encoding='utf-8') as f:
        f.write("\nAsh walking animation (sequence of positions and snapshots):\n")
        for i, pos in enumerate(path):
            clear_console()
            subpath = path[:i+1]
            print(render(grid, start=path[i], goal=goal, path=subpath))
            # log move
            f.write(f"\nMove {i+1}/{len(path)} - Ash at {pos}\n")
            f.write(render(grid, start=path[i], goal=goal, path=subpath) + "\n")
            time.sleep(0.12)
    clear_console()
    print(render(grid, start=goal, goal=goal, path=path))
    print("\nAsh reached the Pokéball!")
    logger.log("Ash reached the Pokéball. End of run.", console=True)

if __name__ == '__main__':
    main()

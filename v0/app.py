#!/usr/bin/env python3
# app.py
"""
Flask app for Pokemon A* Phase 2.
Run: python3 app.py
Visit: http://127.0.0.1:5000
"""

from flask import Flask, jsonify, render_template, send_from_directory
import random
import heapq
import os

# ---------------- Config ----------------
ROWS = 10
COLS = 10
WALL_PROB = 0.16
MUD_PROB = 0.3
SEED = None  # or set an int for reproducibility
TILE_NORMAL = '.'
TILE_WALL = '#'
TILE_MUD = '~'

COSTS = {TILE_NORMAL: 1, TILE_MUD: 3}

# if True, server will include the recorded steps in the JSON (large). Keep False for normal use.
INCLUDE_STEPS = False

# ---------------- App ----------------
app = Flask(__name__, static_folder="static", template_folder="templates")

# ---- Utilities / path helpers ----
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def generate_grid(rows, cols, wall_prob, mud_prob, seed=None):
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
    rows = len(grid); cols = len(grid[0])
    while True:
        r = random.randrange(rows)
        c = random.randrange(cols)
        if grid[r][c] != TILE_WALL:
            return (r, c)

def ensure_reachable(grid, start, goal):
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

def place_entities_on_grid(rows, cols, wall_prob, mud_prob, seed=None, max_place_tries=300):
    grid = generate_grid(rows, cols, wall_prob, mud_prob, seed)
    tries = 0
    while True:
        start = random_empty_cell(grid)
        goal = random_empty_cell(grid)
        if start == goal:
            tries += 1
            if tries > max_place_tries:
                grid = generate_grid(rows, cols, wall_prob, mud_prob, None)
                tries = 0
            continue
        if ensure_reachable(grid, start, goal):
            return grid, start, goal
        else:
            tries += 1
            if tries > max_place_tries:
                grid = generate_grid(rows, cols, wall_prob, mud_prob, None)
                tries = 0

# A* implementation
def astar(grid, start, goal, record_steps=False):
    rows = len(grid); cols = len(grid[0])
    g = {start: 0}
    parent = {}
    open_heap = []
    heapq.heappush(open_heap, (manhattan(start, goal), 0, start))
    open_set = {start}
    closed_set = set()
    steps = []
    while open_heap:
        f, _, current = heapq.heappop(open_heap)
        if current in closed_set:
            continue
        open_set.discard(current)
        closed_set.add(current)

        if record_steps:
            steps.append({
                'current': current,
                'open': list(open_set),
                'closed': list(closed_set),
                'g': dict(g)
            })

        if current == goal:
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
    return None

# Convert grid to simple JSON-friendly structure
def grid_to_json(grid):
    return {"rows": len(grid), "cols": len(grid[0]), "cells": grid}

# ---- Routes ----
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/new")
def api_new():
    """Generate a new grid, place start/goal, run solver, return everything to frontend."""
    if SEED is not None:
        random.seed(SEED)
    grid, start, goal = place_entities_on_grid(ROWS, COLS, WALL_PROB, MUD_PROB, SEED)
    # run A*
    res = astar(grid, start, goal, record_steps=INCLUDE_STEPS)
    if not res:
        return jsonify({"error": "no path found (unexpected)"}), 500
    out = {
        "grid": grid_to_json(grid),
        "start": start,
        "goal": goal,
        "path": res["path"],
        "expanded": res["expanded"]
    }
    if INCLUDE_STEPS:
        out["steps"] = res["steps"]
    return jsonify(out)

@app.route("/sprites/<path:filename>")
def sprites(filename):
    static_dir = os.path.join(app.root_path, "static", "sprites")
    return send_from_directory(static_dir, filename)

# ---- Run app ----
if __name__ == "__main__":
    os.makedirs(os.path.join("static", "sprites"), exist_ok=True)
    app.run(debug=True)

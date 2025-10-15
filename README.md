# 🎮 PokeSearcher — Pokémon-Style Pathfinding Visualizer

## 📖 Overview

**PokeSearcher** brings the nostalgia of Pokémon exploration to life while teaching pathfinding algorithms interactively.  
In this project, you can visualize how different algorithms (starting with **A\*** and soon including **Dijkstra**, **BFS**, and **Greedy Best-First Search**) find optimal paths through a grid inspired by Pokémon’s overworld design.

Ash walks across the grid using sprite-based movement, avoiding walls and crossing mud tiles with higher costs. The Pokéball represents the goal, and as Ash walks, each tile he visits turns green to represent explored paths.

---

## ✨ Features

- 🧠 **A\* Pathfinding Algorithm** (Manhattan heuristic, admissible)  
- 🎨 **Gameboy-style UI** — grid tiles, Pokéball goal, and animated Ash sprite  
- ⚙️ **Tile Costs:** Normal (1), Mud (3), Wall (impassable)  
- 🧩 **Dynamic Grid Generation** — new randomized grid each run  
- ▶️ **Start / Pause Controls** for animation playback  
- 💡 **Live Stats:** total cost, current cost, move number, total moves expected  
- 🌐 **Flask Backend** + **HTML/CSS/JS Frontend**

---

## 🧰 Tech Stack

| Layer | Technology |
|:------|:------------|
| Backend | Python 3 + Flask |
| Frontend | HTML, CSS, Vanilla JS |
| Visualization | DOM Grid + Animated Sprites |
| Assets | Pokémon-style sprites (Ash & Pokéball) |

---

## 🖥️ How to Run Locally

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/NinadGawali/PokeSearcher.git
cd PokeSearcher
```

### 2️⃣ Set Up Environment

Make sure you have Python 3.8+ installed.
```bash
python3 -m venv venv
venv\Scripts\activate    
pip install flask
```

### 3️⃣ Project Structure

```text
PokeSearcher/
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   ├── app.js
│   └── sprites/
│       ├── ash_down_0.png ... ash_up_3.png
│       └── pokeball.png
└── README.md
```

### 4️⃣ Run the App
```bash
python app.py
```
The Flask server will start at: http://127.0.0.1:5000

### 🎥 Video Sample
https://github.com/user-attachments/assets/21f6f649-955b-4204-9f57-2258d0d98bf0

### 🧑‍💻 Author
Ninad Gawali
GitHub: https://github.com/NinadGawali

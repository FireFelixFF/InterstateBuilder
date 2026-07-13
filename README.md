# 🛣️ Highway Builder — Interstate & Divided Highways Edition

A **Streamlit web app** that recreates the core interface, gameplay loop, and capabilities of the game *Subway Builder* (realistic transit/construction simulation with budget, network building, and demand simulation), but themed around building **Interstate Highways** and **Divided Highways**.

- Build highway segments, interchanges, and ramps on a grid map
- Connect cities and simulate traffic demand between them
- Earn revenue from served demand to expand your network
- Educational tool for understanding highway planning, connectivity, and traffic flow

**Inspired by Subway Builder** (hyperrealistic subway construction & passenger simulation game by Colin Miller).

## Features (Matching Subway Builder Spirit)
- **Budget-constrained building**: Start with $1.2B, spend wisely on different road types
- **Realistic(ish) tools**: Interstate (high-capacity, limited access), Divided Highway, Interchanges for crossings, Ramps/Exits to serve cities
- **Traffic simulation**: BFS-based connectivity check between cities + demand model (gravity-inspired). See which pairs are connected and earn revenue
- **Interactive map**: Color-coded grid with city markers, legend, coordinates
- **Dashboard & goals**: Track connectivity %, infrastructure built, revenue history chart
- **Presets & fast-forward**: Load a starter network or simulate multiple days quickly
- **Educational**: Teaches network planning, prioritizing high-demand corridors, proper use of interchanges/ramps

## How to Run

### Option 1: Replit (Easiest for quick testing)
1. Go to [replit.com](https://replit.com) and create a new **Python** Repl (or import from GitHub)
2. Upload or paste the contents of `app.py` and `requirements.txt`
3. In the Shell (or .replit config), run:
   ```
   pip install -r requirements.txt
   streamlit run app.py --server.port 8501
   ```
4. Replit will give you a public URL to play the app instantly.

### Option 2: GitHub + Streamlit Cloud (Recommended for sharing)
1. Create a new GitHub repository
2. Upload `app.py`, `requirements.txt`, and this `README.md`
3. Go to [share.streamlit.io](https://share.streamlit.io)
4. Connect your GitHub account and select the repo
5. Streamlit Cloud will automatically deploy it (free tier available)
6. Share the beautiful public URL with friends!

### Local Development
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Controls & Gameplay
- **Sidebar (left)**: Current budget, construction tools (radio buttons), coordinate inputs (Row/Col), big BUILD button, Reset & Load Starter buttons
- **Main Map**: Visual grid. Use the numbers on the axes to know exact coordinates for placement
- **Build tab**: See the live map + cell inspector
- **Simulate tab**: Run traffic simulations to earn money and see connected city pairs
- **Dashboard tab**: Strategic goals, progress bars, historical performance chart
- **Guide tab**: Full instructions + tips

**Pro tip**: Click "Load Starter Network" first to see a working example, then expand it to connect all 6 cities for maximum revenue!

## Technical Notes
- Built with **Streamlit**, **NumPy**, and **Matplotlib** (lightweight, no heavy GIS libs)
- Grid is 15×20 cells (abstract regional map)
- 6 pre-placed cities with different populations/demand
- Simulation uses pure Python BFS (no NetworkX needed) for connectivity
- Fully self-contained — one file + requirements

## Future Ideas (for contributors)
- Add terrain (rivers = bridge cost, hills = higher cost)
- Full edge-load traffic assignment + congestion penalties
- Different travel "speeds" (Interstate faster than Divided)
- Multiple maps / scenarios / levels with win conditions
- Export network as image or JSON
- Dark mode + better mobile layout

This project demonstrates how to build an engaging simulation/game-style app in pure Streamlit without custom JS components.

Enjoy planning your interstate system! 🚧🛣️

---

*Not affiliated with the official Subway Builder game. Educational/fan recreation of the gameplay concepts.*
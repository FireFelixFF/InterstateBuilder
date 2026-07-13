import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from collections import deque
import random

# ==================== CONFIG ====================
ROWS = 15
COLS = 20
INITIAL_BUDGET = 1200.0  # $1.2 Billion starting

# Cell types
EMPTY = 0
INTERSTATE = 1
DIVIDED = 2
INTERCHANGE = 3
RAMP = 4
CITY = 5

HIGHWAY_TYPES = {
    INTERSTATE: "Interstate Highway",
    DIVIDED: "Divided Highway",
    INTERCHANGE: "Interchange",
    RAMP: "Ramp / Exit",
    CITY: "City / Demand Center"
}

COSTS = {
    INTERSTATE: 42,      # $42M per cell
    DIVIDED: 17,         # $17M
    INTERCHANGE: 88,     # $88M
    RAMP: 26,            # $26M
}

# For future expansion (capacity not fully used in v1 sim)
CAPACITIES = {
    INTERSTATE: 15000,
    DIVIDED: 5500,
    INTERCHANGE: 25000,
    RAMP: 4000,
}

# Pre-defined cities (positions are (row, col))
DEFAULT_CITIES = [
    {"name": "Metro Central", "pos": (7, 10), "pop": 850000},
    {"name": "North Haven", "pos": (2, 10), "pop": 320000},
    {"name": "Eastport", "pos": (7, 17), "pop": 410000},
    {"name": "Westfield", "pos": (7, 3), "pop": 290000},
    {"name": "South Junction", "pos": (12, 10), "pop": 380000},
    {"name": "Riverside", "pos": (4, 5), "pop": 180000},
]

def initialize_state():
    """Initialize or reset the game state"""
    st.session_state.grid = np.zeros((ROWS, COLS), dtype=int)
    # Place cities on grid
    for city in st.session_state.cities:
        r, c = city["pos"]
        st.session_state.grid[r, c] = CITY
    st.session_state.budget = INITIAL_BUDGET
    st.session_state.history = []
    st.session_state.last_sim_result = None
    st.session_state.total_built_length = 0

def get_tool_info(tool_name):
    """Parse selected tool"""
    if "Interstate" in tool_name:
        return INTERSTATE, COSTS[INTERSTATE]
    elif "Divided" in tool_name:
        return DIVIDED, COSTS[DIVIDED]
    elif "Interchange" in tool_name:
        return INTERCHANGE, COSTS[INTERCHANGE]
    elif "Ramp" in tool_name:
        return RAMP, COSTS[RAMP]
    elif "Demolish" in tool_name:
        return 0, 0  # free, refund logic separate
    return EMPTY, 0

def are_connected(grid, start, goal):
    """BFS to check if two positions are connected via highway/city cells"""
    if start == goal:
        return True
    visited = set()
    queue = deque([start])
    visited.add(start)
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    
    while queue:
        current = queue.popleft()
        if current == goal:
            return True
        cr, cc = current
        for dr, dc in directions:
            nr, nc = cr + dr, cc + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and (nr, nc) not in visited:
                if grid[nr, nc] != EMPTY:  # any built cell or city is passable
                    visited.add((nr, nc))
                    queue.append((nr, nc))
    return False

def run_traffic_simulation(grid, cities):
    """Simulate demand between cities. Returns served_pct, revenue, details"""
    total_demand = 0.0
    served_demand = 0.0
    connected_pairs = []
    disconnected_pairs = []
    
    n = len(cities)
    for i in range(n):
        for j in range(i + 1, n):
            c1 = cities[i]
            c2 = cities[j]
            # Simple demand model (gravity-like, scaled)
            dist = abs(c1["pos"][0] - c2["pos"][0]) + abs(c1["pos"][1] - c2["pos"][1])
            pair_demand = (c1["pop"] * c2["pop"]) / 1_200_000_000.0  # scaled
            if dist > 0:
                pair_demand /= (1 + dist * 0.08)  # distance penalty
            total_demand += pair_demand
            
            if are_connected(grid, c1["pos"], c2["pos"]):
                served_demand += pair_demand
                connected_pairs.append((c1["name"], c2["name"], round(pair_demand, 1)))
            else:
                disconnected_pairs.append((c1["name"], c2["name"]))
    
    served_pct = (served_demand / total_demand * 100.0) if total_demand > 0 else 0.0
    
    # Revenue model: base toll/fee per served 'unit' + bonus for high connectivity
    base_revenue = served_demand * 1.35
    connectivity_bonus = len(connected_pairs) * 8.5
    operating_cost = (np.count_nonzero((grid > 0) & (grid != CITY)) * 0.65)  # maintenance
    revenue = max(0, base_revenue + connectivity_bonus - operating_cost)
    
    details = {
        "total_demand": round(total_demand, 1),
        "served_demand": round(served_demand, 1),
        "connected_pairs": connected_pairs,
        "disconnected_pairs": disconnected_pairs,
        "operating_cost": round(operating_cost, 1),
    }
    return round(served_pct, 1), round(revenue, 1), details

def draw_map(grid, cities, highlight_pairs=None):
    """Create beautiful matplotlib map"""
    fig, ax = plt.subplots(figsize=(11, 8.5))
    
    # Base colors (RGB 0-1)
    color_grid = np.zeros((ROWS, COLS, 3))
    for r in range(ROWS):
        for c in range(COLS):
            cell = grid[r, c]
            if cell == EMPTY:
                color_grid[r, c] = [0.52, 0.72, 0.42]      # Grass green
            elif cell == INTERSTATE:
                color_grid[r, c] = [0.35, 0.38, 0.42]      # Dark asphalt gray-blue
            elif cell == DIVIDED:
                color_grid[r, c] = [0.58, 0.60, 0.65]      # Lighter divided road
            elif cell == INTERCHANGE:
                color_grid[r, c] = [0.95, 0.75, 0.25]      # Bright interchange
            elif cell == RAMP:
                color_grid[r, c] = [0.85, 0.55, 0.35]      # Ramp / exit
            elif cell == CITY:
                color_grid[r, c] = [0.95, 0.85, 0.85]      # Light city tint
    
    ax.imshow(color_grid, origin="upper", interpolation="nearest", aspect="equal")
    
    # Grid lines
    ax.set_xticks(np.arange(-0.5, COLS, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, ROWS, 1), minor=True)
    ax.grid(which="minor", color="#222222", linestyle="-", linewidth=0.6, alpha=0.7)
    ax.tick_params(which="minor", size=0)
    ax.set_xticks([])
    ax.set_yticks([])
    
    # Draw cities with markers and labels
    for city in cities:
        r, c = city["pos"]
        # City marker
        ax.plot(c, r, marker="o", markersize=22, color="#E63946", markeredgecolor="white", markeredgewidth=2.5, zorder=5)
        ax.plot(c, r, marker="o", markersize=12, color="white", zorder=6)
        # Name
        ax.text(c, r - 1.35, city["name"], ha="center", va="bottom", fontsize=9, fontweight="bold",
                color="#1D3557", bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="#457B9D", alpha=0.95))
        # Population
        ax.text(c, r + 1.35, f"{city['pop']:,}", ha="center", va="top", fontsize=7.5,
                color="#1D3557", alpha=0.9)
    
    # Title and labels
    ax.set_title("🛣️ INTERSTATE & DIVIDED HIGHWAY BUILDER\nPlan • Build • Simulate Traffic Demand", 
                 fontsize=13, fontweight="bold", pad=12, color="#1D3557")
    ax.set_xlabel("Columns (East → West)", fontsize=9, labelpad=6)
    ax.set_ylabel("Rows (North → South)", fontsize=9, labelpad=6)
    
    # Legend
    legend_elements = [
        Patch(facecolor=[0.52, 0.72, 0.42], edgecolor="black", label="Undeveloped / Rural"),
        Patch(facecolor=[0.35, 0.38, 0.42], edgecolor="black", label="Interstate (High Capacity)"),
        Patch(facecolor=[0.58, 0.60, 0.65], edgecolor="black", label="Divided Highway"),
        Patch(facecolor=[0.95, 0.75, 0.25], edgecolor="black", label="Interchange (Crossings)"),
        Patch(facecolor=[0.85, 0.55, 0.35], edgecolor="black", label="Ramp / Exit"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#E63946", markersize=11, 
                   markeredgecolor="white", markeredgewidth=2, label="City / Traffic Demand Center"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8, framealpha=0.95, 
              fancybox=True, edgecolor="#457B9D")
    
    # Add coordinate labels on axes for easier placement
    ax.set_xticks(range(COLS))
    ax.set_yticks(range(ROWS))
    ax.tick_params(axis='both', which='major', labelsize=6, colors="#333333")
    
    plt.tight_layout()
    return fig

# ==================== STREAMLIT APP ====================
st.set_page_config(
    page_title="Highway Builder | Interstate Edition",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom style
st.markdown("""
<style>
    .main .block-container {padding-top: 1rem;}
    .stMetric {background-color: #f0f4f8; padding: 8px; border-radius: 8px;}
    .stButton button {font-weight: 600;}
</style>
""", unsafe_allow_html=True)

st.title("🛣️ Highway Builder — Interstate & Divided Highways Edition")
st.caption("A Streamlit recreation inspired by Subway Builder. Build realistic highway networks, connect cities, simulate commuter & freight traffic, and grow your budget. Perfect for learning transportation planning!")

# Initialize session state
if "grid" not in st.session_state:
    st.session_state.cities = DEFAULT_CITIES.copy()
    initialize_state()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("💰 Budget & Stats")
    current_budget = st.session_state.budget
    st.metric("Current Budget", f"${current_budget:,.1f} Million", 
              delta=f"{current_budget - INITIAL_BUDGET:+.1f}M" if current_budget != INITIAL_BUDGET else None)
    
    # Quick stats
    highway_cells = int(np.count_nonzero((st.session_state.grid > 0) & (st.session_state.grid != CITY)))
    st.metric("Highway Length Built", f"{highway_cells} segments", 
              help="Each segment ≈ 1 mile in this scale")
    
    if st.session_state.last_sim_result:
        res = st.session_state.last_sim_result
        st.metric("Last Served Demand", f"{res['served_pct']:.1f}%")
    
    st.divider()
    
    st.header("🛠️ Construction Tools")
    tool_choice = st.radio(
        "Choose what to build:",
        [
            "🛤️ Interstate Highway ($42M)",
            "🛣️ Divided Highway ($17M)",
            "🔀 Interchange ($88M)",
            "↗️ Ramp / Exit ($26M)",
            "🗑️ Demolish (Refund 40%)"
        ],
        index=0,
        help="Interstates = high capacity limited-access. Divided = flexible multi-lane. Use Interchanges for crossings & complex junctions. Ramps connect to cities."
    )
    
    tool_id, tool_cost = get_tool_info(tool_choice)
    
    st.write("**Place at coordinates:**")
    col_row, col_col = st.columns(2)
    with col_row:
        place_row = st.number_input("Row (0-14)", min_value=0, max_value=ROWS-1, value=7, step=1, key="row_in")
    with col_col:
        place_col = st.number_input("Col (0-19)", min_value=0, max_value=COLS-1, value=10, step=1, key="col_in")
    
    if st.button("🚧 BUILD / APPLY HERE", type="primary", use_container_width=True):
        current_cell = st.session_state.grid[place_row, place_col]
        
        if tool_id == 0:  # Demolish
            if current_cell != EMPTY and current_cell != CITY:
                refund = int(COSTS.get(current_cell, 0) * 0.4)
                st.session_state.budget += refund
                st.session_state.grid[place_row, place_col] = EMPTY
                st.success(f"Demolished! +${refund}M refunded.")
            else:
                st.warning("Nothing to demolish here (or it's a city).")
        else:
            # Check if placing on city
            if current_cell == CITY:
                st.error("Cannot build over a city center! Place ramps nearby to serve it.")
            else:
                if st.session_state.budget >= tool_cost:
                    st.session_state.grid[place_row, place_col] = tool_id
                    st.session_state.budget -= tool_cost
                    st.success(f"Built {HIGHWAY_TYPES[tool_id]} at ({place_row}, {place_col})! -${tool_cost}M")
                else:
                    st.error(f"Not enough budget! Need ${tool_cost}M more.")
        st.rerun()
    
    st.divider()
    
    st.header("⚡ Quick Actions")
    if st.button("🔄 Full Reset (New Game)", use_container_width=True):
        initialize_state()
        st.success("Map and budget reset!")
        st.rerun()
    
    if st.button("📍 Load Starter Network", use_container_width=True):
        # Build a basic starter network
        g = st.session_state.grid
        # Horizontal interstate across center
        for c in range(2, 18):
            g[7, c] = INTERSTATE
        # Vertical to north
        for r in range(3, 7):
            g[r, 10] = INTERSTATE
        # To south
        for r in range(8, 13):
            g[r, 10] = INTERSTATE
        # Some divided connectors
        g[4, 5] = RAMP
        g[7, 3] = RAMP
        g[7, 17] = RAMP
        g[2, 10] = RAMP
        g[12, 10] = RAMP
        # Interchanges at key points
        g[7, 10] = INTERCHANGE
        st.session_state.budget = 850.0
        st.success("Starter network loaded! Now expand and connect the remaining cities.")
        st.rerun()
    
    st.divider()
    st.caption("💡 Tip: Start with the 'Load Starter Network' button, then expand to connect all 6 cities for maximum revenue!")

# ==================== MAIN TABS ====================
tab_build, tab_sim, tab_dash, tab_guide = st.tabs([
    "🗺️ Build & Plan Network", 
    "🚗 Run Traffic Simulation", 
    "📊 Dashboard & Goals", 
    "📖 How to Play & Tips"
])

with tab_build:
    st.subheader("Interactive Highway Map")
    
    # Draw and show map
    fig = draw_map(st.session_state.grid, st.session_state.cities)
    st.pyplot(fig, use_container_width=True)
    
    st.info("👆 Use the **sidebar tools** to select what to build and enter the exact (Row, Col) coordinates from the map above. The map updates instantly after each build!")
    
    # Current cell inspector
    with st.expander("🔍 Inspect Cell at Current Coordinates"):
        r = st.session_state.get("row_in", 7)
        c = st.session_state.get("col_in", 10)
        cell_val = st.session_state.grid[r, c]
        cell_name = HIGHWAY_TYPES.get(cell_val, "Empty Land")
        st.write(f"**Position ({r}, {c})**: {cell_name}")
        if cell_val in COSTS:
            st.write(f"Original build cost: ${COSTS[cell_val]}M")

with tab_sim:
    st.subheader("🚦 Traffic Demand Simulation")
    st.write("Simulate how commuters, trucks, and travelers use your highway network. Revenue is generated based on how well you connect the cities and serve demand.")
    
    colA, colB = st.columns([1, 1])
    with colA:
        if st.button("▶️ RUN TRAFFIC SIMULATION", type="primary", use_container_width=True):
            served_pct, revenue, details = run_traffic_simulation(
                st.session_state.grid, st.session_state.cities
            )
            st.session_state.budget += revenue
            st.session_state.last_sim_result = {
                "served_pct": served_pct,
                "revenue": revenue,
                "details": details
            }
            # Record history
            st.session_state.history.append({
                "step": len(st.session_state.history) + 1,
                "budget": round(st.session_state.budget, 1),
                "served_pct": served_pct,
                "revenue": revenue
            })
            st.success(f"✅ Simulation complete! Served **{served_pct}%** of total demand. Earned **+${revenue:,.1f}M** revenue.")
            st.rerun()
    
    with colB:
        if st.button("🔁 Run 5-Day Simulation (Fast Forward)", use_container_width=True):
            total_rev = 0
            for _ in range(5):
                served_pct, revenue, _ = run_traffic_simulation(
                    st.session_state.grid, st.session_state.cities
                )
                st.session_state.budget += revenue
                total_rev += revenue
                st.session_state.history.append({
                    "step": len(st.session_state.history) + 1,
                    "budget": round(st.session_state.budget, 1),
                    "served_pct": served_pct,
                    "revenue": revenue
                })
            st.success(f"5-day sim done! Total revenue added: **+${total_rev:,.1f}M**")
            st.rerun()
    
    if st.session_state.last_sim_result:
        res = st.session_state.last_sim_result
        st.divider()
        st.subheader("Last Simulation Results")
        m1, m2, m3 = st.columns(3)
        m1.metric("Demand Served", f"{res['served_pct']}%")
        m2.metric("Revenue Earned", f"+${res['revenue']:,.1f}M")
        m3.metric("New Budget", f"${st.session_state.budget:,.1f}M")
        
        det = res["details"]
        st.write("**Connected City Pairs (traffic flowing):**")
        if det["connected_pairs"]:
            for p in det["connected_pairs"][:8]:  # limit display
                st.write(f"• {p[0]} ↔ {p[1]}  (~{p[2]} demand units)")
        else:
            st.write("No pairs connected yet. Build highways between cities!")
        
        if det["disconnected_pairs"]:
            st.warning(f"**Disconnected pairs** ({len(det['disconnected_pairs'])}): Some cities cannot reach each other.")
            for p in det["disconnected_pairs"][:4]:
                st.write(f"• {p[0]} ↔ {p[1]}")
    
    st.caption("Higher served % + more connected pairs = more revenue. Maintain your network to reduce 'operating costs'.")

with tab_dash:
    st.subheader("📈 Progress Dashboard")
    
    # Goals section
    st.markdown("### 🎯 Strategic Goals (like real transit planning)")
    
    # Calculate progress
    connected_count = 0
    total_pairs = len(st.session_state.cities) * (len(st.session_state.cities) - 1) // 2
    for i in range(len(st.session_state.cities)):
        for j in range(i+1, len(st.session_state.cities)):
            if are_connected(st.session_state.grid, 
                             st.session_state.cities[i]["pos"], 
                             st.session_state.cities[j]["pos"]):
                connected_count += 1
    connect_pct = (connected_count / total_pairs * 100) if total_pairs > 0 else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.progress(min(connect_pct / 100, 1.0), text=f"Network Connectivity: {connected_count}/{total_pairs} city pairs linked ({connect_pct:.0f}%)")
        if connect_pct >= 100:
            st.success("🏆 All cities fully connected! Excellent planning.")
        elif connect_pct >= 60:
            st.info("Good progress — keep expanding the network.")
        else:
            st.warning("Focus on linking the disconnected cities for big revenue gains.")
    
    with col2:
        highway_cells = int(np.count_nonzero((st.session_state.grid > 0) & (st.session_state.grid != CITY)))
        interstate_cells = int(np.count_nonzero(st.session_state.grid == INTERSTATE))
        st.progress(min(highway_cells / 45, 1.0), text=f"Highway Infrastructure: {highway_cells} segments built (target ~45 for full region)")
        if interstate_cells >= 12:
            st.success("Strong Interstate backbone!")
    
    st.divider()
    
    # History chart
    if len(st.session_state.history) >= 2:
        st.markdown("### 📉 Budget & Performance Over Time")
        hist_df = {
            "Simulation #": [h["step"] for h in st.session_state.history],
            "Budget ($M)": [h["budget"] for h in st.session_state.history],
            "Demand Served %": [h["served_pct"] for h in st.session_state.history]
        }
        st.line_chart(hist_df, x="Simulation #", y=["Budget ($M)", "Demand Served %"], 
                      color=["#2A9D8F", "#E76F51"])
        st.caption("Watch your budget grow as you improve the network!")
    else:
        st.info("Run a few traffic simulations to see your progress chart here.")
    
    # Current network summary
    st.markdown("### 🗺️ Current Network Summary")
    highway_cells = int(np.count_nonzero((st.session_state.grid > 0) & (st.session_state.grid != CITY)))
    interchanges = int(np.count_nonzero(st.session_state.grid == INTERCHANGE))
    ramps = int(np.count_nonzero(st.session_state.grid == RAMP))
    
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Total Segments", highway_cells)
    s2.metric("Interstates", int(np.count_nonzero(st.session_state.grid == INTERSTATE)))
    s3.metric("Divided Hwys", int(np.count_nonzero(st.session_state.grid == DIVIDED)))
    s4.metric("Interchanges + Ramps", interchanges + ramps)

with tab_guide:
    st.subheader("📖 How to Play — Highway Builder Edition")
    st.markdown("""
    This app captures the **core loop and spirit** of *Subway Builder* (realistic planning, budget constraints, passenger/traffic simulation, demand-driven design) but applied to **Interstate and Divided Highways**.
    
    ### Gameplay Loop
    1. **Plan** — Look at city locations and populations on the map. High-pop cities generate more demand.
    2. **Build** — Use sidebar tools to lay Interstates (expensive but high capacity, best for long hauls) and Divided Highways (cheaper, good for regional connections). 
       - **Interchanges** are required for clean crossings and complex junctions.
       - **Ramps/Exits** let traffic enter/exit the highway system near cities.
    3. **Simulate** — Run traffic simulation to see which city pairs are connected and how much demand you serve. Earn revenue!
    4. **Optimize & Expand** — Use earnings to build more, improve connectivity, reduce "operating costs", and hit goals.
    
    ### Key Strategies (Real-World Inspired)
    - Connect **high-demand pairs** first (large cities).
    - Use **Interstates** for main corridors, **Divided Highways** for branches.
    - Place **Interchanges** where routes cross or split.
    - Place **Ramps** close to cities so they can access the network.
    - Balance spending — don't go broke building fancy interchanges everywhere.
    - Run multiple simulations (or fast-forward) to grow your budget steadily.
    
    ### Controls
    - **Sidebar**: Budget, tool selection, coordinate entry, build button, reset & preset buttons.
    - **Map**: Visual feedback. Coordinates shown on axes for easy reference.
    - **Simulation tab**: Run sims, see detailed pair connections and revenue.
    - **Dashboard**: Track goals like full connectivity and infrastructure coverage.
    
    ### Differences from Real Subway Builder
    This is a simplified educational prototype (grid-based instead of real city GIS data, basic BFS connectivity instead of advanced pathfinding + capacity-constrained assignment). The real game uses actual census data, complex elevation/terrain, train frequency, and beautiful 3D-ish rendering. This version focuses on the fun planning + simulation feedback loop.
    
    Enjoy building your dream interstate system! 🚀
    """)
    
    st.divider()
    st.caption("Made as a Streamlit web app • Ready for GitHub + Streamlit Cloud or Replit • Educational & fun transportation planning simulator")

# Footer
st.divider()
st.caption("🛣️ Highway Builder v1.0 • Inspired by Subway Builder (2025-2026) • Built for learning & fun • Deploy on Streamlit Cloud from GitHub or run directly on Replit")
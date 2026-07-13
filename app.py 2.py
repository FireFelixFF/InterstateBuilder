import streamlit as st
import folium
from streamlit_folium import st_folium
import math
from collections import deque

# ==================== CONFIG & DATA ====================
st.set_page_config(
    page_title="Highway Builder — Real Map Edition",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Real geographic region: I-70 Corridor (St. Louis to Indianapolis area)
CENTER_LAT = 39.2
CENTER_LON = -87.8
ZOOM_START = 7

# Cities with real coordinates and scaled populations (demand centers)
CITIES = [
    {"name": "St. Louis, MO", "lat": 38.6270, "lon": -90.1994, "pop": 300000},
    {"name": "Terre Haute, IN", "lat": 39.4667, "lon": -87.4139, "pop": 180000},
    {"name": "Indianapolis, IN", "lat": 39.7684, "lon": -86.1581, "pop": 450000},
    {"name": "Richmond, IN", "lat": 39.8289, "lon": -84.8903, "pop": 120000},
    {"name": "Dayton, OH", "lat": 39.7589, "lon": -84.1916, "pop": 250000},
]

# Background "existing" realistic Interstate (approximate I-70 corridor)
BACKGROUND_HIGHWAYS = [
    {
        "name": "Existing I-70",
        "coords": [
            (38.65, -90.25), (38.80, -89.70), (39.10, -88.50),
            (39.40, -87.50), (39.60, -86.80), (39.75, -86.20)
        ],
        "color": "#555555",
        "weight": 5,
        "dash": "6,4"
    }
]

# Game costs per mile (scaled for fun, realistic order of magnitude)
INTERSTATE_COST_PER_MILE = 48   # $48M per mile
DIVIDED_COST_PER_MILE = 19      # $19M per mile

INITIAL_BUDGET = 2800.0         # $2.8 Billion starting budget

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two lat/lon points"""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def initialize_state():
    if "built_segments" not in st.session_state:
        st.session_state.built_segments = []
    if "budget" not in st.session_state:
        st.session_state.budget = INITIAL_BUDGET
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_sim" not in st.session_state:
        st.session_state.last_sim = None

def get_segment_length_and_cost(start_lat, start_lon, end_lat, end_lon, hwy_type):
    miles = haversine(start_lat, start_lon, end_lat, end_lon)
    rate = INTERSTATE_COST_PER_MILE if hwy_type == "Interstate" else DIVIDED_COST_PER_MILE
    cost = miles * rate
    return round(miles, 2), round(cost, 1)

def build_graph(segments, cities):
    """Build connectivity graph from user segments + cities. Nodes are (lat, lon) tuples."""
    nodes = set()
    graph = {}
    
    # Add all city positions as nodes
    for city in cities:
        pos = (round(city["lat"], 5), round(city["lon"], 5))
        nodes.add(pos)
        graph[pos] = []
    
    # Add segment endpoints and connect them
    for seg in segments:
        start = (round(seg["start"][0], 5), round(seg["start"][1], 5))
        end = (round(seg["end"][0], 5), round(seg["end"][1], 5))
        nodes.add(start)
        nodes.add(end)
        
        if start not in graph:
            graph[start] = []
        if end not in graph:
            graph[end] = []
        
        graph[start].append(end)
        graph[end].append(start)
    
    # Connect nodes that are very close (within ~3 miles) — helps with custom points
    node_list = list(nodes)
    for i, n1 in enumerate(node_list):
        for n2 in node_list[i+1:]:
            if haversine(n1[0], n1[1], n2[0], n2[1]) < 3.5:
                if n2 not in graph.get(n1, []):
                    graph.setdefault(n1, []).append(n2)
                    graph.setdefault(n2, []).append(n1)
    
    return graph

def are_cities_connected(graph, city1_pos, city2_pos):
    """BFS to check if two cities are connected via the highway network"""
    start = (round(city1_pos[0], 5), round(city1_pos[1], 5))
    goal = (round(city2_pos[0], 5), round(city2_pos[1], 5))
    
    if start not in graph or goal not in graph:
        return False
    if start == goal:
        return True
    
    visited = set()
    queue = deque([start])
    visited.add(start)
    
    while queue:
        current = queue.popleft()
        if current == goal:
            return True
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return False

def run_simulation(segments, cities):
    """Run traffic simulation and calculate revenue"""
    if not segments:
        return 0.0, 0.0, {"message": "Build some highways first!"}
    
    graph = build_graph(segments, cities)
    
    total_demand = 0.0
    served_demand = 0.0
    connected_pairs = []
    disconnected_pairs = []
    
    for i, c1 in enumerate(cities):
        for j in range(i + 1, len(cities)):
            c2 = cities[j]
            dist = haversine(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
            pair_demand = (c1["pop"] * c2["pop"]) / 1_800_000_000.0
            if dist > 0:
                pair_demand /= (1 + dist * 0.06)
            total_demand += pair_demand
            
            pos1 = (c1["lat"], c1["lon"])
            pos2 = (c2["lat"], c2["lon"])
            
            if are_cities_connected(graph, pos1, pos2):
                served_demand += pair_demand
                connected_pairs.append((c1["name"], c2["name"], round(pair_demand, 1), round(dist, 1)))
            else:
                disconnected_pairs.append((c1["name"], c2["name"]))
    
    served_pct = (served_demand / total_demand * 100.0) if total_demand > 0 else 0.0
    
    # Revenue model
    base_revenue = served_demand * 1.6
    connectivity_bonus = len(connected_pairs) * 12
    total_miles = sum(s["length_miles"] for s in segments)
    maintenance = total_miles * 0.8
    revenue = max(0.0, base_revenue + connectivity_bonus - maintenance)
    
    details = {
        "served_pct": round(served_pct, 1),
        "revenue": round(revenue, 1),
        "connected_pairs": connected_pairs,
        "disconnected_pairs": disconnected_pairs,
        "total_miles": round(total_miles, 1),
        "total_demand": round(total_demand, 1),
    }
    return round(served_pct, 1), round(revenue, 1), details

def create_map(built_segments):
    """Create interactive folium map with real tiles, background highways, cities, and user segments"""
    m = folium.Map(
        location=[CENTER_LAT, CENTER_LON],
        zoom_start=ZOOM_START,
        tiles="OpenStreetMap",
        control_scale=True
    )
    
    # Add background realistic existing highways
    for bg in BACKGROUND_HIGHWAYS:
        folium.PolyLine(
            locations=bg["coords"],
            color=bg["color"],
            weight=bg["weight"],
            dash_array=bg["dash"],
            tooltip=bg["name"],
            opacity=0.85
        ).add_to(m)
    
    # Add user-built highways (bright and prominent)
    for seg in built_segments:
        color = "#1565C0" if seg["type"] == "Interstate" else "#2E7D32"
        folium.PolyLine(
            locations=[seg["start"], seg["end"]],
            color=color,
            weight=6,
            tooltip=f"{seg['type']} • {seg['length_miles']} miles • ${seg['cost']}M",
            opacity=0.95,
            line_cap="round"
        ).add_to(m)
    
    # Add city markers with nice popups
    for city in CITIES:
        popup_html = f"""
        <b>{city['name']}</b><br>
        Population: {city['pop']:,}<br>
        <i>Traffic Demand Center</i>
        """
        folium.Marker(
            location=[city["lat"], city["lon"]],
            popup=folium.Popup(popup_html, max_width=220),
            icon=folium.Icon(color="red", icon="glyphicon-map-marker", prefix="glyphicon"),
            tooltip=city["name"]
        ).add_to(m)
    
    # Add a subtle title control
    title_html = '''
    <div style="position: fixed; 
                bottom: 20px; left: 20px; 
                background-color: rgba(255,255,255,0.9); 
                padding: 6px 12px; 
                border-radius: 6px; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);
                font-size: 13px; font-weight: 600; color: #1a1a1a;">
        🛣️ Highway Builder — Real Map Mode<br>
        <span style="font-size:11px; font-weight:400;">I-70 Corridor • Zoom & Pan freely</span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    return m

# ==================== INITIALIZE ====================
initialize_state()

# ==================== TOP HEADER / METRICS (non-intrusive) ====================
st.title("🛣️ Highway Builder — Real Map Edition")
st.caption("Interactive real-world map • Build Interstates & Divided Highways on actual geography • Simulate realistic traffic demand")

# Clean top metrics bar (doesn't block the map)
metric_cols = st.columns([1.8, 1.3, 1.3, 1.3, 1.3, 1.5])
with metric_cols[0]:
    st.metric("💰 Budget", f"${st.session_state.budget:,.0f}M")
with metric_cols[1]:
    total_miles = sum(s["length_miles"] for s in st.session_state.built_segments)
    st.metric("🛤️ Miles Built", f"{total_miles:.1f} mi")
with metric_cols[2]:
    interstate_miles = sum(s["length_miles"] for s in st.session_state.built_segments if s["type"] == "Interstate")
    st.metric("🛣️ Interstate", f"{interstate_miles:.1f} mi")
with metric_cols[3]:
    if st.session_state.last_sim:
        st.metric("📊 Served Demand", f"{st.session_state.last_sim['served_pct']}%")
    else:
        st.metric("📊 Served Demand", "—")
with metric_cols[4]:
    if st.session_state.last_sim:
        st.metric("💵 Last Revenue", f"+${st.session_state.last_sim['revenue']:,.0f}M")
    else:
        st.metric("💵 Last Revenue", "—")
with metric_cols[5]:
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.built_segments = []
        st.session_state.budget = INITIAL_BUDGET
        st.session_state.history = []
        st.session_state.last_sim = None
        st.rerun()

st.divider()

# ==================== MAIN INTERACTIVE MAP ====================
st.subheader("🗺️ Live Highway Map (Zoom • Pan • Explore)")

map_obj = create_map(st.session_state.built_segments)
map_data = st_folium(
    map_obj,
    width=1400,
    height=620,
    returned_objects=["last_clicked", "last_object_clicked"],
    key="main_map"
)

st.caption("The map shows real OpenStreetMap tiles + existing I-70 corridor (gray dashed). Your new highways appear in bright blue (Interstate) or green (Divided). Click cities for details.")

# ==================== CLEAN BUILD INTERFACE (below map, non-blocking) ====================
st.subheader("🚧 Build New Highway Segment")

with st.form("build_form", clear_on_submit=True):
    form_cols = st.columns([2.2, 2.2, 1.8, 1.8, 1.5])
    
    with form_cols[0]:
        start_choice = st.selectbox(
            "Start Point",
            options=["Custom coordinates"] + [c["name"] for c in CITIES],
            index=1
        )
    
    with form_cols[1]:
        end_choice = st.selectbox(
            "End Point",
            options=["Custom coordinates"] + [c["name"] for c in CITIES],
            index=2
        )
    
    with form_cols[2]:
        hwy_type = st.radio(
            "Highway Type",
            ["Interstate", "Divided Highway"],
            horizontal=True,
            help="Interstate = higher cost, higher capacity. Divided = more affordable regional roads."
        )
    
    with form_cols[3]:
        st.write("")  # spacer
        submitted = st.form_submit_button("🚀 BUILD SEGMENT", type="primary", use_container_width=True)
    
    with form_cols[4]:
        if st.form_submit_button("↩️ Undo Last", use_container_width=True):
            if st.session_state.built_segments:
                last = st.session_state.built_segments.pop()
                st.session_state.budget += last["cost"]
                st.success(f"Undid {last['type']} segment (+${last['cost']}M)")
                st.rerun()
    
    # Custom coordinate inputs (only shown if selected)
    if start_choice == "Custom coordinates" or end_choice == "Custom coordinates":
        st.markdown("**Custom Coordinates** (use map to read approximate lat/lon by zooming)")
        coord_cols = st.columns(4)
        with coord_cols[0]:
            start_lat = st.number_input("Start Latitude", value=39.2, format="%.4f", step=0.01)
        with coord_cols[1]:
            start_lon = st.number_input("Start Longitude", value=-87.8, format="%.4f", step=0.01)
        with coord_cols[2]:
            end_lat = st.number_input("End Latitude", value=39.5, format="%.4f", step=0.01)
        with coord_cols[3]:
            end_lon = st.number_input("End Longitude", value=-86.5, format="%.4f", step=0.01)
    else:
        # Auto-fill from city selection
        start_city = next(c for c in CITIES if c["name"] == start_choice)
        end_city = next(c for c in CITIES if c["name"] == end_choice)
        start_lat, start_lon = start_city["lat"], start_city["lon"]
        end_lat, end_lon = end_city["lat"], end_city["lon"]
    
    if submitted:
        if start_choice == end_choice and start_choice != "Custom coordinates":
            st.error("Start and End cannot be the same city!")
        else:
            miles, cost = get_segment_length_and_cost(start_lat, start_lon, end_lat, end_lon, hwy_type)
            
            if st.session_state.budget >= cost:
                new_seg = {
                    "type": hwy_type,
                    "start": (start_lat, start_lon),
                    "end": (end_lat, end_lon),
                    "length_miles": miles,
                    "cost": cost
                }
                st.session_state.built_segments.append(new_seg)
                st.session_state.budget -= cost
                st.success(f"✅ Built {hwy_type} • {miles} miles • Cost: ${cost}M • Budget remaining: ${st.session_state.budget:,.0f}M")
                st.rerun()
            else:
                st.error(f"❌ Not enough budget! Need ${cost}M (you have ${st.session_state.budget:,.0f}M)")

st.divider()

# ==================== TABS FOR SIMULATION, DASHBOARD, GUIDE (clean navigation) ====================
tab_sim, tab_dash, tab_guide = st.tabs([
    "🚗 Run Traffic Simulation", 
    "📊 Dashboard & Goals", 
    "📖 How to Play"
])

with tab_sim:
    st.subheader("Traffic Demand Simulation on Real Geography")
    st.write("See how well your highway network connects real cities and serves commuter + freight demand. Earn revenue based on connectivity and miles built.")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("▶️ RUN SIMULATION", type="primary", use_container_width=True):
            served_pct, revenue, details = run_simulation(
                st.session_state.built_segments, CITIES
            )
            st.session_state.budget += revenue
            st.session_state.last_sim = details
            st.session_state.history.append({
                "step": len(st.session_state.history) + 1,
                "budget": round(st.session_state.budget, 0),
                "served_pct": served_pct,
                "revenue": revenue,
                "miles": details["total_miles"]
            })
            st.success(f"Simulation complete! Served **{served_pct}%** of demand • Earned **+${revenue:,.0f}M**")
            st.rerun()
    
    with col2:
        if st.button("⏩ Fast-Forward 5 Simulations", use_container_width=True):
            total_rev = 0
            for _ in range(5):
                served_pct, revenue, details = run_simulation(st.session_state.built_segments, CITIES)
                st.session_state.budget += revenue
                total_rev += revenue
                st.session_state.history.append({
                    "step": len(st.session_state.history) + 1,
                    "budget": round(st.session_state.budget, 0),
                    "served_pct": served_pct,
                    "revenue": revenue,
                    "miles": details.get("total_miles", 0)
                })
            st.success(f"5 simulations done! Total revenue added: **+${total_rev:,.0f}M**")
            st.rerun()
    
    if st.session_state.last_sim:
        det = st.session_state.last_sim
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Demand Served", f"{det['served_pct']}%")
        m2.metric("Revenue Earned", f"+${det['revenue']:,.0f}M")
        m3.metric("Network Miles", f"{det['total_miles']:.1f} mi")
        
        if det.get("connected_pairs"):
            st.write("**✅ Connected City Pairs (traffic is flowing):**")
            for p in det["connected_pairs"]:
                st.write(f"• {p[0]} ↔ {p[1]}  • ~{p[2]} demand units • {p[3]} miles apart")
        
        if det.get("disconnected_pairs"):
            st.warning("**⚠️ Still disconnected:** Some cities cannot reach each other yet.")
            for p in det["disconnected_pairs"][:3]:
                st.write(f"• {p[0]} ↔ {p[1]}")

with tab_dash:
    st.subheader("Strategic Dashboard & Progress")
    
    # Goals
    st.markdown("### 🎯 Planning Goals")
    
    connected = 0
    total_pairs = len(CITIES) * (len(CITIES) - 1) // 2
    graph = build_graph(st.session_state.built_segments, CITIES)
    for i in range(len(CITIES)):
        for j in range(i+1, len(CITIES)):
            if are_cities_connected(graph, (CITIES[i]["lat"], CITIES[i]["lon"]), (CITIES[j]["lat"], CITIES[j]["lon"])):
                connected += 1
    connect_pct = (connected / total_pairs * 100) if total_pairs > 0 else 0
    
    st.progress(min(connect_pct/100, 1.0), text=f"Network Connectivity: {connected}/{total_pairs} city pairs linked ({connect_pct:.0f}%)")
    
    if connect_pct >= 100:
        st.success("🏆 Excellent! All major cities are fully connected on your network.")
    elif connect_pct >= 60:
        st.info("Strong progress — focus on the remaining disconnected pairs for big revenue.")
    else:
        st.warning("Keep building connections between the cities to unlock more revenue.")
    
    st.divider()
    
    # History chart
    if len(st.session_state.history) >= 2:
        st.markdown("### 📈 Performance Over Time")
        hist = st.session_state.history
        chart_data = {
            "Simulation": [h["step"] for h in hist],
            "Budget ($M)": [h["budget"] for h in hist],
            "Demand Served %": [h["served_pct"] for h in hist],
        }
        st.line_chart(chart_data, x="Simulation", y=["Budget ($M)", "Demand Served %"])
    else:
        st.info("Run simulations to see your budget growth and performance chart here.")
    
    st.caption("Tip: The more realistic miles you build and the better you connect high-demand cities, the faster your budget grows.")

with tab_guide:
    st.subheader("📖 How to Play — Real Map Highway Builder")
    st.markdown("""
    This is an upgraded version with a **real interactive map** (OpenStreetMap tiles), real geographic coordinates, and realistic background highway data (approximate I-70 corridor).
    
    ### How to Build
    1. Use the **Build form** below the map.
    2. Choose start and end points (cities or custom lat/lon — zoom the map and read coordinates if needed).
    3. Pick Interstate (premium, higher cost) or Divided Highway.
    4. Click **BUILD SEGMENT** — it calculates real-world distance in miles and deducts the correct cost.
    5. Your new highway appears instantly on the map in bright color.
    
    ### Simulation & Revenue
    - Click **Run Simulation** to see which cities are connected via your network.
    - You earn revenue based on served demand + connectivity bonus.
    - Revenue is added to your budget so you can keep building.
    
    ### Tips for Success (Real Planning Principles)
    - Connect the largest cities first for maximum demand.
    - Use **Interstates** for the main long corridors.
    - Use **Divided Highways** for shorter regional links or branches.
    - Build logical routes that follow natural geography.
    - Watch the connectivity % in the Dashboard — aim for 100%.
    
    The map is fully interactive — zoom in/out and pan freely. This gives you a much more realistic planning experience than a fixed grid.
    
    Enjoy designing your real-world interstate system!
    """)

st.divider()
st.caption("🛣️ Highway Builder v2 — Real Map Edition • Built with Streamlit + Folium • Educational transportation planning simulator • Deploy on Replit or Streamlit Cloud from GitHub")
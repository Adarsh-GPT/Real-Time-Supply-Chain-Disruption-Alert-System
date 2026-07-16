"""pages/2_🗺️_Risk_Map.py — Geographic view of supply chain risks."""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Risk Map • SupplyRadar", page_icon="🗺️", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

# ── Load routing data ─────────────────────────────────────────────────────────
@st.cache_data
def load_map_data():
    path = Path("config/shipping_routes.json")
    if not path.exists():
        return {"ports": [], "shipping_routes": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

map_data = load_map_data()
PORTS = {p["name"]: p for p in map_data.get("ports", [])}

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🗺️ Global Supply Chain Risk Map")
st.markdown("Visualising disruptions across major global ports and shipping lanes.")

# ── Try to load cached articles ───────────────────────────────────────────────
# In a real app, you might fetch again, but here we reuse the dashboard cache if available
from core.ingestion import fetch_all_sources
from core.processor import process_batch
from core.risk_engine import score_batch

@st.cache_data(ttl=900, show_spinner=False)
def get_map_articles():
    articles = fetch_all_sources()
    processed = process_batch(articles)
    watchlist = st.session_state.get("watchlist", {})
    return score_batch(processed, watchlist)

with st.spinner("Loading map data..."):
    try:
        articles = get_map_articles()
    except Exception:
        articles = []

# ── Process risks per port ────────────────────────────────────────────────────
port_risks = {}
for p_name, p_data in PORTS.items():
    port_risks[p_name] = {"lat": p_data["lat"], "lng": p_data["lng"], "high": 0, "medium": 0, "low": 0, "articles": [], "volume_rank": p_data.get("volume_rank", 999)}

for a in articles:
    text_lower = a.get("raw_text", "").lower()
    for p_name in PORTS.keys():
        if p_name.lower().replace("port of ", "") in text_lower or p_name.lower() in text_lower:
            r_level = a.get("risk_level", "Low")
            port_risks[p_name][r_level.lower()] += 1
            port_risks[p_name]["articles"].append(a)

# ── Map Settings ──────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1])

with col2:
    st.markdown("#### Map Layers")
    show_routes = st.checkbox("Show Major Shipping Routes", value=True)
    show_safe_ports = st.checkbox("Show Safe Ports (No active alerts)", value=False)
    
    st.markdown("#### Active Port Alerts")
    active_ports = {k: v for k, v in port_risks.items() if v["high"] > 0 or v["medium"] > 0}
    if not active_ports:
        st.info("No active port disruptions detected.")
    else:
        for p_name, p_data in active_ports.items():
            if p_data["high"] > 0:
                st.markdown(f"🔴 **{p_name}** ({p_data['high']} High, {p_data['medium']} Med)")
            else:
                st.markdown(f"🟡 **{p_name}** ({p_data['medium']} Med)")

# ── Build Folium Map ──────────────────────────────────────────────────────────
with col1:
    m = folium.Map(location=[20.0, 0.0], zoom_start=2, tiles="CartoDB dark_matter")

    if show_routes:
        for route in map_data.get("shipping_routes", []):
            folium.PolyLine(
                locations=route["waypoints"],
                color="#00C853", # Neon green for shipping routes to look futuristic
                weight=2,
                opacity=0.4,
                tooltip=route["name"]
            ).add_to(m)

    for p_name, data in port_risks.items():
        total_alerts = data["high"] + data["medium"] + data["low"]
        
        if total_alerts == 0 and not show_safe_ports:
            continue
            
        rank = data.get("volume_rank", 999)
        
        # Determine color based on highest risk
        if data["high"] > 0:
            color = "#FF0000"
            icon_color = "red"
            risk_multiplier = data["high"] * 2
        elif data["medium"] > 0:
            color = "#FFA500"
            icon_color = "orange"
            risk_multiplier = data["medium"] * 2
        elif data["low"] > 0:
            color = "#008000"
            icon_color = "green"
            risk_multiplier = 0
        else:
            color = "#3388ff"
            icon_color = "blue"
            risk_multiplier = 0

        html_popup = f"<div style='font-family:sans-serif;width:250px'>"
        html_popup += f"<h4>{p_name}</h4>"
        html_popup += f"<div style='color:#bbb;font-size:13px;margin-bottom:8px'>Global Volume Rank: #{rank if rank != 999 else 'N/A'}</div>"
        if total_alerts > 0:
            html_popup += f"<b>Alerts:</b> 🔴 {data['high']} &nbsp; 🟡 {data['medium']} &nbsp; 🟢 {data['low']}<br><hr>"
            for a in data["articles"][:3]:  # show top 3
                html_popup += f"<div style='font-size:12px;margin-bottom:6px;'>• {a.get('raw_text')}</div>"
            if len(data["articles"]) > 3:
                html_popup += f"<div style='font-size:12px;color:#666;'>+ {len(data['articles'])-3} more...</div>"
        else:
            html_popup += "No active alerts."
        html_popup += "</div>"
        
        popup_obj = folium.Popup(html_popup, max_width=300)

        # Apply specific markers based on port rank
        if rank <= 5:
            # MEGA PORT: Unique sign (Star marker)
            folium.Marker(
                location=[data["lat"], data["lng"]],
                icon=folium.Icon(icon="star", prefix="fa", color=icon_color),
                popup=popup_obj,
                tooltip=f"⭐ MEGA PORT: {p_name}"
            ).add_to(m)
        elif rank <= 15:
            # NORMAL/LARGE PORT: Standard CircleMarker
            base_radius = 12
            folium.CircleMarker(
                location=[data["lat"], data["lng"]],
                radius=min(base_radius + risk_multiplier, 30),
                color="black", weight=1, fill=True, fill_color=color, fill_opacity=0.8,
                popup=popup_obj, tooltip=f"🚢 {p_name}"
            ).add_to(m)
        else:
            # SMALL PORT: Smaller CircleMarker
            base_radius = 6
            folium.CircleMarker(
                location=[data["lat"], data["lng"]],
                radius=min(base_radius + risk_multiplier, 20),
                color="black", weight=1, fill=True, fill_color=color, fill_opacity=0.8,
                popup=popup_obj, tooltip=p_name
            ).add_to(m)

    st_folium(m, width=1000, height=600, returned_objects=[])

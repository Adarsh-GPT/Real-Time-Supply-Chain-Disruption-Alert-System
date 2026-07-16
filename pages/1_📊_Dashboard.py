"""pages/1_📊_Dashboard.py — Live risk feed with auto-refresh."""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="Dashboard • SupplyRadar", page_icon="📊", layout="wide")

# ── Auth guard ────────────────────────────────────────────────────────────────
if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}

.metric-card {
    background: var(--secondary-background-color);
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid var(--border-color);
    text-align: center;
}
.metric-number { font-size: 2.4rem; font-weight: 700; line-height: 1; }
.metric-label { font-size: 0.85rem; color: #8899aa; margin-top: 4px; }

.risk-card {
    background: var(--secondary-background-color);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0;
    border: 1px solid var(--border-color);
    border-left: 5px solid;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    transition: transform 0.2s, box-shadow 0.2s;
}
.risk-card:hover { 
    transform: translateY(-2px); 
    box-shadow: 0 8px 24px rgba(0,0,0,0.1); 
}
.risk-high { border-left-color: #FF4B4B; }
.risk-medium { border-left-color: #FFD600; }
.risk-low { border-left-color: #00C853; }

.badge { display:inline-block; padding:2px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; margin-right:6px; }
.badge-high { background:rgba(255,75,75,0.2); color:#FF4B4B; border:1px solid #FF4B4B; }
.badge-medium { background:rgba(255,214,0,0.2); color:#FFD600; border:1px solid #FFD600; }
.badge-low { background:rgba(0,200,83,0.15); color:#00C853; border:1px solid #00C853; }
.badge-watchlist { background:rgba(100,181,246,0.2); color:#64b5f6; border:1px solid #64b5f6; }

.headline-text { font-size: 1rem; font-weight: 600; margin-bottom: 6px; }
.headline-link { color: var(--text-color); text-decoration: none; transition: color 0.2s; }
.headline-link:hover { color: var(--primary-color); text-decoration: none; }
.meta-row { font-size: 0.78rem; color: #8899aa; }
.impact-text { font-size: 0.82rem; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Auto-refresh (every 15 min) ───────────────────────────────────────────────
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=15 * 60 * 1000, key="dashboard_refresh")

# ── Fetch Data Function ───────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def get_dashboard_data(search_query: str = ""):
    from config.settings import settings
    if settings.has_firebase:
        from core.firebase_db import get_recent_articles
        return get_recent_articles(limit=100)
    else:
        from core.ingestion import fetch_all_sources
        from core.processor import process_batch
        # days_back=0 forces it to fetch news strictly from today (live)
        from core.ingestion import SUPPLY_CHAIN_QUERY
        final_query = search_query if search_query else SUPPLY_CHAIN_QUERY
        return process_batch(fetch_all_sources(query=final_query, days_back=0))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    profile = st.session_state.get("user_profile", {})
    st.markdown(f"### 👋 {profile.get('name', 'User')}")
    industry_name = profile.get('industry_name', 'All Industries')
    st.caption(f"🏭 {industry_name}")
    st.markdown("---")
    
    st.markdown("**Filters**")
    
    filter_risk = st.multiselect(
        "Risk Level",
        ["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
        key="filter_risk"
    )
    
    import yaml
    categories_cfg = yaml.safe_load(open("config/thresholds.yaml", encoding="utf-8"))["categories"]
    cat_options = {cid: f"{cdata['icon']} {cid.replace('_',' ').title()}" for cid, cdata in categories_cfg.items()}
    cat_options["general"] = "📰 General"
    filter_cats = st.multiselect(
        "Category",
        list(cat_options.keys()),
        default=list(cat_options.keys()),
        format_func=lambda x: cat_options.get(x, x),
        key="filter_cats"
    )
    
    watchlist_only = st.toggle("🎯 Watchlist matches only", value=False)
    
    st.markdown("---")
    if st.button("🔄 Fetch Latest News (15+ Items)", type="primary", use_container_width=True):
        get_dashboard_data.clear()
        st.rerun()
    
    if st.button("🚪 Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.switch_page("app.py")


with st.spinner("Loading live data from secure cloud..."):
    # Smart dynamic query: Fetches news relevant to the user's specific industry + supply chain/disruptions
    industry_term = industry_name.replace("&", "").strip() if industry_name != "All Industries" else ""
    if industry_term:
        dynamic_query = f'"{industry_term}" AND (supply chain OR disruption OR logistics OR shipping)'
    else:
        dynamic_query = ""
        
    articles = get_dashboard_data(dynamic_query)

# Re-score against the logged-in user's watchlist so their dashboard shows personalized hits
from core.risk_engine import score_batch
wl = st.session_state.get("watchlist", {})
articles = score_batch(articles, wl)

from core.risk_engine import compute_summary_stats
stats = compute_summary_stats(articles)

# Alerts are now handled securely by the backend worker.py

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📡 SupplyRadar — Live Risk Feed")
last_updated = datetime.now().strftime("%d %b %Y, %H:%M")
st.caption(f"Last updated: {last_updated} • {stats['total']} articles analysed")

# ── Metric Cards ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number" style="color:#FF4B4B">🔴 {stats['high']}</div>
        <div class="metric-label">HIGH Risk Alerts</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number" style="color:#FFD600">🟡 {stats['medium']}</div>
        <div class="metric-label">MEDIUM Risk Events</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number" style="color:#64b5f6">🎯 {stats['watchlist_hits']}</div>
        <div class="metric-label">Watchlist Matches</div>
    </div>""", unsafe_allow_html=True)
with c4:
    score_color = "#FF4B4B" if stats['avg_score'] >= 0.6 else "#FFD600" if stats['avg_score'] >= 0.3 else "#00C853"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number" style="color:{score_color}">{stats['avg_score']:.2f}</div>
        <div class="metric-label">Avg Risk Score</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Filter articles ───────────────────────────────────────────────────────────
filtered = [
    a for a in articles
    if a.get("risk_level") in filter_risk
    and a.get("category", {}).get("id", "general") in filter_cats
    and (not watchlist_only or a.get("watchlist_match", {}).get("is_watchlist_hit"))
]

if not filtered:
    st.info("No articles match your current filters. Adjust the sidebar filters.")
else:
    st.markdown(f"### Showing {len(filtered)} disruption events")
    
    # Sort so that watchlist/industry matches are at the top
    filtered = sorted(filtered, key=lambda x: x.get("watchlist_match", {}).get("is_watchlist_hit", False), reverse=True)
    
    for article in filtered:
        risk_level = article.get("risk_level", "Low")
        cat = article.get("category", {})
        wl = article.get("watchlist_match", {})
        impact = article.get("impact_badge", "")
        pub = article.get("published_at", "")[:10]
        source = article.get("source_name", "")
        url = article.get("url", "")
        score = article.get("hybrid_score", 0)
        matched_items = [m["item"] for m in wl.get("matched", [])][:3]

        css_class = f"risk-{risk_level.lower()}"
        badge_class = f"badge-{risk_level.lower()}"
        risk_icon = article.get("risk_icon", "⚪")

        watchlist_badge = ""
        is_hit = wl.get("is_watchlist_hit", False)
        if is_hit and matched_items:
            watchlist_badge = f'<span class="badge badge-watchlist">🔥 Industry Match: {", ".join(matched_items)}</span>'
        elif matched_items:
            watchlist_badge = f'<span class="badge badge-watchlist">🎯 {", ".join(matched_items)}</span>'

        headline_link = f'<a href="{url}" class="headline-link" target="_blank">{article.get("raw_text","")}</a>' if url else article.get("raw_text", "")

        html_content = f"""<div class="risk-card {css_class}">
<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
<span class="badge {badge_class}">{risk_icon} {risk_level}</span>
<span class="badge" style="background:rgba(255,255,255,0.05);color:#aaa;border:1px solid #333">
{cat.get('icon','📰')} {cat.get('label','General')}
</span>
{watchlist_badge}
<span style="margin-left:auto;font-size:0.78rem;color:#8899aa;">Score: {score:.2f}</span>
</div>
<div class="headline-text">{headline_link}</div>
<div class="meta-row">📰 {source} &nbsp;|&nbsp; 📅 {pub}</div>
<div class="impact-text" style="color:#b0bec5">{impact}</div>
</div>"""
        st.markdown(html_content, unsafe_allow_html=True)

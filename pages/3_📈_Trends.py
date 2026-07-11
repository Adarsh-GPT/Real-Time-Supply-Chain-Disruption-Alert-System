"""pages/3_📈_Trends.py — Historical risk trends and analytics."""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="Trends • SupplyRadar", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

st.markdown("## 📈 Risk Trends & Analytics")

# ── Load Historical Data ──────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_trend_data():
    from config.settings import settings
    if settings.has_firebase:
        try:
            from core.firebase_db import get_articles_for_trend
            return get_articles_for_trend(days=30)
        except Exception as e:
            st.warning(f"Could not load history from Firebase: {e}")
            return []
    else:
        # Demo mode: generate some fake historical data
        import random
        demo_data = []
        now = datetime.now(timezone.utc)
        categories = ["weather", "labor", "geopolitical", "infrastructure", "trade", "pandemic"]
        levels = ["High", "Medium", "Low"]
        
        for i in range(200):
            days_ago = random.randint(0, 30)
            date = (now - timedelta(days=days_ago)).isoformat()
            r_level = random.choices(levels, weights=[0.2, 0.3, 0.5])[0]
            score = random.uniform(0.6, 1.0) if r_level == "High" else random.uniform(0.3, 0.59) if r_level == "Medium" else random.uniform(0.0, 0.29)
            
            demo_data.append({
                "id": f"demo-{i}",
                "raw_text": f"Historical disruption event {i}",
                "ingested_at": date,
                "risk_level": r_level,
                "hybrid_score": score,
                "category": {"id": random.choice(categories), "label": "Demo Category"}
            })
        return demo_data

with st.spinner("Loading analytics..."):
    articles = load_trend_data()

if not articles:
    st.info("Not enough historical data collected yet. Check back in a few days!")
    st.stop()

df = pd.DataFrame(articles)
df["date"] = pd.to_datetime(df["ingested_at"]).dt.date
df["cat_id"] = df["category"].apply(lambda x: x.get("id", "general") if isinstance(x, dict) else "general")

# ── Chart 1: Alerts over time ─────────────────────────────────────────────────
st.markdown("#### Alerts Volume (Last 30 Days)")
daily_counts = df.groupby(["date", "risk_level"]).size().reset_index(name="count")

# Ensure all dates/levels exist for smooth lines
all_dates = pd.date_range(end=datetime.now().date(), periods=30).date
full_idx = pd.MultiIndex.from_product([all_dates, ["High", "Medium", "Low"]], names=["date", "risk_level"])
daily_counts = daily_counts.set_index(["date", "risk_level"]).reindex(full_idx, fill_value=0).reset_index()

fig1 = px.line(
    daily_counts, 
    x="date", 
    y="count", 
    color="risk_level",
    color_discrete_map={"High": "#FF4B4B", "Medium": "#FFD600", "Low": "#00C853"},
    template="plotly_dark",
    markers=True
)
fig1.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0), legend_title="")
st.plotly_chart(fig1, use_container_width=True)

col1, col2 = st.columns(2)

# ── Chart 2: Category Breakdown ───────────────────────────────────────────────
with col1:
    st.markdown("#### Disruptions by Category")
    cat_counts = df["cat_id"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    fig2 = px.pie(
        cat_counts, 
        names="Category", 
        values="Count", 
        hole=0.4,
        template="plotly_dark"
    )
    fig2.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
    st.plotly_chart(fig2, use_container_width=True)

# ── Chart 3: Average Risk Score ───────────────────────────────────────────────
with col2:
    st.markdown("#### Average Daily Risk Score")
    daily_score = df.groupby("date")["hybrid_score"].mean().reset_index()
    
    fig3 = px.bar(
        daily_score, 
        x="date", 
        y="hybrid_score",
        template="plotly_dark",
        color="hybrid_score",
        color_continuous_scale=["#00C853", "#FFD600", "#FF4B4B"],
        range_color=[0.2, 0.8]
    )
    fig3.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0), coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

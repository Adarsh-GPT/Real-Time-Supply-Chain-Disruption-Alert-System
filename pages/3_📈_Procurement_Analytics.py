"""pages/3_📈_Procurement_Analytics.py — Analytics showcase."""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Procurement Analytics • SupplyRadar", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

# Smartly hide/block this page for non-hospitality users
user_profile = st.session_state.get("user_profile", {})
if user_profile.get("industry") != "hospitality_procurement":
    st.warning("This advanced analytics module is exclusively available for the **Hospitality & Procurement** industry.")
    st.stop()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.header-box { background: var(--secondary-background-color); padding: 1.5rem; border-radius: 10px; border: 1px solid var(--border-color); margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h2>📈 Procurement & Spend Analytics</h2>
    <p style="color:#8899aa;">Power BI-style interactive dashboards showcasing advanced data analysis, risk distribution, and historical spend tracking.</p>
</div>
""", unsafe_allow_html=True)

@st.cache_data
def load_analytics_data():
    """Generates mock data for analytics."""
    np.random.seed(10)
    categories = ['F&B', 'Linens', 'Cleaning Supplies', 'Furniture', 'IT Equipment']
    suppliers = ['Sysco', 'US Foods', 'Ecolab', 'Marriott Supply', 'Dell', 'HP', 'P&G']
    
    data = {
        'Date': [datetime.today() - timedelta(days=i) for i in range(100)],
        'Category': np.random.choice(categories, 100),
        'Supplier': np.random.choice(suppliers, 100),
        'Spend_USD': np.random.uniform(1000, 50000, 100),
        'Risk_Score': np.random.normal(50, 15, 100).clip(0, 100)
    }
    return pd.DataFrame(data)

df = load_analytics_data()

# Top KPIs
st.markdown("### Key Performance Indicators")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Total Spend (YTD)", f"${df['Spend_USD'].sum():,.0f}")
kpi2.metric("Active Suppliers", df['Supplier'].nunique())
kpi3.metric("Avg Risk Score", f"{df['Risk_Score'].mean():.1f}", delta="-2.5", delta_color="inverse")
kpi4.metric("Critical Alerts", len(df[df['Risk_Score'] > 75]))

st.markdown("---")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Spend by Category")
    spend_by_cat = df.groupby('Category')['Spend_USD'].sum().reset_index()
    fig_pie = px.pie(spend_by_cat, values='Spend_USD', names='Category', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig_pie, use_container_width=True)

with col2:
    st.markdown("#### Supplier Risk Distribution")
    fig_hist = px.histogram(df, x='Risk_Score', nbins=20, color_discrete_sequence=['#FF4B4B'])
    fig_hist.update_layout(bargap=0.1)
    st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("#### Historical Spend Trend")
spend_trend = df.groupby(df['Date'].dt.to_period('W'))['Spend_USD'].sum().reset_index()
spend_trend['Date'] = spend_trend['Date'].dt.to_timestamp()
fig_line = px.line(spend_trend, x='Date', y='Spend_USD', markers=True, color_discrete_sequence=['#64b5f6'])
st.plotly_chart(fig_line, use_container_width=True)

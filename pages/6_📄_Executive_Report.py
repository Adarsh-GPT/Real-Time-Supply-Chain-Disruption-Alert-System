"""pages/6_📄_Executive_Report.py — Downloadable PDF summaries."""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Executive Report • SupplyRadar", page_icon="📄", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

st.markdown("## 📄 Executive Summary Report")
st.markdown("Generate a 1-page PDF briefing of current supply chain disruptions, tailored to your watchlist. Perfect for morning briefings or C-suite updates.")

# ── Fetch Data ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def load_report_articles():
    from core.ingestion import fetch_all_sources
    from core.processor import process_batch
    from core.risk_engine import score_batch
    articles = fetch_all_sources()
    processed = process_batch(articles)
    watchlist = st.session_state.get("watchlist", {})
    return score_batch(processed, watchlist)

with st.spinner("Compiling data..."):
    try:
        articles = load_report_articles()
    except Exception as e:
        st.error(f"Failed to load articles: {e}")
        articles = []

if not articles:
    st.info("No data available to generate a report.")
    st.stop()

from core.risk_engine import compute_summary_stats
stats = compute_summary_stats(articles)

# ── UI Preview ────────────────────────────────────────────────────────────────
st.markdown("### Report Preview")
col1, col2, col3 = st.columns(3)
col1.metric("Total Events Analyzed", stats['total'])
col2.metric("Critical Watchlist Impacts", stats['watchlist_hits'])
col3.metric("Global High Risks", stats['high'])

st.markdown("---")

# ── Generate PDF Button ───────────────────────────────────────────────────────
from core.reports import generate_executive_pdf
import time

profile = st.session_state.get("user_profile", {})

col_btn, _ = st.columns([1, 2])
with col_btn:
    with st.spinner("Generating PDF..."):
        try:
            pdf_bytes = generate_executive_pdf(articles, profile)
            
            from datetime import datetime
            filename = f"SupplyRadar_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            
            st.download_button(
                label="⬇️ Download Executive PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")

st.markdown("---")
st.caption("The report includes your tailored watchlist impacts followed by major global risk events. It automatically estimates shipping delays based on our impact matrix.")

"""pages/4_🔍_Search.py — Search historical alerts."""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Search • SupplyRadar", page_icon="🔍", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

st.markdown("## 🔍 Historical Disruption Search")
st.markdown("Search past disruptions by keyword, supplier, or port.")

query = st.text_input("Search query", placeholder="e.g. 'Shanghai port strike' or 'TSMC'", key="search_query")

col1, col2 = st.columns(2)
with col1:
    limit = st.slider("Max results", 10, 100, 50)
with col2:
    min_risk = st.selectbox("Minimum Risk Level", ["All", "High", "Medium"], index=0)

if st.button("Search", type="primary"):
    if not query.strip():
        st.warning("Please enter a search query.")
        st.stop()
        
    with st.spinner("Searching..."):
        from config.settings import settings
        if settings.has_firebase:
            from core.firebase_db import search_articles
            results = search_articles(query, limit=200)
        else:
            # Live Deep-Dive Search: Actively fetch fresh news for this keyword from the web
            from core.ingestion import fetch_all_sources
            from core.processor import process_batch
            from core.risk_engine import score_batch
            
            # Fetch up to 7 days back for this specific search query
            raw = fetch_all_sources(query=query, days_back=7)
            processed = process_batch(raw)
            results = score_batch(processed, st.session_state.get("watchlist", {}))
            
        if min_risk == "High":
            results = [r for r in results if r.get("risk_level") == "High"]
        elif min_risk == "Medium":
            results = [r for r in results if r.get("risk_level") in ["High", "Medium"]]
            
        results = results[:limit]
        
    if not results:
        st.info("No matching disruptions found.")
    else:
        st.success(f"Found {len(results)} matching events.")
        
        # Display as a table
        table_data = []
        for r in results:
            table_data.append({
                "Date": r.get("published_at", "")[:10],
                "Risk": r.get("risk_level", "Low"),
                "Headline": r.get("raw_text", ""),
                "Source": r.get("source_name", ""),
                "Score": round(r.get("hybrid_score", 0), 2)
            })
            
        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            column_config={
                "Risk": st.column_config.TextColumn("Risk", help="Risk Level"),
                "Score": st.column_config.ProgressColumn("Score", format="%.2f", min_value=0, max_value=1),
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Download button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download CSV",
            data=csv,
            file_name=f'supply_radar_search_{query.replace(" ", "_")}.csv',
            mime='text/csv',
        )

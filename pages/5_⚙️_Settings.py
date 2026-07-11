"""pages/5_⚙️_Settings.py — User watchlist configuration."""
import streamlit as st

st.set_page_config(page_title="Settings • SupplyRadar", page_icon="⚙️", layout="wide")

if not st.session_state.get("authenticated"):
    st.switch_page("app.py")

st.markdown("## ⚙️ Settings & Watchlist")
st.markdown("""
Your watchlist is the core of SupplyRadar. The risk engine uses these keywords to 
identify disruptions that specifically affect **your** supply chain.
""")

wl = st.session_state.get("watchlist", {"companies": [], "ports": [], "commodities": [], "countries": []})

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏢 Key Suppliers / Companies")
    comps = st.text_area(
        "One per line", 
        value="\n".join(wl.get("companies", [])),
        height=150,
        help="E.g. TSMC, Samsung, Foxconn"
    )
    
    st.markdown("### ⚓ Key Ports / Hubs")
    ports = st.text_area(
        "One per line", 
        value="\n".join(wl.get("ports", [])),
        height=150,
        help="E.g. Shanghai, Rotterdam, Los Angeles"
    )

with col2:
    st.markdown("### 📦 Critical Commodities")
    comms = st.text_area(
        "One per line", 
        value="\n".join(wl.get("commodities", [])),
        height=150,
        help="E.g. Semiconductors, Lithium, Steel"
    )
    
    st.markdown("### 🌍 Key Countries")
    ctrys = st.text_area(
        "One per line", 
        value="\n".join(wl.get("countries", [])),
        height=150,
        help="E.g. Taiwan, China, Vietnam"
    )

st.markdown("---")

if st.button("💾 Save Watchlist", type="primary", use_container_width=True):
    new_wl = {
        "companies": [x.strip() for x in comps.split("\n") if x.strip()],
        "ports": [x.strip() for x in ports.split("\n") if x.strip()],
        "commodities": [x.strip() for x in comms.split("\n") if x.strip()],
        "countries": [x.strip() for x in ctrys.split("\n") if x.strip()],
    }
    
    st.session_state.watchlist = new_wl
    
    from config.settings import settings
    if settings.has_firebase:
        from core.firebase_db import save_watchlist
        try:
            save_watchlist(st.session_state.uid, new_wl)
            st.success("Watchlist saved to database! Dashboard risk scores will now use these settings.")
        except Exception as e:
            st.error(f"Failed to save: {e}")

st.markdown("---")
st.markdown("### 🔒 Account Security")
with st.expander("Change Password"):
    new_pw = st.text_input("New Password", type="password")
    if st.button("Update Password"):
        if len(new_pw) < 6:
            st.error("Password must be at least 6 characters.")
        else:
            try:
                from core.firebase_db import auth_change_password
                auth_change_password(st.session_state.id_token, new_pw)
                st.success("Password successfully updated!")
            except Exception as e:
                st.error(f"Failed to update password: {e}")

st.markdown("---")
with st.expander("PDF Report Configuration"):
    st.markdown("Feature completed in Phase 6. Use the Executive Report page to generate PDFs.")
    
with st.expander("Telegram Alerts"):
    from config.settings import settings
    if settings.telegram_bot_token and settings.telegram_chat_id:
        st.success("✅ Telegram alerts are configured!")
        if st.button("Send Test Alert"):
            from core.alerts import send_telegram_message
            test_msg = "👋 <b>Hello from SupplyRadar!</b>\n\nYour Telegram integration is working perfectly. You will now receive push notifications for HIGH risk events that match your watchlist."
            if send_telegram_message(settings.telegram_bot_token, settings.telegram_chat_id, test_msg):
                st.toast("Test alert sent to Telegram!", icon="✅")
            else:
                st.error("Failed to send test alert. Check your Bot Token and Chat ID.")
    else:
        st.warning("⚠️ Telegram alerts are NOT configured.")
        st.markdown("""
        **How to set up:**
        1. Message [@BotFather](https://t.me/BotFather) on Telegram and type `/newbot` to create a bot.
        2. Copy the API Token it gives you.
        3. Message [@userinfobot](https://t.me/userinfobot) to get your Chat ID.
        4. Open your `.env` file and add:
        ```env
        TELEGRAM_BOT_TOKEN=your_token_here
        TELEGRAM_CHAT_ID=your_chat_id_here
        ```
        5. Restart the Streamlit app.
        """)

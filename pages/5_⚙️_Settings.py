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
    
with st.expander("📱 Personal Telegram Alerts"):
    st.markdown("Receive instant push notifications on your phone for HIGH risk events matching your watchlist.")
    
    # Load user's personal telegram settings
    profile = st.session_state.get("user_profile", {})
    t_bot = profile.get("telegram_bot_token", "")
    t_chat = profile.get("telegram_chat_id", "")
    
    bot_in = st.text_input("Your Bot Token", value=t_bot, type="password", help="Create a bot via @BotFather on Telegram")
    chat_in = st.text_input("Your Chat ID", value=t_chat, help="Get this from @userinfobot")
    
    if st.button("Save Telegram Settings"):
        profile["telegram_bot_token"] = bot_in
        profile["telegram_chat_id"] = chat_in
        st.session_state.user_profile = profile
        
        # Save to demo DB
        from core.demo_db import save_demo_user
        save_demo_user(st.session_state.email, profile, st.session_state.watchlist)
        st.success("✅ Personal Telegram settings saved!")
        
    if bot_in and chat_in:
        if st.button("Send Test Alert"):
            from core.alerts import send_telegram_message
            test_msg = "👋 <b>Hello from SupplyRadar!</b>\n\nYour personal Telegram integration is working perfectly."
            if send_telegram_message(bot_in, chat_in, test_msg):
                st.toast("Test alert sent to Telegram!", icon="✅")
            else:
                st.error("Failed to send test alert. Check your Bot Token and Chat ID.")

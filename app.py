"""app.py — SupplyRadar main entry point.
Handles login/register with industry selection, then redirects to Dashboard.
"""
import streamlit as st
import yaml
from pathlib import Path

st.set_page_config(
    page_title="SupplyRadar — Supply Chain Intelligence",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');

/* Animated Premium Dark Gradient Background */
.stApp {
    background: linear-gradient(-45deg, #020617, #0f172a, #1e1b4b, #172554);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

html, body, [class*="css"] { 
    font-family: 'Outfit', sans-serif; 
}

/* Glassmorphism Container */
.login-container {
    max-width: 480px;
    margin: 0 auto;
    padding: 3rem;
    background: rgba(15, 23, 42, 0.7) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-radius: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 25px 50px -12px rgba(0,0,0,0.8);
}

.logo-text {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #38bdf8, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.2rem;
    letter-spacing: -1px;
}

.logo-sub {
    text-align: center;
    color: #94a3b8;
    font-size: 1.1rem;
    font-weight: 400;
    margin-bottom: 2.5rem;
    letter-spacing: 0.5px;
}

/* Interactive Industry Cards */
.industry-card {
    background: rgba(30, 41, 59, 0.5);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 12px 16px;
    margin: 6px 0;
    cursor: pointer;
    color: #e2e8f0;
    font-weight: 500;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.industry-card:hover { 
    border-color: #38bdf8;
    transform: translateY(-2px);
    box-shadow: 0 8px 15px rgba(56, 189, 248, 0.2);
    background: rgba(30, 41, 59, 0.8);
}

.error-box {
    background: rgba(255,75,75,0.1);
    border: 1px solid #FF4B4B;
    border-radius: 8px;
    padding: 10px 14px;
    color: #FF4B4B;
    margin: 8px 0;
}
.success-box {
    background: rgba(0,200,83,0.1);
    border: 1px solid #00C853;
    border-radius: 8px;
    padding: 10px 14px;
    color: #00C853;
    margin: 8px 0;
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    .login-container {
        padding: 1.5rem !important;
        margin: 1rem !important;
        border-radius: 16px;
    }
    .logo-text {
        font-size: 2.2rem !important;
    }
    .logo-sub {
        font-size: 0.9rem !important;
        margin-bottom: 1.5rem;
    }
    .industry-card {
        padding: 10px;
        font-size: 0.9rem;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("authenticated", False),
    ("uid", None),
    ("email", None),
    ("id_token", None),
    ("user_profile", {}),
    ("watchlist", {}),
    ("articles_cache", []),
    ("last_fetch_time", None),
    ("sent_alerts", set()),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Load industries ───────────────────────────────────────────────────────────
@st.cache_data
def load_industries():
    path = Path("config/industries.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["industries"]

INDUSTRIES = load_industries()

# ── If already logged in, redirect ───────────────────────────────────────────
if st.session_state.authenticated:
    st.switch_page("pages/1_📊_Dashboard.py")

# ── Login / Register UI ───────────────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 1.2, 1])
with col2:
    st.markdown('<div class="logo-text">📡 SupplyRadar</div>', unsafe_allow_html=True)
    st.markdown('<div class="logo-sub">Real-Time Supply Chain Intelligence</div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["🔑 Sign In", "✨ Create Account"])

    # ── Login Tab ─────────────────────────────────────────────────────────────
    with tab_login:
        email_in = st.text_input("Email", placeholder="you@company.com", key="login_email")
        pass_in = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
        
        if st.button("Sign In →", type="primary", use_container_width=True):
            if not email_in or not pass_in:
                st.markdown('<div class="error-box">Please enter your email and password.</div>', unsafe_allow_html=True)
            else:
                from config.settings import settings
                if not settings.has_firebase:
                    # Demo mode — no Firebase needed
                    st.session_state.authenticated = True
                    st.session_state.uid = "demo-user"
                    st.session_state.email = email_in
                    
                    # Fetch from local demo DB if exists, otherwise fallback to parsing email
                    from core.demo_db import get_demo_user
                    user_data = get_demo_user(email_in)
                    
                    if user_data:
                        st.session_state.user_profile = user_data["profile"]
                        st.session_state.watchlist = user_data["watchlist"]
                    else:
                        name_prefix = email_in.split("@")[0].replace(".", " ").title() if email_in else "User"
                        st.session_state.user_profile = {
                            "name": name_prefix,
                            "industry": "hospitality_procurement",
                            "industry_name": "Hospitality & Procurement",
                        }
                        st.session_state.watchlist = INDUSTRIES["hospitality_procurement"]["default_watchlist"]
                    wl = INDUSTRIES["hospitality_procurement"]["default_watchlist"]
                    st.session_state.watchlist = wl
                    st.switch_page("pages/1_📊_Dashboard.py")
                else:
                    try:
                        from core.firebase_db import auth_login, get_user_profile, get_watchlist
                        user = auth_login(email_in, pass_in)
                        st.session_state.authenticated = True
                        st.session_state.uid = user["uid"]
                        st.session_state.email = user["email"]
                        st.session_state.id_token = user["id_token"]
                        profile = get_user_profile(user["uid"]) or {}
                        st.session_state.user_profile = profile
                        industry_id = profile.get("industry", "hospitality_procurement")
                        default_wl = INDUSTRIES.get(industry_id, {}).get("default_watchlist", {})
                        stored_wl = get_watchlist(user["uid"])
                        st.session_state.watchlist = stored_wl if any(stored_wl.values()) else default_wl
                        st.switch_page("pages/1_📊_Dashboard.py")
                    except ValueError as e:
                        st.markdown(f'<div class="error-box">⚠️ {e}</div>', unsafe_allow_html=True)

        st.markdown("---")
        with st.expander("Forgot Password?"):
            st.caption("Enter your email above, then click below to send a reset link.")
            if st.button("Send Reset Email"):
                if not email_in:
                    st.markdown('<div class="error-box">Please enter your email above.</div>', unsafe_allow_html=True)
                else:
                    try:
                        from core.firebase_db import auth_reset_password
                        auth_reset_password(email_in)
                        st.markdown('<div class="success-box">✅ Password reset email sent!</div>', unsafe_allow_html=True)
                    except ValueError as e:
                        st.markdown(f'<div class="error-box">⚠️ {e}</div>', unsafe_allow_html=True)

    # ── Register Tab ──────────────────────────────────────────────────────────
    with tab_register:
        r_name = st.text_input("Full Name", placeholder="Alex Johnson", key="reg_name")
        r_email = st.text_input("Work Email", placeholder="you@company.com", key="reg_email")
        r_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass")

        st.markdown("**Select your industry** — we'll pre-load your watchlist:")
        industry_options = {iid: f"{idata['icon']} {idata['name']}" for iid, idata in INDUSTRIES.items()}
        selected_industry = st.selectbox(
            "Industry",
            options=list(industry_options.keys()),
            format_func=lambda x: industry_options[x],
            key="reg_industry"
        )
        # Show what will be pre-loaded
        with st.expander("👀 Preview your default watchlist"):
            wl = INDUSTRIES[selected_industry]["default_watchlist"]
            st.write(f"**Companies:** {', '.join(wl.get('companies', [])[:4])}...")
            st.write(f"**Ports:** {', '.join(wl.get('ports', [])[:3])}")
            st.write(f"**Commodities:** {', '.join(wl.get('commodities', [])[:3])}...")

        if st.button("Create Account →", type="primary", use_container_width=True):
            if not all([r_name, r_email, r_pass]):
                st.markdown('<div class="error-box">Please fill all fields.</div>', unsafe_allow_html=True)
            elif len(r_pass) < 6:
                st.markdown('<div class="error-box">Password must be at least 6 characters.</div>', unsafe_allow_html=True)
            else:
                from config.settings import settings
                if not settings.has_firebase:
                    st.markdown('<div class="success-box">✅ Account created! Signing you in...</div>', unsafe_allow_html=True)
                    st.session_state.authenticated = True
                    st.session_state.uid = "demo-user"
                    st.session_state.email = r_email
                    
                    profile = {
                        "name": r_name,
                        "industry": selected_industry,
                        "industry_name": INDUSTRIES[selected_industry]["name"],
                    }
                    wl = INDUSTRIES[selected_industry]["default_watchlist"]
                    
                    # Save persistently to local Demo DB
                    from core.demo_db import save_demo_user
                    save_demo_user(r_email, profile, wl)
                    
                    st.session_state.user_profile = profile
                    st.session_state.watchlist = wl
                    st.switch_page("pages/1_📊_Dashboard.py")
                else:
                    try:
                        from core.firebase_db import auth_signup, save_user_profile
                        user = auth_signup(r_email, r_pass)
                        profile = {
                            "name": r_name,
                            "email": r_email,
                            "industry": selected_industry,
                            "industry_name": INDUSTRIES[selected_industry]["name"],
                            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
                        }
                        save_user_profile(user["uid"], profile)
                        st.session_state.authenticated = True
                        st.session_state.uid = user["uid"]
                        st.session_state.email = r_email
                        st.session_state.id_token = user["id_token"]
                        st.session_state.user_profile = profile
                        st.session_state.watchlist = INDUSTRIES[selected_industry]["default_watchlist"]
                        st.markdown('<div class="success-box">✅ Account created! Redirecting...</div>', unsafe_allow_html=True)
                        st.switch_page("pages/1_📊_Dashboard.py")
                    except ValueError as e:
                        st.markdown(f'<div class="error-box">⚠️ {e}</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center style='color:#445;font-size:0.8rem'>SupplyRadar • Real-Time Supply Chain Intelligence • Free & Open Source</center>",
    unsafe_allow_html=True
)

"""core/firebase_db.py
Firebase Auth (REST) + Firestore CRUD for SupplyRadar.
All auth operations use Firebase REST API (no extra SDK needed).
All DB operations use firebase-admin (service account).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests

from config.settings import settings

log = logging.getLogger(__name__)

# ── Firebase Auth REST ────────────────────────────────────────────────────────

AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def auth_login(email: str, password: str) -> dict:
    """Sign in with email/password. Returns user dict with uid, id_token."""
    if not settings.firebase_api_key:
        raise ValueError("FIREBASE_API_KEY not set. Add it to your .env file.")
    url = f"{AUTH_BASE}:signInWithPassword?key={settings.firebase_api_key}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
    data = resp.json()
    if not resp.ok:
        msg = data.get("error", {}).get("message", "Login failed")
        raise ValueError(_friendly_auth_error(msg))
    return {"uid": data["localId"], "email": data["email"], "id_token": data["idToken"]}


def auth_signup(email: str, password: str) -> dict:
    """Create new account. Returns user dict with uid, id_token."""
    if not settings.firebase_api_key:
        raise ValueError("FIREBASE_API_KEY not set.")
    url = f"{AUTH_BASE}:signUp?key={settings.firebase_api_key}"
    resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=10)
    data = resp.json()
    if not resp.ok:
        msg = data.get("error", {}).get("message", "Signup failed")
        raise ValueError(_friendly_auth_error(msg))
    return {"uid": data["localId"], "email": data["email"], "id_token": data["idToken"]}


def auth_reset_password(email: str) -> None:
    """Send a password reset email."""
    if not settings.firebase_api_key:
        raise ValueError("FIREBASE_API_KEY not set.")
    url = f"{AUTH_BASE}:sendOobCode?key={settings.firebase_api_key}"
    resp = requests.post(url, json={"requestType": "PASSWORD_RESET", "email": email}, timeout=10)
    if not resp.ok:
        msg = resp.json().get("error", {}).get("message", "Reset failed")
        raise ValueError(_friendly_auth_error(msg))


def auth_change_password(id_token: str, new_password: str) -> None:
    """Change the authenticated user's password."""
    if not settings.firebase_api_key:
        raise ValueError("FIREBASE_API_KEY not set.")
    url = f"{AUTH_BASE}:update?key={settings.firebase_api_key}"
    resp = requests.post(url, json={"idToken": id_token, "password": new_password, "returnSecureToken": True}, timeout=10)
    if not resp.ok:
        msg = resp.json().get("error", {}).get("message", "Password change failed")
        raise ValueError(_friendly_auth_error(msg))


def _friendly_auth_error(msg: str) -> str:
    mapping = {
        "EMAIL_NOT_FOUND": "No account found with this email.",
        "INVALID_PASSWORD": "Incorrect password. Please try again.",
        "USER_DISABLED": "This account has been disabled.",
        "EMAIL_EXISTS": "An account with this email already exists.",
        "WEAK_PASSWORD": "Password must be at least 6 characters.",
        "INVALID_EMAIL": "Please enter a valid email address.",
        "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    }
    for key, friendly in mapping.items():
        if key in msg:
            return friendly
    return msg


# ── Firestore Client (lazy init) ──────────────────────────────────────────────

_firestore_db = None


def _get_db():
    global _firestore_db
    if _firestore_db is not None:
        return _firestore_db
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fs

        if not firebase_admin._apps:
            import json
            cred_path = settings.firebase_credentials_path
            
            if settings.firebase_credentials_json:
                # Load from environment variable (useful for cloud deployments)
                cred_dict = json.loads(settings.firebase_credentials_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
            elif cred_path.exists():
                # Load from local JSON file
                cred = credentials.Certificate(str(cred_path))
                firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
            else:
                firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
            log.info("Firebase initialized (project: %s)", settings.firebase_project_id)

        _firestore_db = fs.client()
    except Exception as e:
        log.error("Firebase init failed: %s", e)
        raise
    return _firestore_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── User Profiles ─────────────────────────────────────────────────────────────

def save_user_profile(uid: str, profile: dict) -> None:
    db = _get_db()
    db.collection("users").document(uid).set(profile, merge=True)


def get_user_profile(uid: str) -> Optional[dict]:
    db = _get_db()
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else None

def get_all_users() -> list[dict]:
    """Fetch all registered users and their profiles/watchlists."""
    db = _get_db()
    docs = db.collection("users").stream()
    return [{"uid": d.id, **d.to_dict()} for d in docs]

# ── Headlines ─────────────────────────────────────────────────────────────────

def save_articles(articles: list[dict]) -> int:
    """Batch save articles. Returns count of newly saved (skips duplicates)."""
    db = _get_db()
    col = db.collection("headlines")
    saved = 0
    for article in articles:
        doc_id = article.get("id") or str(uuid.uuid4())[:16]
        ref = col.document(doc_id)
        if not ref.get().exists:
            ref.set({**article, "id": doc_id})
            saved += 1
    return saved


def get_recent_articles(limit: int = 100, risk_level: Optional[str] = None) -> list[dict]:
    db = _get_db()
    query = db.collection("headlines").order_by("ingested_at", direction="DESCENDING").limit(limit)
    docs = query.stream()
    results = [{"id": d.id, **d.to_dict()} for d in docs]
    if risk_level:
        results = [r for r in results if r.get("risk_level") == risk_level]
    return results


def search_articles(query: str, limit: int = 50) -> list[dict]:
    """Simple keyword search over recent 200 articles."""
    docs = get_recent_articles(limit=200)
    q = query.lower()
    return [d for d in docs if q in d.get("raw_text", "").lower()][:limit]


def get_articles_for_trend(days: int = 30) -> list[dict]:
    """Fetch articles for the trend analysis page."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    db = _get_db()
    docs = (
        db.collection("headlines")
        .where("ingested_at", ">=", cutoff)
        .order_by("ingested_at")
        .limit(500)
        .stream()
    )
    return [{"id": d.id, **d.to_dict()} for d in docs]


# ── Watchlist ─────────────────────────────────────────────────────────────────

def save_watchlist(uid: str, watchlist: dict) -> None:
    db = _get_db()
    db.collection("users").document(uid).set({"watchlist": watchlist}, merge=True)


def get_watchlist(uid: str) -> dict:
    profile = get_user_profile(uid) or {}
    return profile.get("watchlist", {"companies": [], "ports": [], "commodities": [], "countries": []})

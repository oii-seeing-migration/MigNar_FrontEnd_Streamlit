# lib/auth.py
import base64
import hashlib
import json
import os
import time
import streamlit as st
from supabase import create_client, Client

TOKEN_REFRESH_BUFFER_SECONDS = 600

# Server-side session directory
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

# Cookie name used for session ID
COOKIE_NAME = "mignar_sid"

# ─── Server-side session persistence ─────────────────────────────────────────

def _session_file(sid: str) -> str:
    """Get path to a session file. Sanitize sid to prevent path traversal."""
    safe = "".join(c for c in sid if c.isalnum() or c == "-")
    return os.path.join(SESSION_DIR, f"{safe}.json")

def _write_session(sid: str, data: dict):
    data["_ts"] = time.time()
    with open(_session_file(sid), "w") as f:
        json.dump(data, f)

def _read_session(sid: str) -> dict | None:
    path = _session_file(sid)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if time.time() - data.get("_ts", 0) > 7 * 86400:
            os.remove(path)
            return None
        return data
    except Exception:
        return None

def _delete_session(sid: str):
    path = _session_file(sid)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def cleanup_old_sessions(max_age_days: int = 7):
    try:
        cutoff = time.time() - max_age_days * 86400
        for f in os.listdir(SESSION_DIR):
            fp = os.path.join(SESSION_DIR, f)
            if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
                os.remove(fp)
    except Exception:
        pass

# ─── Cookie-based session ID (extra-streamlit-components) ────────────────────

def _get_cookie_manager():
    if "_cookie_manager" not in st.session_state:
        try:
            import extra_streamlit_components as stx
        except Exception:
            if not st.session_state.get("_cookie_manager_missing"):
                st.warning("Install extra-streamlit-components: `pip install extra-streamlit-components`")
                st.session_state["_cookie_manager_missing"] = True
            return None
        st.session_state["_cookie_manager"] = stx.CookieManager()
    return st.session_state["_cookie_manager"]

def _get_cookie_sid() -> str | None:
    """Read session ID from browser cookie."""
    mgr = _get_cookie_manager()
    if not mgr:
        return None
    try:
        return mgr.get(COOKIE_NAME)
    except Exception:
        return None

def _set_cookie_sid(sid: str):
    """Set session ID cookie (7 days)."""
    mgr = _get_cookie_manager()
    if not mgr:
        return
    try:
        mgr.set(COOKIE_NAME, sid, max_age=7 * 86400, path="/", same_site="Lax")
    except Exception:
        pass

def _clear_cookie_sid():
    """Clear session ID cookie."""
    mgr = _get_cookie_manager()
    if not mgr:
        return
    try:
        mgr.delete(COOKIE_NAME)
    except Exception:
        pass
    
# ─── Supabase client ─────────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    if "supabase_client" not in st.session_state:
        SB_URL = st.secrets["supabase"]["url"]
        SB_KEY = st.secrets["supabase"]["anon_key"]
        st.session_state.supabase_client = create_client(SB_URL, SB_KEY)
    return st.session_state.supabase_client

# ─── JWT helpers ──────────────────────────────────────────────────────────────

def _b64url_decode(s: str) -> bytes:
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)

def jwt_payload(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        return json.loads(_b64url_decode(parts[1]).decode("utf-8"))
    except Exception:
        return None

# ─── Auth persistence ─────────────────────────────────────────────────────────

def save_auth_to_storage(access_token: str, refresh_token: str, user: dict):
    """Save auth tokens. Creates server-side file + sets browser cookie with session ID."""
    # Deterministic session ID from user ID for simplicity
    uid = user.get("id", "unknown")
    sid = hashlib.sha256(uid.encode()).hexdigest()[:32]
    
    _write_session(sid, {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    })
    
    # Store sid in session_state for cross-page navigation within same WS session
    st.session_state["_auth_sid"] = sid
    
    # Set browser cookie for persistence across refresh/new WS sessions
    _set_cookie_sid(sid)

def clear_auth_from_storage():
    """Clear server-side session + cookie."""
    sid = st.session_state.get("_auth_sid") or _get_cookie_sid()
    if sid:
        _delete_session(sid)
    st.session_state.pop("_auth_sid", None)
    _clear_cookie_sid()

def restore_auth_from_storage() -> bool:
    """
    Try to restore auth. Checks:
    1. session_state (fastest, works within same WS session)
    2. Browser cookie → server-side file (works after refresh)
    """
    if st.session_state.get("session") and st.session_state.get("user"):
        return False
    
    # Get session ID: first from session_state, then from cookie
    sid = st.session_state.get("_auth_sid") or _get_cookie_sid()
    if not sid:
        return False
    
    stored = _read_session(sid)
    if not stored:
        return False
    
    at = stored.get("access_token")
    rt = stored.get("refresh_token")
    user = stored.get("user")
    
    if not at or not user:
        return False
    
    payload = jwt_payload(at) or {}
    exp = payload.get("exp", 0)
    now = time.time()
    
    if exp > now:
        st.session_state.session = {"access_token": at, "refresh_token": rt}
        st.session_state.user = user
        st.session_state["_auth_sid"] = sid
        return True
    elif rt:
        try:
            supabase = get_supabase_client()
            response = supabase.auth.refresh_session(rt)
            if response and response.session:
                new_at = response.session.access_token
                new_rt = response.session.refresh_token
                st.session_state.session = {"access_token": new_at, "refresh_token": new_rt}
                if response.user:
                    st.session_state.user = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "name": getattr(response.user, "user_metadata", {}).get("full_name")
                                or getattr(response.user, "user_metadata", {}).get("name")
                                or response.user.email,
                    }
                else:
                    st.session_state.user = user
                st.session_state["_auth_sid"] = sid
                _write_session(sid, {
                    "access_token": new_at,
                    "refresh_token": new_rt,
                    "user": st.session_state.user,
                })
                return True
        except Exception:
            _delete_session(sid)
            _clear_cookie_sid()
    
    return False

# ─── Bind auth to Supabase client ────────────────────────────────────────────

def bind_auth_from_session() -> tuple[bool, str | None, Client]:
    supabase = get_supabase_client()
    
    sess = st.session_state.get("session") or {}
    at = sess.get("access_token")
    rt = sess.get("refresh_token")
    
    if not at:
        return (False, None, supabase)
    
    payload = jwt_payload(at) or {}
    exp = payload.get("exp", 0)
    now = time.time()
    needs_refresh = exp < (now + TOKEN_REFRESH_BUFFER_SECONDS)
    
    if needs_refresh and rt:
        try:
            response = supabase.auth.refresh_session(rt)
            if response and response.session:
                new_at = response.session.access_token
                new_rt = response.session.refresh_token
                st.session_state.session = {"access_token": new_at, "refresh_token": new_rt}
                at = new_at
                rt = new_rt
                if response.user:
                    st.session_state.user = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "name": getattr(response.user, "user_metadata", {}).get("full_name")
                                or getattr(response.user, "user_metadata", {}).get("name")
                                or response.user.email,
                    }
                # Update server-side session too
                sid = st.session_state.get("_auth_sid")
                if sid:
                    _write_session(sid, {
                        "access_token": new_at,
                        "refresh_token": new_rt,
                        "user": st.session_state.user,
                    })
            else:
                return (False, None, supabase)
        except Exception as e:
            error_msg = str(e).lower()
            if "expired" in error_msg or "invalid" in error_msg:
                st.session_state.pop("session", None)
                st.session_state.pop("user", None)
                clear_auth_from_storage()
                return (False, None, supabase)
    
    try:
        try:
            supabase.auth.set_session(at, rt)
        except TypeError:
            supabase.auth.set_session(access_token=at, refresh_token=rt)
    except Exception:
        pass
    
    try:
        supabase.postgrest.auth(at)
    except Exception:
        pass
    
    uid = None
    if st.session_state.get("user"):
        uid = st.session_state.user.get("id")
    if not uid:
        payload = jwt_payload(at) or {}
        uid = payload.get("sub")
    if not uid:
        try:
            me = supabase.auth.get_user()
            au = getattr(me, "user", None) or me
            uid = getattr(au, "id", None)
        except Exception:
            pass
    
    return (bool(uid), uid, supabase)

# ─── Public API ───────────────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    return st.session_state.get("user")

def require_auth() -> tuple[bool, str | None, dict | None, Client]:
    """Restore session, bind auth, return state."""
    restore_auth_from_storage()
    bind_ok, auth_uid, supabase = bind_auth_from_session()
    user = get_current_user()
    return (bind_ok and bool(auth_uid), auth_uid, user, supabase)

def sign_out():
    """Sign out and clear all state."""
    st.session_state.pop("session", None)
    st.session_state.pop("user", None)
    st.session_state.pop("supabase_client", None)
    st.session_state.pop("_auth_sid", None)
    clear_auth_from_storage()
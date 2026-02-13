# lib/auth.py
import base64
import hashlib
import json
import os
import time
from datetime import datetime, timezone, timedelta
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client, Client

TOKEN_REFRESH_BUFFER_SECONDS = 600

# Server-side session directory (local fallback)
SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".sessions")
os.makedirs(SESSION_DIR, exist_ok=True)

# Cookie name used for session ID
COOKIE_NAME = "mignar_sid"

# Shared session storage (Supabase)
SESSION_TABLE = "app_sessions"
SESSION_TTL_DAYS = 7


def _now_ts() -> float:
    return time.time()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── Local session persistence ──────────────────────────────────────────────

def _session_file(sid: str) -> str:
    safe = "".join(c for c in sid if c.isalnum() or c == "-")
    return os.path.join(SESSION_DIR, f"{safe}.json")


def _write_session(sid: str, data: dict):
    data["_ts"] = _now_ts()
    with open(_session_file(sid), "w") as f:
        json.dump(data, f)


def _read_session(sid: str) -> dict | None:
    path = _session_file(sid)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if _now_ts() - data.get("_ts", 0) > SESSION_TTL_DAYS * 86400:
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


# ─── Browser fingerprint (server-side, works on Streamlit Cloud) ─────────────

FP_PREFIX = "fp_"


def _compute_browser_fp() -> str | None:
    """
    Compute a browser fingerprint from HTTP request headers.

    Uses **only browser-intrinsic headers** that are identical across
    tabs in the same browser but differ between browsers / machines:
      - User-Agent  (browser version + OS)
      - Accept-Language  (user language prefs)
      - Sec-Ch-Ua*  (Chrome client-hints: exact build, platform, mobile)

    IP is deliberately excluded because Streamlit Cloud's load-balancer
    assigns a different X-Forwarded-For per WebSocket / tab.
    """
    try:
        hdrs = st.context.headers
    except Exception:
        return None

    parts = []
    for key in (
        "User-Agent", "user-agent",
        "Accept-Language", "accept-language",
        "Sec-Ch-Ua", "sec-ch-ua",
        "Sec-Ch-Ua-Platform", "sec-ch-ua-platform",
        "Sec-Ch-Ua-Mobile", "sec-ch-ua-mobile",
    ):
        val = hdrs.get(key)
        if val:
            parts.append(val)

    if not parts:
        return None

    raw = "|".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _save_fp_mapping(sid: str):
    """Save browser-fingerprint → SID mapping for cross-tab lookup."""
    fp = _compute_browser_fp()
    if fp:
        _write_session_shared(f"{FP_PREFIX}{fp}", {"real_sid": sid})


def _lookup_sid_by_fp() -> str | None:
    """Look up SID from browser fingerprint."""
    fp = _compute_browser_fp()
    if not fp:
        return None
    data = _read_session_shared(f"{FP_PREFIX}{fp}")
    if data:
        return data.get("real_sid")
    return None


def _clear_fp_mapping():
    """Delete the fingerprint → SID mapping for this browser."""
    fp = _compute_browser_fp()
    if fp:
        _delete_session_shared(f"{FP_PREFIX}{fp}")


# ─── Cookie / localStorage helpers (kept for local / non-Cloud deploys) ──────

def _get_cookie_manager():
    if "_cookie_manager" not in st.session_state:
        try:
            import extra_streamlit_components as stx
        except Exception:
            return None
        st.session_state["_cookie_manager"] = stx.CookieManager()
    return st.session_state["_cookie_manager"]

def _get_cookie_sid() -> str | None:
    """Read session ID from browser cookie (HTTP headers, then CookieManager)."""
    try:
        cookies = st.context.cookies
        val = cookies.get(COOKIE_NAME)
        if val:
            return val
    except Exception:
        pass

    mgr = _get_cookie_manager()
    if mgr:
        try:
            val = mgr.get(COOKIE_NAME)
            if val:
                return val
        except Exception:
            pass
    return None


def _set_cookie_and_ls(sid: str):
    """
    Set session ID in both cookie and localStorage on the parent frame.
    
    Key fixes for Streamlit Cloud:
    - Force Secure + SameSite=None for HTTPS (detect via parent frame, not srcdoc)
    - Write to parent frame's document.cookie AND localStorage
    - localStorage is the primary cross-tab mechanism (cookies may be blocked)
    """
    js = f"""
    <script>
    (function() {{
      var sid = "{sid}";
      var cookieName = "{COOKIE_NAME}";
      var maxAge = {7 * 86400};

      // Detect HTTPS from parent frame (srcdoc has protocol "about:")
      var isHttps = false;
      try {{ isHttps = window.parent.location.protocol === "https:"; }} catch(e) {{}}
      if (!isHttps) {{
        try {{ isHttps = window.top.location.protocol === "https:"; }} catch(e) {{}}
      }}
      if (!isHttps) {{
        // Fallback: assume HTTPS on *.streamlit.app
        try {{
          var host = window.parent.location.hostname || "";
          if (host.indexOf("streamlit.app") !== -1 || host.indexOf("streamlit.io") !== -1) isHttps = true;
        }} catch(e) {{}}
      }}

      var sameSite = isHttps ? "None" : "Lax";
      var secure   = isHttps ? "; Secure" : "";
      var cookieVal = cookieName + "=" + sid + "; path=/; max-age=" + maxAge + "; SameSite=" + sameSite + secure;

      // Set cookie on all reachable frames
      var frames = [window];
      try {{ if (window.parent && window.parent !== window) frames.push(window.parent); }} catch(e) {{}}
      try {{ if (window.top && window.top !== window && window.top !== window.parent) frames.push(window.top); }} catch(e) {{}}

      for (var i = 0; i < frames.length; i++) {{
        try {{ frames[i].document.cookie = cookieVal; }} catch(e) {{}}
        try {{ frames[i].localStorage.setItem(cookieName, sid); }} catch(e) {{}}
      }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)

    mgr = _get_cookie_manager()
    if mgr:
        try:
            mgr.set(COOKIE_NAME, sid, max_age=7 * 86400, path="/", same_site="None", secure=True)
        except Exception:
            try:
                mgr.set(COOKIE_NAME, sid, max_age=7 * 86400, path="/", same_site="Lax")
            except Exception:
                pass


def _clear_cookie_and_ls():
    """Clear session ID cookie + localStorage on all reachable frames."""
    js = f"""
    <script>
    (function() {{
      var cookieName = "{COOKIE_NAME}";

      var isHttps = false;
      try {{ isHttps = window.parent.location.protocol === "https:"; }} catch(e) {{}}
      if (!isHttps) {{
        try {{ isHttps = window.top.location.protocol === "https:"; }} catch(e) {{}}
      }}
      if (!isHttps) {{
        try {{
          var host = window.parent.location.hostname || "";
          if (host.indexOf("streamlit.app") !== -1 || host.indexOf("streamlit.io") !== -1) isHttps = true;
        }} catch(e) {{}}
      }}

      var sameSite = isHttps ? "None" : "Lax";
      var secure   = isHttps ? "; Secure" : "";
      var cookieVal = cookieName + "=; path=/; max-age=0; SameSite=" + sameSite + secure;

      var frames = [window];
      try {{ if (window.parent && window.parent !== window) frames.push(window.parent); }} catch(e) {{}}
      try {{ if (window.top && window.top !== window && window.top !== window.parent) frames.push(window.top); }} catch(e) {{}}

      for (var i = 0; i < frames.length; i++) {{
        try {{ frames[i].document.cookie = cookieVal; }} catch(e) {{}}
        try {{ frames[i].localStorage.removeItem(cookieName); }} catch(e) {{}}
      }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)

    mgr = _get_cookie_manager()
    if mgr:
        try:
            mgr.delete(COOKIE_NAME)
        except Exception:
            pass


def _read_sid_from_localstorage() -> str | None:
    """
    Inject JS that reads localStorage and, if a SID is found, writes it
    back into a cookie on document.cookie so that st.context.cookies can
    pick it up on the NEXT rerun.

    Returns None always — the value is delivered asynchronously via cookie,
    so the caller must trigger a rerun and re-check st.context.cookies.
    """
    if st.session_state.get("_ls_bridge_done"):
        return None

    # Inject JS: read localStorage → write to document.cookie → force rerun
    js = f"""
    <script>
    (function() {{
      var cookieName = "{COOKIE_NAME}";
      var sid = null;

      // Try reading from localStorage in parent frames
      var frames = [window];
      try {{ if (window.parent && window.parent !== window) frames.push(window.parent); }} catch(e) {{}}
      try {{ if (window.top && window.top !== window && window.top !== window.parent) frames.push(window.top); }} catch(e) {{}}

      for (var i = 0; i < frames.length; i++) {{
        try {{
          var val = frames[i].localStorage.getItem(cookieName);
          if (val) {{ sid = val; break; }}
        }} catch(e) {{}}
      }}

      if (sid) {{
        // Write it as a cookie on all reachable frames so st.context.cookies sees it
        var isHttps = false;
        try {{ isHttps = window.parent.location.protocol === "https:"; }} catch(e) {{}}
        if (!isHttps) {{
          try {{ isHttps = window.top.location.protocol === "https:"; }} catch(e) {{}}
        }}
        if (!isHttps) {{
          try {{
            var host = window.parent.location.hostname || "";
            if (host.indexOf("streamlit.app") !== -1 || host.indexOf("streamlit.io") !== -1) isHttps = true;
          }} catch(e) {{}}
        }}

        var sameSite = isHttps ? "None" : "Lax";
        var secure   = isHttps ? "; Secure" : "";
        var cookieVal = cookieName + "=" + sid + "; path=/; max-age={7 * 86400}; SameSite=" + sameSite + secure;

        for (var i = 0; i < frames.length; i++) {{
          try {{ frames[i].document.cookie = cookieVal; }} catch(e) {{}}
        }}
      }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)
    st.session_state["_ls_bridge_done"] = True
    return None


# ─── URL param helpers ───────────────────────────────────────────────────────

def _get_url_sid() -> str | None:
    try:
        val = st.query_params.get("sid")
    except Exception:
        return None
    if isinstance(val, list):
        return val[0] if val else None
    return val if isinstance(val, str) else None


def _set_url_sid(sid: str):
    try:
        st.query_params["sid"] = sid
    except Exception:
        pass


def _clear_url_sid():
    try:
        if "sid" in st.query_params:
            del st.query_params["sid"]
    except Exception:
        pass


def _inject_sid_into_links(sid: str):
    if not sid or st.session_state.get("_sid_links_injected") == sid:
        return

    js = f"""
    <script>
    (function() {{
      var sid = "{sid}";
      if (!sid) return;

      function appendSid(href) {{
        try {{
          var url = new URL(href, window.location.origin);
          if (!url.searchParams.get("sid")) {{
            url.searchParams.set("sid", sid);
          }}
          return url.toString();
        }} catch (e) {{
          return href;
        }}
      }}

      function updateLinks(root) {{
        var anchors = root.querySelectorAll('a[href]');
        for (var i = 0; i < anchors.length; i++) {{
          var a = anchors[i];
          var href = a.getAttribute("href");
          if (!href) continue;

          if (href.startsWith("http://") || href.startsWith("https://")) {{
            if (!href.startsWith(window.location.origin)) continue;
          }} else if (!href.startsWith("/")) {{
            continue;
          }}

          a.href = appendSid(a.href);
        }}
      }}

      function attach(root) {{
        updateLinks(root);
        var obs = new MutationObserver(function() {{ updateLinks(root); }});
        obs.observe(root, {{
          subtree: true,
          childList: true,
          attributes: true,
          attributeFilter: ["href"]
        }});
      }}

      try {{
        if (window.parent && window.parent.document &&
            window.parent.location && window.parent.location.origin === window.location.origin) {{
          attach(window.parent.document);
        }} else {{
          attach(document);
        }}
      }} catch (e) {{
        try {{ attach(document); }} catch (e2) {{}}
      }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)
    st.session_state["_sid_links_injected"] = sid


def _ensure_sid_from_state() -> str | None:
    sid = st.session_state.get("_auth_sid")
    if not sid:
        user = st.session_state.get("user") or {}
        uid = user.get("id")
        if uid:
            sid = hashlib.sha256(uid.encode()).hexdigest()[:32]
            st.session_state["_auth_sid"] = sid
    if sid:
        _set_url_sid(sid)
        _set_cookie_and_ls(sid)
    return sid


# ─── Supabase client ────────────────────────────────────────────────────────

def get_supabase_client() -> Client:
    if "supabase_client" not in st.session_state:
        SB_URL = st.secrets["supabase"]["url"]
        SB_KEY = st.secrets["supabase"]["anon_key"]
        st.session_state.supabase_client = create_client(SB_URL, SB_KEY)
    return st.session_state.supabase_client


# ─── JWT helpers ─────────────────────────────────────────────────────────────

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


# ─── Shared session persistence ──────────────────────────────────────────────

def _write_session_shared(sid: str, data: dict) -> bool:
    data = dict(data)
    data["_ts"] = _now_ts()
    payload = {
        "sid": sid,
        "data": data,
        "updated_at": _now_iso(),
    }
    try:
        supabase = get_supabase_client()
        supabase.table(SESSION_TABLE).upsert(payload, on_conflict="sid").execute()
        return True
    except Exception:
        return False


def _read_session_shared(sid: str) -> dict | None:
    try:
        supabase = get_supabase_client()
        res = supabase.table(SESSION_TABLE).select("data").eq("sid", sid).limit(1).execute()
        row = res.data[0] if getattr(res, "data", None) else None
        if not row:
            return None
        data = row.get("data") or {}
        ts = data.get("_ts", 0)
        if ts and _now_ts() - ts > SESSION_TTL_DAYS * 86400:
            _delete_session_shared(sid)
            return None
        return data
    except Exception:
        return None


def _delete_session_shared(sid: str):
    try:
        supabase = get_supabase_client()
        supabase.table(SESSION_TABLE).delete().eq("sid", sid).execute()
    except Exception:
        pass


def _persist_session(sid: str, access_token: str, refresh_token: str, user: dict):
    payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user,
    }
    _write_session_shared(sid, payload)
    _write_session(sid, payload)


def cleanup_old_sessions(max_age_days: int = SESSION_TTL_DAYS):
    try:
        cutoff = _now_ts() - max_age_days * 86400
        for f in os.listdir(SESSION_DIR):
            fp = os.path.join(SESSION_DIR, f)
            if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
                os.remove(fp)
    except Exception:
        pass
    try:
        supabase = get_supabase_client()
        cutoff_iso = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        supabase.table(SESSION_TABLE).delete().lt("updated_at", cutoff_iso).execute()
    except Exception:
        pass


# ─── Auth persistence ────────────────────────────────────────────────────────

def save_auth_to_storage(access_token: str, refresh_token: str, user: dict):
    """Save auth tokens. Creates shared session + local fallback + cookie + localStorage + fingerprint."""
    uid = user.get("id", "unknown")
    sid = hashlib.sha256(uid.encode()).hexdigest()[:32]

    _persist_session(sid, access_token, refresh_token, user)
    _save_fp_mapping(sid)

    st.session_state["_auth_sid"] = sid
    _set_cookie_and_ls(sid)
    _set_url_sid(sid)


def clear_auth_from_storage():
    """Clear shared session + local fallback + cookie + localStorage + fingerprint."""
    sid = st.session_state.get("_auth_sid") or _get_cookie_sid() or _get_url_sid()
    if sid:
        _delete_session_shared(sid)
        _delete_session(sid)
    _clear_fp_mapping()
    st.session_state.pop("_auth_sid", None)
    _clear_cookie_and_ls()
    _clear_url_sid()


def _try_restore_from_stored(sid: str) -> bool:
    """Given a valid sid, try to restore session from shared or local storage."""
    stored = _read_session_shared(sid) or _read_session(sid)
    if not stored:
        return False

    at = stored.get("access_token")
    rt = stored.get("refresh_token")
    user = stored.get("user")

    if not at or not user:
        return False

    payload = jwt_payload(at) or {}
    exp = payload.get("exp", 0)
    now = _now_ts()

    if exp > now:
        st.session_state.session = {"access_token": at, "refresh_token": rt}
        st.session_state.user = user
        st.session_state["_auth_sid"] = sid
        _set_url_sid(sid)
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
                _persist_session(sid, new_at, new_rt, st.session_state.user)
                _set_url_sid(sid)
                return True
        except Exception:
            _delete_session_shared(sid)
            _delete_session(sid)
            _clear_cookie_and_ls()

    return False


def restore_auth_from_storage() -> bool:
    """
    Try to restore auth from stored session.

    Strategy (multi-user safe — scoped by browser fingerprint, never
    scans the DB for "any" session):

      1. Already in session_state → done
      2. SID from URL  ?sid=…   → look up in Supabase / local file
      3. SID from cookie         → look up
      4. SID via browser fingerprint (IP+UA+Lang → Supabase)  ← main
         mechanism that actually works on Streamlit Cloud
      5. CookieManager probe rerun (fallback for local deploys)
    """
    # 1. Already authenticated in this session
    if st.session_state.get("session") and st.session_state.get("user"):
        _ensure_sid_from_state()
        return False

    # 2. Try SID from URL or cookie or session_state
    sid = _get_url_sid() or _get_cookie_sid() or st.session_state.get("_auth_sid")
    if sid and _try_restore_from_stored(sid):
        return True

    # 3. Try browser fingerprint (reliable on Streamlit Cloud — no JS needed)
    fp_sid = _lookup_sid_by_fp()
    if fp_sid and _try_restore_from_stored(fp_sid):
        return True

    # 4. CookieManager probe rerun (may help on localhost / self-hosted)
    if not st.session_state.get("_cookie_probe_rerun_done"):
        _get_cookie_manager()
        st.session_state["_cookie_probe_rerun_done"] = True
        st.rerun()

    # 5. Retry cookie after probe rerun
    sid = _get_cookie_sid()
    if sid and _try_restore_from_stored(sid):
        return True

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
    now = _now_ts()
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
                sid = st.session_state.get("_auth_sid")
                if sid:
                    _persist_session(sid, new_at, new_rt, st.session_state.user)
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


# ─── Public API ──────────────────────────────────────────────────────────────

def ensure_sid() -> str | None:
    """Ensure sid is present in URL, cookie, and localStorage."""
    sid = _ensure_sid_from_state()
    if sid:
        _inject_sid_into_links(sid)
    return sid


def get_auth_debug_state() -> dict:
    sid_cookie = _get_cookie_sid()
    sid_state = st.session_state.get("_auth_sid")
    sid_url = _get_url_sid()
    sid = sid_state or sid_cookie or sid_url

    shared = _read_session_shared(sid) if sid else None
    shared_user = (shared or {}).get("user") or {}
    shared_at = (shared or {}).get("access_token")
    shared_exp = None
    if shared_at:
        shared_exp = (jwt_payload(shared_at) or {}).get("exp")

    stored = _read_session(sid) if sid else None
    stored_user = (stored or {}).get("user") or {}
    stored_at = (stored or {}).get("access_token")
    stored_exp = None
    if stored_at:
        stored_exp = (jwt_payload(stored_at) or {}).get("exp")

    sess = st.session_state.get("session") or {}
    sess_at = sess.get("access_token")
    sess_exp = None
    if sess_at:
        sess_exp = (jwt_payload(sess_at) or {}).get("exp")

    fp = _compute_browser_fp()
    fp_sid = _lookup_sid_by_fp() if fp else None

    return {
        "cookie_sid": sid_cookie,
        "url_sid": sid_url,
        "session_sid": sid_state,
        "active_sid": sid,
        "browser_fp": (fp[:8] + "…") if fp else None,
        "fp_lookup_sid": fp_sid,
        "cookie_probe_rerun_done": st.session_state.get("_cookie_probe_rerun_done", False),
        "session_shared_exists": bool(shared),
        "session_shared_ts": (shared or {}).get("_ts"),
        "shared_user_id": shared_user.get("id"),
        "shared_has_access_token": bool(shared_at),
        "shared_access_exp": shared_exp,
        "session_file_exists": bool(sid and os.path.exists(_session_file(sid))),
        "session_file_ts": (stored or {}).get("_ts"),
        "stored_user_id": stored_user.get("id"),
        "stored_has_access_token": bool(stored_at),
        "stored_access_exp": stored_exp,
        "session_state_user_id": (st.session_state.get("user") or {}).get("id"),
        "session_state_has_access_token": bool(sess_at),
        "session_state_access_exp": sess_exp,
    }


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def require_auth() -> tuple[bool, str | None, dict | None, Client]:
    """Restore session, bind auth, return state."""
    restore_auth_from_storage()
    bind_ok, auth_uid, supabase = bind_auth_from_session()
    user = get_current_user()
    if user:
        ensure_sid()
    return (bind_ok and bool(auth_uid), auth_uid, user, supabase)


def sign_out():
    """Sign out and clear all state."""
    _clear_fp_mapping()
    st.session_state.pop("session", None)
    st.session_state.pop("user", None)
    st.session_state.pop("supabase_client", None)
    st.session_state.pop("_auth_sid", None)
    st.session_state.pop("_cookie_manager", None)
    st.session_state.pop("_cookie_probe_rerun_done", None)
    st.session_state.pop("_ls_bridge_done", None)
    st.session_state.pop("_ls_bridge_rerun_done", None)
    clear_auth_from_storage()
import base64
import json
import urllib.parse
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# -----------------------------------------------------------------------------
# Secrets (required)
# -----------------------------------------------------------------------------
# .streamlit/secrets.toml
# [supabase]
# url = "https://<PROJECT>.supabase.co"
# anon_key = "<SUPABASE_ANON_PUBLIC_KEY>"
# [oauth]
# provider = "google"
# redirect_base = "http://localhost:8501"   # optional fallback; we also detect current origin

SB_URL = st.secrets["supabase"]["url"]
SB_ANON = st.secrets["supabase"]["anon_key"]
OAUTH_PROVIDER = (st.secrets.get("oauth") or {}).get("provider", "google")
FALLBACK_REDIRECT_BASE = (st.secrets.get("oauth") or {}).get("redirect_base", "http://localhost:8501")

supabase: Client = create_client(SB_URL, SB_ANON)

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------
def base64url_decode(data: str) -> bytes:
    padding = '=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)

def decode_jwt_without_verification(jwt: str) -> dict | None:
    try:
        parts = jwt.split(".")
        if len(parts) != 3:
            return None
        payload = json.loads(base64url_decode(parts[1]).decode("utf-8"))
        return payload
    except Exception:
        return None

def set_user_from_jwt(jwt: str):
    payload = decode_jwt_without_verification(jwt) or {}
    email = payload.get("email") or (payload.get("user_metadata") or {}).get("email")
    name = (payload.get("user_metadata") or {}).get("full_name") \
        or (payload.get("user_metadata") or {}).get("name") \
        or payload.get("name") \
        or email
    avatar = (payload.get("user_metadata") or {}).get("avatar_url") or payload.get("picture")
    sub = payload.get("sub") or payload.get("user_id")
    if not email and not sub:
        return False
    st.session_state["user"] = {
        "id": sub or email,
        "email": email,
        "name": name or "User",
        "avatar_url": avatar,
    }
    return True

def build_oauth_url(redirect_base: str) -> str:
    authorize = f"{SB_URL}/auth/v1/authorize"
    params = {
        "provider": OAUTH_PROVIDER,
        "redirect_to": redirect_base,  # must be in Supabase Auth → Redirect URLs
        "response_type": "code",       # prefer code flow, but we also handle token hash
        "prompt": "select_account",
    }
    return f"{authorize}?{urllib.parse.urlencode(params)}"

def sign_out():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for k in ("user", "sb_session"):
        st.session_state.pop(k, None)
    st.toast("Signed out.")

# -----------------------------------------------------------------------------
# Ensure redirect_to matches active origin (prevents 8501/8503 mismatch)
# -----------------------------------------------------------------------------
st.markdown("""
<script>
(function() {
  try {
    const url = new URL(window.location.href);
    if (!url.searchParams.get("origin")) {
      url.searchParams.set("origin", window.location.origin);
      window.location.replace(url);
    }
  } catch (e) {}
})();
</script>
""", unsafe_allow_html=True)

CURRENT_ORIGIN = st.query_params.get("origin") or FALLBACK_REDIRECT_BASE
REDIRECT_BASE = CURRENT_ORIGIN

# -----------------------------------------------------------------------------
# Handle code flow (?code=...)
# -----------------------------------------------------------------------------
auth_code = st.query_params.get("code")
if auth_code and not st.session_state.get("user"):
    try:
        session = supabase.auth.exchange_code_for_session(auth_code)
        user = session.user
        meta = getattr(user, "user_metadata", {}) or {}
        st.session_state["user"] = {
            "id": user.id,
            "email": user.email,
            "name": meta.get("full_name") or meta.get("name") or user.email,
            "avatar_url": meta.get("avatar_url"),
        }
        st.session_state["sb_session"] = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
        st.toast("Signed in successfully.")
    except Exception as e:
        st.error("Authentication failed during code exchange.")
        st.caption(str(e))
    # Clean URL and rerun
    if "code" in st.query_params:
        del st.query_params["code"]
    st.rerun()

# -----------------------------------------------------------------------------
# Handle implicit/token flow (#access_token=... or #id_token=...)
# Move tokens from hash to query, then set session from JWT locally.
# -----------------------------------------------------------------------------
st.markdown("""
<script>
(function() {
  try {
    if (window.location.hash && window.location.hash.length > 1) {
      const hash = window.location.hash.substring(1);
      const params = new URLSearchParams(hash);
      if (params.has("access_token") || params.has("id_token")) {
        const qs = new URLSearchParams(window.location.search);
        ["access_token","id_token","refresh_token","expires_in","expires_at","token_type","provider_token"]
          .forEach(k => { if (params.has(k)) qs.set(k, params.get(k)); });
        // Remove hash and replace with query params
        const newUrl = window.location.pathname + "?" + qs.toString();
        window.location.replace(newUrl);
        // Force immediate stop - don't let script continue
        throw new Error("Redirecting");
      }
    }
  } catch (e) {}
})();
</script>
""", unsafe_allow_html=True)

jwt_token = st.query_params.get("access_token") or st.query_params.get("id_token")
refresh_token = st.query_params.get("refresh_token")
if jwt_token and not st.session_state.get("user"):
    if set_user_from_jwt(jwt_token):
        st.session_state["sb_session"] = {
            "access_token": jwt_token,
            "refresh_token": refresh_token,
        }
        st.toast("Signed in successfully.")
        # Clean URL and rerun
        for k in ("access_token","id_token","refresh_token","expires_in","expires_at","token_type","provider_token"):
            if k in st.query_params:
                del st.query_params[k]
        st.rerun()
    else:
        st.error("Could not parse login token.")
        # Clean URL and rerun
        for k in ("access_token","id_token","refresh_token","expires_in","expires_at","token_type","provider_token"):
            if k in st.query_params:
                del st.query_params[k]
        st.rerun()

# -----------------------------------------------------------------------------
# UI: header with greeting and sign-out
# -----------------------------------------------------------------------------
st.markdown("""
<style>
.header { display:flex; align-items:center; gap:14px; margin-bottom:8px; }
.header .title { font-size:2rem; font-weight:700; margin:0; }
.header .subtitle { font-size:0.95rem; opacity:0.85; margin-top:-4px; }
.userbox { margin-left:auto; display:flex; align-items:center; gap:10px; }
.avatar { width:36px; height:36px; border-radius:50%; object-fit:cover; border:1px solid rgba(0,0,0,.12); }
.grid { display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:18px; }
.card { border-radius:18px; padding:18px; background:#fff; box-shadow:0 4px 14px rgba(0,0,0,0.12); }
.card h3 { margin:.2rem 0 0.35rem 0; }
.card p { margin:0; opacity:.85; }
.action-btn { margin-top:10px; width:100%; font-weight:600; border-radius:12px; padding:.8rem; border:0; }
.card-1 .action-btn { background:linear-gradient(135deg,#1f77b4,#4fa3ff); color:#fff; }
.card-2 .action-btn { background:linear-gradient(135deg,#00876c,#4fb783); color:#fff; }
.card-3 .action-btn { background:linear-gradient(135deg,#8b3fa9,#c37bff); color:#fff; }
.card-4 .action-btn { background:linear-gradient(135deg,#b34733,#ff916f); color:#fff; }
</style>
""", unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([0.75, 0.25])
    with col1:
        st.markdown("""
<div class="header">
  <div>
    <div class="title">Narrative Highlighter</div>
    <div class="subtitle">Explore narrative frames and meso narratives; sign in to annotate.</div>
  </div>
</div>
""", unsafe_allow_html=True)
    with col2:
        user = st.session_state.get("user")
        st.markdown('<div class="userbox">', unsafe_allow_html=True)
        if user:
            name = user.get("name") or user.get("email") or "User"
            avatar = user.get("avatar_url")
            if avatar:
                st.image(avatar, width=36, caption=None)
            else:
                st.markdown('<img class="avatar" src="https://api.dicebear.com/8.x/initials/svg?seed=User" />', unsafe_allow_html=True)
            st.write(f"Hello, {name}")
            if st.button("Sign out", use_container_width=False):
                sign_out()
                st.rerun()
        else:
            if st.button("Sign in with Google", use_container_width=False):
                # Clear stale params and redirect to Supabase authorize
                for k in ("origin","code","access_token","id_token","refresh_token","expires_in","expires_at","token_type","provider_token"):
                    if k in st.query_params:
                        del st.query_params[k]
                oauth_url = build_oauth_url(REDIRECT_BASE)
                st.markdown(f'<meta http-equiv="refresh" content="0; url={oauth_url}">', unsafe_allow_html=True)
                st.markdown(f"[Click here if not redirected]({oauth_url})")
                st.stop()
        st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar navigation
# -----------------------------------------------------------------------------
st.sidebar.subheader("Navigation")
try:
    st.sidebar.page_link("navigation_page.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/00_Narratives_Taxonomy.py", label="Meso Narratives Taxonomy", icon="🗂️")
    st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
    st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
    st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
    st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
except Exception:
    pass

# -----------------------------------------------------------------------------
# Main cards
# -----------------------------------------------------------------------------
st.markdown('<div class="grid">', unsafe_allow_html=True)
with st.container():
    colA, colB = st.columns(2, gap="large")
    with colA:
        st.markdown('<div class="card card-1">', unsafe_allow_html=True)
        st.markdown("### 📰 Narratives on Articles")
        st.markdown("Browse articles and view highlighted narrative fragments from multiple models.")
        if st.button("Open", key="btn_articles", help="Go to per-article highlights"):
            try: st.switch_page("pages/01_Narratives_on_Articles.py")
            except Exception: st.toast("Use the sidebar to navigate.")
        st.markdown('</div>', unsafe_allow_html=True)
    with colB:
        st.markdown('<div class="card card-2">', unsafe_allow_html=True)
        st.markdown("### 🗂️ Meso Narratives Taxonomy")
        st.markdown("Review and annotate the taxonomy of meso narratives.")
        if st.button("Open", key="btn_taxonomy", help="Go to taxonomy"):
            try: st.switch_page("pages/00_Narratives_Taxonomy.py")
            except Exception: st.toast("Use the sidebar to navigate.")
        st.markdown('</div>', unsafe_allow_html=True)

with st.container():
    colC, colD = st.columns(2, gap="large")
    with colC:
        st.markdown('<div class="card card-3">', unsafe_allow_html=True)
        st.markdown("### 📊 Aggregative Dashboard")
        st.markdown("Rank frames & meso narratives; inspect prevalence, intensity & volume.")
        if st.button("Open", key="btn_agg", help="Go to aggregate view"):
            try: st.switch_page("pages/02_Aggregative_Dashboard.py")
            except Exception: st.toast("Use the sidebar to navigate.")
        st.markdown('</div>', unsafe_allow_html=True)
    with colD:
        st.markdown('<div class="card card-4">', unsafe_allow_html=True)
        st.markdown("### ⚖️ Contrastive & ⏱ Temporal")
        st.markdown("Compare shifts and track trends over time.")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("Contrastive", key="btn_contrast", help="Go to contrastive view"):
                try: st.switch_page("pages/03_Contrastive_Dashboard.py")
                except Exception: st.toast("Use the sidebar to navigate.")
        with col_d2:
            if st.button("Temporal", key="btn_time", help="Go to temporal view"):
                try: st.switch_page("pages/04_Temporal_Dashboard.py")
                except Exception: st.toast("Use the sidebar to navigate.")
        st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("---")
user = st.session_state.get("user")
if user:
    st.caption(f"Signed in as {user.get('name') or user.get('email')} • Redirect base: {REDIRECT_BASE}")
else:
    st.caption(f"You are not signed in • Redirect base: {REDIRECT_BASE}")
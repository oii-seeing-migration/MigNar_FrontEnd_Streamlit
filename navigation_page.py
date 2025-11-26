import base64
import json
import urllib.parse
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Narrative Highlighter", layout="wide")

# -----------------------------------------------------------------------------
# Secrets (required) - Use publishable_key instead of anon_key
# -----------------------------------------------------------------------------
SB_URL = st.secrets["supabase"]["url"]
SB_KEY = st.secrets["supabase"].get("publishable_key") or st.secrets["supabase"]["anon_key"]
OAUTH_PROVIDER = (st.secrets.get("oauth") or {}).get("provider", "google")
FALLBACK_REDIRECT_BASE = (st.secrets.get("oauth") or {}).get("redirect_base", "http://localhost:8501")

supabase: Client = create_client(SB_URL, SB_KEY)

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
    """Build OAuth URL - Supabase defaults to implicit flow returning hash tokens"""
    authorize = f"{SB_URL}/auth/v1/authorize"
    params = {
        "provider": OAUTH_PROVIDER,
        "redirect_to": redirect_base,
    }
    return f"{authorize}?{urllib.parse.urlencode(params)}"

def sign_out():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for k in ("user", "sb_session"):
        st.session_state.pop(k, None)
    # Clear sessionStorage via JavaScript
    st.markdown("""
    <script>
    sessionStorage.removeItem('supabase_auth_token');
    sessionStorage.removeItem('supabase_refresh_token');
    </script>
    """, unsafe_allow_html=True)
    st.toast("Signed out.")

CURRENT_ORIGIN = st.query_params.get("origin") or FALLBACK_REDIRECT_BASE
REDIRECT_BASE = CURRENT_ORIGIN

# -----------------------------------------------------------------------------
# CRITICAL: Handle hash-based OAuth tokens from Supabase
# This JavaScript runs first and converts hash tokens to query params
# -----------------------------------------------------------------------------
st.markdown("""
<script>
(function() {
    // Step 1: If URL has hash with access_token, store in sessionStorage and redirect
    if (window.location.hash && window.location.hash.includes('access_token')) {
        const hash = window.location.hash.substring(1);
        const hashParams = new URLSearchParams(hash);
        
        if (hashParams.has("access_token")) {
            sessionStorage.setItem('supabase_auth_token', hashParams.get("access_token"));
            sessionStorage.setItem('supabase_refresh_token', hashParams.get("refresh_token") || "");
            
            // Redirect to clean URL with callback flag
            window.location.replace(window.location.pathname + "?auth_callback=true");
        }
    }
    
    // Step 2: If returning from callback and tokens exist in sessionStorage
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('auth_callback')) {
        const token = sessionStorage.getItem('supabase_auth_token');
        const refresh = sessionStorage.getItem('supabase_refresh_token');
        
        if (token) {
            // Clear sessionStorage
            sessionStorage.removeItem('supabase_auth_token');
            sessionStorage.removeItem('supabase_refresh_token');
            
            // Add tokens to URL query params
            const newParams = new URLSearchParams(window.location.search);
            newParams.delete('auth_callback');
            newParams.set('access_token', token);
            if (refresh) newParams.set('refresh_token', refresh);
            
            window.location.replace(window.location.pathname + "?" + newParams.toString());
        }
    }
})();
</script>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Handle implicit/token flow (tokens in query params after JavaScript processing)
# -----------------------------------------------------------------------------
jwt_token = st.query_params.get("access_token")
refresh_token = st.query_params.get("refresh_token")

if jwt_token and not st.session_state.get("user"):
    if set_user_from_jwt(jwt_token):
        st.session_state["sb_session"] = {
            "access_token": jwt_token,
            "refresh_token": refresh_token,
        }
        st.toast("✅ Signed in successfully!")
        # Clean URL
        for k in ("access_token","refresh_token","expires_in","expires_at","token_type","provider_token"):
            if k in st.query_params:
                del st.query_params[k]
        st.rerun()
    else:
        st.error("Could not parse login token.")
        for k in ("access_token","refresh_token"):
            if k in st.query_params:
                del st.query_params[k]

# -----------------------------------------------------------------------------
# Handle code flow (?code=...) - for PKCE if enabled
# -----------------------------------------------------------------------------
auth_code = st.query_params.get("code")
if auth_code and not st.session_state.get("user"):
    try:
        response = supabase.auth.exchange_code_for_session({"auth_code": auth_code})
        if response and response.user:
            st.session_state["user"] = {
                "id": response.user.id,
                "email": response.user.email,
                "name": (response.user.user_metadata or {}).get("full_name") or response.user.email,
                "avatar_url": (response.user.user_metadata or {}).get("avatar_url"),
            }
            st.session_state["sb_session"] = {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
            }
            st.toast("✅ Signed in successfully.")
            del st.query_params["code"]
            st.rerun()
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        if "code" in st.query_params:
            del st.query_params["code"]

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
                oauth_url = build_oauth_url(REDIRECT_BASE)
                st.markdown(f'<meta http-equiv="refresh" content="0; url={oauth_url}">', unsafe_allow_html=True)
                st.markdown(f"[Click here if not redirected]({oauth_url})")
                st.stop()
        st.markdown('</div>', unsafe_allow_html=True)

# Rest of your UI code stays the same...
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
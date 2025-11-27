import streamlit as st
from supabase import create_client, Client
import base64
import json
import urllib.parse

st.set_page_config(page_title="Google Sign In", layout="wide", page_icon="🔐")

# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------
SB_URL = st.secrets["supabase"]["url"]
SB_KEY = st.secrets["supabase"]["anon_key"]

supabase: Client = create_client(SB_URL, SB_KEY)

# -----------------------------------------------------------------------------
# Get the correct redirect URL based on environment
# -----------------------------------------------------------------------------
def get_redirect_url():
    """
    Returns the appropriate redirect URL based on the environment.
    Priority:
    1. Custom domain from secrets (if set)
    2. Streamlit Cloud URL (if running on cloud)
    3. Localhost (for local development)
    """
    # Check if custom redirect URL is set in secrets
    if "redirect_url" in st.secrets.get("app", {}):
        return st.secrets["app"]["redirect_url"]
    
    # Try to detect Streamlit Cloud environment
    try:
        # Streamlit Cloud sets specific headers/environment variables
        if st.runtime.exists():
            # Get the current URL from browser
            # This is a workaround - we'll use the app name from secrets
            app_name = st.secrets.get("app", {}).get("name", "")
            if app_name:
                return f"https://{app_name}.streamlit.app"
    except:
        pass
    
    # Default to localhost for local development
    return "http://localhost:8501"

REDIRECT_URL = get_redirect_url()

# -----------------------------------------------------------------------------
# Initialize session state ONCE at the very beginning
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
    
if "session" not in st.session_state:
    st.session_state.session = None
    
if "auth_processed" not in st.session_state:
    st.session_state.auth_processed = False

# -----------------------------------------------------------------------------
# Helper to decode JWT without verification
# -----------------------------------------------------------------------------
def base64url_decode(data: str) -> bytes:
    padding = '=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)

def decode_jwt(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = base64url_decode(parts[1])
        return json.loads(payload.decode('utf-8'))
    except:
        return {}

# -----------------------------------------------------------------------------
# Handle tokens from query params - ONLY ONCE
# -----------------------------------------------------------------------------
access_token = st.query_params.get("access_token")
refresh_token = st.query_params.get("refresh_token")

# Only process if we have a token AND haven't processed it yet
if access_token and not st.session_state.auth_processed:
    with st.spinner("🔄 Processing login..."):
        try:
            payload = decode_jwt(access_token)
            
            if payload and payload.get("email"):
                user_metadata = payload.get("user_metadata", {})
                
                # Update session state
                st.session_state.user = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": user_metadata.get("full_name", payload.get("email")),
                    "avatar_url": user_metadata.get("avatar_url", user_metadata.get("picture")),
                }
                st.session_state.session = {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }
                st.session_state.auth_processed = True
                
                # Clean URL
                del st.query_params["access_token"]
                if "refresh_token" in st.query_params:
                    del st.query_params["refresh_token"]
                
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Invalid token payload")
                st.session_state.auth_processed = True
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            st.session_state.auth_processed = True

# -----------------------------------------------------------------------------
# Display UI based on authentication state
# -----------------------------------------------------------------------------
user = st.session_state.user

if user:
    # Logged in state
    st.title("🔐 Welcome!")
    
    col1, col2 = st.columns([1, 5])
    
    with col1:
        avatar_url = user.get("avatar_url")
        if avatar_url:
            try:
                st.image(avatar_url, width=80)
            except:
                st.markdown("# 👤")
        else:
            st.markdown("# 👤")
    
    with col2:
        st.markdown(f"### {user['name']}")
        st.markdown(f"📧 {user['email']}")
    
    st.divider()
    
    # Action buttons
    col_a, col_b, col_c = st.columns([2, 2, 6])
    
    with col_a:
        if st.button("🚪 Sign Out", use_container_width=True):
            try:
                supabase.auth.sign_out()
            except:
                pass
            st.session_state.user = None
            st.session_state.session = None
            st.session_state.auth_processed = False
            st.rerun()
    
    with col_b:
        with st.expander("🔍 Session Info"):
            st.json(st.session_state.session)

else:
    # Not logged in state
    st.title("🔐 Google Sign In")
    st.markdown("### Welcome! Please sign in to continue")
    
    st.divider()
    
    # Build OAuth URL with dynamic redirect
    authorize_url = f"{SB_URL}/auth/v1/authorize"
    params = {
        "provider": "google",
        "redirect_to": REDIRECT_URL,
        "flow_type": "implicit"
    }
    oauth_url = f"{authorize_url}?{urllib.parse.urlencode(params)}"
    
    # Primary sign-in method
    st.subheader("🚀 Quick Sign In")
    st.info("Click the button below to sign in with your Google account")
    
    st.markdown(f"""
    <a href="{oauth_url}" target="_self">
        <button style="
            background-color: #4285F4;
            color: white;
            padding: 14px 32px;
            font-size: 16px;
            font-weight: 500;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            transition: background-color 0.3s;
        "
        onmouseover="this.style.backgroundColor='#357ae8'"
        onmouseout="this.style.backgroundColor='#4285F4'">
            <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><path d="M17.6 9.2l-.1-1.8H9v3.4h4.8C13.6 12 13 13 12 13.6v2.2h3a8.8 8.8 0 0 0 2.6-6.6z" fill="#FFF"/><path d="M9 18c2.4 0 4.5-.8 6-2.2l-3-2.2a5.4 5.4 0 0 1-8-2.9H1V13a9 9 0 0 0 8 5z" fill="#FFF"/><path d="M4 10.7a5.4 5.4 0 0 1 0-3.4V5H1a9 9 0 0 0 0 8l3-2.3z" fill="#FFF"/><path d="M9 3.6c1.3 0 2.5.4 3.4 1.3L15 2.3A9 9 0 0 0 1 5l3 2.4a5.4 5.4 0 0 1 5-3.7z" fill="#FFF"/></g></svg>
            Sign in with Google
        </button>
    </a>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # Alternative manual method
    st.subheader("🔧 Alternative: Manual Sign In")
    
    st.warning("""
    **If the button above doesn't redirect you automatically**, use this manual method:
    
    1. Click the link below to open Google Sign In
    2. Sign in with your Google account
    3. After signing in, you'll be redirected back - **copy the complete URL** from your browser's address bar
    4. Paste the URL in the text box below
    """)
    
    st.markdown(f"**Step 1:** [Open Google Sign In →]({oauth_url})")
    
    st.markdown("**Step 2 & 3:** Paste the redirect URL here:")
    
    manual_url = st.text_input(
        "Complete URL from browser:",
        placeholder=f"{REDIRECT_URL}/#access_token=eyJhbGc...",
        help="The URL should contain '#access_token=' after you sign in",
        label_visibility="collapsed"
    )

    if manual_url:
        if "#access_token=" in manual_url:
            try:
                hash_part = manual_url.split("#")[1]
                hash_params = dict(urllib.parse.parse_qsl(hash_part))
                
                if "access_token" in hash_params:
                    new_url = f"{REDIRECT_URL}?access_token={hash_params['access_token']}"
                    if "refresh_token" in hash_params:
                        new_url += f"&refresh_token={hash_params['refresh_token']}"
                    
                    st.success("✅ Token extracted successfully! Redirecting...")
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={new_url}">', unsafe_allow_html=True)
                    st.info(f"If you're not redirected, [click here]({new_url})")
            except Exception as e:
                st.error(f"❌ Error parsing URL: {e}")
                st.info("Please make sure you copied the complete URL including the '#access_token=...' part")
        else:
            st.warning("⚠️ The URL doesn't contain an access token. Please sign in first using the link above.")

    # Debug section
    with st.expander("🛠️ Developer Info"):
        st.write("**Redirect URL:**", REDIRECT_URL)
        st.write("**Query Params:**", dict(st.query_params))
        st.write("**Session State:**")
        st.json({
            "user": st.session_state.user,
            "auth_processed": st.session_state.auth_processed,
            "has_session": st.session_state.session is not None
        })
        
        if st.button("🗑️ Clear All Session Data"):
            st.session_state.user = None
            st.session_state.session = None
            st.session_state.auth_processed = False
            for key in list(st.query_params.keys()):
                del st.query_params[key]
            st.rerun()
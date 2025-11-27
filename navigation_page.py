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

st.title("🔐 Google Sign In")

# Handle tokens from query params
access_token = st.query_params.get("access_token")
refresh_token = st.query_params.get("refresh_token")

if access_token and not st.session_state.get("user"):
    st.info("🔄 Processing login...")
    
    try:
        payload = decode_jwt(access_token)
        
        if payload and payload.get("email"):
            user_metadata = payload.get("user_metadata", {})
            
            st.session_state["user"] = {
                "id": payload.get("sub"),
                "email": payload.get("email"),
                "name": user_metadata.get("full_name", payload.get("email")),
                "avatar_url": user_metadata.get("avatar_url"),
            }
            st.session_state["session"] = {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
            
            # Clean URL
            del st.query_params["access_token"]
            if "refresh_token" in st.query_params:
                del st.query_params["refresh_token"]
            
            st.success("✅ Login successful!")
            st.rerun()
        else:
            st.error("❌ Invalid token payload")
    except Exception as e:
        st.error(f"❌ Authentication failed: {e}")

# Show user info
user = st.session_state.get("user")

if user:
    col1, col2 = st.columns([1, 4])
    
    with col1:
        if user.get("avatar_url"):
            st.image(user["avatar_url"], width=100)
    
    with col2:
        st.success(f"### ✅ Logged in as: **{user['name']}**")
        st.write(f"📧 **Email:** {user['email']}")
    
    st.write("---")
    
    with st.expander("🔍 Session Details"):
        st.json(st.session_state.get("session", {}))
    
    if st.button("🚪 Sign Out", type="secondary"):
        try:
            supabase.auth.sign_out()
        except:
            pass
        st.session_state.clear()
        st.rerun()
else:
    st.warning("⚠️ Not logged in")
    
    st.write("---")
    
    # Build OAuth URL
    redirect_url = "http://localhost:8501"
    authorize_url = f"{SB_URL}/auth/v1/authorize"
    params = {
        "provider": "google",
        "redirect_to": redirect_url,
        "flow_type": "implicit"
    }
    oauth_url = f"{authorize_url}?{urllib.parse.urlencode(params)}"
    
    # Step-by-step instructions
    st.subheader("📝 Sign In Instructions")
    
    st.info("""
    **Due to browser security restrictions, please follow these 3 simple steps:**
    
    1️⃣ Click the **Google Sign In** link below
    
    2️⃣ Sign in with your Google account
    
    3️⃣ After redirecting back, **copy the entire URL** from your browser's address bar and paste it in the box that appears below
    """)
    
    st.markdown(f"### [🔐 Step 1: Click here to sign in with Google]({oauth_url})")
    
    st.write("---")
    
    st.subheader("3️⃣ Step 3: Paste the redirect URL here")
    
    manual_url = st.text_input(
        "Paste the full URL from your browser:",
        placeholder="http://localhost:8501/#access_token=...",
        help="After signing in with Google, copy the entire URL from your browser's address bar and paste it here"
    )

    if manual_url:
        if "#access_token=" in manual_url:
            try:
                # Extract hash part
                hash_part = manual_url.split("#")[1]
                hash_params = dict(urllib.parse.parse_qsl(hash_part))
                
                if "access_token" in hash_params:
                    # Reconstruct URL with query params
                    new_url = f"http://localhost:8501?access_token={hash_params['access_token']}"
                    if "refresh_token" in hash_params:
                        new_url += f"&refresh_token={hash_params['refresh_token']}"
                    
                    st.success("✅ Token extracted! Redirecting...")
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={new_url}">', unsafe_allow_html=True)
                    st.info(f"If not redirected automatically, [click here]({new_url})")
            except Exception as e:
                st.error(f"❌ Error parsing URL: {e}")
                st.write("Please make sure you copied the entire URL including the `#access_token=...` part")
        else:
            st.warning("⚠️ The pasted URL doesn't contain an access token. Please sign in first using the link above.")

with st.expander("🛠️ Debug Info"):
    st.write("**Query Params:**", dict(st.query_params))
    st.write("**Session State:**", dict(st.session_state))
    
    if st.button("🗑️ Clear All Session Data"):
        st.session_state.clear()
        for key in list(st.query_params.keys()):
            del st.query_params[key]
        st.rerun()
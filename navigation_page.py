import streamlit as st
from supabase import create_client, Client
import base64
import json
import urllib.parse

st.set_page_config(
    page_title="Sign In - MigNar", 
    layout="wide", 
    page_icon=".streamlit/static/MigNar_icon.png"
)
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
    if "redirect_url" in st.secrets.get("app", {}):
        return st.secrets["app"]["redirect_url"]
    return "http://localhost:8501"

REDIRECT_URL = get_redirect_url()

# -----------------------------------------------------------------------------
# Initialize session state
# -----------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None
    
if "session" not in st.session_state:
    st.session_state.session = None
    
if "auth_processed" not in st.session_state:
    st.session_state.auth_processed = False

if "show_signup" not in st.session_state:
    st.session_state.show_signup = False

# -----------------------------------------------------------------------------
# Helper to decode JWT
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
# Handle tokens from query params (OAuth callback)
# -----------------------------------------------------------------------------
access_token = st.query_params.get("access_token")
refresh_token = st.query_params.get("refresh_token")

if access_token and not st.session_state.auth_processed:
    with st.spinner("🔄 Processing login..."):
        try:
            payload = decode_jwt(access_token)
            
            if payload and payload.get("email"):
                user_metadata = payload.get("user_metadata", {})
                app_metadata = payload.get("app_metadata", {})
                
                # Get provider info
                provider = app_metadata.get("provider", "email")
                
                st.session_state.user = {
                    "id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": user_metadata.get("full_name") or user_metadata.get("name") or user_metadata.get("user_name") or payload.get("email"),
                    "avatar_url": user_metadata.get("avatar_url") or user_metadata.get("picture"),
                    "provider": provider,
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
# Display UI
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
        
        # Show provider badge
        provider = user.get("provider", "email")
        provider_emoji = {"google": "🔵", "github": "⚫", "email": "📧"}.get(provider, "🔐")
        st.markdown(f"**Signed in with:** {provider_emoji} {provider.title()}")
    
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
    st.title("🔐 Sign In")
    st.markdown("### Welcome! Please sign in to continue")
    
    st.divider()
    
    # Tabs for different auth methods
    tab1, tab2 = st.tabs(["📧 Email", "🌐 Social Login"])
    
    with tab1:
        # Email/Password Authentication
        st.subheader("Sign in with Email")
        
        # Toggle between Sign In and Sign Up
        auth_mode = st.radio(
            "Select mode:",
            ["Sign In", "Sign Up"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        with st.form("email_auth_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            if auth_mode == "Sign Up":
                password_confirm = st.text_input("Confirm Password", type="password", placeholder="••••••••")
                full_name = st.text_input("Full Name (optional)", placeholder="John Doe")
            
            submitted = st.form_submit_button(
                f"{'Create Account' if auth_mode == 'Sign Up' else 'Sign In'}",
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not email or not password:
                    st.error("❌ Please fill in all required fields")
                elif auth_mode == "Sign Up" and password != password_confirm:
                    st.error("❌ Passwords don't match")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    try:
                        if auth_mode == "Sign Up":
                            # Sign up new user
                            with st.spinner("Creating account..."):
                                response = supabase.auth.sign_up({
                                    "email": email,
                                    "password": password,
                                    "options": {
                                        "data": {
                                            "full_name": full_name if full_name else email.split("@")[0]
                                        }
                                    }
                                })
                                
                                if response.user:
                                    st.success("✅ Account created successfully!")
                                    st.info("🔒 Please check your email to confirm your account (if email confirmation is enabled)")
                                    
                                    # Auto sign-in if email confirmation is disabled
                                    if response.session:
                                        st.session_state.user = {
                                            "id": response.user.id,
                                            "email": response.user.email,
                                            "name": full_name if full_name else email.split("@")[0],
                                            "avatar_url": None,
                                            "provider": "email",
                                        }
                                        st.session_state.session = {
                                            "access_token": response.session.access_token,
                                            "refresh_token": response.session.refresh_token,
                                        }
                                        st.session_state.auth_processed = True
                                        st.rerun()
                                else:
                                    st.error("❌ Failed to create account")
                        else:
                            # Sign in existing user
                            with st.spinner("Signing in..."):
                                response = supabase.auth.sign_in_with_password({
                                    "email": email,
                                    "password": password
                                })
                                
                                if response.user and response.session:
                                    user_metadata = response.user.user_metadata or {}
                                    
                                    st.session_state.user = {
                                        "id": response.user.id,
                                        "email": response.user.email,
                                        "name": user_metadata.get("full_name", email.split("@")[0]),
                                        "avatar_url": user_metadata.get("avatar_url"),
                                        "provider": "email",
                                    }
                                    st.session_state.session = {
                                        "access_token": response.session.access_token,
                                        "refresh_token": response.session.refresh_token,
                                    }
                                    st.session_state.auth_processed = True
                                    st.success("✅ Login successful!")
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid email or password")
                    except Exception as e:
                        error_msg = str(e)
                        if "Invalid login credentials" in error_msg:
                            st.error("❌ Invalid email or password")
                        elif "User already registered" in error_msg:
                            st.error("❌ Email already registered. Please sign in instead.")
                        else:
                            st.error(f"❌ Authentication failed: {error_msg}")
        
        # Password reset option
        if auth_mode == "Sign In":
            with st.expander("🔑 Forgot Password?"):
                reset_email = st.text_input("Enter your email:", placeholder="your@email.com", key="reset_email")
                if st.button("Send Reset Link"):
                    if reset_email:
                        try:
                            supabase.auth.reset_password_email(reset_email)
                            st.success("✅ Password reset link sent! Check your email.")
                        except Exception as e:
                            st.error(f"❌ Failed to send reset link: {e}")
                    else:
                        st.warning("⚠️ Please enter your email")
    
    with tab2:
        # OAuth Authentication
        st.subheader("Sign in with Social Account")
        
        # Build OAuth URLs
        def get_oauth_url(provider: str) -> str:
            authorize_url = f"{SB_URL}/auth/v1/authorize"
            params = {
                "provider": provider,
                "redirect_to": REDIRECT_URL,
                "flow_type": "implicit"
            }
            return f"{authorize_url}?{urllib.parse.urlencode(params)}"
        
        google_oauth_url = get_oauth_url("google")
        github_oauth_url = get_oauth_url("github")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <a href="{google_oauth_url}" target="_self">
                <button style="
                    background-color: #4285F4;
                    color: white;
                    padding: 14px 24px;
                    font-size: 16px;
                    font-weight: 500;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: background-color 0.3s;
                    width: 100%;
                "
                onmouseover="this.style.backgroundColor='#357ae8'"
                onmouseout="this.style.backgroundColor='#4285F4'">
                    <svg width="20" height="20" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><path d="M17.6 9.2l-.1-1.8H9v3.4h4.8C13.6 12 13 13 12 13.6v2.2h3a8.8 8.8 0 0 0 2.6-6.6z" fill="#FFF"/><path d="M9 18c2.4 0 4.5-.8 6-2.2l-3-2.2a5.4 5.4 0 0 1-8-2.9H1V13a9 9 0 0 0 8 5z" fill="#FFF"/><path d="M4 10.7a5.4 5.4 0 0 1 0-3.4V5H1a9 9 0 0 0 0 8l3-2.3z" fill="#FFF"/><path d="M9 3.6c1.3 0 2.5.4 3.4 1.3L15 2.3A9 9 0 0 0 1 5l3 2.4a5.4 5.4 0 0 1 5-3.7z" fill="#FFF"/></g></svg>
                    Google
                </button>
            </a>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <a href="{github_oauth_url}" target="_self">
                <button style="
                    background-color: #24292e;
                    color: white;
                    padding: 14px 24px;
                    font-size: 16px;
                    font-weight: 500;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    transition: background-color 0.3s;
                    width: 100%;
                "
                onmouseover="this.style.backgroundColor='#1a1e22'"
                onmouseout="this.style.backgroundColor='#24292e'">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
                    GitHub
                </button>
            </a>
            """, unsafe_allow_html=True)
        
        st.divider()
        
        # Manual OAuth fallback
        with st.expander("🔧 Manual Social Login"):
            st.warning("""
            **If the buttons above don't work**, use this manual method:
            
            1. Click one of the links below
            2. After signing in, **copy the complete URL** from your browser
            3. Paste it in the text box below
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"[Open Google →]({google_oauth_url})")
            with col2:
                st.markdown(f"[Open GitHub →]({github_oauth_url})")
            
            manual_url = st.text_input(
                "Paste the redirect URL here:",
                placeholder=f"{REDIRECT_URL}/#access_token=eyJhbGc...",
                help="The URL should contain '#access_token=' after you sign in",
                label_visibility="collapsed",
                key="manual_oauth_url"
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
                        st.error(f"❌ Error: {e}")
                else:
                    st.warning("⚠️ Please sign in first using one of the links above.")

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
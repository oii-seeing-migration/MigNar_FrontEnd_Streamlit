import streamlit as st

def apply_sidebar_names():
    st.markdown("""
    <style>
        /* 1. Sign In (navigation_page.py) */
        [data-testid="stSidebarNav"] li:nth-child(1) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(1) span::before {
            content: "🔐 Sign In";
            visibility: visible;
        }
        
        /* 4. Narratives Taxonomy */
        [data-testid="stSidebarNav"] li:nth-child(4) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(4) span::before {
            content: "📚 Narratives Taxonomy";
            visibility: visible;
        }
        
        /* 5. Narratives on Articles */
        [data-testid="stSidebarNav"] li:nth-child(5) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(5) span::before {
            content: "📰 Narratives on Articles";
            visibility: visible;
        }
        
        /* 6. Aggregative Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(6) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(6) span::before {
            content: "📊 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱: Aggregative";
            visibility: visible;
        }
        
        /* 7. Comparative Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(7) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(7) span::before {
            content: "⚖️ 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱: Comparative";
            visibility: visible;
        }
        
        /* 8. Temporal Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(8) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(8) span::before {
            content: "📈 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱: Temporal";
            visibility: visible;
        }
        
        /* 2. App Instructions */
        [data-testid="stSidebarNav"] li:nth-child(2) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(2) span::before {
            content: "📖 App Instructions";
            visibility: visible;
        }
        
        /* 3. Annotator Guide */
        [data-testid="stSidebarNav"] li:nth-child(3) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(3) span::before {
            content: "📝 Annotators' Guide";
            visibility: visible;
        }
                
        /* 10. Feedback */
        [data-testid="stSidebarNav"] li:nth-child(10) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(10) span::before {
            content: "💬 Feedback";
            visibility: visible;
        }

        /* 9. RealWorldStats Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(9) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(9) span::before {
            content: "🌍 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱: Real-World Stats";
            visibility: visible;
        }
    </style>
    """, unsafe_allow_html=True)


def apply_app_anonymize():
    st.markdown("""
    <style>
        /* Hide the hamburger menu */
        #MainMenu { visibility: hidden !important; }
        
        /* Hide the Streamlit default footer */
        footer { visibility: hidden !important; }
        
        /* Hide the top header bar (stops "Manage app" and Deploy buttons) */
        header { visibility: hidden !important; }
        
        /* Hide the Streamlit toolbar (top right) */
        [data-testid="stToolbar"] { visibility: hidden !important; }

        /* HIDE THE CREATOR AVATAR (Specific to Streamlit Cloud deployments) */
        [data-testid="appCreatorAvatar"] {
            display: none !important;
        }

        /* HIDE THE "MADE WITH STREAMLIT" CLOUD BADGE (Bottom right corner) */
        a[href="https://streamlit.io/cloud"] {
            display: none !important;
        }
        
        /* General safety catch for the profile image specifically */
        img[alt="App Creator Avatar"] {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
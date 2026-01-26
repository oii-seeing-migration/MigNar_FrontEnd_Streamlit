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
            content: "📊 Aggregative Dashboard";
            visibility: visible;
        }
        
        /* 7. Contrastive Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(7) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(7) span::before {
            content: "⚖️ Contrastive Dashboard";
            visibility: visible;
        }
        
        /* 8. Temporal Dashboard */
        [data-testid="stSidebarNav"] li:nth-child(8) span {
            visibility: hidden;
        }
        [data-testid="stSidebarNav"] li:nth-child(8) span::before {
            content: "📈 Temporal Dashboard";
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
            content: "📝 Annotator Guide";
            visibility: visible;
        }
    </style>
    """, unsafe_allow_html=True)
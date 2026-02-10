import os
from datetime import datetime
import streamlit as st
from lib.auth import require_auth

st.set_page_config(
    page_title="Feedback",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png"
)

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

FEEDBACK_TABLE = "user_feedback"
BIND_OK, AUTH_UID, USER, supabase = require_auth()

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.feedback-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 30px;
    border-radius: 12px;
    margin-bottom: 20px;
}
.feedback-header h1 {
    margin: 0;
    font-size: 2rem;
}
.feedback-header p {
    margin: 10px 0 0 0;
    opacity: 0.9;
}
.login-banner {
    background: #e3f2fd;
    border: 1px solid #90caf9;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.login-banner.logged {
    background: #e8f5e9;
    border-color: #81c784;
}
.feedback-card {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 12px;
}
.feedback-card.open { border-left: 4px solid #2196f3; }
.feedback-card.in_progress { border-left: 4px solid #ff9800; }
.feedback-card.resolved { border-left: 4px solid #4caf50; }
.feedback-card.wont_fix { border-left: 4px solid #9e9e9e; }
.feedback-card.duplicate { border-left: 4px solid #795548; }
.status-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}
.status-open { background: #e3f2fd; color: #1565c0; }
.status-in_progress { background: #fff3e0; color: #e65100; }
.status-resolved { background: #e8f5e9; color: #2e7d32; }
.status-wont_fix { background: #f5f5f5; color: #616161; }
.status-duplicate { background: #efebe9; color: #4e342e; }
.type-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 500;
    margin-right: 8px;
}
.type-bug { background: #ffebee; color: #c62828; }
.type-feature { background: #e8f5e9; color: #2e7d32; }
.type-usability { background: #fff3e0; color: #e65100; }
.type-data_quality { background: #e3f2fd; color: #1565c0; }
.type-documentation { background: #f3e5f5; color: #7b1fa2; }
.type-other { background: #eceff1; color: #546e7a; }
.severity-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 500;
}
.severity-low { background: #e8f5e9; color: #2e7d32; }
.severity-medium { background: #fff3e0; color: #e65100; }
.severity-high { background: #ffebee; color: #c62828; }
.severity-critical { background: #c62828; color: white; }
.thank-you-box {
    background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
    border: 2px solid #66bb6a;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    margin: 20px 0;
}
</style>
""", unsafe_allow_html=True)

# ── DB Functions ───────────────────────────────────────────────────────────────
def submit_feedback(user: dict, feedback_type: str, subject: str, description: str,
                    page_context: str = None, severity: str = None) -> tuple[bool, str]:
    uid = AUTH_UID or user.get("id")
    if not uid:
        return (False, "No user ID available")
    
    try:
        payload = {
            "user_id": str(uid),
            "user_name": user.get("name") or user.get("email") or "Unknown",
            "user_email": user.get("email") or "",
            "feedback_type": feedback_type,
            "subject": subject,
            "description": description,
            "page_context": page_context or None,
            "severity": severity or None,
        }
        supabase.table(FEEDBACK_TABLE).insert(payload).execute()
        return (True, "Feedback submitted successfully!")
    except Exception as e:
        return (False, f"Error submitting feedback: {e}")

def fetch_user_feedback(user_id: str) -> list[dict]:
    if not user_id:
        return []
    try:
        res = supabase.table(FEEDBACK_TABLE).select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []

# ── Page Constants ─────────────────────────────────────────────────────────────
FEEDBACK_TYPES = {
    "bug": ("🐛 Bug Report", "Something isn't working correctly"),
    "feature": ("✨ Feature Request", "Suggest a new feature or improvement"),
    "usability": ("🎯 Usability Issue", "Something is confusing or hard to use"),
    "data_quality": ("📊 Data Quality", "Issues with the data or annotations"),
    "documentation": ("📖 Documentation", "Improvements to guides or documentation"),
    "other": ("💬 Other", "General feedback or comments"),
}

SEVERITY_OPTIONS = {
    "low": "Low - Minor inconvenience",
    "medium": "Medium - Affects workflow",
    "high": "High - Significant impact",
    "critical": "Critical - Blocking issue",
}

PAGE_OPTIONS = [
    "(General / Not page-specific)",
    "Sign In / Authentication",
    "Annotator Guide",
    "Narratives Taxonomy",
    "Narratives on Articles",
    "Aggregative Dashboard",
    "Contrastive Dashboard",
    "Temporal Dashboard",
]

# ── Main Content ───────────────────────────────────────────────────────────────
st.markdown("""
<div class='feedback-header'>
    <h1>💬 Feedback</h1>
    <p>Help us improve MigNar! Report bugs, suggest features, or share your thoughts.</p>
</div>
""", unsafe_allow_html=True)

# Login banner
if USER and AUTH_UID and BIND_OK:
    st.markdown(f"<div class='login-banner logged'>✅ Signed in as <strong>{USER.get('name') or USER.get('email')}</strong></div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='login-banner'>🔐 <a href='/'>Sign in</a> to submit feedback and track your submissions.</div>", unsafe_allow_html=True)

# Tabs for Submit / View History
tab_submit, tab_history = st.tabs(["📝 Submit Feedback", "📋 My Submissions"])

# ── Submit Feedback Tab ────────────────────────────────────────────────────────
with tab_submit:
    is_logged_in = USER and AUTH_UID and BIND_OK
    
    with st.form(key="feedback_form", clear_on_submit=True):
        st.subheader("Tell us what's on your mind")
        
        # Feedback type selection with icons
        st.markdown("**What type of feedback is this?**")
        type_cols = st.columns(3)
        type_options = list(FEEDBACK_TYPES.keys())
        type_labels = [f"{FEEDBACK_TYPES[t][0]}" for t in type_options]
        
        feedback_type = st.radio(
            "Feedback Type",
            options=type_options,
            format_func=lambda x: FEEDBACK_TYPES[x][0],
            horizontal=True,
            label_visibility="collapsed",
            disabled=not is_logged_in,
        )
        
        if feedback_type:
            st.caption(f"*{FEEDBACK_TYPES[feedback_type][1]}*")
        
        st.markdown("---")
        
        # Context and severity (side by side)
        col1, col2 = st.columns(2)
        with col1:
            page_context = st.selectbox(
                "Related Page (optional)",
                options=PAGE_OPTIONS,
                index=0,
                disabled=not is_logged_in,
                help="Which page is this feedback about?"
            )
        with col2:
            severity = st.selectbox(
                "Severity (optional)",
                options=[""] + list(SEVERITY_OPTIONS.keys()),
                format_func=lambda x: "— Select severity —" if x == "" else SEVERITY_OPTIONS[x],
                disabled=not is_logged_in,
                help="How much does this issue affect your work?"
            )
        
        # Subject
        subject = st.text_input(
            "Subject *",
            placeholder="Brief summary of your feedback",
            max_chars=200,
            disabled=not is_logged_in,
        )
        
        # Description
        description = st.text_area(
            "Description *",
            placeholder="Please provide as much detail as possible. For bugs, include:\n• Steps to reproduce\n• What you expected to happen\n• What actually happened",
            height=200,
            disabled=not is_logged_in,
        )
        
        # Submit button
        st.markdown("---")
        submit_cols = st.columns([0.7, 0.3])
        with submit_cols[0]:
            st.caption("* Required fields")
        with submit_cols[1]:
            submitted = st.form_submit_button(
                "📤 Submit Feedback",
                type="primary",
                use_container_width=True,
                disabled=not is_logged_in,
            )
    
    # Handle form submission
    if submitted and is_logged_in:
        # Validation
        if not subject.strip():
            st.error("Please enter a subject for your feedback.")
        elif not description.strip():
            st.error("Please enter a description for your feedback.")
        elif len(description.strip()) < 20:
            st.error("Please provide more detail in your description (at least 20 characters).")
        else:
            # Submit to database
            page_ctx = None if page_context == PAGE_OPTIONS[0] else page_context
            sev = severity if severity else None
            
            success, message = submit_feedback(
                user=USER,
                feedback_type=feedback_type,
                subject=subject.strip(),
                description=description.strip(),
                page_context=page_ctx,
                severity=sev,
            )
            
            if success:
                st.markdown("""
                <div class='thank-you-box'>
                    <h3>🎉 Thank you for your feedback!</h3>
                    <p>We appreciate you taking the time to help us improve MigNar.</p>
                    <p>You can track the status of your submission in the "My Submissions" tab.</p>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()
            else:
                st.error(message)

# ── View History Tab ───────────────────────────────────────────────────────────
with tab_history:
    if not (USER and AUTH_UID and BIND_OK):
        st.info("🔐 Sign in to view your previous feedback submissions.")
    else:
        feedback_list = fetch_user_feedback(AUTH_UID)
        
        if not feedback_list:
            st.info("You haven't submitted any feedback yet. Use the 'Submit Feedback' tab to share your thoughts!")
        else:
            st.markdown(f"**{len(feedback_list)} submission(s)**")
            
            # Filter by status
            status_filter = st.selectbox(
                "Filter by status",
                options=["All", "open", "in_progress", "resolved", "wont_fix", "duplicate"],
                format_func=lambda x: {
                    "All": "All Statuses",
                    "open": "🔵 Open",
                    "in_progress": "🟠 In Progress",
                    "resolved": "🟢 Resolved",
                    "wont_fix": "⚪ Won't Fix",
                    "duplicate": "🟤 Duplicate",
                }.get(x, x)
            )
            
            filtered_feedback = feedback_list if status_filter == "All" else [f for f in feedback_list if f.get("status") == status_filter]
            
            for fb in filtered_feedback:
                fb_type = fb.get("feedback_type", "other")
                fb_status = fb.get("status", "open")
                fb_severity = fb.get("severity")
                created = fb.get("created_at", "")
                
                # Parse date
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    date_str = dt.strftime("%b %d, %Y at %H:%M")
                except:
                    date_str = created[:10] if created else "Unknown"
                
                st.markdown(f"""
                <div class='feedback-card {fb_status}'>
                    <div style='display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;'>
                        <div>
                            <span class='type-badge type-{fb_type}'>{FEEDBACK_TYPES.get(fb_type, ('Other', ''))[0]}</span>
                            {f"<span class='severity-badge severity-{fb_severity}'>{fb_severity.upper()}</span>" if fb_severity else ""}
                        </div>
                        <span class='status-badge status-{fb_status}'>{fb_status.replace('_', ' ')}</span>
                    </div>
                    <div style='font-weight: 600; font-size: 1.1rem; margin-bottom: 6px;'>{fb.get('subject', 'No subject')}</div>
                    <div style='color: #666; font-size: 0.9rem; margin-bottom: 8px;'>{fb.get('description', '')[:200]}{'...' if len(fb.get('description', '')) > 200 else ''}</div>
                    <div style='font-size: 0.75rem; color: #999;'>
                        {f"📄 {fb.get('page_context')}" if fb.get('page_context') else ""} 
                        <span style='float: right;'>📅 {date_str}</span>
                    </div>
                    {f"<div style='margin-top: 10px; padding: 8px; background: #fff3e0; border-radius: 4px; font-size: 0.85rem;'><strong>Admin note:</strong> {fb.get('admin_notes')}</div>" if fb.get('admin_notes') else ""}
                </div>
                """, unsafe_allow_html=True)

# ── Sidebar info ───────────────────────────────────────────────────────────────
st.sidebar.header("About Feedback")
st.sidebar.markdown("""
**Feedback Types:**
- 🐛 **Bug** - Report errors or broken features
- ✨ **Feature** - Suggest improvements
- 🎯 **Usability** - UI/UX issues
- 📊 **Data Quality** - Annotation or data problems
- 📖 **Documentation** - Guide improvements
- 💬 **Other** - General comments

**Status Legend:**
- 🔵 Open - Under review
- 🟠 In Progress - Being worked on
- 🟢 Resolved - Fixed/implemented
- ⚪ Won't Fix - Not planned
- 🟤 Duplicate - Already reported
""")

if USER and AUTH_UID and BIND_OK:
    feedback_count = len(fetch_user_feedback(AUTH_UID))
    st.sidebar.divider()
    st.sidebar.metric("Your Submissions", feedback_count)
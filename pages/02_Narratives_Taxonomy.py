import os, re, importlib.util, urllib.parse, base64, json
import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Meso Narratives Taxonomy",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

# ── Supabase client ────────────────────────────────────────────────────────────
SB_URL = st.secrets["supabase"]["url"]
SB_KEY = st.secrets["supabase"]["anon_key"]
supabase: Client = create_client(SB_URL, SB_KEY)

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

def bind_auth_from_session() -> tuple[bool, str | None]:
    sess = st.session_state.get("session") or {}
    at = sess.get("access_token")
    rt = sess.get("refresh_token")
    if not at:
        return (False, None)
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
    try:
        me = supabase.auth.get_user()
        au = getattr(me, "user", None) or me
        uid = getattr(au, "id", None)
    except Exception:
        pass
    if not uid:
        payload = jwt_payload(at) or {}
        uid = payload.get("sub")
    ok = bool(uid)
    return (ok, uid)

BIND_OK, AUTH_UID = bind_auth_from_session()
USER = st.session_state.get("user")

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.open-btn { display:inline-block; background:#1976d2; color:#fff !important; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:0.75rem; margin:2px 0; }
.open-btn:hover { background:#0d47a1; }
.suggest-btn { display:inline-block; background:#43a047; color:#fff !important; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:0.75rem; margin:2px 0; }
.theme-box { padding:10px 12px; border-radius:10px; margin-top:14px; display:flex; align-items:center; justify-content:space-between; }
.theme-left { font-weight:600; }
.theme-right { font-size:0.9rem; opacity:0.8; }
.narr-row { padding:8px 10px; border-radius:8px; display:flex; align-items:center; gap:10px; }
.narr-text { flex:1; }
.narr-count { text-align:right; font-size:0.9rem; opacity:0.8; }
.login-banner { background:#e3f2fd; border:1px solid #90caf9; padding:8px 12px; border-radius:8px; margin-bottom:10px; }
.login-banner.logged { background:#e8f5e9; border-color:#81c784; }
div[data-testid="column"] { padding-left: 0 !important; padding-right: 0 !important; }
.theme-num { font-weight:700; color:#1565c0; margin-right:6px; }
.meso-num { font-weight:600; color:#666; margin-right:6px; font-size:0.9rem; }
.suggest-row { background: #e8f5e9; border: 1px dashed #81c784; border-radius: 8px; padding: 8px 10px; margin-top: 8px; }
.suggest-label { color: #2e7d32; font-weight: 600; font-size: 0.9rem; }

/* Sticky save button container */
.sticky-save-container {
    position: sticky;
    top: 0;
    z-index: 999;
    background: linear-gradient(to bottom, rgba(255,255,255,1) 0%, rgba(255,255,255,1) 85%, rgba(255,255,255,0) 100%);
    padding: 10px 0 20px 0;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR   = os.path.expanduser("./data")
MESO_PATH  = os.path.join(DATA_DIR, "meso_monthly.parquet")
TAXON_DIR  = os.path.join(os.path.dirname(__file__), "../taxonomy")
ARTICLES_SLUG = "Narratives_on_Articles"

# Updated label options to match Annotator Guide
ANNOT_OPTIONS = ["", "good", "too broad", "too narrow", "duplicate", "wrong theme", "poor wording", "other issues"]
THEME_ANNOT_OPTIONS = ["", "good", "too broad", "too narrow", "duplicate", "wrong theme", "poor wording", "other issues"]
REAL_OPTIONS = set(ANNOT_OPTIONS[1:])
REAL_THEME_OPTIONS = set(THEME_ANNOT_OPTIONS[1:])
ANNOT_TABLE = "taxonomy_annotations"

# Special meso name for human-suggested narratives
HUMAN_SUGGESTED_MESO = "human suggested narratives"

# Sources to exclude by default (US Congress and UK Parliament party breakdowns)
EXCLUDED_SOURCES_DEFAULT = {
    "US Congress (All)",
    "US Congress (Rep)",
    "US Congress (Dem)",
    "UK Parliament (Lab)",
    "UK Parliament (Con)",
}

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=True, ttl="30m", max_entries=1)
def load_meso_df(fp: str) -> pd.DataFrame:
    if not os.path.exists(fp):
        return pd.DataFrame(columns=["month","model","version","source_domain","theme","meso_narrative","count"])
    df = pd.read_parquet(fp)
    if "month" in df.columns:
        df["month"] = df["month"].astype(str)
    for c in ["source_domain","model","theme","meso_narrative"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
    if "version" in df.columns:
        df["version"] = pd.to_numeric(df["version"], errors="coerce").fillna(0).astype(int)
    return df

@st.cache_data(show_spinner=True, ttl="30m", max_entries=1)
def list_revisions() -> list[int]:
    if not os.path.isdir(TAXON_DIR):
        return []
    revs = []
    for fname in os.listdir(TAXON_DIR):
        m = re.fullmatch(r"meso_narratives_revision_(\d+)\.py", fname)
        if m:
            revs.append(int(m.group(1)))
    return sorted(set(revs))

@st.cache_data(show_spinner=True, ttl="30m", max_entries=1)
def load_taxonomy(revision: int) -> dict[str, list[str]]:
    path = os.path.join(TAXON_DIR, f"meso_narratives_revision_{revision}.py")
    if not os.path.exists(path):
        return {}
    spec = importlib.util.spec_from_file_location("meso_tax", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return {}
    data = getattr(mod, "mesoNarratives", None)
    if not isinstance(data, dict):
        for v in vars(mod).values():
            if isinstance(v, dict):
                data = v
                break
    if not isinstance(data, dict):
        return {}
    out = {}
    for k, v in data.items():
        if isinstance(v, (list, tuple)):
            out[str(k)] = [str(x) for x in v if isinstance(x, str)]
    return out

@st.cache_data(show_spinner=True, ttl="30m", max_entries=1)
def build_taxonomy_numbering(taxonomy: dict[str, list[str]]) -> tuple[dict[str, int], dict[tuple[str, str], str]]:
    """
    Build stable numbering for taxonomy items.
    Returns:
        theme_numbers: {theme_name: theme_number}
        meso_numbers: {(theme_name, meso_name): "T.M" format string}
    
    Themes are sorted alphabetically to ensure stable numbering regardless of filters.
    """
    theme_numbers = {}
    meso_numbers = {}
    
    # Sort themes alphabetically for stable ordering
    sorted_themes = sorted(taxonomy.keys())
    
    for theme_idx, theme in enumerate(sorted_themes, start=1):
        theme_numbers[theme] = theme_idx
        meso_list = taxonomy.get(theme, [])
        for meso_idx, meso in enumerate(meso_list, start=1):
            meso_numbers[(theme, meso)] = f"{theme_idx}.{meso_idx}"
    
    return theme_numbers, meso_numbers

def fetch_user_annotations(user_id: str | None, revision: int) -> dict[tuple[str,str], tuple[str, str]]:
    """Fetch annotations with labels AND comments - NOT cached to ensure fresh data"""
    if not user_id:
        return {}
    try:
        res = supabase.table(ANNOT_TABLE).select("theme,meso,label,comment").eq("user_id", user_id).eq("revision", revision).execute()
        items = res.data or []
        return {
            (i["theme"], i["meso"]): (i.get("label") or "", i.get("comment") or "")
            for i in items if isinstance(i, dict)
        }
    except Exception as e:
        st.error(f"Error fetching annotations: {e}")
        return {}

# ── DB write ───────────────────────────────────────────────────────────────────
def batch_upsert_annotations(user: dict, revision: int, annotations: dict) -> tuple[int, int, list[str]]:
    """Batch upsert all annotations. Returns (success_count, fail_count, error_messages)"""
    uid = AUTH_UID or user.get("id")
    if not uid:
        return (0, len(annotations), ["No user ID available"])
    
    success_count = 0
    fail_count = 0
    errors = []
    
    for key, (label, comment) in annotations.items():
        theme, meso = key
        try:
            payload = {
                "user_id": str(uid),
                "user_name": user.get("name") or user.get("email") or "Unknown",
                "theme": theme,
                "meso": meso,
                "revision": revision,
                "label": label or "",
                "comment": comment or "",
            }
            result = supabase.table(ANNOT_TABLE).upsert(payload, on_conflict="user_id,revision,theme,meso").execute()
            success_count += 1
        except Exception as e:
            fail_count += 1
            errors.append(f"{theme[:20]}...: {str(e)[:50]}")
    
    return (success_count, fail_count, errors)

# ── Load data ──────────────────────────────────────────────────────────────────
meso_df = load_meso_df(MESO_PATH)
revs = list_revisions()
if not revs:
    st.error("No taxonomy revision files found.")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.header("Controls")
if USER and AUTH_UID and BIND_OK:
    st.sidebar.success(f"✅ Signed in as **{USER.get('name') or USER.get('email')}**")
    st.sidebar.caption(f"User ID: ...{str(AUTH_UID)[-6:]}")
elif USER:
    st.sidebar.warning("⚠️ Signed in, but DB session not bound. Refresh page.")
else:
    st.sidebar.warning("🔐 Not signed in. [Go to Sign In page](/) to annotate.")

chosen_rev = st.sidebar.selectbox("Revision Version", revs, index=len(revs)-1)
taxonomy = load_taxonomy(chosen_rev)

# Build stable numbering based on taxonomy (not affected by filters)
theme_numbers, meso_numbers = build_taxonomy_numbering(taxonomy)

srcs = sorted(meso_df.source_domain.unique()) if "source_domain" in meso_df.columns else []
models = sorted(meso_df.model.unique()) if "model" in meso_df.columns else []

# Calculate default sources (exclude US Congress and UK Parliament party breakdowns)
default_sources = [s for s in srcs if s not in EXCLUDED_SOURCES_DEFAULT]

source_choice = st.sidebar.multiselect(
    "Source Domains",
    options=srcs,
    default=default_sources,
    help="Select source domains to include. By default, US Congress and UK Parliament party breakdowns are excluded."
)

model_choice = st.sidebar.selectbox("Model", ["(All models)"] + models, 
                                    index=models.index("Ensemble") + 1 if "Ensemble" in models else 0)
model_filter = None if model_choice == "(All models)" else model_choice

st.sidebar.divider()
NEW_MIN_COUNT = st.sidebar.number_input(
    "Min count for new narratives",
    min_value=1,
    max_value=500,
    value=2,
    step=5,
    help="Minimum article count required to display new narratives not in the taxonomy"
)

# Debug toggle in sidebar
# show_debug = st.sidebar.checkbox("Show debug info", value=False)
show_debug = False  # Force disable for production

# ── Main content ───────────────────────────────────────────────────────────────
st.title(f"Narratives Taxonomy (Revision {chosen_rev})")

# ── Login banner ───────────────────────────────────────────────────────────────
if USER and AUTH_UID and BIND_OK:
    st.markdown(f"<div class='login-banner logged'>✅ Signed in as <strong>{USER.get('name') or USER.get('email')}</strong> — Make changes and click Save at the top</div>", unsafe_allow_html=True)
elif USER:
    st.markdown("<div class='login-banner'>⚠️ Signed in, but database session not fully bound. Try refreshing the page.</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='login-banner'>🔐 You are not signed in. <a href='/'>Sign in</a> to save your annotations.</div>", unsafe_allow_html=True)

st.caption("Review narratives, annotate quality, and explore articles. Fill out the form below and click Save All Changes.")
st.info("📖 **New to annotation?** [Read the Annotator Guide](/Annotator_Guide) to understand what each quality label means and how to use them effectively.")

# ── Debug info ─────────────────────────────────────────────────────────────────
if show_debug:
    with st.expander("🔧 Debug Info", expanded=True):
        st.write("**Auth State:**")
        st.json({
            "BIND_OK": BIND_OK,
            "AUTH_UID": str(AUTH_UID)[-10:] if AUTH_UID else None,
            "USER": {"name": USER.get("name"), "id": str(USER.get("id"))[-10:]} if USER else None,
        })
        st.write("**Supabase Config:**")
        st.write(f"URL: {SB_URL[:30]}...")
        st.write(f"Table: {ANNOT_TABLE}")

# ── Filter and aggregate ───────────────────────────────────────────────────────
filtered = meso_df[meso_df.version == chosen_rev] if "version" in meso_df.columns else meso_df.copy()

# Apply source filter (multiselect)
if source_choice and "source_domain" in filtered.columns:
    filtered = filtered[filtered.source_domain.isin(source_choice)]

if model_filter and "model" in filtered.columns:
    filtered = filtered[filtered.model == model_filter]

agg = filtered.groupby(["theme","meso_narrative"], as_index=False)["count"].sum() if not filtered.empty else pd.DataFrame(columns=["theme","meso_narrative","count"])
counts = {(r.theme, r.meso_narrative): int(r.count) for r in agg.itertuples()} if not agg.empty else {}

taxonomy_themes = set(taxonomy.keys())
theme_totals: dict[str, int] = {}
for (th, mn), c in counts.items():
    theme_totals[th] = theme_totals.get(th, 0) + c

raw_new_narrs: dict[str, set[str]] = {}
for (th, mn), c in counts.items():
    if th not in taxonomy_themes or mn not in taxonomy.get(th, []):
        raw_new_narrs.setdefault(th, set()).add(mn)

visible_themes = []
for th in set(theme_totals.keys()).union(taxonomy_themes):
    if th in taxonomy_themes or theme_totals.get(th, 0) >= NEW_MIN_COUNT:
        visible_themes.append(th)

theme_narr_map: dict[str, tuple[list[str], list[str]]] = {}
for th in visible_themes:
    base = list(taxonomy.get(th, []))
    extras = []
    for mn in raw_new_narrs.get(th, set()):
        c = counts.get((th, mn), 0)
        if mn not in base and c >= NEW_MIN_COUNT:
            extras.append(mn)
    theme_narr_map[th] = (base, sorted(extras))

# order visible themes by taxonomy numbering, then alphabetically
visible_themes_sorted = sorted(visible_themes, key=lambda t: (theme_numbers.get(t, float('inf')), t))

# Fetch existing annotations (not cached)
prefill_map = fetch_user_annotations(AUTH_UID if AUTH_UID else (USER.get("id") if USER else None), chosen_rev)

if show_debug:
    with st.expander("🔧 Prefill Data", expanded=False):
        st.write(f"Loaded {len(prefill_map)} existing annotations")
        if prefill_map:
            st.write("Sample:", dict(list(prefill_map.items())[:3]))

def articles_link(theme: str | None = None, meso: str | None = None) -> str:
    params = []
    if theme: params.append("theme=" + urllib.parse.quote(theme))
    if meso: params.append("meso=" + urllib.parse.quote(meso))
    return f"/{ARTICLES_SLUG}" + (("?" + "&".join(params)) if params else "")

def link_button(theme: str, meso: str | None = None, label: str = "View on Articles"):
    st.markdown(f"<a class='open-btn' href='{articles_link(theme, meso)}' target='_blank' rel='noopener'>{label}</a>", unsafe_allow_html=True)

# ── FORM: Wrap all annotations in a form to prevent reloads ────────────────────
with st.form(key="annotation_form", clear_on_submit=False):
    form_data = {}
    
    # ── Save Button (will be positioned fixed via CSS) ─────────────────────────
    save_col1, save_col2 = st.columns([1, 1])
    with save_col1:
        submitted = st.form_submit_button("💾 Save All Changes", type="primary", use_container_width=True, disabled=not (USER and AUTH_UID and BIND_OK))
    with save_col2:
        if not (USER and AUTH_UID and BIND_OK):
            st.caption("🔐 Sign in to save")
    
    # ── Render themes and narratives ───────────────────────────────────────────
    for theme in visible_themes_sorted:
        total = theme_totals.get(theme, 0)
        in_tax = theme in taxonomy_themes
        new_theme = not in_tax
        color = "#e3f2fd" if in_tax else "#fff3e0"
        base_list, extras = theme_narr_map.get(theme, ([], []))

        # Get theme number (only for taxonomy themes)
        theme_num = theme_numbers.get(theme)
        theme_num_display = f"<span class='theme-num'>T{theme_num}.</span>" if theme_num else ""
        new_tag = " • NEW theme" if new_theme else ""

        st.markdown(
            f"<div class='theme-box' style='background:{color};'>"
            f"<div class='theme-left'>{theme_num_display}Theme: {theme}</div>"
            f"<div class='theme-right'>Total: {total}{new_tag}</div>"
            "</div>", unsafe_allow_html=True
        )

        # Header row for columns (appears once per theme, right after theme box)
        header = st.columns([0.15, 0.35, 0.08, 0.20, 0.22])
        with header[0]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        with header[1]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        with header[2]: 
            st.markdown("<small style='text-align:center; display:block;'><strong>Count</strong></small>", unsafe_allow_html=True)
        with header[3]: 
            st.markdown("<small style='text-align:center; display:block;'><strong>Label</strong></small>", unsafe_allow_html=True)
        with header[4]: 
            st.markdown("<small style='text-align:center; display:block;'><strong>Comment</strong></small>", unsafe_allow_html=True)

        # Theme-level annotation row
        theme_key = (theme, "")
        theme_label_prev, theme_comment_prev = prefill_map.get(theme_key, ("", ""))
        
        theme_annot_row = st.columns([0.15, 0.35, 0.08, 0.20, 0.22])
        with theme_annot_row[0]:
            link_button(theme, None, "View on Articles")
        with theme_annot_row[1]:
            st.markdown(f"<div style='padding:8px 0; font-weight:600; color:#1565c0;'>Theme level</div>", unsafe_allow_html=True)
        with theme_annot_row[2]:
            st.markdown(f"<div style='text-align:center; padding:8px 10px;'><span class='narr-count'>{total}</span></div>", unsafe_allow_html=True)
        with theme_annot_row[3]:
            if USER and AUTH_UID and BIND_OK:
                theme_idx = (THEME_ANNOT_OPTIONS.index(theme_label_prev) if theme_label_prev in THEME_ANNOT_OPTIONS else 0)
                theme_choice = st.selectbox(
                    "theme quality",
                    THEME_ANNOT_OPTIONS,
                    index=theme_idx,
                    key=f"theme_annot::{chosen_rev}::{theme}",
                    label_visibility="collapsed",
                    format_func=lambda v: ("—" if v == "" else v),
                    help="Rate the quality of this theme"
                )
                form_data[f"theme_annot::{theme}"] = theme_choice
            else:
                st.selectbox(
                    "theme quality",
                    THEME_ANNOT_OPTIONS,
                    index=0,
                    key=f"theme_annot::{chosen_rev}::{theme}",
                    label_visibility="collapsed",
                    format_func=lambda v: ("—" if v == "" else v),
                    disabled=True,
                    help="Sign in to annotate"
                )
        with theme_annot_row[4]:
            if USER and AUTH_UID and BIND_OK:
                theme_comment = st.text_input(
                    "Theme comment",
                    value=theme_comment_prev,
                    key=f"theme_comment::{chosen_rev}::{theme}",
                    placeholder="Add comment about this theme...",
                    label_visibility="collapsed"
                )
                form_data[f"theme_comment::{theme}"] = theme_comment
            else:
                st.text_input(
                    "Theme comment",
                    value="",
                    key=f"theme_comment::{chosen_rev}::{theme}",
                    placeholder="Sign in to comment",
                    disabled=True,
                    label_visibility="collapsed"
                )

        # Meso narratives header row (just shows "Meso Narratives" label, no column headers)
        meso_header = st.columns([0.15, 0.35, 0.08, 0.20, 0.22])
        with meso_header[0]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        with meso_header[1]: 
            st.markdown("<small style='padding-left:1px; margin-top:10px; display:block;'><strong>Meso Narratives</strong></small>", unsafe_allow_html=True)
        with meso_header[2]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        with meso_header[3]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)
        with meso_header[4]: 
            st.markdown("<small>&nbsp;</small>", unsafe_allow_html=True)

        # Meso narratives
        for mn in base_list + extras:
            cnt = counts.get((theme, mn), 0)
            is_new = (mn in extras) or new_theme or (mn not in base_list and not in_tax)
            row_bg = "#fafafa" if not is_new else "#fff8e1"

            narr_key = (theme, mn)
            prev_label, prev_comment = prefill_map.get(narr_key, ("", ""))
            
            key_sel = f"annot::{chosen_rev}::{theme}::{mn}"
            key_comment = f"comment::{chosen_rev}::{theme}::{mn}"

            # Get meso number (only for taxonomy meso narratives)
            meso_num = meso_numbers.get((theme, mn))
            meso_num_display = f"<span class='meso-num'>{meso_num}</span>" if meso_num else ""
            new_tag = " <em style='color:#c77;'>(NEW)</em>" if is_new else ""

            row = st.columns([0.15, 0.35, 0.08, 0.20, 0.22])
            with row[0]:
                link_button(theme, mn, "View on Articles")
            with row[1]:
                st.markdown(f"<div class='narr-row' style='background:{row_bg};'><span class='narr-text'>{meso_num_display}{mn}{new_tag}</span></div>", unsafe_allow_html=True)
            with row[2]:
                st.markdown(f"<div style='text-align:center; padding:8px 10px;'><span class='narr-count'>{cnt}</span></div>", unsafe_allow_html=True)
            with row[3]:
                if USER and AUTH_UID and BIND_OK:
                    idx = (ANNOT_OPTIONS.index(prev_label) if prev_label in ANNOT_OPTIONS else 0)
                    choice = st.selectbox(
                        "label",
                        ANNOT_OPTIONS,
                        index=idx,
                        key=key_sel,
                        label_visibility="collapsed",
                        format_func=lambda v: ("—" if v == "" else v),
                        help="Rate the quality of this narrative"
                    )
                    form_data[f"meso_annot::{theme}::{mn}"] = choice
                else:
                    st.selectbox(
                        "label",
                        ANNOT_OPTIONS,
                        index=0,
                        key=key_sel,
                        label_visibility="collapsed",
                        format_func=lambda v: ("—" if v == "" else v),
                        disabled=True,
                        help="Sign in to annotate"
                    )
            with row[4]:
                if USER and AUTH_UID and BIND_OK:
                    comment = st.text_input(
                        "comment",
                        value=prev_comment,
                        key=key_comment,
                        placeholder="Add comment...",
                        label_visibility="collapsed"
                    )
                    form_data[f"meso_comment::{theme}::{mn}"] = comment
                else:
                    st.text_input(
                        "comment",
                        value="",
                        key=key_comment,
                        placeholder="Sign in to comment",
                        disabled=True,
                        label_visibility="collapsed"
                    )
        
        # ── Suggest New Narratives Row ─────────────────────────────────────────
        suggest_key = (theme, HUMAN_SUGGESTED_MESO)
        _, suggest_prev_comment = prefill_map.get(suggest_key, ("", ""))
        
        suggest_row = st.columns([0.15, 0.35, 0.50])
        with suggest_row[0]:
            st.markdown("<span class='suggest-btn'>➕ Suggest New</span>", unsafe_allow_html=True)
        with suggest_row[1]:
            st.markdown("<div class='suggest-row'><span class='suggest-label'>Suggest new meso narratives in comment box, separated by <code>;</code></span></div>", unsafe_allow_html=True)
        with suggest_row[2]:
            if USER and AUTH_UID and BIND_OK:
                suggest_comment = st.text_input(
                    "Suggest new narratives",
                    value=suggest_prev_comment,
                    key=f"suggest::{chosen_rev}::{theme}",
                    placeholder="e.g., Migrants enrich local cuisine; Migrants revive dying industries",
                    label_visibility="collapsed"
                )
                form_data[f"suggest::{theme}"] = suggest_comment
            else:
                st.text_input(
                    "Suggest new narratives",
                    value="",
                    key=f"suggest::{chosen_rev}::{theme}",
                    placeholder="Sign in to suggest new narratives",
                    disabled=True,
                    label_visibility="collapsed"
                )
    
    # Process form submission (after all fields are rendered)
    if submitted and USER and AUTH_UID and BIND_OK:
        # Collect ALL annotations (not just changed ones, to ensure saving works)
        annotations_to_save = {}
        
        for theme in visible_themes_sorted:
            # Theme annotations - always save if there's a value
            theme_key = (theme, "")
            new_label = form_data.get(f"theme_annot::{theme}", "")
            new_comment = form_data.get(f"theme_comment::{theme}", "")
            saved_label, saved_comment = prefill_map.get(theme_key, ("", ""))
            
            # Save if there's any value OR if it changed
            if new_label or new_comment or (new_label != saved_label) or (new_comment != saved_comment):
                annotations_to_save[theme_key] = (new_label, new_comment)
            
            # Meso annotations
            base_list, extras = theme_narr_map.get(theme, ([], []))
            for mn in base_list + extras:
                narr_key = (theme, mn)
                new_label = form_data.get(f"meso_annot::{theme}::{mn}", "")
                new_comment = form_data.get(f"meso_comment::{theme}::{mn}", "")
                saved_label, saved_comment = prefill_map.get(narr_key, ("", ""))
                
                if new_label or new_comment or (new_label != saved_label) or (new_comment != saved_comment):
                    annotations_to_save[narr_key] = (new_label, new_comment)
            
            # Human suggested narratives
            suggest_key = (theme, HUMAN_SUGGESTED_MESO)
            new_suggest_comment = form_data.get(f"suggest::{theme}", "")
            _, saved_suggest_comment = prefill_map.get(suggest_key, ("", ""))
            
            if new_suggest_comment or new_suggest_comment != saved_suggest_comment:
                annotations_to_save[suggest_key] = ("", new_suggest_comment)
        
        if show_debug:
            st.write(f"**Attempting to save {len(annotations_to_save)} annotations**")
            if annotations_to_save:
                st.write("Sample:", dict(list(annotations_to_save.items())[:3]))
        
        if annotations_to_save:
            success, fail, errors = batch_upsert_annotations(USER, chosen_rev, annotations_to_save)
            if fail == 0:
                st.success(f"✅ Saved {success} annotation(s)")
                st.rerun()
            else:
                st.warning(f"⚠️ Saved {success}, failed {fail}")
                if errors:
                    with st.expander("Show errors"):
                        for err in errors[:10]:
                            st.error(err)
        else:
            st.info("No changes to save")

# ── Footer stats ───────────────────────────────────────────────────────────────
st.markdown("---")
n_tax_themes = len(taxonomy)
n_tax_narr = sum(len(v) for v in taxonomy.values())
n_new_narr_kept = sum(len(extras) for _, (base, extras) in theme_narr_map.items() if extras)

if USER and AUTH_UID:
    n_annotated = len([v for v in prefill_map.values() if v[0] in (REAL_OPTIONS | REAL_THEME_OPTIONS)])
    n_commented = len([v for v in prefill_map.values() if v[1].strip()])
    n_suggested = len([k for k, v in prefill_map.items() if k[1] == HUMAN_SUGGESTED_MESO and v[1].strip()])
    total_items = len(visible_themes_sorted) + sum(len(base) + len(extras) for base, extras in theme_narr_map.values())
    st.caption(
        f"**Your Progress:** {n_annotated} annotated, {n_commented} commented, {n_suggested} themes with suggestions (out of {total_items} total items) • "
        f"Revision {chosen_rev}: {n_tax_themes} themes, {n_tax_narr} base narratives, {n_new_narr_kept} new narratives (count≥{NEW_MIN_COUNT})"
    )
else:
    st.caption(
        f"Revision {chosen_rev}: {n_tax_themes} themes, {n_tax_narr} base narratives, {n_new_narr_kept} new narratives (count≥{NEW_MIN_COUNT})"
    )
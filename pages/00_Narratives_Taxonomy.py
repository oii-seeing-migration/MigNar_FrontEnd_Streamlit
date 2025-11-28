import os, re, importlib.util, urllib.parse, base64, json
import pandas as pd
import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="Meso Narratives Taxonomy",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")

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
    # Bind to GoTrue (auth)
    try:
        try:
            supabase.auth.set_session(at, rt)
        except TypeError:
            supabase.auth.set_session(access_token=at, refresh_token=rt)
    except Exception:
        pass
    # Bind to PostgREST (critical for RLS)
    try:
        supabase.postgrest.auth(at)
    except Exception:
        pass
    # Resolve auth uid (prefer API; fallback to JWT payload)
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

# Auth status (set by navigation_page.py after login)
USER = st.session_state.get("user")

# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.open-btn { display:inline-block; background:#1976d2; color:#fff !important; padding:4px 10px; border-radius:4px; text-decoration:none; font-size:0.75rem; margin:2px 0; }
.open-btn:hover { background:#0d47a1; }
.theme-box { padding:10px 12px; border-radius:10px; margin-top:14px; display:flex; align-items:center; justify-content:space-between; }
.theme-left { font-weight:600; }
.theme-right { font-size:0.9rem; opacity:0.8; }
.narr-row { padding:8px 10px; border-radius:8px; display:flex; align-items:center; gap:10px; }
.narr-text { flex:1; }
.narr-count { text-align:right; font-size:0.9rem; opacity:0.8; }
.login-banner { background:#e3f2fd; border:1px solid #90caf9; padding:8px 12px; border-radius:8px; margin-bottom:10px; }
.login-banner.logged { background:#e8f5e9; border-color:#81c784; }

/* Fix alignment - remove extra padding from streamlit columns */
div[data-testid="column"] { padding-left: 0 !important; padding-right: 0 !important; }
</style>
""", unsafe_allow_html=True)

DATA_DIR   = os.path.expanduser("./data")
MESO_PATH  = os.path.join(DATA_DIR, "meso_daily.parquet")
TAXON_DIR  = os.path.join(os.path.dirname(__file__), "../taxonomy")
NEW_MIN_COUNT = 3
ARTICLES_SLUG = "Narratives_on_Articles"

ANNOT_OPTIONS = ["", "duplicate narrative", "too specific", "too generic", "good"]
REAL_OPTIONS = set(ANNOT_OPTIONS[1:])
ANNOT_TABLE = "taxonomy_annotations"

# ── Data loaders ───────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=True)
def load_meso_df(fp: str) -> pd.DataFrame:
    if not os.path.exists(fp):
        return pd.DataFrame(columns=["day","model","version","source_domain","theme","meso_narrative","count"])
    df = pd.read_parquet(fp)
    if "day" in df.columns:
        df["day"] = pd.to_datetime(df["day"], errors="coerce").dt.date
    for c in ["source_domain","model","theme","meso_narrative"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
    if "version" in df.columns:
        df["version"] = pd.to_numeric(df["version"], errors="coerce").fillna(0).astype(int)
    return df

@st.cache_data(show_spinner=True)
def list_revisions() -> list[int]:
    if not os.path.isdir(TAXON_DIR):
        return []
    revs = []
    for fname in os.listdir(TAXON_DIR):
        m = re.fullmatch(r"meso_narratives_revision_(\d+)\.py", fname)
        if m:
            revs.append(int(m.group(1)))
    return sorted(set(revs))

@st.cache_data(show_spinner=True)
def load_taxonomy(revision: int) -> dict[str, list[str]]:
    path = os.path.join(TAXON_DIR, f"meso_narratives_revision_{revision}.py")
    if not os.path.exists(path):
        return {}
    spec = importlib.util.spec_from_file_location("meso_tax", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)  # type: ignore
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

@st.cache_data(show_spinner=False, ttl=10)
def fetch_user_annotations(user_id: str | None, revision: int) -> dict[tuple[str,str], str]:
    if not user_id:
        return {}
    try:
        res = supabase.table(ANNOT_TABLE).select("theme,meso,label").eq("user_id", user_id).eq("revision", revision).execute()
        items = res.data or []
        return {(i["theme"], i["meso"]): i["label"] for i in items if isinstance(i, dict)}
    except Exception:
        return {}

# ── DB write ───────────────────────────────────────────────────────────────────
def upsert_annotation(user: dict, revision: int, theme: str, meso: str, label: str) -> bool:
    try:
        uid = AUTH_UID or user.get("id")
        if not uid:
            st.error("No authenticated user ID available. Please sign in again.")
            return False
        payload = {
            "user_id": str(uid),          # must equal auth.uid()::text for RLS to pass
            "user_name": user.get("name"),
            "theme": theme,
            "meso": meso,
            "revision": revision,
            "label": label,
        }
        supabase.table(ANNOT_TABLE).upsert(payload, on_conflict="user_id,revision,theme,meso").execute()
        return True
    except Exception as e:
        st.error(f"Failed to save annotation: {e}")
        return False

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

srcs = sorted(meso_df.source_domain.unique()) if "source_domain" in meso_df.columns else []
models = sorted(meso_df.model.unique()) if "model" in meso_df.columns else []
source_choice = st.sidebar.selectbox("Source Domain", ["(All sources)"] + srcs, index=0)
model_choice = st.sidebar.selectbox("Model", ["(All models)"] + models, index=0)
source_filter = None if source_choice == "(All sources)" else source_choice
model_filter = None if model_choice == "(All models)" else model_choice

# ── Login banner ───────────────────────────────────────────────────────────────
if USER and AUTH_UID and BIND_OK:
    st.markdown(f"<div class='login-banner logged'>✅ Signed in as <strong>{USER.get('name') or USER.get('email')}</strong> — Annotations will be saved</div>", unsafe_allow_html=True)
elif USER:
    st.markdown("<div class='login-banner'>⚠️ Signed in, but database session not fully bound. Try refreshing the page if saves fail.</div>", unsafe_allow_html=True)
else:
    st.markdown("<div class='login-banner'>🔐 You are not signed in. <a href='/'>Sign in</a> to save your annotations.</div>", unsafe_allow_html=True)

# ── Filter and aggregate ───────────────────────────────────────────────────────
filtered = meso_df[meso_df.version == chosen_rev] if "version" in meso_df.columns else meso_df.copy()
if source_filter and "source_domain" in filtered.columns:
    filtered = filtered[filtered.source_domain == source_filter]
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

visible_themes_sorted = sorted(visible_themes, key=lambda t: theme_totals.get(t, 0), reverse=True)

st.title(f"Meso Narratives Taxonomy (Revision {chosen_rev})")
st.caption("Review narratives, annotate quality, and explore articles. Your annotations are saved automatically.")

prefill_map = fetch_user_annotations(AUTH_UID if AUTH_UID else (USER.get("id") if USER else None), chosen_rev)

def articles_link(theme: str | None = None, meso: str | None = None) -> str:
    params = []
    if theme: params.append("theme=" + urllib.parse.quote(theme))
    if meso: params.append("meso=" + urllib.parse.quote(meso))
    return f"/{ARTICLES_SLUG}" + (("?" + "&".join(params)) if params else "")

def link_button(theme: str, meso: str | None = None, label: str = "View on Articles"):
    st.markdown(f"<a class='open-btn' href='{articles_link(theme, meso)}' target='_blank' rel='noopener'>{label}</a>", unsafe_allow_html=True)

for theme in visible_themes_sorted:
    total = theme_totals.get(theme, 0)
    in_tax = theme in taxonomy_themes
    new_theme = not in_tax
    color = "#e3f2fd" if in_tax else "#fff3e0"
    base_list, extras = theme_narr_map.get(theme, ([], []))

    st.markdown(
        f"<div class='theme-box' style='background:{color};'>"
        f"<div class='theme-left'>Theme: {theme}</div>"
        f"<div class='theme-right'>Total: {total}{' • NEW theme' if new_theme else ''}</div>"
        "</div>", unsafe_allow_html=True
    )

    header = st.columns([0.18, 0.52, 0.15, 0.15])
    with header[0]: 
        link_button(theme, None, "View on Articles")
    with header[1]: 
        st.markdown("<small style='padding-left:10px;'><strong>Meso Narratives</strong></small>", unsafe_allow_html=True)
    with header[2]: 
        st.markdown("<small style='text-align:right; display:block;'><strong>Count</strong></small>", unsafe_allow_html=True)
    with header[3]: 
        st.markdown("<small style='text-align:center; display:block;'><strong>Quality</strong></small>", unsafe_allow_html=True)

    for mn in base_list + extras:
        cnt = counts.get((theme, mn), 0)
        is_new = (mn in extras) or new_theme or (mn not in base_list and not in_tax)
        row_bg = "#fafafa" if not is_new else "#fff8e1"

        pre = prefill_map.get((theme, mn))
        key_sel = f"annot::{chosen_rev}::{theme}::{mn}"

        row = st.columns([0.18, 0.52, 0.15, 0.15])
        with row[0]:
            link_button(theme, mn, "View on Articles")
        with row[1]:
            new_tag = " <em style='color:#c77;'>(NEW)</em>" if is_new else ""
            st.markdown(f"<div class='narr-row' style='background:{row_bg};'><span class='narr-text'>{mn}{new_tag}</span></div>", unsafe_allow_html=True)
        with row[2]:
            st.markdown(f"<div style='text-align:right; padding:8px 10px;'><span class='narr-count'>{cnt}</span></div>", unsafe_allow_html=True)
        with row[3]:
            if USER and AUTH_UID and BIND_OK:
                # Determine default index (0 = blank) or previously saved label
                idx = (ANNOT_OPTIONS.index(pre) if pre in ANNOT_OPTIONS else 0)
                choice = st.selectbox(
                    "quality",
                    ANNOT_OPTIONS,
                    index=idx,
                    key=key_sel,
                    label_visibility="collapsed",
                    format_func=lambda v: ("—" if v == "" else v),
                    help="Rate the quality of this narrative"
                )
                # Save only if a real option chosen and changed
                if choice in REAL_OPTIONS and choice != pre:
                    if upsert_annotation(USER, chosen_rev, theme, mn, choice):
                        st.toast("✓ Saved")
                        prefill_map[(theme, mn)] = choice
                        # Clear cache to show updated data
                        fetch_user_annotations.clear()
            else:
                st.selectbox(
                    "quality",
                    ANNOT_OPTIONS,
                    index=0,
                    key=key_sel,
                    label_visibility="collapsed",
                    format_func=lambda v: ("—" if v == "" else v),
                    disabled=True,
                    help="Sign in to annotate"
                )


st.markdown("---")
n_tax_themes = len(taxonomy)
n_tax_narr = sum(len(v) for v in taxonomy.values())
n_new_narr_kept = sum(len(extras) for _, (base, extras) in theme_narr_map.items() if extras)

# Show annotation stats if logged in
if USER and AUTH_UID:
    n_annotated = len([v for v in prefill_map.values() if v in REAL_OPTIONS])
    total_narratives = sum(len(base) + len(extras) for base, extras in theme_narr_map.values())
    st.caption(
        f"**Your Progress:** {n_annotated} / {total_narratives} narratives annotated • "
        f"Revision {chosen_rev}: {n_tax_themes} themes, {n_tax_narr} base narratives, {n_new_narr_kept} new narratives (count≥{NEW_MIN_COUNT})"
    )
else:
    st.caption(
        f"Revision {chosen_rev}: {n_tax_themes} themes, {n_tax_narr} base narratives, {n_new_narr_kept} new narratives (count≥{NEW_MIN_COUNT})"
    )
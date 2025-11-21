import os, re, importlib.util, urllib.parse
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Meso Narratives Taxonomy", layout="wide")

# Styling
st.markdown("""
<style>
.open-btn {
  display:inline-block;
  background:#1976d2;
  color:#fff !important;
  padding:4px 10px;
  border-radius:4px;
  text-decoration:none;
  font-size:0.75rem;
  margin:2px 0;
}
.open-btn:hover { background:#0d47a1; }
.theme-box { padding:6px 10px; border-radius:6px; margin-top:14px; }
.narr-row { padding:4px 6px; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

DATA_DIR   = os.path.expanduser("./data")
MESO_PATH  = os.path.join(DATA_DIR, "meso_daily.parquet")
TAXON_DIR  = os.path.join(os.path.dirname(__file__), "../taxonomy")
NEW_MIN_COUNT = 3          # threshold for showing NEW themes/narratives
ARTICLES_SLUG = "Narratives_on_Articles"  # page slug (observed in URL)

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

meso_df = load_meso_df(MESO_PATH)
revs = list_revisions()
if not revs:
    st.error("No taxonomy revision files found.")
    st.stop()

# Sidebar filters
st.sidebar.header("Controls")
chosen_rev = st.sidebar.selectbox("Revision Version", revs, index=len(revs)-1)
taxonomy = load_taxonomy(chosen_rev)

source_choice = st.sidebar.selectbox("Source Domain", ["(All sources)"] + sorted(meso_df.source_domain.unique()), index=0)
source_filter = None if source_choice == "(All sources)" else source_choice
model_choice = st.sidebar.selectbox("Model", ["(All models)"] + sorted(meso_df.model.unique()), index=0)
model_filter = None if model_choice == "(All models)" else model_choice

# Filter data
filtered = meso_df[meso_df.version == chosen_rev]
if source_filter:
    filtered = filtered[filtered.source_domain == source_filter]
if model_filter:
    filtered = filtered[filtered.model == model_filter]

# Aggregate counts
agg = filtered.groupby(["theme","meso_narrative"], as_index=False)["count"].sum()
counts = {(r.theme, r.meso_narrative): int(r.count) for r in agg.itertuples()}

taxonomy_themes = set(taxonomy.keys())

# Theme totals
theme_totals = {}
for (th, mn), c in counts.items():
    theme_totals[th] = theme_totals.get(th, 0) + c

# New narratives
raw_new_narrs = {}
for (th, mn), c in counts.items():
    if th not in taxonomy_themes or mn not in taxonomy.get(th, []):
        raw_new_narrs.setdefault(th, set()).add(mn)

# Visible themes logic
visible_themes = []
for th in set(theme_totals.keys()).union(taxonomy_themes):
    if th in taxonomy_themes:
        visible_themes.append(th)
    else:
        if theme_totals.get(th, 0) >= NEW_MIN_COUNT:
            visible_themes.append(th)

# Build narrative lists per theme
theme_narr_map = {}
for th in visible_themes:
    base = list(taxonomy.get(th, []))  # always show taxonomy narratives
    extras = []
    for mn in raw_new_narrs.get(th, set()):
        c = counts.get((th, mn), 0)
        if mn not in base and c >= NEW_MIN_COUNT:
            extras.append(mn)
    theme_narr_map[th] = (base, sorted(extras))

# Sort themes desc by total count
visible_themes_sorted = sorted(visible_themes, key=lambda t: theme_totals.get(t, 0), reverse=True)

st.title(f"Meso Narratives Taxonomy (Revision {chosen_rev})")
st.caption("Click links to open Articles view in a new tab with filters applied.")

# Deep link builder (uses page slug path)
def build_link(theme: str | None = None, meso: str | None = None) -> str:
    params = []
    if theme:
        params.append("theme=" + urllib.parse.quote(theme))
    if meso:
        params.append("meso=" + urllib.parse.quote(meso))
    if params:
        return f"/{ARTICLES_SLUG}?" + "&".join(params)
    return f"/{ARTICLES_SLUG}"

def link_button(theme: str, meso: str | None = None, label: str = "Open"):
    href = build_link(theme, meso)
    st.markdown(f"<a class='open-btn' href='{href}' target='_blank' rel='noopener'>{label}</a>", unsafe_allow_html=True)

# Render taxonomy
for theme in visible_themes_sorted:
    total = theme_totals.get(theme, 0)
    in_tax = theme in taxonomy_themes
    new_theme = not in_tax
    color = "#e3f2fd" if in_tax else "#fff3e0"
    base_list, extras = theme_narr_map.get(theme, ([], []))

    st.markdown(
        f"<div class='theme-box' style='background:{color};'>"
        f"<strong>Theme:</strong> {theme} "
        f"<span style='color:#555'>(total: {total})</span>"
        f"{' <em>(NEW)</em>' if new_theme else ''}"
        "</div>",
        unsafe_allow_html=True
    )

    header = st.columns([0.18, 0.57, 0.15, 0.10])
    with header[0]: link_button(theme, None, "Open Theme")
    with header[1]: st.markdown("<small><strong>Meso Narratives</strong></small>", unsafe_allow_html=True)
    with header[2]: st.markdown("<small><strong>Count</strong></small>", unsafe_allow_html=True)
    with header[3]: st.markdown("<small><strong>Action</strong></small>", unsafe_allow_html=True)

    for mn in base_list + extras:
        cnt = counts.get((theme, mn), 0)
        is_new = (mn in extras) or new_theme or (mn not in base_list and not in_tax)
        row_bg = "#fafafa" if not is_new else "#fff8e1"
        row = st.columns([0.18, 0.57, 0.15, 0.10])
        with row[0]: st.write("")
        with row[1]:
            new_tag = " <em style='color:#c77;'>(NEW)</em>" if is_new else ""
            st.markdown(
                f"<div class='narr-row' style='background:{row_bg};'>{mn}{new_tag}</div>",
                unsafe_allow_html=True
            )
        with row[2]:
            st.markdown(f"<span style='font-size:0.85rem'>{cnt}</span>", unsafe_allow_html=True)
        with row[3]:
            link_button(theme, mn, "Open")

st.markdown("---")
n_tax_themes = len(taxonomy)
n_tax_narr = sum(len(v) for v in taxonomy.values())
n_new_narr_kept = sum(len(extras) for th, (base, extras) in theme_narr_map.items() if th not in taxonomy_themes or extras)
st.caption(
    f"Revision {chosen_rev}: taxonomy themes={n_tax_themes}, taxonomy narratives={n_tax_narr}. "
    f"New narratives shown (count≥{NEW_MIN_COUNT})={n_new_narr_kept}."
)
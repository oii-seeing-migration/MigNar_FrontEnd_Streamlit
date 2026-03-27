import os, json, re, html as html_module
from collections import Counter
from urllib.parse import unquote
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher

st.set_page_config(
    page_title="Narratives on Articles",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png",
)

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

from lib.auth import get_auth_debug_state, require_auth

BIND_OK, AUTH_UID, USER, supabase = require_auth()

# ── Load taxonomy for suggestion dropdowns ────────────────────────────────
from taxonomy.meso_narratives_revision_2 import mesoNarratives as _TAXONOMY

TAXONOMY_THEMES = sorted(_TAXONOMY.keys())
TAXONOMY_MESO_BY_THEME: dict[str, list[str]] = {
    theme: [entry[0] for entry in entries if isinstance(entry, (list, tuple)) and len(entry) >= 1]
    for theme, entries in _TAXONOMY.items()
}
TAXONOMY_ALL_MESO = sorted({m for mesos in TAXONOMY_MESO_BY_THEME.values() for m in mesos})



# with st.expander("Auth Debug"):
#     st.json(get_auth_debug_state())

STANCE_VALIDATIONS_TABLE = "stance_validations"
NARRATIVE_VALIDATIONS_TABLE = "narrative_validations"


# ═══════════════════════════════════════════════════════════════════════════════
# Validation helpers
# ═══════════════════════════════════════════════════════════════════════════════
def fetch_user_stance_validation(user_id: str, source_table: str, article_id: str) -> dict | None:
    if not user_id:
        return None
    try:
        res = (
            supabase.table(STANCE_VALIDATIONS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("source_table", source_table)
            .eq("article_id", article_id)
            .execute()
        )
        items = res.data or []
        return items[0] if items else None
    except Exception:
        return None


def fetch_user_narrative_validations(
    user_id: str, source_table: str, article_id: str
) -> dict[tuple[str, str, str], dict]:
    if not user_id:
        return {}
    try:
        res = (
            supabase.table(NARRATIVE_VALIDATIONS_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("source_table", source_table)
            .eq("article_id", article_id)
            .execute()
        )
        items = res.data or []
        return {
            (i["model"], i["theme"], i["meso_narrative"]): i
            for i in items
            if isinstance(i, dict)
        }
    except Exception:
        return {}


def upsert_stance_validation(
    user: dict,
    source_table: str,
    article_id: str,
    article_title: str,
    article_body: str,
    llm_stances: dict,
    ensemble_stance: str,
    user_stance: str,
    user_comment: str = "",
) -> bool:
    uid = AUTH_UID or user.get("id")
    if not uid:
        return False
    try:
        payload = {
            "user_id": str(uid),
            "user_name": user.get("name") or user.get("email") or "Unknown",
            "source_table": source_table,
            "article_id": str(article_id),
            "article_title": article_title,
            "article_body": article_body or "",
            "llm_stances": json.dumps(llm_stances),
            "ensemble_stance": ensemble_stance,
            "user_stance": user_stance,
            "user_comment": user_comment or "",
        }
        supabase.table(STANCE_VALIDATIONS_TABLE).upsert(
            payload, on_conflict="user_id,source_table,article_id"
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error saving stance validation: {e}")
        return False


def upsert_narrative_validation(
    user: dict,
    source_table: str,
    article_id: str,
    article_title: str,
    article_body: str,
    model: str,
    theme: str,
    meso_narrative: str,
    text_fragment: str,
    score_theme: int | None,
    score_meso: int | None,
    user_comment: str = "",
    taxonomy_version: int | None = None,
) -> bool:
    uid = AUTH_UID or user.get("id")
    if not uid:
        return False
    try:
        payload = {
            "user_id": str(uid),
            "user_name": user.get("name") or user.get("email") or "Unknown",
            "source_table": source_table,
            "article_id": str(article_id),
            "article_title": article_title,
            "article_body": article_body or "",
            "model": model,
            "theme": theme,
            "meso_narrative": meso_narrative,
            "text_fragment": text_fragment or "",
            "score_theme": score_theme,
            "score_meso": score_meso,
            "user_comment": user_comment or "",
            "taxonomy_version": taxonomy_version,
        }
        supabase.table(NARRATIVE_VALIDATIONS_TABLE).upsert(
            payload,
            on_conflict="user_id,source_table,article_id,model,theme,meso_narrative",
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error saving narrative validation: {e}")
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════════════════════════
_qp = st.query_params


def _get_param(k):
    v = _qp.get(k)
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else None)


pre_theme = _get_param("theme")
pre_meso = _get_param("meso")
pre_source_table = _get_param("source_table")
pre_title = _get_param("title")

DATA_PATH = os.getenv("MESO_SAMPLES_PATH") or os.path.join(
    os.getenv("EXPORT_DIR") or "./data", "meso_samples.parquet"
)


def load_samples(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_parquet(path)
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].fillna("")
    for col in df.select_dtypes(include=["object"]).columns:
        if df[col].nunique() < len(df) * 0.5:
            df[col] = df[col].astype("category")
    return df


def safe_json_load(s: str | None):
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


df = load_samples(DATA_PATH)
if df.empty:
    st.error(f"No data found: {DATA_PATH}")
    st.stop()

# ── Taxonomy version filter ──────────────────────────────────────────────
if "version" in df.columns:
    df["version"] = pd.to_numeric(df["version"], errors="coerce")
    available_versions = sorted(df["version"].dropna().unique())
    if available_versions:
        latest_version = int(max(available_versions))
        version_options = [int(v) for v in available_versions]
        selected_version = st.sidebar.selectbox(
            "Taxonomy Version",
            options=version_options,
            index=version_options.index(latest_version),
            help="Filter articles by taxonomy/prompt version. Defaults to latest.",
        )
        df = df[df["version"] == selected_version].copy()
        if df.empty:
            st.error(f"No data found for taxonomy version {selected_version}.")
            st.stop()

THEME_COL = (
    "theme"
    if "theme" in df.columns
    else ("dominant_theme" if "dominant_theme" in df.columns else None)
)
MESO_SAMPLE_COL = (
    "meso"
    if "meso" in df.columns
    else ("meso_narrative" if "meso_narrative" in df.columns else None)
)

for c in [THEME_COL, MESO_SAMPLE_COL, "title", "body"]:
    if c and c in df.columns:
        df[c] = df[c].astype(str)


# ═══════════════════════════════════════════════════════════════════════════════
# Computed columns
# ═══════════════════════════════════════════════════════════════════════════════
def count_models_per_meso(row: pd.Series):
    meso_models: dict[str, set[str]] = {}
    for col in row.index:
        if isinstance(col, str) and col.startswith("annotation_parsed_"):
            model_name = col[len("annotation_parsed_"):]
            arr = safe_json_load(row[col])
            if isinstance(arr, list):
                for obj in arr:
                    if isinstance(obj, dict):
                        mn = obj.get("meso narrative")
                        if isinstance(mn, str) and mn.strip():
                            meso_models.setdefault(mn.strip(), set()).add(model_name)
    return meso_models


def gather_meso_set(row: pd.Series):
    return set(row["_meso_models_dict"].keys())


def extract_stance_per_model(row: pd.Series) -> dict[str, str]:
    stances: dict[str, str] = {}
    for col in row.index:
        if isinstance(col, str) and col.startswith("stance_"):
            model_name = col[len("stance_"):]
            stance_val = row[col]
            if isinstance(stance_val, str) and stance_val.strip():
                stances[model_name] = stance_val.strip().upper()
    return stances


def compute_ensemble_stance(stances: dict[str, str]) -> str:
    if not stances:
        return "UNKNOWN"
    counts = Counter(stances.values())
    c = {
        "OPEN": counts.get("OPEN", 0),
        "RESTRICTIVE": counts.get("RESTRICTIVE", 0),
        "NEUTRAL": counts.get("NEUTRAL", 0),
        "IRRELEVANT": counts.get("IRRELEVANT", 0),
    }
    mx = max(c.values())
    winners = [l for l, v in c.items() if v == mx]
    if len(winners) == 1:
        return winners[0]
    if "OPEN" in winners and "RESTRICTIVE" in winners:
        return "NEUTRAL"
    for label in ("IRRELEVANT", "NEUTRAL", "OPEN", "RESTRICTIVE"):
        if label in winners:
            return label
    return "UNKNOWN"


df["_stance_per_model"] = df.apply(extract_stance_per_model, axis=1)
df["_ensemble_stance"] = df["_stance_per_model"].apply(compute_ensemble_stance)
df["_meso_models_dict"] = df.apply(count_models_per_meso, axis=1)
df["_meso_all_set"] = df.apply(gather_meso_set, axis=1)


# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ═══════════════════════════════════════════════════════════════════════════════
st.sidebar.header("Filters")

if USER and AUTH_UID and BIND_OK:
    st.sidebar.success(
        f"✅ Signed in as **{USER.get('name') or USER.get('email')}**"
    )
elif USER:
    st.sidebar.warning("⚠️ Signed in, but DB session not bound. Refresh page.")
else:
    st.sidebar.warning("🔐 Not signed in. [Go to Sign In page](/) to validate.")

available_models = sorted(
    {
        col[len("annotation_parsed_"):]
        for col in df.columns
        if isinstance(col, str) and col.startswith("annotation_parsed_")
    }
)

min_agreement = st.sidebar.slider(
    "Min Models Agreement",
    min_value=1,
    max_value=max(len(available_models), 1),
    value=2,
    help="Minimum number of models that must agree on a meso narrative for it to appear in the dropdown",
)

source_options = ["(All)"] + (
    sorted(df["source_table"].unique()) if "source_table" in df.columns else []
)
pre_source_idx = (
    source_options.index(pre_source_table)
    if pre_source_table and pre_source_table in source_options
    else 0
)
src_choice = st.sidebar.selectbox("Source Table", source_options, index=pre_source_idx)
work_df = (
    df
    if src_choice == "(All)" or "source_table" not in df.columns
    else df[df["source_table"] == src_choice]
)

STANCE_OPTIONS = ["(All)", "OPEN", "RESTRICTIVE", "NEUTRAL", "IRRELEVANT"]
stance_filter = st.sidebar.selectbox(
    "Stance (Ensemble)",
    options=STANCE_OPTIONS,
    index=0,
    help="Filter articles by their ensemble stance.",
)
if stance_filter != "(All)":
    work_df = work_df[work_df["_ensemble_stance"] == stance_filter].copy()

if THEME_COL:
    theme_vals = sorted(
        t for t in work_df[THEME_COL].unique() if isinstance(t, str) and t.strip()
    )
    if pre_theme not in theme_vals:
        pre_theme = None
    theme_choice = st.sidebar.selectbox(
        "Theme",
        ["(All)"] + theme_vals,
        index=(theme_vals.index(pre_theme) + 1) if pre_theme else 0,
    )
    if theme_choice != "(All)":
        work_df = work_df[work_df[THEME_COL] == theme_choice].copy()
else:
    theme_choice = "(All)"


def filter_meso_by_agreement(meso_models_dict, min_agree):
    return {m for m, mdls in meso_models_dict.items() if len(mdls) >= min_agree}


work_df = work_df.copy()
work_df["_meso_filtered_set"] = work_df["_meso_models_dict"].apply(
    lambda d: filter_meso_by_agreement(d, min_agreement)
)

all_meso_values = sorted({m for s in work_df["_meso_filtered_set"] for m in s})
if pre_meso not in all_meso_values:
    pre_meso = None
meso_choice = st.sidebar.selectbox(
    f"Meso Narrative (≥{min_agreement} models)",
    ["(All)"] + all_meso_values,
    index=(all_meso_values.index(pre_meso) + 1) if pre_meso else 0,
)
if meso_choice != "(All)":
    work_df = work_df[work_df["_meso_filtered_set"].apply(lambda s: meso_choice in s)]
selected_meso = meso_choice if meso_choice != "(All)" else None


def sync_params(th, mn):
    want = {}
    if th != "(All)":
        want["theme"] = th
    if mn != "(All)":
        want["meso"] = mn
    changed = any(_qp.get(k) != want.get(k) for k in ("theme", "meso"))
    if changed:
        for k in ("theme", "meso"):
            if k in _qp:
                del _qp[k]
        for k, v in want.items():
            _qp[k] = v


sync_params(theme_choice, meso_choice)

if work_df.empty:
    st.warning("No rows match filters.")
    st.stop()

title_col = "title" if "title" in work_df.columns else None
if not title_col:
    st.error("Missing title column.")
    st.stop()

titles = work_df[title_col].tolist()
pre_title_idx = 0
if pre_title:
    decoded = unquote(pre_title)
    if decoded in titles:
        pre_title_idx = titles.index(decoded)
    else:
        prefix = decoded[:-3] if decoded.endswith("...") else decoded
        for idx, t in enumerate(titles):
            if t.startswith(prefix) or prefix.startswith(t.rstrip("...")):
                pre_title_idx = idx
                break

title_choice = st.sidebar.selectbox("Record", titles, index=pre_title_idx)
row = work_df[work_df[title_col] == title_choice].iloc[0]


# ═══════════════════════════════════════════════════════════════════════════════
# Article header
# ═══════════════════════════════════════════════════════════════════════════════
st.title(row[title_col])
if isinstance(row.get("url"), str) and row["url"]:
    st.markdown(f"[Open Source Link]({row['url']})")
st.caption(f"Source: {row.get('source_table', '')} | Date: {row.get('pub_date', '')}")

# Legend
_, legend_right = st.columns([0.7, 0.3])
with legend_right:
    st.markdown(
        """<div style="background:#f8f9fa;border:1px solid #dee2e6;border-radius:8px;
        padding:10px;font-size:0.85rem">
        <strong>🎨 Legend</strong><br>
        <span style="background:#80deea;padding:2px 6px;border-radius:3px">Blue</span> = Selected Narrative<br>
        <span style="background:#fff59d;padding:2px 6px;border-radius:3px">Yellow</span> = Other Narratives<br>
        👁️ = Click to reveal (spoiler)</div>""",
        unsafe_allow_html=True,
    )

body_text = row.get("body", "") or ""
source_table = row.get("source_table", "")
article_id = str(row.get("article_id", ""))
article_title = row.get("title", "")
ensemble_stance = row.get("_ensemble_stance", "UNKNOWN")

taxonomy_version = row.get("version", None)
if taxonomy_version is not None:
    try:
        taxonomy_version = int(taxonomy_version)
    except (ValueError, TypeError):
        taxonomy_version = None


# ═══════════════════════════════════════════════════════════════════════════════
# Annotation extraction & highlighting
# ═══════════════════════════════════════════════════════════════════════════════
def extract_all_model_narratives(r: pd.Series):
    out = []
    for col in r.index:
        if isinstance(col, str) and col.startswith("annotation_parsed_"):
            model_name = col[len("annotation_parsed_"):]
            ann_list = safe_json_load(r[col]) or []
            if not isinstance(ann_list, list):
                continue
            for o in ann_list:
                if not isinstance(o, dict):
                    continue
                frag = o.get("text fragment")
                th = o.get("narrative theme")
                mn = o.get("meso narrative")
                if isinstance(th, str) and th.strip() and isinstance(mn, str) and mn.strip():
                    out.append(
                        {
                            "fragment": frag.strip() if isinstance(frag, str) and frag.strip() else "",
                            "theme": th.strip(),
                            "meso": mn.strip(),
                            "model": model_name,
                            "has_fragment": bool(isinstance(frag, str) and frag.strip()),
                        }
                    )
    return out


all_ann_frag_objs = extract_all_model_narratives(row)


def normalize_text(t: str) -> str:
    t = t.strip()
    t = re.sub(r"['']", "'", t)
    t = re.sub(r'["\u201c\u201d]', '"', t)
    t = t.replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", t)


def normalize_fragment(f: str) -> str:
    f = normalize_text(f)
    f = re.sub(r"(?:\u2026|\.{3,})", "...", f)
    f = re.sub(r"(?:\.{3,}|\u2026)$", "", f).strip()
    return re.sub(r"\b(\d+)\s*(%|percent|per\s*cent)\b", "<<NUMPCT>>", f, flags=re.IGNORECASE)


def build_regex(nf: str):
    parts = [p for p in nf.split("...") if p]
    if not parts:
        return None
    esc = []
    for p in parts:
        ep = re.escape(normalize_text(p))
        ep = re.sub(r"\s+", r"[\\s,;:\–\—-]+", ep)
        ep = ep.replace(re.escape("<<NUMPCT>>"), r"(?:\d+\s*(?:%|percent|per\s*cent))")
        esc.append(ep)
    pattern = r".{0,280}?".join(esc)
    try:
        return re.compile(pattern, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    except re.error:
        return None


def direct_search(body: str, frag: str):
    i = body.find(frag)
    if i >= 0:
        return (i, i + len(frag))
    il = body.lower().find(frag.lower())
    if il >= 0:
        return (il, il + len(frag))
    return None


def fuzzy_search(body: str, nf: str):
    anchor = re.sub(r"^[^A-Za-z0-9]+", "", nf)[:8].lower()
    if not anchor:
        return None
    positions = [m.start() for m in re.finditer(re.escape(anchor), body.lower())]
    if not positions:
        return None
    target = re.sub(r"\s+", " ", nf.lower())
    best = None
    for pos in positions:
        window = body[pos : pos + int(len(nf) * 1.4)]
        window_norm = re.sub(r"\s+", " ", window.lower())
        ratio = SequenceMatcher(None, target, window_norm[: len(target)]).ratio()
        if not best or ratio > best[0]:
            best = (ratio, pos, pos + len(nf))
    if best and best[0] >= 0.80:
        return (best[1], best[2])
    return None


matches = []
for obj in all_ann_frag_objs:
    if not obj["has_fragment"]:
        continue
    frag = obj["fragment"]
    nf = normalize_fragment(frag)
    span = direct_search(body_text, frag) or direct_search(body_text, nf)
    if span is None:
        rgx = build_regex(nf)
        if rgx:
            m = rgx.search(body_text)
            if m:
                span = m.span()
    if span is None:
        span = fuzzy_search(body_text, nf)
    if span is None:
        continue
    matches.append((span[0], span[1], obj["theme"], obj["meso"], obj["model"]))


def merge_overlaps(raw_matches):
    events = []
    for s, e, th, mn, mdl in raw_matches:
        events.append((s, 1, th, mn, mdl))
        events.append((e, -1, th, mn, mdl))
    events.sort(key=lambda x: (x[0], -x[1]))
    active: dict[tuple, int] = {}
    segs = []
    last = None

    def keys():
        return {k for k, v in active.items() if v > 0}

    for pos, kind, th, mn, mdl in events:
        if last is not None and pos > last and keys():
            segs.append((last, pos, keys().copy()))
        key = (th, mn, mdl)
        if kind == 1:
            active[key] = active.get(key, 0) + 1
        else:
            if key in active:
                active[key] -= 1
                if active[key] <= 0:
                    active.pop(key, None)
        last = pos
    return segs


segments = merge_overlaps(matches)


def apply_highlights(txt: str, segs):
    if not segs:
        return txt
    segs.sort(key=lambda x: x[0])
    out = []
    last = 0
    for s, e, label_set in segs:
        out.append(txt[last:s])
        labels = []
        meso_hit = False
        for th, mn, mdl in sorted(label_set):
            labels.append(f"{mdl} — {th} — {mn}")
            if selected_meso and mn == selected_meso:
                meso_hit = True
        tip = " | ".join(labels)
        cls = "highlight-selected" if meso_hit else "highlight"
        out.append(f'<span class="{cls}" title="{tip}">{txt[s:e]}</span>')
        last = e
    out.append(txt[last:])
    return "".join(out)


# ═══════════════════════════════════════════════════════════════════════════════
# Styles
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    """<style>
.highlight{background:#fff59d;padding:2px 3px;border-radius:3px;cursor:help}
.highlight:hover{background:#ffeb3b}
.highlight-selected{background:#80deea;padding:2px 3px;border-radius:3px;cursor:help}
.highlight-selected:hover{background:#4dd0e1}
.login-banner{background:#e3f2fd;border:1px solid #90caf9;padding:8px 12px;border-radius:8px;margin-bottom:10px}
.login-banner.logged{background:#e8f5e9;border-color:#81c784}
.meso-selected-cell{background-color:#80deea!important;border-radius:4px;padding:2px 6px}
.stance-badge{padding:3px 10px;border-radius:4px;font-weight:600;font-size:.85rem;display:inline-block}
.stance-open{background-color:#c8e6c9;color:#2e7d32}
.stance-restrictive{background-color:#ffcdd2;color:#c62828}
.stance-neutral{background-color:#fff9c4;color:#f57f17}
.stance-irrelevant{background-color:#e0e0e0;color:#616161}
.stance-unknown{background-color:#f5f5f5;color:#9e9e9e}
/* ── compact column headers with subscript ── */
.col-hdr{font-weight:700;font-size:.85rem;line-height:1.15;white-space:nowrap}
.col-hdr sub{font-weight:400;font-size:.72rem;color:#666}
</style>""",
    unsafe_allow_html=True,
)

st.markdown(apply_highlights(body_text, segments), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Fetch existing validations
# ═══════════════════════════════════════════════════════════════════════════════
existing_stance_validation = None
existing_narrative_validations: dict[tuple[str, str, str], dict] = {}
if USER and AUTH_UID and BIND_OK:
    existing_stance_validation = fetch_user_stance_validation(AUTH_UID, source_table, article_id)
    existing_narrative_validations = fetch_user_narrative_validations(AUTH_UID, source_table, article_id)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION FORM
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

is_logged_in = bool(USER and AUTH_UID and BIND_OK)

if is_logged_in:
    st.markdown(
        f"<div class='login-banner logged'>✅ Signed in as "
        f"<strong>{USER.get('name') or USER.get('email')}</strong> "
        f"— Validate the LLM annotations below</div>",
        unsafe_allow_html=True,
    )
elif USER:
    st.markdown(
        "<div class='login-banner'>⚠️ Signed in, but database session not fully bound. "
        "Try refreshing the page.</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='login-banner'>🔐 <a href='/'>Sign in</a> to validate LLM annotations.</div>",
        unsafe_allow_html=True,
    )


def stance_to_badge_html(stance: str) -> str:
    cls_map = {
        "OPEN": "stance-open",
        "RESTRICTIVE": "stance-restrictive",
        "NEUTRAL": "stance-neutral",
        "IRRELEVANT": "stance-irrelevant",
        "UNKNOWN": "stance-unknown",
    }
    return f'<span class="stance-badge {cls_map.get(stance, "stance-unknown")}">{stance}</span>'


stance_per_model = row.get("_stance_per_model", {})

# Column ratios:  Model | Theme | Meso | Fragment | ScoreTheme | ScoreMeso | Comment
#                 0.10    0.13   0.14    0.22       0.12         0.12        0.15
COL_RATIOS = [0.10, 0.13, 0.14, 0.22, 0.12, 0.12, 0.15]

with st.form(key="validation_form", clear_on_submit=False):
    widget_values: dict[str, object] = {}

    # ── Narrative annotations ─────────────────────────────────────────────
    st.subheader("📝 Narrative Annotations")
    st.caption(
        "Rate each LLM narrative annotation from 0 (completely wrong) to 5 "
        "(perfectly correct). Leave blank to skip."
    )
    if is_logged_in:
        st.caption("💡 **Model names are hidden** to avoid bias.")

    if not all_ann_frag_objs:
        st.info("No narrative annotations found for this article.")
    else:
        # ── Header row ────────────────────────────────────────────────
        hdr = st.columns(COL_RATIOS)
        with hdr[0]:
            st.markdown('<span class="col-hdr">Model</span>', unsafe_allow_html=True)
        with hdr[1]:
            st.markdown('<span class="col-hdr">Theme</span>', unsafe_allow_html=True)
        with hdr[2]:
            st.markdown('<span class="col-hdr">Meso Narrative</span>', unsafe_allow_html=True)
        with hdr[3]:
            st.markdown('<span class="col-hdr">Fragment</span>', unsafe_allow_html=True)
        with hdr[4]:
            st.markdown(
                '<span class="col-hdr">Score<sub>theme</sub></span>',
                unsafe_allow_html=True,
            )
        with hdr[5]:
            st.markdown(
                '<span class="col-hdr">Score<sub>meso</sub></span>',
                unsafe_allow_html=True,
            )
        with hdr[6]:
            st.markdown('<span class="col-hdr">Comment</span>', unsafe_allow_html=True)

        st.markdown("<hr style='margin:5px 0'>", unsafe_allow_html=True)

        # ── Annotation rows ───────────────────────────────────────────
        for idx, obj in enumerate(all_ann_frag_objs):
            model = obj["model"]
            theme = obj["theme"]
            meso = obj["meso"]
            fragment = obj["fragment"] if obj["has_fragment"] else "[no fragment]"
            is_selected_meso = selected_meso and meso == selected_meso

            existing = existing_narrative_validations.get((model, theme, meso), {})
            ex_score_theme = existing.get("score_theme") if existing else None
            ex_score_meso = existing.get("score_meso") if existing else None
            ex_comment = existing.get("user_comment", "") if existing else ""

            cols = st.columns(COL_RATIOS)

            # Model
            with cols[0]:
                if is_logged_in:
                    with st.expander("👁️", expanded=False):
                        st.caption(model)
                else:
                    st.caption(model)

            # Theme
            with cols[1]:
                st.caption(theme)

            # Meso narrative
            with cols[2]:
                if is_selected_meso:
                    st.markdown(
                        f"<span class='meso-selected-cell'>{html_module.escape(meso)}</span>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(meso)

            # Fragment
            with cols[3]:
                display = fragment[:60] + "..." if len(fragment) > 60 else fragment
                st.caption(display)

            # Score (theme)
            score_opts = ["—", "0", "1", "2", "3", "4", "5"]
            with cols[4]:
                if is_logged_in:
                    def_idx = (
                        score_opts.index(str(ex_score_theme))
                        if ex_score_theme is not None and str(ex_score_theme) in score_opts
                        else 0
                    )
                    widget_values[f"score_theme::{idx}"] = st.selectbox(
                        "ScoreT",
                        options=score_opts,
                        index=def_idx,
                        key=f"score_theme_{source_table}_{article_id}_{idx}",
                        label_visibility="collapsed",
                    )
                else:
                    st.selectbox(
                        "ScoreT",
                        options=["—"],
                        disabled=True,
                        key=f"score_theme_dis_{idx}",
                        label_visibility="collapsed",
                    )

            # Score (meso)
            with cols[5]:
                if is_logged_in:
                    def_idx = (
                        score_opts.index(str(ex_score_meso))
                        if ex_score_meso is not None and str(ex_score_meso) in score_opts
                        else 0
                    )
                    widget_values[f"score_meso::{idx}"] = st.selectbox(
                        "ScoreM",
                        options=score_opts,
                        index=def_idx,
                        key=f"score_meso_{source_table}_{article_id}_{idx}",
                        label_visibility="collapsed",
                    )
                else:
                    st.selectbox(
                        "ScoreM",
                        options=["—"],
                        disabled=True,
                        key=f"score_meso_dis_{idx}",
                        label_visibility="collapsed",
                    )

            # Comment
            with cols[6]:
                if is_logged_in:
                    widget_values[f"narr_comment::{idx}"] = st.text_input(
                        "Comment",
                        value=ex_comment,
                        key=f"narr_comment_{source_table}_{article_id}_{idx}",
                        placeholder="Optional note…",
                        label_visibility="collapsed",
                    )
                else:
                    st.text_input(
                        "Comment",
                        placeholder="",
                        disabled=True,
                        key=f"narr_comment_dis_{idx}",
                        label_visibility="collapsed",
                    )

    st.markdown("---")

    # ── Suggest a missing narrative ───────────────────────────────────────
    st.subheader("➕ Suggest a Missing Narrative")

    # ── Part A: Pick from taxonomy (3 slots) ──────────────────────────────
    st.caption(
        "**From taxonomy:** Select a theme and meso narrative from the existing taxonomy. "
        "Optionally paste the supporting text fragment."
    )

    suggest_tax_ratios = [0.18, 0.26, 0.18, 0.08, 0.08, 0.13]
    thdr = st.columns(suggest_tax_ratios)
    with thdr[0]:
        st.markdown('<span class="col-hdr">Theme <sub>(taxonomy)</sub></span>', unsafe_allow_html=True)
    with thdr[1]:
        st.markdown('<span class="col-hdr">Meso Narrative <sub>(taxonomy)</sub></span>', unsafe_allow_html=True)
    with thdr[2]:
        st.markdown('<span class="col-hdr">Fragment</span>', unsafe_allow_html=True)
    with thdr[3]:
        st.markdown('<span class="col-hdr">Score<sub>theme</sub></span>', unsafe_allow_html=True)
    with thdr[4]:
        st.markdown('<span class="col-hdr">Score<sub>meso</sub></span>', unsafe_allow_html=True)
    with thdr[5]:
        st.markdown('<span class="col-hdr">Comment</span>', unsafe_allow_html=True)

    for ti in range(3):
        tc = st.columns(suggest_tax_ratios)
        with tc[0]:
            if is_logged_in:
                theme_opts = ["—"] + TAXONOMY_THEMES
                widget_values[f"sugtax_theme_{ti}"] = st.selectbox(
                    "Theme",
                    options=theme_opts,
                    key=f"sugtax_theme_{source_table}_{article_id}_{ti}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "Theme",
                    options=["Sign in"],
                    disabled=True,
                    key=f"sugtax_theme_dis_{ti}",
                    label_visibility="collapsed",
                )
        with tc[1]:
            if is_logged_in:
                chosen_tax_theme = widget_values.get(f"sugtax_theme_{ti}", "—")
                if chosen_tax_theme != "—" and chosen_tax_theme in TAXONOMY_MESO_BY_THEME:
                    meso_opts = ["—"] + TAXONOMY_MESO_BY_THEME[chosen_tax_theme]
                else:
                    meso_opts = ["—"] + TAXONOMY_ALL_MESO
                widget_values[f"sugtax_meso_{ti}"] = st.selectbox(
                    "Meso",
                    options=meso_opts,
                    key=f"sugtax_meso_{source_table}_{article_id}_{ti}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "Meso",
                    options=["Sign in"],
                    disabled=True,
                    key=f"sugtax_meso_dis_{ti}",
                    label_visibility="collapsed",
                )
        with tc[2]:
            if is_logged_in:
                widget_values[f"sugtax_frag_{ti}"] = st.text_input(
                    "Fragment",
                    placeholder="(optional)",
                    key=f"sugtax_frag_{source_table}_{article_id}_{ti}",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Fragment",
                    placeholder="",
                    disabled=True,
                    key=f"sugtax_frag_dis_{ti}",
                    label_visibility="collapsed",
                )
        with tc[3]:
            if is_logged_in:
                widget_values[f"sugtax_st_{ti}"] = st.selectbox(
                    "ST",
                    options=["—", "3", "4", "5"],
                    key=f"sugtax_st_{source_table}_{article_id}_{ti}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "ST",
                    options=["—"],
                    disabled=True,
                    key=f"sugtax_st_dis_{ti}",
                    label_visibility="collapsed",
                )
        with tc[4]:
            if is_logged_in:
                widget_values[f"sugtax_sm_{ti}"] = st.selectbox(
                    "SM",
                    options=["—", "3", "4", "5"],
                    key=f"sugtax_sm_{source_table}_{article_id}_{ti}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "SM",
                    options=["—"],
                    disabled=True,
                    key=f"sugtax_sm_dis_{ti}",
                    label_visibility="collapsed",
                )
        with tc[5]:
            if is_logged_in:
                widget_values[f"sugtax_comment_{ti}"] = st.text_input(
                    "Comment",
                    key=f"sugtax_comment_{source_table}_{article_id}_{ti}",
                    placeholder="Optional note…",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Comment",
                    placeholder="",
                    disabled=True,
                    key=f"sugtax_comment_dis_{ti}",
                    label_visibility="collapsed",
                )

    # ── Part B: Free-text suggestion (2 slots) ───────────────────────────
    st.caption(
        "**New narrative:** If the narrative is not in the taxonomy, type it below."
    )

    suggest_ratios = [0.16, 0.24, 0.18, 0.08, 0.08, 0.13]
    shdr = st.columns(suggest_ratios)
    with shdr[0]:
        st.markdown('<span class="col-hdr">Theme <sub>(free text)</sub></span>', unsafe_allow_html=True)
    with shdr[1]:
        st.markdown('<span class="col-hdr">Meso Narrative <sub>(free text)</sub></span>', unsafe_allow_html=True)
    with shdr[2]:
        st.markdown('<span class="col-hdr">Fragment</span>', unsafe_allow_html=True)
    with shdr[3]:
        st.markdown(
            '<span class="col-hdr">Score<sub>theme</sub></span>',
            unsafe_allow_html=True,
        )
    with shdr[4]:
        st.markdown(
            '<span class="col-hdr">Score<sub>meso</sub></span>',
            unsafe_allow_html=True,
        )
    with shdr[5]:
        st.markdown('<span class="col-hdr">Comment</span>', unsafe_allow_html=True)

    for si in range(2):
        sc = st.columns(suggest_ratios)
        with sc[0]:
            if is_logged_in:
                widget_values[f"sug_theme_{si}"] = st.text_input(
                    "Theme",
                    placeholder="e.g., Economic Impact",
                    key=f"sug_theme_{source_table}_{article_id}_{si}",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Theme",
                    placeholder="Sign in",
                    disabled=True,
                    key=f"sug_theme_dis_{si}",
                    label_visibility="collapsed",
                )
        with sc[1]:
            if is_logged_in:
                widget_values[f"sug_meso_{si}"] = st.text_input(
                    "Meso",
                    placeholder="e.g., Migrants contribute to tax revenue",
                    key=f"sug_meso_{source_table}_{article_id}_{si}",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Meso",
                    placeholder="Sign in",
                    disabled=True,
                    key=f"sug_meso_dis_{si}",
                    label_visibility="collapsed",
                )
        with sc[2]:
            if is_logged_in:
                widget_values[f"sug_frag_{si}"] = st.text_input(
                    "Fragment",
                    placeholder="(optional)",
                    key=f"sug_frag_{source_table}_{article_id}_{si}",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Fragment",
                    placeholder="",
                    disabled=True,
                    key=f"sug_frag_dis_{si}",
                    label_visibility="collapsed",
                )
        with sc[3]:
            if is_logged_in:
                widget_values[f"sug_st_{si}"] = st.selectbox(
                    "ST",
                    options=["—", "3", "4", "5"],
                    key=f"sug_st_{source_table}_{article_id}_{si}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "ST",
                    options=["—"],
                    disabled=True,
                    key=f"sug_st_dis_{si}",
                    label_visibility="collapsed",
                )
        with sc[4]:
            if is_logged_in:
                widget_values[f"sug_sm_{si}"] = st.selectbox(
                    "SM",
                    options=["—", "3", "4", "5"],
                    key=f"sug_sm_{source_table}_{article_id}_{si}",
                    label_visibility="collapsed",
                )
            else:
                st.selectbox(
                    "SM",
                    options=["—"],
                    disabled=True,
                    key=f"sug_sm_dis_{si}",
                    label_visibility="collapsed",
                )
        with sc[5]:
            if is_logged_in:
                widget_values[f"sug_comment_{si}"] = st.text_input(
                    "Comment",
                    key=f"sug_comment_{source_table}_{article_id}_{si}",
                    placeholder="Optional note…",
                    label_visibility="collapsed",
                )
            else:
                st.text_input(
                    "Comment",
                    placeholder="",
                    disabled=True,
                    key=f"sug_comment_dis_{si}",
                    label_visibility="collapsed",
                )

    st.markdown("---")


    # ── Stance validation ─────────────────────────────────────────────────
    st.subheader("🎯 Validate Stance")
    st.markdown("**Your stance assessment:**")
    # if is_logged_in:
    #     st.caption("💡 To avoid bias, label the stance *before* expanding the LLM predictions below.")

    st_cols = st.columns([0.4, 0.6])
    with st_cols[0]:
        if is_logged_in:
            ex_user_stance = (
                existing_stance_validation.get("user_stance", "")
                if existing_stance_validation
                else ""
            )
            stance_options = ["—", "OPEN", "RESTRICTIVE", "NEUTRAL", "IRRELEVANT"]
            def_st_idx = stance_options.index(ex_user_stance) if ex_user_stance in stance_options else 0
            widget_values["user_stance"] = st.selectbox(
                "Your Stance",
                options=stance_options,
                index=def_st_idx,
                key=f"user_stance_{source_table}_{article_id}",
                label_visibility="collapsed",
                help="What stance does this article express toward migration?",
            )
        else:
            st.selectbox(
                "Your Stance",
                options=["Sign in to validate"],
                disabled=True,
                label_visibility="collapsed",
            )
    with st_cols[1]:
        if is_logged_in:
            ex_st_comment = (
                existing_stance_validation.get("user_comment", "")
                if existing_stance_validation
                else ""
            )
            widget_values["stance_comment"] = st.text_input(
                "Comment (optional)",
                value=ex_st_comment,
                placeholder="Any notes about the stance…",
                key=f"stance_comment_{source_table}_{article_id}",
                label_visibility="collapsed",
            )
        else:
            st.text_input(
                "Comment",
                placeholder="",
                disabled=True,
                label_visibility="collapsed",
            )

    if stance_per_model:
        st.markdown("**LLM Stance Predictions:**")
        if is_logged_in:
            with st.expander("👁️ LLM stances (hidden to annotators)", expanded=False):
                for mn, st_val in sorted(stance_per_model.items()):
                    st.markdown(f"**{mn}:** {stance_to_badge_html(st_val)}", unsafe_allow_html=True)
                st.markdown(f"**🔷 Ensemble:** {stance_to_badge_html(ensemble_stance)}", unsafe_allow_html=True)
        else:
            for mn, st_val in sorted(stance_per_model.items()):
                st.markdown(f"**{mn}:** {stance_to_badge_html(st_val)}", unsafe_allow_html=True)
            st.markdown(f"**🔷 Ensemble:** {stance_to_badge_html(ensemble_stance)}", unsafe_allow_html=True)

    st.markdown("---")

    # ── Save button ───────────────────────────────────────────────────────
    save_left, save_right = st.columns([0.7, 0.3])
    with save_left:
        st.caption("💾 Click to save all your validations for this article" if is_logged_in else "🔐 Sign in to save validations")
    with save_right:
        save_clicked = st.form_submit_button(
            "💾 Save Validations",
            type="primary",
            use_container_width=True,
            disabled=not is_logged_in,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Process submission
# ═══════════════════════════════════════════════════════════════════════════════
if save_clicked and is_logged_in:
    ok = 0
    fail = 0

    # LLM narrative validations
    for idx, obj in enumerate(all_ann_frag_objs):
        st_val = widget_values.get(f"score_theme::{idx}", "—")
        sm_val = widget_values.get(f"score_meso::{idx}", "—")
        comment = widget_values.get(f"narr_comment::{idx}", "").strip()

        if st_val != "—" or sm_val != "—" or comment:
            s_theme = int(st_val) if st_val != "—" else None
            s_meso = int(sm_val) if sm_val != "—" else None
            if upsert_narrative_validation(
                user=USER,
                source_table=source_table,
                article_id=article_id,
                article_title=article_title,
                article_body=body_text,
                model=obj["model"],
                theme=obj["theme"],
                meso_narrative=obj["meso"],
                text_fragment=obj["fragment"] if obj["has_fragment"] else "",
                score_theme=s_theme,
                score_meso=s_meso,
                user_comment=comment,
                taxonomy_version=taxonomy_version,
            ):
                ok += 1
            else:
                fail += 1

    # Taxonomy-based suggested narratives (3 slots)
    for ti in range(3):
        tax_theme = widget_values.get(f"sugtax_theme_{ti}", "—")
        tax_meso = widget_values.get(f"sugtax_meso_{ti}", "—")
        tax_frag = widget_values.get(f"sugtax_frag_{ti}", "").strip()
        tax_st = widget_values.get(f"sugtax_st_{ti}", "—")
        tax_sm = widget_values.get(f"sugtax_sm_{ti}", "—")
        tax_comment = widget_values.get(f"sugtax_comment_{ti}", "").strip()

        if tax_theme != "—" and tax_meso != "—" and (tax_st != "—" or tax_sm != "—"):
            if upsert_narrative_validation(
                user=USER,
                source_table=source_table,
                article_id=article_id,
                article_title=article_title,
                article_body=body_text,
                model="human_suggested_taxonomy",
                theme=tax_theme,
                meso_narrative=tax_meso,
                text_fragment=tax_frag,
                score_theme=int(tax_st) if tax_st != "—" else None,
                score_meso=int(tax_sm) if tax_sm != "—" else None,
                user_comment=tax_comment,
                taxonomy_version=taxonomy_version,
            ):
                ok += 1
            else:
                fail += 1

    # Free-text suggested narratives (2 slots)
    for si in range(2):
        sug_theme = widget_values.get(f"sug_theme_{si}", "").strip()
        sug_meso = widget_values.get(f"sug_meso_{si}", "").strip()
        sug_frag = widget_values.get(f"sug_frag_{si}", "").strip()
        sug_st = widget_values.get(f"sug_st_{si}", "—")
        sug_sm = widget_values.get(f"sug_sm_{si}", "—")
        sug_comment = widget_values.get(f"sug_comment_{si}", "").strip()

        if sug_theme and sug_meso and (sug_st != "—" or sug_sm != "—"):
            if upsert_narrative_validation(
                user=USER,
                source_table=source_table,
                article_id=article_id,
                article_title=article_title,
                article_body=body_text,
                model="human_suggested",
                theme=sug_theme,
                meso_narrative=sug_meso,
                text_fragment=sug_frag,
                score_theme=int(sug_st) if sug_st != "—" else None,
                score_meso=int(sug_sm) if sug_sm != "—" else None,
                user_comment=sug_comment,
                taxonomy_version=taxonomy_version,
            ):
                ok += 1
            else:
                fail += 1

    # Stance validation
    user_stance = widget_values.get("user_stance", "—")
    stance_comment = widget_values.get("stance_comment", "")
    if user_stance != "—":
        if upsert_stance_validation(
            user=USER,
            source_table=source_table,
            article_id=article_id,
            article_title=article_title,
            article_body=body_text,
            llm_stances=stance_per_model,
            ensemble_stance=ensemble_stance,
            user_stance=user_stance,
            user_comment=stance_comment,
        ):
            ok += 1
        else:
            fail += 1

    if ok > 0 and fail == 0:
        st.success(f"✅ Saved {ok} validation(s) successfully!")
        st.session_state["validations_saved_notice"] = ok
        st.rerun()
    elif ok > 0:
        st.warning(f"⚠️ Saved {ok}, failed {fail}")
    elif fail > 0:
        st.error(f"❌ Failed to save {fail} validation(s)")
    else:
        st.info("No validations to save. Select a score or stance to validate.")

# ═══════════════════════════════════════════════════════════════════════════════
# Footer
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

saved_notice_count = st.session_state.pop("validations_saved_notice", None)
if saved_notice_count:
    st.caption(f"✅ Your validations were saved after clicking the save button ({saved_notice_count} item(s)).")


st.caption(f"Article ID: {article_id} | Source: {source_table}")
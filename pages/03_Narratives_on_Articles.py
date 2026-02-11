import os, json, re, html as html_module
from collections import Counter
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher


st.set_page_config(page_title="Narratives on Articles",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

from lib.auth import get_auth_debug_state, require_auth

# At the top of the page (after st.set_page_config)
BIND_OK, AUTH_UID, USER, supabase = require_auth()

with st.expander("Auth Debug"):
    st.json(get_auth_debug_state())
    
STANCE_VALIDATIONS_TABLE = "stance_validations"
NARRATIVE_VALIDATIONS_TABLE = "narrative_validations"


# ── Validation DB functions ────────────────────────────────────────────────────
def fetch_user_stance_validation(user_id: str, source_table: str, article_id: str) -> dict | None:
    if not user_id:
        return None
    try:
        res = supabase.table(STANCE_VALIDATIONS_TABLE).select("*").eq("user_id", user_id).eq("source_table", source_table).eq("article_id", article_id).execute()
        items = res.data or []
        return items[0] if items else None
    except Exception:
        return None

def fetch_user_narrative_validations(user_id: str, source_table: str, article_id: str) -> dict[tuple[str, str, str], dict]:
    if not user_id:
        return {}
    try:
        res = supabase.table(NARRATIVE_VALIDATIONS_TABLE).select("*").eq("user_id", user_id).eq("source_table", source_table).eq("article_id", article_id).execute()
        items = res.data or []
        return {(i["model"], i["theme"], i["meso_narrative"]): i for i in items if isinstance(i, dict)}
    except Exception:
        return {}

def upsert_stance_validation(user: dict, source_table: str, article_id: str, article_title: str, 
                              article_body: str, llm_stances: dict, ensemble_stance: str, 
                              user_stance: str, user_comment: str = "") -> bool:
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
        supabase.table(STANCE_VALIDATIONS_TABLE).upsert(payload, on_conflict="user_id,source_table,article_id").execute()
        return True
    except Exception as e:
        st.error(f"Error saving stance validation: {e}")
        return False

def upsert_narrative_validation(user: dict, source_table: str, article_id: str, article_title: str,
                                 article_body: str, model: str, theme: str, meso_narrative: str, 
                                 text_fragment: str, score: int | None, user_comment: str = "") -> bool:
    uid = AUTH_UID or user.get("id")
    if not uid:
        return False
    try:
        if score is None:
            is_correct = None
        elif score <= 2:
            is_correct = False
        else:
            is_correct = True
            
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
            "is_correct": is_correct,
            "user_comment": f"Score: {score}/5. {user_comment}" if score is not None else user_comment,
        }
        supabase.table(NARRATIVE_VALIDATIONS_TABLE).upsert(payload, on_conflict="user_id,source_table,article_id,model,theme,meso_narrative").execute()
        return True
    except Exception as e:
        st.error(f"Error saving narrative validation: {e}")
        return False

# ── Data loading ───────────────────────────────────────────────────────────────
_qp = st.query_params
def _get_param(k):
    v = _qp.get(k)
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else None)

pre_theme = _get_param("theme")
pre_meso  = _get_param("meso")
pre_source_table = _get_param("source_table")
pre_title = _get_param("title")

DATA_PATH = os.getenv("MESO_SAMPLES_PATH") or os.path.join(os.getenv("EXPORT_DIR") or "./data", "meso_samples.parquet")

def load_samples(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    df = pd.read_parquet(path)
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].fillna("")
    for col in df.select_dtypes(include=['object']).columns:
        if df[col].nunique() < len(df) * 0.5:
            df[col] = df[col].astype('category')
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

THEME_COL = "theme" if "theme" in df.columns else ("dominant_theme" if "dominant_theme" in df.columns else None)
MESO_SAMPLE_COL = "meso" if "meso" in df.columns else ("meso_narrative" if "meso_narrative" in df.columns else None)

for c in [THEME_COL, MESO_SAMPLE_COL, "title", "body"]:
    if c and c in df.columns:
        df[c] = df[c].astype(str)

def count_models_per_meso(row: pd.Series):
    meso_models = {}
    for col in row.index:
        if isinstance(col, str) and col.startswith("annotation_parsed_"):
            model_name = col[len("annotation_parsed_"):]
            arr = safe_json_load(row[col])
            if isinstance(arr, list):
                for obj in arr:
                    if isinstance(obj, dict):
                        mn = obj.get("meso narrative")
                        if isinstance(mn, str) and mn.strip():
                            mn_key = mn.strip()
                            if mn_key not in meso_models:
                                meso_models[mn_key] = set()
                            meso_models[mn_key].add(model_name)
    return meso_models

def gather_meso_set(row: pd.Series):
    return set(row["_meso_models_dict"].keys())

def extract_stance_per_model(row: pd.Series) -> dict[str, str]:
    stances = {}
    for col in row.index:
        if isinstance(col, str) and col.startswith("stance_"):
            model_name = col[len("stance_"):]
            stance_val = row[col]
            if isinstance(stance_val, str) and stance_val.strip():
                stances[model_name] = stance_val.strip().upper()
    return stances

def compute_ensemble_stance(stances: dict[str, str]) -> str:
    """
    Compute ensemble stance from individual model stances.
    
    Algorithm:
    1. Plurality rule: If a single label has the highest count, assign that label.
    2. Tiebreaking: When multiple labels share the maximum count:
       - If both OPEN and RESTRICTIVE are tied leaders (both > 0), assign NEUTRAL
       - Otherwise, apply priority ordering: IRRELEVANT > NEUTRAL > OPEN > RESTRICTIVE
    
    Args:
        stances: Dict mapping model_name -> stance label (OPEN/RESTRICTIVE/NEUTRAL/IRRELEVANT)
    
    Returns:
        Ensemble stance label
    """
    if not stances:
        return "UNKNOWN"
    
    # Count votes for each stance label
    stance_counts = Counter(stances.values())
    c_open = stance_counts.get("OPEN", 0)
    c_restrictive = stance_counts.get("RESTRICTIVE", 0)
    c_neutral = stance_counts.get("NEUTRAL", 0)
    c_irrelevant = stance_counts.get("IRRELEVANT", 0)
    
    counts = {
        "OPEN": c_open,
        "RESTRICTIVE": c_restrictive,
        "NEUTRAL": c_neutral,
        "IRRELEVANT": c_irrelevant,
    }
    
    # Find maximum count
    max_count = max(counts.values())
    
    # Find all labels with maximum count (winners)
    winners = [label for label, count in counts.items() if count == max_count]
    
    # Plurality rule: single winner
    if len(winners) == 1:
        return winners[0]
    
    # Tiebreaking
    # If both OPEN and RESTRICTIVE are among tied leaders with count > 0, assign NEUTRAL
    if "OPEN" in winners and "RESTRICTIVE" in winners and c_open > 0 and c_restrictive > 0:
        return "NEUTRAL"
    
    # Otherwise, apply priority ordering: IRRELEVANT > NEUTRAL > OPEN > RESTRICTIVE
    priority_order = ["IRRELEVANT", "NEUTRAL", "OPEN", "RESTRICTIVE"]
    for label in priority_order:
        if label in winners:
            return label
    
    # Fallback (should not reach here)
    return "UNKNOWN"

df["_stance_per_model"] = df.apply(extract_stance_per_model, axis=1)
df["_ensemble_stance"] = df["_stance_per_model"].apply(compute_ensemble_stance)
df["_meso_models_dict"] = df.apply(count_models_per_meso, axis=1)
df["_meso_all_set"] = df.apply(gather_meso_set, axis=1)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

if USER and AUTH_UID and BIND_OK:
    st.sidebar.success(f"✅ Signed in as **{USER.get('name') or USER.get('email')}**")
elif USER:
    st.sidebar.warning("⚠️ Signed in, but DB session not bound. Refresh page.")
else:
    st.sidebar.warning("🔐 Not signed in. [Go to Sign In page](/) to validate.")

available_models = []
for col in df.columns:
    if isinstance(col, str) and col.startswith("annotation_parsed_"):
        model_name = col[len("annotation_parsed_"):]
        available_models.append(model_name)
available_models = sorted(set(available_models))

min_agreement = st.sidebar.slider("Min Models Agreement", min_value=1, max_value=len(available_models) if available_models else 1, value=2, help="Minimum number of models that must agree on a meso narrative for it to appear in the dropdown")


source_options = ["(All)"] + (sorted(df["source_table"].unique()) if "source_table" in df.columns else [])
pre_source_idx = 0
if pre_source_table and pre_source_table in source_options:
    pre_source_idx = source_options.index(pre_source_table)
src_choice = st.sidebar.selectbox("Source Table", source_options, index=pre_source_idx)
work_df = df if src_choice == "(All)" or "source_table" not in df.columns else df[df["source_table"] == src_choice]

STANCE_OPTIONS = ["(All)", "OPEN", "RESTRICTIVE", "NEUTRAL", "IRRELEVANT"]
stance_filter = st.sidebar.selectbox("Stance (Ensemble)", options=STANCE_OPTIONS, index=0, help="Filter articles by their ensemble stance.")

if stance_filter != "(All)":
    work_df = work_df[work_df["_ensemble_stance"] == stance_filter].copy()

if THEME_COL:
    theme_vals = sorted(t for t in work_df[THEME_COL].unique() if isinstance(t, str) and t.strip())
    if pre_theme not in theme_vals:
        pre_theme = None
    theme_choice = st.sidebar.selectbox("Theme", ["(All)"] + theme_vals, index=(theme_vals.index(pre_theme) + 1) if pre_theme else 0)
    if theme_choice != "(All)":
        work_df = work_df[work_df[THEME_COL] == theme_choice].copy()
else:
    theme_choice = "(All)"

def filter_meso_by_agreement(meso_models_dict, min_agree):
    return {meso for meso, models in meso_models_dict.items() if len(models) >= min_agree}

work_df = work_df.copy()
work_df["_meso_filtered_set"] = work_df["_meso_models_dict"].apply(lambda d: filter_meso_by_agreement(d, min_agreement))

all_meso_values = sorted({m for s in work_df["_meso_filtered_set"] for m in s})
if pre_meso not in all_meso_values:
    pre_meso = None
meso_choice = st.sidebar.selectbox("Meso Narrative (≥{} models)".format(min_agreement), ["(All)"] + all_meso_values, index=(all_meso_values.index(pre_meso) + 1) if pre_meso else 0)
if meso_choice != "(All)":
    work_df = work_df[work_df["_meso_filtered_set"].apply(lambda s: meso_choice in s)]
selected_meso = meso_choice if meso_choice != "(All)" else None

def sync_params(th, mn):
    want = {}
    if th != "(All)":
        want["theme"] = th
    if mn != "(All)":
        want["meso"] = mn
    changed = False
    for k in ("theme", "meso"):
        cur = _qp.get(k)
        new = want.get(k)
        if cur != new:
            changed = True
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
    from urllib.parse import unquote
    pre_title_decoded = unquote(pre_title)
    
    # First try exact match
    if pre_title_decoded in titles:
        pre_title_idx = titles.index(pre_title_decoded)
    else:
        # Try prefix match (for truncated titles ending with "...")
        if pre_title_decoded.endswith("..."):
            prefix = pre_title_decoded[:-3]  # Remove the "..."
            for idx, t in enumerate(titles):
                if t.startswith(prefix):
                    pre_title_idx = idx
                    break
        else:
            # Try if any title starts with the decoded value
            for idx, t in enumerate(titles):
                if t.startswith(pre_title_decoded) or pre_title_decoded.startswith(t.rstrip("...")):
                    pre_title_idx = idx
                    break
title_choice = st.sidebar.selectbox("Record", titles, index=pre_title_idx)
row = work_df[work_df[title_col] == title_choice].iloc[0]

# ── Main content ───────────────────────────────────────────────────────────────
st.title(row[title_col])
if isinstance(row.get("url"), str) and row["url"]:
    st.markdown(f"[Open Source Link]({row['url']})")

st.caption(f"Source: {row.get('source_table','')} | Date: {row.get('pub_date','')}")

# ── Legend ─────────────────────────────────────────────────────────────────────
legend_col1, legend_col2 = st.columns([0.7, 0.3])
with legend_col2:
    st.markdown("""<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 10px; font-size: 0.85rem;"><strong>🎨 Legend</strong><br><span style="background: #80deea; padding: 2px 6px; border-radius: 3px;">Blue</span> = Selected Narrative<br><span style="background: #fff59d; padding: 2px 6px; border-radius: 3px;">Yellow</span> = Other Narratives<br>👁️ = Click to reveal (spoiler)</div>""", unsafe_allow_html=True)

body_text = row.get("body", "") or ""
source_table = row.get("source_table", "")
article_id = str(row.get("article_id", ""))
article_title = row.get("title", "")
ensemble_stance = row.get("_ensemble_stance", "UNKNOWN")


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
                    out.append({
                        "fragment": (frag.strip() if isinstance(frag, str) and frag.strip() else ""),
                        "theme": th.strip(),
                        "meso": mn.strip(),
                        "model": model_name,
                        "has_fragment": bool(isinstance(frag, str) and frag.strip())
                    })
    return out

all_ann_frag_objs = extract_all_model_narratives(row)

def normalize_text(t: str) -> str:
    t = t.strip()
    t = re.sub(r"['']", "'", t)
    t = re.sub(r'[""]', '"', t)
    t = t.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", t)

def normalize_fragment(f: str) -> str:
    f = normalize_text(f)
    f = re.sub(r"(?:…|\.{3,})", "...", f)
    f = re.sub(r"(?:\.{3,}|…)$", "", f).strip()
    return re.sub(r"\b(\d+)\s*(%|percent|per\s*cent)\b", "<<NUMPCT>>", f, flags=re.IGNORECASE)

def build_regex(nf: str):
    parts = [p for p in nf.split("...") if p]
    if not parts:
        return None
    esc = []
    for p in parts:
        ep = re.escape(normalize_text(p))
        ep = re.sub(r"\s+", r"[\\s,;:–—-]+", ep)
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
        window = body[pos:pos + int(len(nf) * 1.4)]
        window_norm = re.sub(r"\s+", " ", window.lower())
        ratio = SequenceMatcher(None, target, window_norm[:len(target)]).ratio()
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
    s, e = span
    matches.append((s, e, obj["theme"], obj["meso"], obj["model"]))

def merge_overlaps(matches):
    events = []
    for s, e, th, mn, mdl in matches:
        events.append((s, 1, th, mn, mdl))
        events.append((e, -1, th, mn, mdl))
    events.sort(key=lambda x: (x[0], -x[1]))
    active = {}
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
        for th, mn, mdl in sorted(label_set, key=lambda x: (str(x[2] or ""), str(x[0] or ""), str(x[1] or ""))):
            labels.append(f"{mdl} — {th} — {mn}")
            if selected_meso and mn == selected_meso:
                meso_hit = True
        tip = " | ".join(labels)
        cls = "highlight-selected" if meso_hit else "highlight"
        out.append(f'<span class="{cls}" title="{tip}">{txt[s:e]}</span>')
        last = e
    out.append(txt[last:])
    return "".join(out)

# ── Styles ─────────────────────────────────────────────────────────────────────
st.markdown("""<style>
.highlight { background:#fff59d; padding:2px 3px; border-radius:3px; cursor:help; }
.highlight:hover { background:#ffeb3b; }
.highlight-selected { background:#80deea; padding:2px 3px; border-radius:3px; cursor:help; }
.highlight-selected:hover { background:#4dd0e1; }
.login-banner { background:#e3f2fd; border:1px solid #90caf9; padding:8px 12px; border-radius:8px; margin-bottom:10px; }
.login-banner.logged { background:#e8f5e9; border-color:#81c784; }
.meso-selected-cell { background-color: #80deea !important; border-radius: 4px; padding: 2px 6px; }
.stance-badge { padding: 3px 10px; border-radius: 4px; font-weight: 600; font-size: 0.85rem; display: inline-block; }
.stance-open { background-color: #c8e6c9; color: #2e7d32; }
.stance-restrictive { background-color: #ffcdd2; color: #c62828; }
.stance-neutral { background-color: #fff9c4; color: #f57f17; }
.stance-irrelevant { background-color: #e0e0e0; color: #616161; }
.stance-unknown { background-color: #f5f5f5; color: #9e9e9e; }
.val-table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.9rem; }
.val-table th { text-align: left; padding: 8px 12px; background: #f1f5f9; border-bottom: 2px solid #e2e8f0; font-weight: 600; color: #475569; }
.val-table td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: middle; }
.val-table tr:hover { background: #f8fafc; }
.val-table tr.ensemble-row { background: #f1f5f9; font-weight: 600; }
.val-table tr.ensemble-row td { border-top: 2px solid #cbd5e1; }
</style>""", unsafe_allow_html=True)

st.markdown(apply_highlights(body_text, segments), unsafe_allow_html=True)

# ── Fetch existing validations ─────────────────────────────────────────────────
existing_stance_validation = None
existing_narrative_validations = {}
if USER and AUTH_UID and BIND_OK:
    existing_stance_validation = fetch_user_stance_validation(AUTH_UID, source_table, article_id)
    existing_narrative_validations = fetch_user_narrative_validations(AUTH_UID, source_table, article_id)

# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION FORM
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

if USER and AUTH_UID and BIND_OK:
    st.markdown(f"<div class='login-banner logged'>✅ Signed in as <strong>{USER.get('name') or USER.get('email')}</strong> — Validate the LLM annotations below</div>", unsafe_allow_html=True)
elif USER:
    st.markdown("<div class='login-banner'>⚠️ Signed in, but database session not fully bound. Try refreshing the page.</div>", unsafe_allow_html=True)

else:
    st.markdown("<div class='login-banner'>🔐 <a href='/'>Sign in</a> to validate LLM annotations.</div>", unsafe_allow_html=True)

def stance_to_badge_html(stance: str) -> str:
    cls_map = {"OPEN": "stance-open", "RESTRICTIVE": "stance-restrictive", "NEUTRAL": "stance-neutral", "IRRELEVANT": "stance-irrelevant", "UNKNOWN": "stance-unknown"}
    cls = cls_map.get(stance, "stance-unknown")
    return f'<span class="stance-badge {cls}">{stance}</span>'

is_logged_in = USER and AUTH_UID and BIND_OK
stance_per_model = row.get("_stance_per_model", {})

with st.form(key="validation_form", clear_on_submit=False):
    widget_values = {}
    
    # ── Narratives Validation Section ──────────────────────────────────────────
    st.subheader("📝 Narrative Annotations")
    st.caption("Rate each LLM narrative annotation from 0 (completely wrong) to 5 (perfectly correct). Leave blank to skip.")
    if is_logged_in:
        st.caption("💡 **Model names are hidden** to avoid bias. Use the expander to reveal after scoring.")
    
    if not all_ann_frag_objs:
        st.info("No narrative annotations found for this article.")
    else:
        # Column headers
        header_cols = st.columns([0.10, 0.15, 0.30, 0.30, 0.15])
        with header_cols[0]:
            st.markdown("**Model**")
        with header_cols[1]:
            st.markdown("**Theme**")
        with header_cols[2]:
            st.markdown("**Meso Narrative**")
        with header_cols[3]:
            st.markdown("**Fragment**")
        with header_cols[4]:
            st.markdown("**Score**")
        
        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
        
        # Create the validation table with score column
        for idx, obj in enumerate(all_ann_frag_objs):
            model = obj["model"]
            theme = obj["theme"]
            meso = obj["meso"]
            fragment = obj["fragment"] if obj["has_fragment"] else "[no fragment]"
            is_selected_meso = selected_meso and meso == selected_meso
            
            # Check for existing validation
            existing = existing_narrative_validations.get((model, theme, meso), {})
            existing_comment = existing.get("user_comment", "") if existing else ""
            existing_score = None
            if existing_comment and existing_comment.startswith("Score: "):
                try:
                    existing_score = int(existing_comment.split("/")[0].replace("Score: ", ""))
                except:
                    pass
            
            # Create columns for each row: Model | Theme | Meso | Fragment | Score
            cols = st.columns([0.10, 0.15, 0.30, 0.30, 0.15])
            
            with cols[0]:
                if is_logged_in:
                    # Use expander for spoiler effect - just eye icon
                    with st.expander("👁️", expanded=False):
                        st.caption(model)
                else:
                    st.caption(model)
            
            with cols[1]:
                st.caption(theme)
            
            with cols[2]:
                if is_selected_meso:
                    st.markdown(f"<span class='meso-selected-cell'>{html_module.escape(meso)}</span>", unsafe_allow_html=True)
                else:
                    st.caption(meso)
            
            with cols[3]:
                frag_display = fragment[:60] + "..." if len(fragment) > 60 else fragment
                st.caption(frag_display)
            
            with cols[4]:
                if is_logged_in:
                    score_options = ["—", "0", "1", "2", "3", "4", "5"]
                    default_idx = score_options.index(str(existing_score)) if existing_score is not None else 0
                    widget_values[f"narr_score::{idx}"] = st.selectbox(
                        f"Score",
                        options=score_options,
                        index=default_idx,
                        key=f"narr_score_{source_table}_{article_id}_{idx}",
                        label_visibility="collapsed"
                    )
                else:
                    st.selectbox("Score", options=["—"], disabled=True, key=f"narr_score_disabled_{idx}", label_visibility="collapsed")
    
    st.markdown("---")
    
    # ── Suggest New Narrative Section ──────────────────────────────────────────
    st.subheader("➕ Suggest a Missing Narrative")
    st.caption("If you think the LLMs missed a narrative in this article, suggest it here.")
    
    # Column headers for suggestions
    suggest_header_cols = st.columns([0.25, 0.35, 0.25, 0.15])
    with suggest_header_cols[0]:
        st.markdown("**Theme**")
    with suggest_header_cols[1]:
        st.markdown("**Meso Narrative**")
    with suggest_header_cols[2]:
        st.markdown("**Text Fragment**")
    with suggest_header_cols[3]:
        st.markdown("**Confidence**")
    
    # 3 rows for suggestions
    for suggest_idx in range(3):
        suggest_cols = st.columns([0.25, 0.35, 0.25, 0.15])
        with suggest_cols[0]:
            if is_logged_in:
                widget_values[f"suggest_theme_{suggest_idx}"] = st.text_input(
                    "Theme", 
                    placeholder="e.g., Economic Impact", 
                    key=f"suggest_theme_{source_table}_{article_id}_{suggest_idx}", 
                    label_visibility="collapsed"
                )
            else:
                st.text_input("Theme", placeholder="Sign in to suggest", disabled=True, key=f"suggest_theme_disabled_{suggest_idx}", label_visibility="collapsed")
        with suggest_cols[1]:
            if is_logged_in:
                widget_values[f"suggest_meso_{suggest_idx}"] = st.text_input(
                    "Meso Narrative", 
                    placeholder="e.g., Migrants contribute to tax revenue", 
                    key=f"suggest_meso_{source_table}_{article_id}_{suggest_idx}", 
                    label_visibility="collapsed"
                )
            else:
                st.text_input("Meso", placeholder="Sign in to suggest", disabled=True, key=f"suggest_meso_disabled_{suggest_idx}", label_visibility="collapsed")
        with suggest_cols[2]:
            if is_logged_in:
                widget_values[f"suggest_fragment_{suggest_idx}"] = st.text_input(
                    "Text Fragment", 
                    placeholder="(optional)", 
                    key=f"suggest_frag_{source_table}_{article_id}_{suggest_idx}", 
                    label_visibility="collapsed"
                )
            else:
                st.text_input("Fragment", placeholder="", disabled=True, key=f"suggest_frag_disabled_{suggest_idx}", label_visibility="collapsed")
        with suggest_cols[3]:
            if is_logged_in:
                widget_values[f"suggest_score_{suggest_idx}"] = st.selectbox(
                    "Confidence", 
                    options=["—", "3", "4", "5"], 
                    key=f"suggest_score_{source_table}_{article_id}_{suggest_idx}", 
                    label_visibility="collapsed"
                )
            else:
                st.selectbox("Score", options=["—"], disabled=True, key=f"suggest_score_disabled_{suggest_idx}", label_visibility="collapsed")
    
    st.markdown("---")
    
    # ── Stance Validation Section ──────────────────────────────────────────────
    st.subheader("🎯 Validate Stance")
    
    st.markdown("**Your stance assessment:**")
    if is_logged_in:
        st.caption("💡 To avoid bias, label the stance *before* expanding the LLM predictions below.")
    
    stance_cols = st.columns([0.4, 0.6])
    with stance_cols[0]:
        if is_logged_in:
            existing_user_stance = existing_stance_validation.get("user_stance", "") if existing_stance_validation else ""
            stance_options = ["—", "OPEN", "RESTRICTIVE", "NEUTRAL", "IRRELEVANT"]
            default_stance_idx = stance_options.index(existing_user_stance) if existing_user_stance in stance_options else 0
            widget_values["user_stance"] = st.selectbox("Your Stance", options=stance_options, index=default_stance_idx, key=f"user_stance_{source_table}_{article_id}", label_visibility="collapsed", help="What stance does this article express toward migration?")
        else:
            st.selectbox("Your Stance", options=["Sign in to validate"], disabled=True, label_visibility="collapsed")
    with stance_cols[1]:
        if is_logged_in:
            existing_comment = existing_stance_validation.get("user_comment", "") if existing_stance_validation else ""
            widget_values["stance_comment"] = st.text_input("Comment (optional)", value=existing_comment, placeholder="Any notes about the stance...", key=f"stance_comment_{source_table}_{article_id}", label_visibility="collapsed")
        else:
            st.text_input("Comment", placeholder="", disabled=True, label_visibility="collapsed")
    
    # LLM Stances - use expander as spoiler
    if stance_per_model:
        st.markdown("**LLM Stance Predictions:**")
        
        if is_logged_in:
            with st.expander("👁️ Click to reveal LLM stances (after you've made your assessment)", expanded=False):
                for model_name, stance in sorted(stance_per_model.items()):
                    st.markdown(f"**{model_name}:** {stance_to_badge_html(stance)}", unsafe_allow_html=True)
                st.markdown(f"**🔷 Ensemble:** {stance_to_badge_html(ensemble_stance)}", unsafe_allow_html=True)
        else:
            for model_name, stance in sorted(stance_per_model.items()):
                st.markdown(f"**{model_name}:** {stance_to_badge_html(stance)}", unsafe_allow_html=True)
            st.markdown(f"**🔷 Ensemble:** {stance_to_badge_html(ensemble_stance)}", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ── Save Button ────────────────────────────────────────────────────────────
    save_cols = st.columns([0.7, 0.3])
    with save_cols[0]:
        if is_logged_in:
            st.caption("💾 Click to save all your validations for this article")
        else:
            st.caption("🔐 Sign in to save validations")
    with save_cols[1]:
        save_clicked = st.form_submit_button("💾 Save Validations", type="primary", use_container_width=True, disabled=not is_logged_in)

# ── Process form submission ────────────────────────────────────────────────────
if save_clicked and is_logged_in:
    success_count = 0
    fail_count = 0
    
    for idx, obj in enumerate(all_ann_frag_objs):
        score_val = widget_values.get(f"narr_score::{idx}", "—")
        if score_val != "—":
            score = int(score_val)
            if upsert_narrative_validation(user=USER, source_table=source_table, article_id=article_id, article_title=article_title, article_body=body_text, model=obj["model"], theme=obj["theme"], meso_narrative=obj["meso"], text_fragment=obj["fragment"] if obj["has_fragment"] else "", score=score, user_comment=""):
                success_count += 1
            else:
                fail_count += 1
    
    # Process suggested narratives (3 rows)
    for suggest_idx in range(3):
        suggest_theme = widget_values.get(f"suggest_theme_{suggest_idx}", "").strip()
        suggest_meso = widget_values.get(f"suggest_meso_{suggest_idx}", "").strip()
        suggest_fragment = widget_values.get(f"suggest_fragment_{suggest_idx}", "").strip()
        suggest_score_val = widget_values.get(f"suggest_score_{suggest_idx}", "—")
        
        if suggest_theme and suggest_meso and suggest_score_val != "—":
            if upsert_narrative_validation(user=USER, source_table=source_table, article_id=article_id, article_title=article_title, article_body=body_text, model="human_suggested", theme=suggest_theme, meso_narrative=suggest_meso, text_fragment=suggest_fragment, score=int(suggest_score_val), user_comment="User-suggested narrative"):
                success_count += 1
            else:
                fail_count += 1
    
    user_stance = widget_values.get("user_stance", "—")
    stance_comment = widget_values.get("stance_comment", "")
    
    if user_stance != "—":
        if upsert_stance_validation(user=USER, source_table=source_table, article_id=article_id, article_title=article_title, article_body=body_text, llm_stances=stance_per_model, ensemble_stance=ensemble_stance, user_stance=user_stance, user_comment=stance_comment):
            success_count += 1
        else:
            fail_count += 1
    
    if success_count > 0 and fail_count == 0:
        st.success(f"✅ Saved {success_count} validation(s) successfully!")
        st.rerun()
    elif success_count > 0:
        st.warning(f"⚠️ Saved {success_count}, failed {fail_count}")
    elif fail_count > 0:
        st.error(f"❌ Failed to save {fail_count} validation(s)")
    else:
        st.info("No validations to save. Select a score or stance to validate.")

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Article ID: {article_id} | Source: {source_table}")
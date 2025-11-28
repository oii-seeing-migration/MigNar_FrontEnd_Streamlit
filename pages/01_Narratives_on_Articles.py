import os, json, re
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher

st.set_page_config(page_title="Narratives on Articles",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")

_qp = st.query_params
def _get_param(k):
    v = _qp.get(k)
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else None)

pre_theme = _get_param("theme")
pre_meso  = _get_param("meso")

DATA_PATH = os.getenv("MESO_SAMPLES_PATH") or os.path.join(os.getenv("EXPORT_DIR") or "./data", "meso_samples.parquet")

@st.cache_data(show_spinner=True)
def load_samples(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)

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
        df[c] = df[c].fillna("").astype(str)

def gather_meso_set(row: pd.Series):
    out = set()
    for col in row.index:
        if isinstance(col, str) and col.startswith("annotation_parsed_"):
            arr = safe_json_load(row[col])
            if isinstance(arr, list):
                for obj in arr:
                    if isinstance(obj, dict):
                        mn = obj.get("meso narrative")
                        if isinstance(mn, str) and mn.strip():
                            out.add(mn.strip())
    return out

df["_meso_all_set"] = df.apply(gather_meso_set, axis=1)

st.sidebar.header("Filters")
source_options = ["(All)"] + (sorted(df["source_table"].unique()) if "source_table" in df.columns else [])
src_choice = st.sidebar.selectbox("Source Table", source_options, index=0)
work_df = df if src_choice == "(All)" or "source_table" not in df.columns else df[df["source_table"] == src_choice]

if THEME_COL:
    theme_vals = sorted(t for t in work_df[THEME_COL].unique() if isinstance(t, str) and t.strip())
    if pre_theme not in theme_vals:
        pre_theme = None
    theme_choice = st.sidebar.selectbox("Sample Theme", ["(All)"] + theme_vals,
                                        index=(theme_vals.index(pre_theme) + 1) if pre_theme else 0)
    if theme_choice != "(All)":
        work_df = work_df[work_df[THEME_COL] == theme_choice]
else:
    theme_choice = "(All)"

all_meso_values = sorted({m for s in work_df["_meso_all_set"] for m in s})
if pre_meso not in all_meso_values:
    pre_meso = None
meso_choice = st.sidebar.selectbox("Meso Narrative (any model)", ["(All)"] + all_meso_values,
                                   index=(all_meso_values.index(pre_meso) + 1) if pre_meso else 0)
if meso_choice != "(All)":
    work_df = work_df[work_df["_meso_all_set"].apply(lambda s: meso_choice in s)]
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
title_choice = st.sidebar.selectbox("Record", titles, index=0)
row = work_df[work_df[title_col] == title_choice].iloc[0]

st.title(row[title_col])
if isinstance(row.get("url"), str) and row["url"]:
    st.markdown(f"[Open Source Link]({row['url']})")
st.caption(f"Source: {row.get('source_table','')} | Date: {row.get('pub_date','')}")

body_text = row.get("body", "") or ""

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
    t = re.sub(r"[‘’]", "'", t)
    t = re.sub(r"[“”]", '"', t)
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

st.markdown("""
<style>
.highlight { background:#fff59d; padding:2px 3px; border-radius:3px; cursor:help; }
.highlight:hover { background:#ffeb3b; }
.highlight-selected { background:#80deea; padding:2px 3px; border-radius:3px; cursor:help; }
.highlight-selected:hover { background:#4dd0e1; }
</style>
""", unsafe_allow_html=True)

st.markdown(apply_highlights(body_text, segments), unsafe_allow_html=True)

with st.expander("Narratives Metadata"):
    rows = [{
        "#": i,
        "selected_meso_filter": (selected_meso == o["meso"]) if selected_meso else False,
        "model": o["model"],
        "narrative theme": o["theme"],
        "meso narrative": o["meso"],
        "text fragment": (o["fragment"] if o["has_fragment"] else "[no fragment]"),
        "fragment_present": o["has_fragment"]
    } for i, o in enumerate(all_ann_frag_objs)]
    meta_df = pd.DataFrame(rows)
    st.dataframe(meta_df, use_container_width=True, hide_index=True)
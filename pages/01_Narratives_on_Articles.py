import os, json, re
import pandas as pd
import streamlit as st
from difflib import SequenceMatcher

st.set_page_config(page_title="Narratives on Articles", layout="wide")

DATA_PATH = os.getenv("MESO_SAMPLES_PATH") or "data/meso_samples.parquet"

@st.cache_data(show_spinner=True)
def load_samples(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=[
            "source_table","article_id","theme","meso",
            "title","body","url","pub_date","annotation_parsed","fragments"
        ])
    df = pd.read_parquet(path)
    for c in ["theme","meso","title","body","annotation_parsed"]:
        if c in df.columns:
            df[c] = df[c].fillna("").astype(str)
    return df

def safe_json_load(s: str | None):
    if s is None: return None
    try: return json.loads(s)
    except Exception: return None

df = load_samples(DATA_PATH)
if df.empty:
    st.error(f"No data at {DATA_PATH}")
    st.stop()

# Sidebar filters (these only filter which article row you open; highlighting always uses full annotation_parsed)
st.sidebar.header("Filters")
source_label_map = {
    "(All)": None,
    "Articles": "articles",
    "UK Parliament": "uk_parliament_contributions",
    "US Congress": "us_congress_speech",
}
src_choice = st.sidebar.selectbox("Source", list(source_label_map.keys()), index=0)
src_filter = source_label_map[src_choice]
work_df = df if src_filter is None else df[df.source_table == src_filter]

theme_list = sorted(t for t in work_df.theme.unique() if isinstance(t, str) and t.strip())
theme_choice = st.sidebar.selectbox("Theme (sample dominant)", ["(All)"] + theme_list, index=0)
if theme_choice != "(All)":
    work_df = work_df[work_df.theme == theme_choice]

meso_list = sorted(m for m in work_df.meso.unique() if isinstance(m, str) and m.strip())
meso_choice = st.sidebar.selectbox("Meso Narrative (sample)", ["(All)"] + meso_list, index=0)
if meso_choice != "(All)":
    work_df = work_df[work_df.meso == meso_choice]

if work_df.empty:
    st.warning("No rows match filters.")
    st.stop()

title_choice = st.sidebar.selectbox("Record", work_df.title.tolist())
row = work_df[work_df.title == title_choice].iloc[0]

st.title(row.title)
if row.url:
    st.markdown(f"[Open Source Link]({row.url})")
st.caption(f"Source: {row.source_table} | Date: {row.pub_date}")

body_text = row.body or ""
ann_raw = row.annotation_parsed or ""

# 1) Parse ALL meso narratives and fragments from annotation_parsed
def extract_all_fragments(ann_str: str):
    arr = safe_json_load(ann_str) or []
    out = []
    if isinstance(arr, list):
        for o in arr:
            if not isinstance(o, dict): continue
            frag = o.get("text fragment")
            th   = o.get("narrative theme")
            mn   = o.get("meso narrative")
            if isinstance(frag, str) and frag.strip():
                out.append({
                    "fragment": frag.strip(),
                    "theme": th if isinstance(th, str) else None,
                    "meso": mn if isinstance(mn, str) else None
                })
    return out

ann_frag_objs = extract_all_fragments(ann_raw)

# 2) Robust matching to find each fragment in the body (highlight ALL found fragments)
def normalize_text(t: str) -> str:
    t = t.strip()
    t = re.sub(r"[‘’]", "'", t)
    t = re.sub(r"[“”]", '"', t)
    t = t.replace("–","-").replace("—","-")
    t = re.sub(r"\s+", " ", t)
    return t

def normalize_fragment(f: str) -> str:
    f = normalize_text(f)
    f = re.sub(r"(?:…|\.{3,})", "...", f)          # unify ellipsis
    f = re.sub(r"(?:\.{3,}|…)$", "", f).strip()     # trim trailing ellipsis
    f = re.sub(r"\b(\d+)\s*(%|percent|per\s*cent)\b", r"<<NUMPCT>>", f, flags=re.IGNORECASE)
    return f

def build_regex(nf: str):
    parts = [p for p in nf.split("...") if p]
    if not parts: return None
    esc_parts = []
    for p in parts:
        p = normalize_text(p)
        ep = re.escape(p)
        ep = re.sub(r"\s+", r"[\\s,;:–—-]+", ep)
        ep = ep.replace(re.escape("<<NUMPCT>>"), r"(?:\d+\s*(?:%|percent|per\s*cent))")
        esc_parts.append(ep)
    pattern = r".{0,280}?".join(esc_parts)
    try:
        return re.compile(pattern, re.IGNORECASE | re.DOTALL | re.MULTILINE)
    except re.error:
        return None

def direct_search(body: str, frag: str):
    idx = body.find(frag)
    if idx >= 0: return (idx, idx + len(frag))
    ib = body.lower().find(frag.lower())
    if ib >= 0: return (ib, ib + len(frag))
    return None

def fuzzy_search(body: str, nf: str):
    anchor = re.sub(r"^[^A-Za-z0-9]+", "", nf)[:8].lower()
    if not anchor: return None
    positions = [m.start() for m in re.finditer(re.escape(anchor), body.lower())]
    if not positions: return None
    target = re.sub(r"\s+", " ", nf.lower())
    best = None
    for pos in positions:
        window = body[pos:pos + int(len(nf)*1.4)]
        window_norm = re.sub(r"\s+", " ", window.lower())
        ratio = SequenceMatcher(None, target, window_norm[:len(target)]).ratio()
        if best is None or ratio > best[0]:
            best = (ratio, pos, pos + len(nf))
    if best and best[0] >= 0.80:
        return (best[1], best[2])
    return None

# Find spans for every fragment; allow overlaps but merge bands; all narratives appear in tooltip
matches = []  # (start, end, theme, meso)
for obj in ann_frag_objs:
    frag = obj["fragment"]
    nf = normalize_fragment(frag)
    span = direct_search(body_text, frag) or direct_search(body_text, nf)
    if span is None:
        rgx = build_regex(nf)
        if rgx:
            m = rgx.search(body_text)
            if m: span = m.span()
    if span is None:
        span = fuzzy_search(body_text, nf)
    if span is None:
        continue
    s, e = span
    matches.append((s, e, obj["theme"], obj["meso"]))

def merge_overlaps(matches):
    events = []
    for s, e, th, mn in matches:
        events.append((s, 1, th, mn))
        events.append((e, -1, th, mn))
    events.sort(key=lambda x: (x[0], -x[1]))
    active = {}
    segments = []
    last_pos = None

    def active_keys():
        return {k for k, c in active.items() if c > 0}

    for pos, kind, th, mn in events:
        if last_pos is not None and pos > last_pos and active_keys():
            segments.append((last_pos, pos, active_keys().copy()))
        if kind == 1:
            active[(th, mn)] = active.get((th, mn), 0) + 1
        else:
            if (th, mn) in active:
                active[(th, mn)] -= 1
                if active[(th, mn)] <= 0:
                    active.pop((th, mn), None)
        last_pos = pos
    return segments

segments = merge_overlaps(matches)

def apply_highlights(text: str, segments):
    if not segments: return text
    segments.sort(key=lambda x: x[0])
    out = []
    last = 0
    for s, e, th_mn_set in segments:
        out.append(text[last:s])
        labels = []
        for th, mn in sorted(th_mn_set, key=lambda x: (str(x[0] or ""), str(x[1] or ""))):
            labels.append(f"{th or '(n/a)'} — {mn or '(n/a)'}")
        tip = " | ".join(labels)
        out.append(f'<span class="highlight" title="{tip}">{text[s:e]}</span>')
        last = e
    out.append(text[last:])
    return "".join(out)

highlighted = apply_highlights(body_text, segments)

st.markdown("""
<style>
.highlight {
  background:#fff59d;
  padding:2px 3px;
  border-radius:3px;
  cursor:help;
  transition:background-color .15s;
}
.highlight:hover { background:#ffeb3b; }
code, pre { white-space:pre-wrap; }
</style>
""", unsafe_allow_html=True)

st.markdown(highlighted, unsafe_allow_html=True)

# 3) Tabular view of ALL narratives from annotation_parsed (remove raw and summary)
with st.expander("Narratives Metadata", expanded=False):
    ann_rows = [{
        "#": i,
        "narrative theme": o.get("theme") if isinstance(o, dict) else o.get("narrative theme"),
        "meso narrative": o.get("meso") if isinstance(o, dict) else o.get("meso narrative"),
        "text fragment": o.get("fragment") if isinstance(o, dict) else o.get("text fragment"),
    } for i, o in enumerate(ann_frag_objs)]
    meta_df = pd.DataFrame(ann_rows, columns=["#","narrative theme","meso narrative","text fragment"])
    st.dataframe(meta_df, use_container_width=True, hide_index=True)

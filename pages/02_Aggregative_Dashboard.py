import os
import streamlit as st
import altair as alt
import pandas as pd

st.set_page_config(page_title="Aggregative Dashboard",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")
st.title("Aggregative Dashboard")

# Use precomputed aggregates from ~/data
DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_daily.parquet")
FRAMES_PATH = os.path.join(DATA_DIR, "frames_daily.parquet")
MESO_PATH = os.path.join(DATA_DIR, "meso_daily.parquet")

@st.cache_data(ttl="1h", show_spinner=True)
def load_parquets(stance_fp: str, frames_fp: str, meso_fp: str):
    def _read_parquet(fp):
        if not os.path.exists(fp):
            return pd.DataFrame()
        df = pd.read_parquet(fp)
        # Normalize expected columns
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"], errors="coerce").dt.date
        if "source_domain" in df.columns:
            df["source_domain"] = df["source_domain"].fillna("").astype(str)
        if "model" in df.columns:
            df["model"] = df["model"].fillna("").astype(str)
        if "count" in df.columns:
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
        return df

    stance_df = _read_parquet(stance_fp)
    frames_df = _read_parquet(frames_fp)
    meso_df = _read_parquet(meso_fp)
    return stance_df, frames_df, meso_df

stance_df, frames_df, meso_df = load_parquets(STANCE_PATH, FRAMES_PATH, MESO_PATH)

if stance_df.empty and frames_df.empty and meso_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Make sure stance_daily.parquet, frames_daily.parquet, meso_daily.parquet exist.")
    st.stop()

# Sidebar: model selector (single model for now, e.g., 'Qwen3-32B')
st.sidebar.header("Filters")
available_models = sorted(set(
    list(stance_df.get("model", pd.Series(dtype=str)).unique() if "model" in stance_df else []) +
    list(frames_df.get("model", pd.Series(dtype=str)).unique() if "model" in frames_df else []) +
    list(meso_df.get("model", pd.Series(dtype=str)).unique() if "model" in meso_df else [])
))
default_model = "Qwen3-32B" if "Qwen3-32B" in available_models else (available_models[0] if available_models else None)
selected_model = st.sidebar.selectbox("Model", options=available_models, index=available_models.index(default_model) if default_model in available_models else 0)

def by_model(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model" not in df.columns or not selected_model:
        return df
    return df[df["model"] == selected_model].copy()

stance_df = by_model(stance_df)
frames_df = by_model(frames_df)
meso_df = by_model(meso_df)

# Date range bounds from filtered-by-model data
date_cols = []
for df in (stance_df, frames_df, meso_df):
    if not df.empty and "day" in df.columns:
        date_cols.append(pd.Series(df["day"]))
if date_cols:
    all_days = pd.concat(date_cols, ignore_index=True).dropna()
    min_dt = all_days.min()
    max_dt = all_days.max()
else:
    min_dt = max_dt = None

if min_dt and max_dt:
    picked = st.sidebar.date_input(
        "Date range",
        value=(min_dt, max_dt),
        min_value=min_dt,
        max_value=max_dt
    )
    if isinstance(picked, tuple) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date = end_date = picked
else:
    st.info("No valid day column detected; using full dataset.")
    start_date = end_date = None

def filter_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "day" not in df.columns or not start_date or not end_date:
        return df
    return df[(df["day"] >= start_date) & (df["day"] <= end_date)].copy()

stance_f = filter_by_date(stance_df)
frames_f = filter_by_date(frames_df)
meso_f = filter_by_date(meso_df)

# Domains available after model + date filters
domains = set()
for df in (stance_f, frames_f, meso_f):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains if d])

selected_domains = st.sidebar.multiselect(
    "Source domain",
    options=domains,
    default=domains
)

def filter_by_domain(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not selected_domains:
        return df
    return df[df["source_domain"].isin(selected_domains)].copy()

stance_f = filter_by_domain(stance_f)
frames_f = filter_by_domain(frames_f)
meso_f = filter_by_domain(meso_f)

# Macros (from 03_Contrastive_Dashboard) + apply here
st.sidebar.subheader("Macros")
min_support = st.sidebar.slider("Min articles per label", 0, 50, 0, 1)
top_n = st.sidebar.slider("Top N items", 5, 40, 25, 1)

# 1) Stance bubble chart (aggregate per domain across selected range)
st.subheader("Aggregate Stance Toward Migration (by Source Domain)")
if stance_f.empty:
    st.info("No stance data available for the selected filters.")
else:
    stance_sum = (
        stance_f.groupby(["source_domain", "stance"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    # Pivot (OPEN/RESTRICTIVE/NEUTRAL) and totals
    pivot = stance_sum.pivot_table(
        index="source_domain",
        columns="stance",
        values="articles",
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    for col in ["OPEN", "RESTRICTIVE", "NEUTRAL"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["total"] = pivot["OPEN"] + pivot["RESTRICTIVE"] + pivot["NEUTRAL"]
    # Apply min_support on domain totals (optional for robustness)
    if min_support > 0:
        pivot = pivot[pivot["total"] >= int(min_support)].copy()

    pivot["stance_score"] = (pivot["OPEN"] - pivot["RESTRICTIVE"]) / pivot["total"].replace({0: pd.NA})
    stance_chart_df = pivot.dropna(subset=["stance_score"]).copy()

    st.caption("Score = (OPEN - RESTRICTIVE) / (OPEN + RESTRICTIVE + NEUTRAL). Bubble size = total articles.")
    # Bubble chart: x = stance score (-1..1), y = domain, size = total, color ~ stance score
    color_scale = alt.Scale(scheme="redyellowgreen", domain=(-1, 0, 1))
    h = max(24 * len(stance_chart_df), 360)
    chart = alt.Chart(stance_chart_df).mark_circle(opacity=0.85, stroke="black", strokeWidth=0.4).encode(
        x=alt.X("stance_score:Q", title="Stance Toward Migration", scale=alt.Scale(domain=(-1, 1), clamp=True)),
        y=alt.Y("source_domain:N", sort="-x", title="Source Domain", axis=alt.Axis(labelLimit=0, labelOverlap=False)),
        size=alt.Size("total:Q", title="Total Articles", scale=alt.Scale(range=[30, 1200])),
        color=alt.Color("stance_score:Q", title="Stance", scale=color_scale),
        tooltip=[
            alt.Tooltip("source_domain:N", title="Domain"),
            alt.Tooltip("stance_score:Q", title="Score", format=".2f"),
            alt.Tooltip("OPEN:Q", title="OPEN"),
            alt.Tooltip("RESTRICTIVE:Q", title="RESTRICTIVE"),
            alt.Tooltip("NEUTRAL:Q", title="NEUTRAL"),
            alt.Tooltip("total:Q", title="Total"),
        ],
    ).properties(height=h, title=f"Aggregate Stance by Domain (Model: {selected_model})")
    st.altair_chart(chart, use_container_width=True)


# 2) Frames bar chart (top frames by total articles)
st.subheader("Top Narrative Frames (selected range)")
if frames_f.empty:
    st.info("No frame data available for the selected filters.")
else:
    frames_sum = (
        frames_f.groupby("frame", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    if min_support > 0:
        frames_sum = frames_sum[frames_sum["articles"] >= int(min_support)]
    frames_top = frames_sum.sort_values("articles", ascending=False).head(int(top_n))
    h = max(24 * len(frames_top), 360)
    frames_chart = alt.Chart(frames_top).mark_bar().encode(
        x=alt.X("articles:Q", title="# Articles"),
        y=alt.Y("frame:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False), title="Narrative Frame"),
        color=alt.value("#1f77b4"),
        tooltip=[alt.Tooltip("frame:N", title="Frame"), alt.Tooltip("articles:Q", title="# Articles")],
    ).properties(title=f"Top Frames (Model: {selected_model})", height=h)
    st.altair_chart(frames_chart, use_container_width=True)

# 3) Meso narratives bar chart (top meso narratives)
st.subheader("Top Meso Narratives (selected range)")
if meso_f.empty:
    st.info("No meso narrative data available for the selected filters.")
else:
    meso_sum = (
        meso_f.groupby("meso_narrative", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    if min_support > 0:
        meso_sum = meso_sum[meso_sum["articles"] >= int(min_support)]
    meso_top = meso_sum.sort_values("articles", ascending=False).head(int(top_n))
    h = max(24 * len(meso_top), 360)
    meso_chart = alt.Chart(meso_top).mark_bar().encode(
        x=alt.X("articles:Q", title="# Articles"),
        y=alt.Y("meso_narrative:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False,titleAngle=270, titlePadding=300, labelPadding=6), title="Meso Narrative"),#     y=alt.Y(
        tooltip=[alt.Tooltip("meso_narrative:N", title="Meso Narrative"), alt.Tooltip("articles:Q", title="# Articles")],
    ).properties(title=f"Top Meso Narratives (Model: {selected_model})", height=h)
    st.altair_chart(meso_chart, use_container_width=True)

with st.expander("Raw aggregates"):
    st.write("Model:", selected_model)
    st.write("Stance (filtered):", stance_f.head(1000))
    st.write("Frames (filtered):", frames_f.head(1000))
    st.write("Meso (filtered):", meso_f.head(1000))
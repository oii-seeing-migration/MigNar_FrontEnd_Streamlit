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
THEMES_PATH = os.path.join(DATA_DIR, "themes_daily.parquet")
MESO_PATH = os.path.join(DATA_DIR, "meso_daily.parquet")

@st.cache_data(ttl="30m", show_spinner=True, max_entries=10)
def load_parquets(stance_fp: str, themes_fp: str, meso_fp: str):
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
    themes_df = _read_parquet(themes_fp)
    meso_df = _read_parquet(meso_fp)
    return stance_df, themes_df, meso_df

stance_df, themes_df, meso_df = load_parquets(STANCE_PATH, THEMES_PATH, MESO_PATH)

if stance_df.empty and themes_df.empty and meso_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Make sure stance_daily.parquet, themes_daily.parquet, meso_daily.parquet exist.")
    st.stop()

# Sidebar: model selector (single model for now, e.g., 'gpt-oss-20b')
st.sidebar.header("Filters")
available_models = sorted(set(
    list(stance_df.get("model", pd.Series(dtype=str)).unique() if "model" in stance_df else []) +
    list(themes_df.get("model", pd.Series(dtype=str)).unique() if "model" in themes_df else []) +
    list(meso_df.get("model", pd.Series(dtype=str)).unique() if "model" in meso_df else [])
))
default_model = "gpt-oss-20b" if "gpt-oss-20b" in available_models else (available_models[0] if available_models else None)
selected_model = st.sidebar.selectbox("Model", options=available_models, index=available_models.index(default_model) if default_model in available_models else 0)

def by_model(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model" not in df.columns or not selected_model:
        return df
    return df[df["model"] == selected_model].copy()

stance_df = by_model(stance_df)
themes_df = by_model(themes_df)
meso_df = by_model(meso_df)

# Date range bounds from filtered-by-model data
date_cols = []
for df in (stance_df, themes_df, meso_df):
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
themes_f = filter_by_date(themes_df)
meso_f = filter_by_date(meso_df)

# Domains available after model + date filters
domains = set()
for df in (stance_f, themes_f, meso_f):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains if d])
default_domains = ['UK Parliament (Con)','UK Parliament (Lab)','US Congress (Rep)','US Congress (Dem)', 'dailymail.co.uk','telegraph.co.uk', 'theguardian.com','bbc.co.uk','independent.co.uk','thesun.co.uk','mirror.co.uk']
default_domains = [d for d in default_domains if d in domains]

selected_domains = st.sidebar.multiselect(
    "Source domain",
    options=domains,
    default=default_domains
)

def filter_by_domain(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not selected_domains:
        return df
    return df[df["source_domain"].isin(selected_domains)].copy()

st.sidebar.markdown("---")
if st.sidebar.button("🧹 Clear Cache (if slow)"):
    st.cache_data.clear()
    st.success("Cache cleared! Refresh to reload data.")

stance_f = filter_by_domain(stance_f)
themes_f = filter_by_domain(themes_f)
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
    st.altair_chart(chart, width="stretch")


# 2) Themes bar chart (top themes by total articles)
st.subheader("Top Narrative Themes (selected range)")
if themes_f.empty:
    st.info("No theme data available for the selected filters.")
else:
    themes_sum = (
        themes_f.groupby("theme", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    if min_support > 0:
        themes_sum = themes_sum[themes_sum["articles"] >= int(min_support)]
    themes_top = themes_sum.sort_values("articles", ascending=False).head(int(top_n))
    h = max(24 * len(themes_top), 360)
    themes_chart = alt.Chart(themes_top).mark_bar().encode(
        x=alt.X("articles:Q", title="# Articles"),
        y=alt.Y("theme:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False), title="Narrative Theme"),
        color=alt.value("#1f77b4"),
        tooltip=[alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("articles:Q", title="# Articles")],
    ).properties(title=f"Top Themes (Model: {selected_model})", height=h)
    st.altair_chart(themes_chart, width="stretch")

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
    st.altair_chart(meso_chart, width="stretch")

with st.expander("Raw aggregates"):
    st.write("Model:", selected_model)
    st.write("Stance (filtered):", stance_f.head(100))
    st.write("Themes (filtered):", themes_f.head(100))
    st.write("Meso (filtered):", meso_f.head(100))
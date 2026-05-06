import os
import streamlit as st
import altair as alt
import pandas as pd
from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

st.set_page_config(page_title="Aggregative Dashboard",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")


from lib.data_loader import load_parquets


st.title("Aggregative Dashboard")

# ------------------------------------------------------------
# Use precomputed aggregates from ~/data
# ------------------------------------------------------------
# DATA_DIR = os.path.expanduser("./data")
# STANCE_PATH = os.path.join(DATA_DIR, "stance_monthly.parquet")
# THEMES_PATH = os.path.join(DATA_DIR, "themes_monthly.parquet")
# MESO_PATH = os.path.join(DATA_DIR, "meso_monthly.parquet")

# @st.cache_data(ttl="30m", show_spinner=True, max_entries=1)
# def load_parquets(stance_fp: str, themes_fp: str, meso_fp: str):
#     def _read_parquet(fp):
#         if not os.path.exists(fp):
#             return pd.DataFrame()
#         df = pd.read_parquet(fp)
#         # Normalize expected columns
#         if "month" in df.columns:
#             # Convert YYYY-MM string to datetime for filtering
#             df["month"] = pd.to_datetime(df["month"] + "-01", errors="coerce")
#         if "source_domain" in df.columns:
#             df["source_domain"] = df["source_domain"].fillna("").astype(str)
#         if "model" in df.columns:
#             df["model"] = df["model"].fillna("").astype(str)
#         if "count" in df.columns:
#             df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
#         return df

#     stance_df = _read_parquet(stance_fp)
#     themes_df = _read_parquet(themes_fp)
#     meso_df = _read_parquet(meso_fp)
#     return stance_df, themes_df, meso_df

# stance_df, themes_df, meso_df = load_parquets(STANCE_PATH, THEMES_PATH, MESO_PATH)
stance_df, themes_df, meso_df = load_parquets()

if stance_df.empty and themes_df.empty and meso_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Make sure stance_monthly.parquet, themes_monthly.parquet, meso_monthly.parquet exist.")
    st.stop()

# ------------------------------------------------------------
# Sidebar Controls
# ------------------------------------------------------------
st.sidebar.header("Filters")
available_models = sorted(set(
    list(stance_df.get("model", pd.Series(dtype=str)).unique() if "model" in stance_df else []) +
    list(themes_df.get("model", pd.Series(dtype=str)).unique() if "model" in themes_df else []) +
    list(meso_df.get("model", pd.Series(dtype=str)).unique() if "model" in meso_df else [])
))
default_model = "Ensemble" if "Ensemble" in available_models else (available_models[0] if available_models else None)

selected_model = st.sidebar.selectbox(
    "Model",
    options=available_models,
    index=available_models.index(default_model) if default_model in available_models else 0,
    help="Filters all charts to a single annotation model. Selecting 'Ensemble' shows consensus outputs.",
)

def by_model(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "model" not in df.columns or not selected_model:
        return df
    return df[df["model"] == selected_model].copy()

stance_df = by_model(stance_df)
themes_df = by_model(themes_df)
meso_df = by_model(meso_df)


available_versions = sorted(set(
    list(pd.to_numeric(themes_df["version"], errors="coerce").dropna().astype(int).unique().tolist())
    if ("version" in themes_df.columns and not themes_df.empty) else []
    +
    list(pd.to_numeric(meso_df["version"], errors="coerce").dropna().astype(int).unique().tolist())
    if ("version" in meso_df.columns and not meso_df.empty) else []
))

if available_versions:
    version_options = ["(All versions)"] + available_versions
    selected_version = st.sidebar.selectbox(
        "Taxonomy Version",
        options=version_options,
        index=len(version_options) - 1,  # default to latest version
        help="Filters Theme and Meso aggregates by taxonomy revision. '(All versions)' keeps all revisions.",
    )
else:
    selected_version = "(All versions)"

def by_version(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or selected_version == "(All versions)" or "version" not in df.columns:
        return df
    v = pd.to_numeric(df["version"], errors="coerce")
    return df[v == int(selected_version)].copy()

# Apply version filter ONLY to themes/meso
themes_df = by_version(themes_df)
meso_df = by_version(meso_df)


# Date range bounds from filtered-by-model data
date_cols = []
for df in (stance_df, themes_df, meso_df):
    if not df.empty and "month" in df.columns:
        date_cols.append(pd.Series(df["month"]))
if date_cols:
    all_months = pd.concat(date_cols, ignore_index=True).dropna()
    min_dt = all_months.min().date()
    max_dt = all_months.max().date()
else:
    min_dt = max_dt = None

if min_dt and max_dt:
    picked = st.sidebar.date_input(
        "Date range",
        value=(min_dt, max_dt),
        min_value=min_dt,
        max_value=max_dt,
        help="Limits all aggregates to records whose month falls inside this interval.",
    )
    if isinstance(picked, tuple) and len(picked) == 2:
        start_date, end_date = picked
    else:
        start_date = end_date = picked
else:
    st.info("No valid day column detected; using full dataset.")
    start_date = end_date = None

def filter_by_date(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "month" not in df.columns or not start_date or not end_date:
        return df
    # Convert date picker values to month start for comparison
    return df[(df["month"].dt.date >= start_date) & (df["month"].dt.date <= end_date)].copy()

stance_f = filter_by_date(stance_df)
themes_f = filter_by_date(themes_df)
meso_f = filter_by_date(meso_df)

# Domains available after model + date filters
domains = set()
for df in (stance_f, themes_f, meso_f):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains if d])

default_domains = [
    'UK Parliament (Con)', 'UK Parliament (Lab)', 'US Congress (Rep)', 'US Congress (Dem)', 
    'dailymail.co.uk', 'telegraph.co.uk', 'theguardian.com', 'bbc.co.uk', 
    'independent.co.uk', 'thesun.co.uk', 'mirror.co.uk'
]
default_domains = [d for d in default_domains if d in domains]

selected_domains = st.sidebar.multiselect(
    "Source domain",
    options=domains,
    default=default_domains,
    help="Keeps only the selected outlets/domains in all charts. Empty selection shows all available domains.",
)

def filter_by_domain(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not selected_domains:
        return df
    return df[df["source_domain"].isin(selected_domains)].copy()

st.sidebar.markdown("---")

stance_f = filter_by_domain(stance_f)
themes_f = filter_by_domain(themes_f)
meso_f = filter_by_domain(meso_f)

# ------------------------------------------------------------
# 1) Stance bubble chart (aggregate per domain)
# ------------------------------------------------------------
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
    pivot["stance_score"] = (pivot["OPEN"] - pivot["RESTRICTIVE"]) / pivot["total"].replace({0: pd.NA})
    stance_chart_df = pivot.dropna(subset=["stance_score"]).copy()

    st.caption("Score = (OPEN - RESTRICTIVE) / (OPEN + RESTRICTIVE + NEUTRAL). Bubble size = total articles.")
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


# ------------------------------------------------------------
# 2) Themes bar chart
# ------------------------------------------------------------
DEFAULT_THEMES = [
    "EU migration to and from the UK",
    "migrants and crimes",
    "detention and deportation of migrants",
    "migrants and human rights",
    "migrants, economy, and labour market",
    "small boats and Channel crossings",
    "work visas and sponsorship",
    "public opinion on migration",
]

st.subheader("Aggregate Narrative Themes")

if themes_f.empty:
    st.info("No theme data available for the selected filters.")
else:
    themes_sum = (
        themes_f.groupby("theme", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
        
    overall_themes = themes_sum.sort_values("articles", ascending=False)["theme"].tolist()
    
    selected_themes = st.multiselect(
        "Select themes",
        options=overall_themes,
        default=[t for t in DEFAULT_THEMES if t in overall_themes],
        help="Choose which themes to include. All selected themes will be displayed.",
    )

    if selected_themes:
        themes_plot = themes_sum[themes_sum["theme"].isin(selected_themes)]
        
        h = max(24 * len(themes_plot), 360)
        themes_chart = alt.Chart(themes_plot).mark_bar().encode(
            x=alt.X("articles:Q", title="# Articles"),
            y=alt.Y("theme:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False, titleAngle=270, titlePadding=70, labelPadding=6), title="Narrative Theme"),
            color=alt.value("#1f77b4"),
            tooltip=[alt.Tooltip("theme:N", title="Theme"), alt.Tooltip("articles:Q", title="# Articles")],
        ).properties(title=f"Themes (Model: {selected_model})", height=h)
        
        st.altair_chart(themes_chart, width="stretch")
    else:
        st.info("Please select at least one theme to generate the chart.")


# ------------------------------------------------------------
# 3) Meso narratives bar chart
# ------------------------------------------------------------
DEFAULT_MESO_NARRATIVES = [
    "EU migration enhances labour mobility and economic growth",
    "EU migration takes jobs from local workers",
    "Most migrants are law-abiding citizens",
    "Migrants are involved in violent crimes",
    "Migrants are involved in child abuse scandals",
    "Migrants sell illegal drugs",
    "Migrants are involved in fraud",
    "Current detention practices violate human rights",
    "Deportations separate families and harm children",
    "Current detention practices are legitimate and necessary",
    "Migrants face systemic human rights abuses",
    "Human rights claims by migrants are often exaggerated",
    "Migrants fill critical labour shortages",
    "Migrants take jobs away from local workers",
    "Stopping the boats should be a government priority",
    "People crossing the Channel are desperate, not criminals",
    "Migrants burden the healthcare system",
    "Migrants are necessary for the NHS to function",
    "The social care sector would collapse without migrant workers",
    "Public opinion supports welcoming migrants",
    "Public opinion supports restricting migration",
]

st.subheader("Aggregate Meso Narratives")

if meso_f.empty:
    st.info("No meso narrative data available for the selected filters.")
else:
    meso_sum = (
        meso_f.groupby("meso_narrative", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
        
    overall_meso = meso_sum.sort_values("articles", ascending=False)["meso_narrative"].tolist()
    
    selected_meso = st.multiselect(
        "Select meso narratives",
        options=overall_meso,
        default=[m for m in DEFAULT_MESO_NARRATIVES if m in overall_meso],
        help="Choose which meso narratives to include. All selected meso narratives will be displayed.",
    )

    if selected_meso:
        meso_plot = meso_sum[meso_sum["meso_narrative"].isin(selected_meso)]

        h = max(24 * len(meso_plot), 360)
        meso_chart = alt.Chart(meso_plot).mark_bar().encode(
            x=alt.X("articles:Q", title="# Articles"),
            y=alt.Y("meso_narrative:N", sort="-x", axis=alt.Axis(labelLimit=0, labelOverlap=False, titleAngle=270, titlePadding=200, labelPadding=6), title="Meso Narrative"),
            tooltip=[alt.Tooltip("meso_narrative:N", title="Meso Narrative"), alt.Tooltip("articles:Q", title="# Articles")],
        ).properties(title=f"Meso Narratives (Model: {selected_model})", height=h)
        
        st.altair_chart(meso_chart, width="stretch")
    else:
        st.info("Please select at least one meso narrative to generate the chart.")


# ------------------------------------------------------------
# Raw Data Expander
# ------------------------------------------------------------
with st.expander("Raw aggregates"):
    st.write("Model:", selected_model)
    st.write("Stance (filtered):", stance_f.head(100))
    st.write("Themes (filtered):", themes_f.head(100))
    st.write("Meso (filtered):", meso_f.head(100))
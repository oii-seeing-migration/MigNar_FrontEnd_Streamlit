import os
import streamlit as st
import altair as alt
import pandas as pd
from datetime import date
from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

st.set_page_config(page_title="Comparative Dashboard",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")



st.title("Comparative Dashboard")

# ------------------------------------------------------------
# UK Media Outlet Groups (for default selection)
# ------------------------------------------------------------
UK_LEFT_WING = [
    "theguardian.com",
    "mirror.co.uk",
    "independent.co.uk",
    "huffingtonpost.co.uk",
    "dailyrecord.co.uk",
    "thenational.scot",
    "heraldscotland.com"
]
UK_RIGHT_WING = [
    "telegraph.co.uk",
    "dailymail.co.uk",
    "express.co.uk",
    "thesun.co.uk",
    "spectator.co.uk",
    "thetimes.co.uk",
    "thescottishsun.co.uk"
]

# ------------------------------------------------------------
# Load precomputed aggregates from ./data (no DB round-trips)
# ------------------------------------------------------------
from lib.data_loader import load_parquets
stance_df, themes_df, meso_df = load_parquets()



if themes_df.empty and meso_df.empty:
    st.error("No aggregates found. Please generate exports first (stance/themes/meso parquet files).")
    st.stop()


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

st.sidebar.markdown("---")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def global_date_bounds(dfs: list[pd.DataFrame]):
    series = []
    for df in dfs:
        if not df.empty and "month" in df.columns:
            series.append(df["month"])
    if not series:
        return None, None
    all_months = pd.concat(series, ignore_index=True).dropna()
    return all_months.min().date(), all_months.max().date()


def _norm_date_input(p):
    if isinstance(p, tuple) and len(p) == 2:
        a, b = p
        return (min(a, b), max(a, b))
    return (p, p)

def pick_domains_for_range(dfs: list[pd.DataFrame], model: str, start_date, end_date):
    doms = set()
    for df in dfs:
        if df.empty or "month" not in df.columns:
            continue
        m = df[(df["month"].dt.date >= start_date) & (df["month"].dt.date <= end_date)].copy()
        if model and "model" in m.columns:
            m = m[m["model"] == model]
        if "source_domain" in m.columns:
            doms.update(m["source_domain"].dropna().unique().tolist())
    return sorted([d for d in doms if d])

def filter_slice(df: pd.DataFrame, model: str, start_date, end_date, domains: set | None):
    if df.empty:
        return df
    m = df[(df["month"].dt.date >= start_date) & (df["month"].dt.date <= end_date)].copy()
    if model and "model" in m.columns:
        m = m[m["model"] == model]
    if domains and "source_domain" in m.columns:
        m = m[m["source_domain"].isin(domains)]
    return m

def total_articles_from_stance(stance_slice: pd.DataFrame) -> int:
    if stance_slice.empty:
        return 0
    return int(stance_slice["count"].sum())

def themes_counts(themes_slice: pd.DataFrame) -> pd.DataFrame:
    if themes_slice.empty:
        return pd.DataFrame(columns=["narrative theme", "articles"])
    g = (
        themes_slice.groupby("theme", as_index=False)["count"]
        .sum()
        .rename(columns={"theme": "narrative theme", "count": "articles"})
    )
    return g

def meso_counts(meso_slice: pd.DataFrame) -> pd.DataFrame:
    if meso_slice.empty:
        return pd.DataFrame(columns=["meso narrative", "articles"])
    g = (
        meso_slice.groupby("meso_narrative", as_index=False)["count"]
        .sum()
        .rename(columns={"meso_narrative": "meso narrative", "count": "articles"})
    )
    return g

# ------------------------------------------------------------
# Sidebar controls (Filter A, Filter B)
# ------------------------------------------------------------
# Available models (union from stance/themes/meso)
available_models = sorted(set(
    list(themes_df["model"].unique() if "model" in themes_df else []) +
    list(stance_df["model"].unique() if "model" in stance_df else []) +
    list(meso_df["model"].unique() if "model" in meso_df else [])
))
if not available_models:
    st.error("No models available in aggregates.")
    st.stop()

min_dt, max_dt = global_date_bounds([themes_df, stance_df, meso_df])
if not min_dt or not max_dt:
    st.error("No valid 'month' column found in aggregates.")
    st.stop()

# Filter A
st.sidebar.markdown("#### Filter A")
selected_model_A = st.sidebar.selectbox(
    "Model (A)",
    options=available_models,
    index=available_models.index("Ensemble") if "Ensemble" in available_models else 0,
    key="model_a",
    help="Model used to compute Filter A prevalence values.",
)
period_1_in = st.sidebar.date_input(
    "Period (A)",
    value=(date(2016, 1, 1), max_dt),
    min_value=min_dt,
    max_value=max_dt,
    key="period_1",
    help="Date window used for Filter A. Only records in this interval are included.",
)
period_1 = _norm_date_input(period_1_in)
domains_1_options = pick_domains_for_range([themes_df, stance_df, meso_df], selected_model_A, period_1[0], period_1[1])
default_1 = [d for d in UK_LEFT_WING if d in domains_1_options] or domains_1_options[:3]
domains_1_selected = st.sidebar.multiselect(
    "Source domain (A)",
    options=domains_1_options,
    default=default_1,
    key="domain_1",
    help="Source domains included in Filter A. Empty means all domains available for the chosen period/model.",
)
domains_1 = set(domains_1_selected) if domains_1_selected else None

# Filter B
st.sidebar.markdown("#### Filter B")
selected_model_B = st.sidebar.selectbox(
    "Model (B)",
    options=available_models,
    index=available_models.index("Ensemble") if "Ensemble" in available_models else 0,
    key="model_b",
    help="Model used to compute Filter B prevalence values.",
)
period_2_in = st.sidebar.date_input(
    "Period (B)",
    value=(date(2016, 1, 1), max_dt),
    min_value=min_dt,
    max_value=max_dt,
    key="period_2",
    help="Date window used for Filter B. Only records in this interval are included.",
)
period_2 = _norm_date_input(period_2_in)
domains_2_options = pick_domains_for_range([themes_df, stance_df, meso_df], selected_model_B, period_2[0], period_2[1])
default_2 = [d for d in UK_RIGHT_WING if d in domains_2_options] or domains_2_options[:3]
domains_2_selected = st.sidebar.multiselect(
    "Source domain (B)",
    options=domains_2_options,
    default=default_2,
    key="domain_2",
    help="Source domains included in Filter B. Empty means all domains available for the chosen period/model.",
)
domains_2 = set(domains_2_selected) if domains_2_selected else None

st.sidebar.markdown("---")

# ------------------------------------------------------------
# Compute contrast using aggregates
# ------------------------------------------------------------
# Slices
stance_a = filter_slice(stance_df, selected_model_A, period_1[0], period_1[1], domains_1)
stance_b = filter_slice(stance_df, selected_model_B, period_2[0], period_2[1], domains_2)
themes_a = filter_slice(themes_df, selected_model_A, period_1[0], period_1[1], domains_1)
themes_b = filter_slice(themes_df, selected_model_B, period_2[0], period_2[1], domains_2)
meso_a   = filter_slice(meso_df,   selected_model_A, period_1[0], period_1[1], domains_1)
meso_b   = filter_slice(meso_df,   selected_model_B, period_2[0], period_2[1], domains_2)

# Denominators (relevant articles)
total_a = total_articles_from_stance(stance_a)
total_b = total_articles_from_stance(stance_b)

# Aggregate counts
themes_a_counts = themes_counts(themes_a).rename(columns={"articles": "articles_1"})
themes_b_counts = themes_counts(themes_b).rename(columns={"articles": "articles_2"})
meso_a_counts   = meso_counts(meso_a).rename(columns={"articles": "articles_1"})
meso_b_counts   = meso_counts(meso_b).rename(columns={"articles": "articles_2"})

# ------------------------------------------------------------
# Themes contrast setup
# ------------------------------------------------------------
themes_contrast = pd.merge(themes_a_counts, themes_b_counts, on="narrative theme", how="outer").fillna(0)
if not themes_contrast.empty:
    themes_contrast["articles_1"] = themes_contrast["articles_1"].astype(int)
    themes_contrast["articles_2"] = themes_contrast["articles_2"].astype(int)
    themes_contrast["prevalence_1"] = (themes_contrast["articles_1"] / total_a) if total_a > 0 else 0.0
    themes_contrast["prevalence_2"] = (themes_contrast["articles_2"] / total_b) if total_b > 0 else 0.0
    themes_contrast["diff_prevalence"] = themes_contrast["prevalence_2"] - themes_contrast["prevalence_1"]
    themes_contrast["support_articles"] = themes_contrast["articles_1"] + themes_contrast["articles_2"]

# ------------------------------------------------------------
# Meso narratives contrast setup
# ------------------------------------------------------------
meso_contrast = pd.merge(meso_a_counts, meso_b_counts, on="meso narrative", how="outer").fillna(0)
if not meso_contrast.empty:
    meso_contrast["articles_1"] = meso_contrast["articles_1"].astype(int)
    meso_contrast["articles_2"] = meso_contrast["articles_2"].astype(int)
    meso_contrast["prevalence_1"] = (meso_contrast["articles_1"] / total_a) if total_a > 0 else 0.0
    meso_contrast["prevalence_2"] = (meso_contrast["articles_2"] / total_b) if total_b > 0 else 0.0
    meso_contrast["diff_prevalence"] = meso_contrast["prevalence_2"] - meso_contrast["prevalence_1"]
    meso_contrast["support_articles"] = meso_contrast["articles_1"] + meso_contrast["articles_2"]

# If both empty after filtering, stop
if (themes_contrast is None or themes_contrast.empty) and (meso_contrast is None or meso_contrast.empty):
    st.info("No themes or meso narratives found for the selected filters.")
    st.stop()

# Legend/summary
legend_html = f"""
<div style="display:flex;align-items:center;gap:18px;flex-wrap:wrap;margin:6px 0 14px;">
  <div style="display:flex;align-items:center;gap:6px;">
    <span style="display:inline-block;width:14px;height:14px;background:#d7191c;border:1px solid #999;border-radius:2px;"></span>
    <span><strong>Filter A</strong></span>
    <span style="color:#666;">{period_1[0]} → {period_1[1]} | Domains: {', '.join(sorted(domains_1)) if domains_1 else 'All'} | Model: {selected_model_A}</span>
  </div>
  <div style="display:flex;align-items:center;gap:6px;">
    <span style="display:inline-block;width:14px;height:14px;background:#2c7bb6;border:1px solid #999;border-radius:2px;"></span>
    <span><strong>Filter B</strong></span>
    <span style="color:#666;">{period_2[0]} → {period_2[1]} | Domains: {', '.join(sorted(domains_2)) if domains_2 else 'All'} | Model: {selected_model_B}</span>
  </div>
</div>
"""
st.markdown(legend_html, unsafe_allow_html=True)

# ------------------------------------------------------------
# Plot: Themes diverging bar (B minus A)
# ------------------------------------------------------------
DEFAULT_THEMES = [
    "EU migration to and from the UK",
    "international students in higher education",
    "legal vs. illegal immigration",
    "migrants and crimes",
    "migrants and housing",
    "detention and deportation of migrants",
    "migrants and human rights",
    "migrants and national identity",
    "migrants and racism/xenophobia",
    "migrants, economy, and labour market",
    "small boats and Channel crossings",
    "work visas and sponsorship",
    "migrants and healthcare system",
    "public opinion on migration",
]

st.subheader("Contrast in Narrative Themes (Filter B minus Filter A)")

if not themes_contrast.empty:
    overall_themes = themes_contrast.sort_values("support_articles", ascending=False)["narrative theme"].tolist()
    
    selected_themes = st.multiselect(
        "Select themes",
        options=overall_themes,
        default=[t for t in DEFAULT_THEMES if t in overall_themes],
        help="Choose which themes to include in the contrast chart. All selected themes will be displayed.",
    )

    if selected_themes:
        plot_df = themes_contrast[themes_contrast["narrative theme"].isin(selected_themes)].copy()
            
        melt_themes = plot_df[["narrative theme", "prevalence_1", "prevalence_2", "diff_prevalence"]].copy().reset_index(drop=True)

        melt_themes = melt_themes.melt(
            id_vars=["narrative theme", "diff_prevalence"],
            value_vars=["prevalence_1", "prevalence_2"],
            var_name="side_var",
            value_name="prevalence"
        )
        melt_themes["side_key"] = melt_themes["side_var"].map({"prevalence_1": "Filter A", "prevalence_2": "Filter B"})
        melt_themes["signed_prev"] = melt_themes.apply(lambda r: -r["prevalence"] if r["side_key"] == "Filter A" else r["prevalence"], axis=1)

        theme_order = melt_themes.drop_duplicates("narrative theme").sort_values("diff_prevalence")["narrative theme"].tolist()
        max_val_t = float(melt_themes["prevalence"].max() or 0.0)
        x_limit_t = (max_val_t * 1.15) if max_val_t > 0 else 0.05

        themes_bar = alt.Chart(melt_themes).mark_bar().encode(
            x=alt.X("signed_prev:Q", title="Prevalence (% of relevant articles)", scale=alt.Scale(domain=[-x_limit_t, x_limit_t], nice=False), axis=alt.Axis(format=".0%")),
            y=alt.Y("narrative theme:N", sort=theme_order, title="Theme", axis=alt.Axis(labelLimit=0, labelOverlap=False, titlePadding=120)),
            color=alt.Color("side_key:N", title=None, scale=alt.Scale(domain=["Filter A", "Filter B"], range=["#d7191c", "#2c7bb6"]), legend=alt.Legend(orient="top")),
            tooltip=[
                alt.Tooltip("narrative theme:N", title="Theme"),
                alt.Tooltip("side_key:N", title="Filter"),
                alt.Tooltip("prevalence:Q", title="Prevalence", format=".1%"),
                alt.Tooltip("diff_prevalence:Q", title="(B − A) pp", format=".1%"),
            ],
        )
        st.altair_chart(themes_bar, width="stretch")
    else:
        st.info("Please select at least one theme to generate the chart.")

# ------------------------------------------------------------
# Plot: Meso narratives diverging bar (B minus A)
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

st.subheader("Contrast in Meso Narratives (Filter B minus Filter A)")

if not meso_contrast.empty:
    overall_meso = meso_contrast.sort_values("support_articles", ascending=False)["meso narrative"].tolist()
    
    selected_meso = st.multiselect(
        "Select meso narratives",
        options=overall_meso,
        default=[m for m in DEFAULT_MESO_NARRATIVES if m in overall_meso],
        help="Choose which meso narratives to include in the contrast chart. All selected narratives will be displayed.",
    )

    if selected_meso:
        meso_plot = meso_contrast[meso_contrast["meso narrative"].isin(selected_meso)].copy()
            
        melt_meso = meso_plot[["meso narrative", "prevalence_1", "prevalence_2", "diff_prevalence"]].copy().reset_index(drop=True)
        melt_meso = melt_meso.melt(
            id_vars=["meso narrative", "diff_prevalence"],
            value_vars=["prevalence_1", "prevalence_2"],
            var_name="side_var",
            value_name="prevalence"
        )
        melt_meso["side_key"] = melt_meso["side_var"].map({"prevalence_1": "Filter A", "prevalence_2": "Filter B"})
        melt_meso["signed_prev"] = melt_meso.apply(lambda r: -r["prevalence"] if r["side_key"] == "Filter A" else r["prevalence"], axis=1)

        meso_order = melt_meso.drop_duplicates("meso narrative").sort_values("diff_prevalence")["meso narrative"].tolist()
        max_val_m = float(melt_meso["prevalence"].max() or 0.0)
        x_limit_m = (max_val_m * 1.15) if max_val_m > 0 else 0.05

        meso_bar = alt.Chart(melt_meso).mark_bar().encode(
            x=alt.X("signed_prev:Q", title="Prevalence (% of relevant articles)", scale=alt.Scale(domain=[-x_limit_m, x_limit_m], nice=False), axis=alt.Axis(format=".0%")),
            y=alt.Y("meso narrative:N", sort=meso_order, title="Meso Narrative", axis=alt.Axis(labelLimit=0, labelOverlap=False, titlePadding=220)),
            color=alt.Color("side_key:N", title=None, scale=alt.Scale(domain=["Filter A", "Filter B"], range=["#d7191c", "#2c7bb6"]), legend=alt.Legend(orient="top")),
            tooltip=[
                alt.Tooltip("meso narrative:N", title="Meso Narrative"),
                alt.Tooltip("side_key:N", title="Filter"),
                alt.Tooltip("prevalence:Q", title="Prevalence", format=".1%"),
                alt.Tooltip("diff_prevalence:Q", title="(B − A) pp", format=".1%"),
            ],
        )
        st.altair_chart(meso_bar, width="stretch")
    else:
        st.info("Please select at least one meso narrative to generate the chart.")

# ------------------------------------------------------------
# Raw data expanders
# ------------------------------------------------------------
if not themes_contrast.empty:
    with st.expander("Raw Themes Contrast Data"):
        st.dataframe(themes_contrast[[
            "narrative theme",
            "articles_1", "articles_2",
            "prevalence_1", "prevalence_2",
            "diff_prevalence",
            "support_articles",
        ]].sort_values("diff_prevalence", ascending=False))

if not meso_contrast.empty:
    with st.expander("Raw Meso Contrast Data"):
        st.dataframe(meso_contrast[[
            "meso narrative",
            "articles_1", "articles_2",
            "prevalence_1", "prevalence_2",
            "diff_prevalence",
            "support_articles",
        ]].sort_values("diff_prevalence", ascending=False))
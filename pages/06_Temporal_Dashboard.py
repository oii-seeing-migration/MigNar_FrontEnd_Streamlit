import os
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st
from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()


st.set_page_config(
    page_title="Temporal Dashboard",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png",
)



st.title("Temporal Dashboard")

# -------------------------------------
# Load precomputed aggregates (Parquet)
# -------------------------------------
DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_monthly.parquet")
THEMES_PATH = os.path.join(DATA_DIR, "themes_monthly.parquet")
MESO_PATH = os.path.join(DATA_DIR, "meso_monthly.parquet")

EXCLUDED_SOURCES_DEFAULT = {
    "US Congress (All)",
    "US Congress (Rep)",
    "US Congress (Dem)",
    "UK Parliament (Lab)",
    "UK Parliament (Con)",
    "UK Parliament (Reform)",
    "UK Parliament (Green)",
    "UK Parliament (SNP)",
    "UK Parliament (LD)",
}

from lib.data_loader import load_parquets
stance_df, themes_df, meso_df = load_parquets()



if stance_df.empty and themes_df.empty and meso_df.empty:
    st.error(
        f"No aggregates found in {DATA_DIR}. "
        "Ensure stance_monthly.parquet, themes_monthly.parquet, and meso_monthly.parquet exist."
    )
    st.stop()

# -------------------------------------
# Helpers
# -------------------------------------
def _time_axis_and_scale(freq_label: str):
    if freq_label == "Weekly":
        axis = alt.Axis(title="Period", format="%b %d, %Y", tickCount={"interval": "week", "step": 1})
        scale = alt.Scale(nice={"interval": "week", "step": 1})
    elif freq_label == "Monthly":
        axis = alt.Axis(title="Period", format="%b %Y", tickCount={"interval": "month", "step": 1})
        scale = alt.Scale(nice={"interval": "month", "step": 1})
    else:
        axis = alt.Axis(title="Period", format="%Y", tickCount={"interval": "year", "step": 1})
        scale = alt.Scale(nice={"interval": "year", "step": 1})
    return axis, scale


def _freq_to_pandas(freq_label: str) -> str:
    return {"Weekly": "W-MON", "Monthly": "M", "Yearly": "Y-DEC"}[freq_label]


def add_period(df: pd.DataFrame, freq_label: str) -> pd.DataFrame:
    if df.empty or "month" not in df.columns:
        return df
    out = df.copy()
    freq = _freq_to_pandas(freq_label)
    out["period"] = out["month"].dt.to_period(freq).dt.start_time
    return out


def available_models_union(*dfs):
    models = set()
    for df in dfs:
        if not df.empty and "model" in df.columns:
            models.update(df["model"].dropna().unique().tolist())
    return sorted([m for m in models if m])


def model_filter(df: pd.DataFrame, model: str) -> pd.DataFrame:
    if df.empty or "model" not in df.columns:
        return df
    return df[df["model"] == model].copy()


def date_filter(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    if df.empty or "month" not in df.columns:
        return df
    return df[(df["month"].dt.date >= start_date) & (df["month"].dt.date <= end_date)].copy()


def domain_filter(df: pd.DataFrame, selected_domains: list[str]) -> pd.DataFrame:
    if df.empty or "source_domain" not in df.columns:
        return df
    if selected_domains is None:
        return df
    if len(selected_domains) == 0:
        return df.iloc[0:0].copy()
    return df[df["source_domain"].isin(selected_domains)].copy()


def by_version(df: pd.DataFrame, selected_version) -> pd.DataFrame:
    if df.empty or selected_version == "(All versions)" or "version" not in df.columns:
        return df
    v = pd.to_numeric(df["version"], errors="coerce")
    return df[v == int(selected_version)].copy()


# -------------------------------------
# Sidebar controls
# -------------------------------------
models = available_models_union(stance_df, themes_df, meso_df)
default_model = "Ensemble" if "Ensemble" in models else (models[0] if models else None)

if not models:
    st.error("No models found in aggregates.")
    st.stop()

selected_model = st.sidebar.selectbox(
    "Model",
    options=models,
    index=models.index(default_model) if default_model in models else 0,
    help="Filters all temporal series to a single model. 'Ensemble' uses consensus outputs.",
)

st.sidebar.markdown("---")

stance_m = model_filter(stance_df, selected_model)
themes_m = model_filter(themes_df, selected_model)
meso_m = model_filter(meso_df, selected_model)

date_series = []
for df in (stance_m, themes_m, meso_m):
    if not df.empty and "month" in df.columns:
        date_series.append(df["month"])

if date_series:
    all_months = pd.concat(date_series, ignore_index=True).dropna()
    min_dt = all_months.min().date()
    max_dt = all_months.max().date()
else:
    st.error("No valid 'month' column found for the selected model.")
    st.stop()

freq_label = st.sidebar.selectbox(
    "Granularity",
    ["Monthly", "Yearly"],
    index=1,
    help="Controls temporal aggregation of lines. Monthly shows finer variation; Yearly shows long-run trends.",
)

y_axis_metric = st.sidebar.radio(
    "Y-Axis Metric",
    options=["Percentage", "Count"],
    index=0,
    help="Display chart lines as a percentage of total relevant articles or as a raw article count.",
)

if y_axis_metric == "Percentage":
    y_field = "prevalence:Q"
    y_format = ".0%"
    y_title = "Prevalence"
else:
    y_field = "articles:Q"
    y_format = "d"
    y_title = "Article Count"

picked = st.sidebar.date_input(
    "Date range",
    value=(date(2016, 1, 1), max_dt),
    min_value=min_dt,
    max_value=max_dt,
    help="Limits all temporal series to periods whose month lies inside this interval.",
)

if isinstance(picked, tuple) and len(picked) == 2:
    start_date, end_date = picked
else:
    start_date = end_date = picked

stance_f_all = date_filter(stance_m, start_date, end_date)
themes_f_all = date_filter(themes_m, start_date, end_date)
meso_f_all = date_filter(meso_m, start_date, end_date)

domains = set()
for df in (stance_f_all, themes_f_all, meso_f_all):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains])

default_narrative_domains = [d for d in domains if d not in EXCLUDED_SOURCES_DEFAULT]
default_stance_domains = [
    d for d in domains
    if d.startswith("UK Parliament") or d.startswith("US Congress")
]

selected_stance_domains = st.sidebar.multiselect(
    "Stance source domain",
    options=domains,
    default=default_stance_domains,
    help="Filters the stance chart only. Defaults to UK Parliament and US Congress domains.",
)

selected_narrative_domains = st.sidebar.multiselect(
    "Narratives source domain",
    options=domains,
    default=default_narrative_domains,
    help="Filters the theme and meso narrative charts only.",
)

stance_f = domain_filter(stance_f_all, selected_stance_domains)
themes_f = domain_filter(themes_f_all, selected_narrative_domains)
meso_f = domain_filter(meso_f_all, selected_narrative_domains)

stance_p = add_period(stance_f, freq_label)
themes_p = add_period(themes_f, freq_label)
meso_p = add_period(meso_f, freq_label)

st.sidebar.markdown("---")

available_versions = sorted(
    set(
        (
            list(pd.to_numeric(themes_df["version"], errors="coerce").dropna().astype(int).unique().tolist())
            if ("version" in themes_df.columns and not themes_df.empty)
            else []
        )
        + (
            list(pd.to_numeric(meso_df["version"], errors="coerce").dropna().astype(int).unique().tolist())
            if ("version" in meso_df.columns and not meso_df.empty)
            else []
        )
    )
)

if available_versions:
    version_options = ["(All versions)"] + available_versions
    selected_version = st.sidebar.selectbox(
        "Taxonomy Version",
        options=version_options,
        index=len(version_options) - 1,
        help="Filters Theme and Meso temporal series by taxonomy revision. '(All versions)' keeps all revisions.",
    )
else:
    selected_version = "(All versions)"

themes_p = by_version(themes_p, selected_version)
meso_p = by_version(meso_p, selected_version)

# -------------------------------------
# Build denominators for narratives only
# denominator = relevant stance articles in narrative domains
# -------------------------------------
stance_for_narratives = domain_filter(stance_f_all, selected_narrative_domains)
stance_for_narratives_p = add_period(stance_for_narratives, freq_label)

if not stance_for_narratives_p.empty and "stance" in stance_for_narratives_p.columns:
    narrative_totals_per_period = (
        stance_for_narratives_p[
            stance_for_narratives_p["stance"].isin(["OPEN", "RESTRICTIVE", "NEUTRAL"])
        ]
        .groupby("period", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "total"})
    )
else:
    narrative_totals_per_period = pd.DataFrame(columns=["period", "total"])

# -------------------------------------
# Stance
# -------------------------------------
st.subheader("Stance Toward Migration Over Time (by Domain)")

if stance_p.empty:
    st.info("No stance data in selected filters.")
else:
    stance_sum = (
        stance_p.groupby(["period", "source_domain", "stance"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )

    pivot = stance_sum.pivot_table(
        index=["period", "source_domain"],
        columns="stance",
        values="articles",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    for col in ["OPEN", "RESTRICTIVE", "NEUTRAL"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["total"] = pivot["OPEN"] + pivot["RESTRICTIVE"] + pivot["NEUTRAL"]
    pivot["stance_score"] = pivot.apply(
        lambda r: (r["OPEN"] - r["RESTRICTIVE"]) / r["total"] if r["total"] > 0 else None,
        axis=1,
    )

    stance_ts = pivot.dropna(subset=["stance_score"]).copy()

    if selected_stance_domains:
        stance_ts = stance_ts[stance_ts["source_domain"].isin(selected_stance_domains)].copy()

    if stance_ts.empty:
        st.info("No stance series to plot after filtering.")
    else:
        if freq_label == "Yearly":
            stance_ts["period_plot"] = stance_ts["period"] + pd.DateOffset(months=6)
        elif freq_label == "Monthly":
            stance_ts["period_plot"] = stance_ts["period"] + pd.DateOffset(days=15)
        else:
            stance_ts["period_plot"] = stance_ts["period"] + pd.DateOffset(days=3, hours=12)

        axis_x, scale_x = _time_axis_and_scale(freq_label)
        stance_line = alt.Chart(stance_ts).mark_line(point=True, interpolate="monotone").encode(
            x=alt.X("period_plot:T", axis=axis_x, scale=scale_x),
            y=alt.Y(
                "stance_score:Q",
                title="Stance Score",
                scale=alt.Scale(domain=(-1, 1), clamp=True),
            ),
            color=alt.Color("source_domain:N", title="Domain"),
            tooltip=[
                alt.Tooltip("source_domain:N", title="Domain"),
                alt.Tooltip("period:T", title="Period"),
                alt.Tooltip("stance_score:Q", title="Score", format=".2f"),
                alt.Tooltip("OPEN:Q", title="OPEN"),
                alt.Tooltip("RESTRICTIVE:Q", title="RESTRICTIVE"),
                alt.Tooltip("NEUTRAL:Q", title="NEUTRAL"),
                alt.Tooltip("total:Q", title="Total"),
            ],
        ).properties(title=f"Stance Score Over Time ({freq_label}, Model: {selected_model})", height=420)

        st.altair_chart(stance_line, width="stretch")

# -------------------------------------
# Themes
# -------------------------------------
DEFAULT_THEMES = [
    "EU migration to and from the UK",
    # "international students in higher education",
    # "legal vs. illegal immigration",
    "migrants and crimes",
    # "migrants and housing",
    "detention and deportation of migrants",
    "migrants and human rights",
    # "migrants and national identity",
    # "migrants and racism/xenophobia",
    "migrants, economy, and labour market",
    "small boats and Channel crossings",
    "work visas and sponsorship",
    # "migrants and healthcare system",
    "public opinion on migration",
]


st.subheader("Themes Over Time")

if themes_p.empty or narrative_totals_per_period.empty:
    st.info("No theme data in selected filters.")
else:
    themes_counts = (
        themes_p.groupby(["period", "theme"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )

    themes_ts = themes_counts.merge(narrative_totals_per_period, on="period", how="left")
    themes_ts["prevalence"] = themes_ts.apply(
        lambda r: (r["articles"] / r["total"]) if pd.notna(r["total"]) and r["total"] > 0 else 0.0,
        axis=1,
    )

    overall_themes = (
        themes_ts.groupby("theme")["articles"]
        .sum()
        .sort_values(ascending=False)
        .head(49)
        .index.tolist()
    )

    selected_themes = st.multiselect(
        "Select themes",
        options=overall_themes,
        default=DEFAULT_THEMES,
        help="Choose which themes to plot over time. If nothing is selected, the top 8 themes by volume are used.",
    )

    if not selected_themes:
        selected_themes = overall_themes[:8]

    plot_themes = themes_ts[themes_ts["theme"].isin(selected_themes)].copy()

    if freq_label == "Yearly":
        plot_themes["period_plot"] = plot_themes["period"] + pd.DateOffset(months=6)
    elif freq_label == "Monthly":
        plot_themes["period_plot"] = plot_themes["period"] + pd.DateOffset(days=15)
    else:
        plot_themes["period_plot"] = plot_themes["period"] + pd.DateOffset(days=3, hours=12)

    axis_x, scale_x = _time_axis_and_scale(freq_label)
    line = alt.Chart(plot_themes).mark_line(point=True, interpolate="monotone").encode(
        x=alt.X("period_plot:T", axis=axis_x, scale=scale_x),
        y=alt.Y(y_field, axis=alt.Axis(format=y_format), title=y_title),
        color=alt.Color(
            "theme:N",
            title="Theme",
            legend=alt.Legend(labelLimit=1000),
        ),
        tooltip=[
            alt.Tooltip("theme:N", title="Theme"),
            alt.Tooltip("period:T", title="Period"),
            alt.Tooltip("articles:Q", title="# Articles"),
            alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
        ],
    ).properties(title=f"Theme {y_title} Over Time ({freq_label}, Model: {selected_model})")

    st.altair_chart(line, width="stretch")

# ------------------------------------------------------------
# Meso narratives
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

st.subheader("Meso Narratives Over Time")

if meso_p.empty or narrative_totals_per_period.empty:
    st.info("No meso narrative data in selected filters.")
else:
    meso_counts = (
        meso_p.groupby(["period", "meso_narrative"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )

    meso_ts = meso_counts.merge(narrative_totals_per_period, on="period", how="left")
    meso_ts["prevalence"] = meso_ts.apply(
        lambda r: (r["articles"] / r["total"]) if pd.notna(r["total"]) and r["total"] > 0 else 0.0,
        axis=1,
    )

    top_meso = (
        meso_ts.groupby("meso_narrative")["articles"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )

    available_meso_options = meso_ts["meso_narrative"].dropna().unique().tolist()
    
    selected_meso = st.multiselect(
        "Select meso narratives",
        options=available_meso_options,
        default=[m for m in DEFAULT_MESO_NARRATIVES if m in available_meso_options],
        help="Choose which meso narratives to plot over time. If nothing is selected, the top narratives by volume are used.",
    )

    if not selected_meso:
        # Fallback to top volume narratives if selection is cleared
        selected_meso = top_meso 

    plot_meso = meso_ts[meso_ts["meso_narrative"].isin(selected_meso)].copy()

    if freq_label == "Yearly":
        plot_meso["period_plot"] = plot_meso["period"] + pd.DateOffset(months=6)
    elif freq_label == "Monthly":
        plot_meso["period_plot"] = plot_meso["period"] + pd.DateOffset(days=15)
    else:
        plot_meso["period_plot"] = plot_meso["period"] + pd.DateOffset(days=3, hours=12)

    axis_x, scale_x = _time_axis_and_scale(freq_label)
    meso_line = alt.Chart(plot_meso).mark_line(point=True, interpolate="monotone").encode(
        x=alt.X("period_plot:T", axis=axis_x, scale=scale_x),
        y=alt.Y(y_field, axis=alt.Axis(format=y_format), title=y_title),
        color=alt.Color("meso_narrative:N", title="Meso Narrative"),
        tooltip=[
            alt.Tooltip("meso_narrative:N", title="Meso Narrative"),
            alt.Tooltip("period:T", title="Period"),
            alt.Tooltip("articles:Q", title="# Articles"),
            alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
        ],
    ).properties(title=f"Meso Narrative {y_title} Over Time ({freq_label}, Model: {selected_model})")

    st.altair_chart(meso_line, width="stretch")

with st.expander("Underlying Data Snapshots"):
    st.write("Themes (filtered):", themes_f.head(100))
    st.write("Stance (filtered):", stance_f.head(100))
    st.write("Meso (filtered):", meso_f.head(100))
    st.write("Narrative denominators:", narrative_totals_per_period.head(100))
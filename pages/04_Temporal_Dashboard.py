import os
import streamlit as st
import altair as alt
import pandas as pd
from datetime import date

st.set_page_config(page_title="Temporal Dashboard",
                   layout="wide",
                   page_icon=".streamlit/static/MigNar_icon.png")

# # Sidebar navigation
# st.sidebar.subheader("Navigation")
# try:
#     st.sidebar.page_link("navigation_page.py", label="Navigation Page", icon="🧭")
#     st.sidebar.page_link("pages/01_Narratives_on_Articles.py", label="Narratives on Articles", icon="📰")
#     st.sidebar.page_link("pages/02_Aggregative_Dashboard.py", label="Aggregative Dashboard", icon="📊")
#     st.sidebar.page_link("pages/03_Contrastive_Dashboard.py", label="Contrastive Dashboard", icon="⚖️")
#     st.sidebar.page_link("pages/04_Temporal_Dashboard.py", label="Temporal Dashboard", icon="⏱")
# except Exception:
#     pass

st.title("Temporal Dashboard")

# -------------------------------------
# Load precomputed aggregates (Parquet)
# -------------------------------------
DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_daily.parquet")
THEMES_PATH = os.path.join(DATA_DIR, "themes_daily.parquet")
MESO_PATH   = os.path.join(DATA_DIR, "meso_daily.parquet")  # not used directly here

@st.cache_data(ttl="1h", show_spinner=True)
def load_parquets(stance_fp: str, themes_fp: str, meso_fp: str):
    def _read_parquet(fp):
        if not os.path.exists(fp):
            return pd.DataFrame()
        df = pd.read_parquet(fp)
        if "day" in df.columns:
            df["day"] = pd.to_datetime(df["day"], errors="coerce")
        for col in ("source_domain", "model"):
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)
        if "count" in df.columns:
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
        return df

    stance_df = _read_parquet(stance_fp)
    themes_df = _read_parquet(themes_fp)
    meso_df   = _read_parquet(meso_fp)
    return stance_df, themes_df, meso_df

stance_df, themes_df, meso_df = load_parquets(STANCE_PATH, THEMES_PATH, MESO_PATH)

if stance_df.empty and themes_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Ensure stance_daily.parquet and themes_daily.parquet exist.")
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
    else:  # Yearly
        axis = alt.Axis(title="Period", format="%Y", tickCount={"interval": "year", "step": 1})
        scale = alt.Scale(nice={"interval": "year", "step": 1})
    return axis, scale

def _freq_to_pandas(freq_label: str) -> str:
    # Use pandas-supported period codes:
    # - Weekly anchored to Monday
    # - Monthly period ('M')
    # - Yearly period ('A-DEC')
    return {"Weekly": "W-MON", "Monthly": "M", "Yearly": "A-DEC"}[freq_label]

def add_period(df: pd.DataFrame, freq_label: str) -> pd.DataFrame:
    if df.empty or "day" not in df.columns:
        return df
    freq = _freq_to_pandas(freq_label)
    out = df.copy()
    # Convert to Period, then to start-of-period Timestamp (avoids 'MS' unsupported error)
    out["period"] = out["day"].dt.to_period(freq).dt.start_time
    return out

def available_models_union(*dfs):
    models = set()
    for df in dfs:
        if not df.empty and "model" in df.columns:
            models.update(df["model"].dropna().unique().tolist())
    return sorted([m for m in models if m])

# -------------------------------------
# Sidebar controls (Model, Time, Domain)
# -------------------------------------
# Model selector
models = available_models_union(stance_df, themes_df)
default_model = "gpt-oss-20b" if "gpt-oss-20b" in models else (models[0] if models else None)
if not models:
    st.error("No models found in aggregates.")
    st.stop()
selected_model = st.sidebar.selectbox("Model", options=models, index=models.index(default_model) if default_model in models else 0)

# Date bounds across selected model
def model_filter(df):
    if df.empty or "model" not in df.columns:
        return df
    return df[df["model"] == selected_model].copy()

stance_m = model_filter(stance_df)
themes_m = model_filter(themes_df)
meso_m   = model_filter(meso_df)

date_series = []
for df in (stance_m, themes_m):
    if not df.empty and "day" in df.columns:
        date_series.append(df["day"])
if date_series:
    all_days = pd.concat(date_series).dropna()
    min_dt, max_dt = all_days.min().date(), all_days.max().date()
else:
    st.error("No valid 'day' column found for the selected model.")
    st.stop()

# Granularity
freq_label = st.sidebar.selectbox("Granularity", ["Weekly", "Monthly", "Yearly"], index=2)

# Date picker
picked = st.sidebar.date_input("Date range", value=(date(2000, 1, 1), max_dt), min_value=min_dt, max_value=max_dt)
if isinstance(picked, tuple) and len(picked) == 2:
    start_date, end_date = picked
else:
    start_date = end_date = picked

def date_filter(df: pd.DataFrame):
    if df.empty or "day" not in df.columns:
        return df
    return df[(df["day"].dt.date >= start_date) & (df["day"].dt.date <= end_date)].copy()

stance_f = date_filter(stance_m)
themes_f = date_filter(themes_m)
meso_f   = date_filter(meso_m)

# Domain filter (defaults to all domains in filtered range)
domains = set()
for df in (stance_f, themes_f, meso_f):
    if not df.empty and "source_domain" in df.columns:
        domains.update(df["source_domain"].dropna().unique().tolist())
domains = sorted([d for d in domains if d])
default_domains = ['UK Parliament (Con)','UK Parliament (Lab)','US Congress (Rep)','US Congress (Dem)', 'dailymail.co.uk','telegraph.co.uk', 'theguardian.com','bbc.co.uk','independent.co.uk','thesun.co.uk','mirror.co.uk']
default_domains = [d for d in default_domains if d in domains]
selected_domains = st.sidebar.multiselect("Source domain", options=domains,
                                          default=default_domains)

def domain_filter(df: pd.DataFrame):
    if df.empty or not selected_domains or "source_domain" not in df.columns:
        return df
    return df[df["source_domain"].isin(selected_domains)].copy()

stance_f = domain_filter(stance_f)
themes_f = domain_filter(themes_f)
meso_f   = domain_filter(meso_f)

# Add period column post-filter
stance_p = add_period(stance_f, freq_label)
themes_p = add_period(themes_f, freq_label)
meso_p   = add_period(meso_f, freq_label)

# -------------------------------------
# Build denominators (total relevant per period)
# -------------------------------------
# Total relevant articles per period from stance counts (sum across labels)
if not stance_p.empty:
    totals_per_period = (
        stance_p.groupby("period", as_index=False)["count"]
        .sum()
        .rename(columns={"count": "total"})
    )
else:
    totals_per_period = pd.DataFrame(columns=["period", "total"])


# -------------------------------------
# Stance: temporal stance-score lines (by domain)
# Score = (OPEN - RESTRICTIVE) / (OPEN + RESTRICTIVE + NEUTRAL)
# -------------------------------------
st.subheader("Stance Toward Migration Over Time (by Domain)")
if stance_p.empty:
    st.info("No stance data in selected filters.")
else:
    # Sum per period x domain x stance
    stance_sum = (
        stance_p.groupby(["period", "source_domain", "stance"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    # Pivot to OPEN/RESTRICTIVE/NEUTRAL columns
    pivot = stance_sum.pivot_table(
        index=["period", "source_domain"],
        columns="stance",
        values="articles",
        aggfunc="sum",
        fill_value=0
    ).reset_index()

    for col in ["OPEN", "RESTRICTIVE", "NEUTRAL"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot["total"] = pivot["OPEN"] + pivot["RESTRICTIVE"] + pivot["NEUTRAL"]
    pivot["stance_score"] = pivot.apply(
        lambda r: (r["OPEN"] - r["RESTRICTIVE"]) / r["total"] if r["total"] > 0 else None, axis=1
    )
    stance_ts = pivot.dropna(subset=["stance_score"]).copy()

    # Keep only selected domains (already filtered, but safe)
    if selected_domains:
        stance_ts = stance_ts[stance_ts["source_domain"].isin(selected_domains)].copy()

    if stance_ts.empty:
        st.info("No stance series to plot after filtering.")
    else:
        axis_x, scale_x = _time_axis_and_scale(freq_label)
        stance_line = alt.Chart(stance_ts).mark_line(point=True).encode(
            x=alt.X("period:T", axis=axis_x, scale=scale_x),
            y=alt.Y("stance_score:Q", title="Stance Score", scale=alt.Scale(domain=(-1, 1), clamp=True)),
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
        st.altair_chart(stance_line, use_container_width=True)




# -------------------------------------
# Themes: temporal prevalence lines
# -------------------------------------
if themes_p.empty or totals_per_period.empty:
    st.info("No theme data in selected filters.")
else:
    themes_counts = (
        themes_p.groupby(["period", "theme"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    themes_ts = themes_counts.merge(totals_per_period, on="period", how="left")
    themes_ts["prevalence"] = themes_ts.apply(
        lambda r: (r["articles"] / r["total"]) if r["total"] and r["total"] > 0 else 0.0, axis=1
    )

    # Top themes overall in the window to drive selection
    overall_themes = (
        themes_ts.groupby("theme")["articles"]
        .sum()
        .sort_values(ascending=False)
        .head(30)
        .index.tolist()
    )
    selected_themes = st.multiselect(
        "Select themes (empty = top 8 auto)",
        options=overall_themes,
        default=overall_themes[:8]
    )
    if not selected_themes:
        selected_themes = overall_themes[:8]
    plot_themes = themes_ts[themes_ts["theme"].isin(selected_themes)].copy()

    axis_x, scale_x = _time_axis_and_scale(freq_label)
    line = alt.Chart(plot_themes).mark_line(point=True).encode(
        x=alt.X("period:T", axis=axis_x, scale=scale_x),
        y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
        color=alt.Color("theme:N", title="Theme"),
        tooltip=[
            alt.Tooltip("theme:N", title="Theme"),
            alt.Tooltip("period:T", title="Period"),
            alt.Tooltip("articles:Q", title="# Articles"),
            alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
        ]
    ).properties(title=f"Theme Prevalence Over Time ({freq_label}, Model: {selected_model})")
    st.altair_chart(line, use_container_width=True)



# -------------------------------------
# Meso narratives: temporal prevalence lines
# -------------------------------------
st.subheader("Meso Narratives Over Time")
if meso_p.empty or totals_per_period.empty:
    st.info("No meso narrative data in selected filters.")
else:
    meso_counts = (
        meso_p.groupby(["period", "meso_narrative"], as_index=False)["count"]
        .sum()
        .rename(columns={"count": "articles"})
    )
    meso_ts = meso_counts.merge(totals_per_period, on="period", how="left")
    meso_ts["prevalence"] = meso_ts.apply(
        lambda r: (r["articles"] / r["total"]) if r["total"] and r["total"] > 0 else 0.0, axis=1
    )

    # Top 5 meso narratives in current window
    top_meso = (
        meso_ts.groupby("meso_narrative")["articles"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .index.tolist()
    )
    selected_meso = st.multiselect(
        "Select meso narratives (empty = top 5 auto)",
        options=meso_ts["meso_narrative"].dropna().unique().tolist(),
        default=top_meso
    )
    if not selected_meso:
        selected_meso = top_meso

    plot_meso = meso_ts[meso_ts["meso_narrative"].isin(selected_meso)].copy()

    axis_x, scale_x = _time_axis_and_scale(freq_label)
    meso_line = alt.Chart(plot_meso).mark_line(point=True).encode(
        x=alt.X("period:T", axis=axis_x, scale=scale_x),
        y=alt.Y("prevalence:Q", axis=alt.Axis(format=".0%"), title="Prevalence"),
        color=alt.Color("meso_narrative:N", title="Meso Narrative"),
        tooltip=[
            alt.Tooltip("meso_narrative:N", title="Meso Narrative"),
            alt.Tooltip("period:T", title="Period"),
            alt.Tooltip("articles:Q", title="# Articles"),
            alt.Tooltip("prevalence:Q", format=".1%", title="Prevalence"),
        ]
    ).properties(title=f"Meso Narrative Prevalence Over Time ({freq_label}, Model: {selected_model})")
    st.altair_chart(meso_line, use_container_width=True)





with st.expander("Underlying Data Snapshots"):
    st.write("Themes (filtered):", themes_f.head(1000))
    st.write("Stance (filtered):", stance_f.head(1000))
    st.write("Meso (filtered):", meso_f.head(1000))
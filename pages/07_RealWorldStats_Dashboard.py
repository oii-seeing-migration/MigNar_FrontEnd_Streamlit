import os
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.interpolate import PchipInterpolator
from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

st.set_page_config(page_title="Real-World Stats Dashboard", layout="wide")

from lib.real_world_stats import load_real_world_data, DATASETS_METADATA, DEFAULT_NARRATIVES, DEFAULT_INCLUDED_CATEGORIES

st.title("**Real-World Stats on Migration** (next to narratives)")

# -------------------------------------
# Load Precomputed Narrative Aggregates 
# -------------------------------------
from lib.data_loader import load_parquets
stance_df, themes_df, meso_df = load_parquets()

DATA_DIR = os.path.expanduser("./data")
if stance_df.empty and themes_df.empty and meso_df.empty:
    st.error(f"No aggregates found in {DATA_DIR}. Ensure parquets exist.")
    st.stop()

# Build Domain Options
all_domains = set()
for d in [stance_df, themes_df, meso_df]:
    if not d.empty and "source_domain" in d.columns:
        all_domains.update(d["source_domain"].dropna().unique().tolist())
all_domains = sorted(list(all_domains))

# Default Domain Clusters
UK_LEFT = ["theguardian.com", "mirror.co.uk", "independent.co.uk", "huffingtonpost.co.uk", "dailyrecord.co.uk", "thenational.scot", "heraldscotland.com"]
UK_RIGHT = ["telegraph.co.uk", "dailymail.co.uk", "express.co.uk", "thesun.co.uk", "spectator.co.uk", "thetimes.co.uk", "thescottishsun.co.uk"]
UK_LABOUR = ["UK Parliament (Lab)"]
UK_CONS = ["UK Parliament (Con)"]

# -------------------------------
# Sidebar / Global Controls
# -------------------------------
st.sidebar.header("Time Range (X-Axis)")

time_range = st.sidebar.slider("time range", min_value=2000, max_value=2030, value=(2016, 2026))

st.sidebar.markdown("---")

st.sidebar.header("Real-World Settings (Left Y-Axis)")
rw_stat_options = list(DATASETS_METADATA.keys())
selected_rw_stat = st.sidebar.selectbox("Real-World Stat Dataset", options=rw_stat_options, index=rw_stat_options.index("Offence Convictions")  if "Offence Convictions" in rw_stat_options else 0)

rw_data = load_real_world_data(selected_rw_stat, data_dir=os.path.join(DATA_DIR, "real-stats"))

if not rw_data.empty:
    # 1. Get the configured defaults for this dataset
    configured_defaults = DEFAULT_INCLUDED_CATEGORIES.get(selected_rw_stat, [])
    
    # 2. Filter out any defaults that aren't actually in the dataframe's columns
    valid_defaults = [cat for cat in configured_defaults if cat in rw_data.columns]
    
    # 3. Fallback: If no valid defaults found, just pick the first column
    if not valid_defaults:
        valid_defaults = list(rw_data.columns[:1])
        
    selected_categories = st.sidebar.multiselect("Included Line Categories", options=rw_data.columns, default=valid_defaults)
else:
    selected_categories = []


st.sidebar.markdown("---")
st.sidebar.header("Narrative Settings (Right Y-Axis)")

models = list(set(stance_df["model"].dropna().unique().tolist() + themes_df["model"].dropna().unique().tolist()))
default_model = "Ensemble" if "Ensemble" in models else (models[0] if models else "")
selected_model = st.sidebar.selectbox("Extraction Model", options=models, index=models.index(default_model) if default_model else 0)

versions = ["(All versions)"] + sorted([str(int(v)) for v in themes_df["version"].dropna().unique() if pd.notna(v)])
selected_version = st.sidebar.selectbox("Taxonomy Version", options=versions, index=len(versions)-1)
y_axis_metric = st.sidebar.radio("Narrative Metric", options=["Percentage (Prevalence)", "Count (Articles)"], index=0)


if "Percentage" in y_axis_metric:
    narr_y_range = st.sidebar.slider("Narrative Y-Axis Range (%)", min_value=0, max_value=100, value=(0, 60), step=5)
    narr_y_min = narr_y_range[0] / 100.0
    narr_y_max = narr_y_range[1] / 100.0


NEW_MIN_COUNT = st.sidebar.number_input(
    "Min count for narratives",
    min_value=1,
    max_value=500,
    value=5,
    step=1,
    help="Minimum total article count required for a narrative to appear in the options"
)

# Pull Default Themes/Mesos dynamically based on Real-World choice
defaults = DEFAULT_NARRATIVES.get(selected_rw_stat, {"themes": [], "mesos": []})

# Filter valid themes based on minimum count
theme_base = themes_df[themes_df["model"] == selected_model]
if selected_version != "(All versions)":
    theme_base = theme_base[pd.to_numeric(theme_base["version"], errors="coerce") == int(selected_version)]

theme_counts = theme_base.groupby("theme")["count"].sum()
valid_themes = sorted(theme_counts[theme_counts >= NEW_MIN_COUNT].index.tolist())

selected_themes = st.sidebar.multiselect(
    "Overlay Themes", 
    options=valid_themes, 
    default=[t for t in defaults.get("themes", []) if t in valid_themes]
)

# Filter Meso narratives based on selected themes AND minimum count
meso_base = meso_df[meso_df["model"] == selected_model]
if selected_version != "(All versions)":
    meso_base = meso_base[pd.to_numeric(meso_base["version"], errors="coerce") == int(selected_version)]


if selected_themes:
    # If themes are selected, only show mesos that belong to those themes
    if "theme" in meso_base.columns:
        meso_base = meso_base[meso_base["theme"].isin(selected_themes)]

meso_counts = meso_base.groupby("meso_narrative")["count"].sum()
valid_mesos = sorted(meso_counts[meso_counts >= NEW_MIN_COUNT].index.tolist())

selected_mesos = st.sidebar.multiselect(
    "Overlay Meso Narratives", 
    options=valid_mesos, 
    default=[m for m in defaults.get("mesos", []) if m in valid_mesos]
)

# -------------------------------
# Filter & Plotting Logic
# -------------------------------
def get_smoothed_curves(x_vals, y_vals):
    x_pts = x_vals + 0.5
    if len(x_pts) >= 4:
        x_sm = np.linspace(x_pts.min(), x_pts.max(), 300)
        y_sm = np.maximum(PchipInterpolator(x_pts, y_vals)(x_sm), 0)
    else:
        x_sm, y_sm = x_pts, y_vals
    return x_pts, y_vals, x_sm, y_sm


@st.cache_data(show_spinner=False)
def fetch_narrative_evolution(domains, n_type, n_name, selected_model, selected_version, time_range, y_axis_metric, df_base, stance_base):
    col = "theme" if n_type == "theme" else "meso_narrative"
    
    t = df_base[
        (df_base["model"] == selected_model) & 
        (df_base["source_domain"].isin(domains)) &
        (df_base["year"] >= time_range[0]) & 
        (df_base["year"] <= time_range[1]) &
        (df_base[col] == n_name)
    ].copy()

    if selected_version != "(All versions)":
        t = t[pd.to_numeric(t["version"], errors="coerce") == int(selected_version)]

    grouped = t.groupby("year")["count"].sum().reset_index()

    if "Percentage" in y_axis_metric:
        s = stance_base[
            (stance_base["model"] == selected_model) &
            (stance_base["source_domain"].isin(domains)) &
            (stance_base["year"] >= time_range[0]) & 
            (stance_base["year"] <= time_range[1]) &
            (stance_base["stance"].isin(["OPEN", "RESTRICTIVE", "NEUTRAL"]))
        ].copy()
        s_g = s.groupby("year")["count"].sum().reset_index().rename(columns={"count": "total_m"})
        out = grouped.merge(s_g, on="year", how="left")
        out["value"] = np.where(out["total_m"] > 0, out["count"] / out["total_m"], 0.0)
    else:
        grouped["value"] = grouped["count"]
        out = grouped

    return out.sort_values("year")

# @st.cache_resource(show_spinner=False)
def draw_dual_chart(domains_list, selected_categories, selected_themes, selected_mesos, time_range, selected_rw_stat, y_axis_metric, narr_y_min, narr_y_max, rw_data_slice, df_themes, df_meso, df_stance, selected_model, selected_version):
    fig, ax1 = plt.subplots(figsize=(11, 6))
    fig.patch.set_facecolor('#ffffff')
    ax1.set_facecolor('#ffffff')

    ax1.spines['bottom'].set_visible(True); ax1.spines['bottom'].set_linewidth(1.2)
    ax1.spines['left'].set_visible(True);   ax1.spines['left'].set_linewidth(1.2)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Left Axis: Real World Stats
    if not rw_data_slice.empty and len(selected_categories) > 0:
        s_slice = rw_data_slice.loc[(rw_data_slice.index >= time_range[0]) & (rw_data_slice.index <= time_range[1])]
        
        stat_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#8c564b", "#e377c2", "#17becf", "#bcbd22"] 
        style_idx = 0
        
        for cat in selected_categories:
            if cat in s_slice.columns:
                x_p, y_p, x_s, y_s = get_smoothed_curves(s_slice.index.values, s_slice[cat].values)
                
                c_col = stat_colors[style_idx % len(stat_colors)]
                l_styl = "solid"  
                l_wid = 4.5        
                m_size = 100
                style_idx += 1
                
                # Plot the line and scatter points
                ax1.plot(x_s, y_s, color=c_col, linestyle=l_styl, linewidth=l_wid, zorder=2)
                ax1.scatter(x_p, y_p, color=c_col, s=m_size, marker="s", edgecolor='white', linewidth=0.8, zorder=3)
                
                # Legend formatting
                ax1.plot([], [], color=c_col, linestyle=l_styl, linewidth=l_wid, label=f"Stat: {cat}")

    def fmt_cn(x, pos):
        if x >= 1e6: return f'{x*1e-6:g}m'
        elif x >= 1e3: return f'{x*1e-3:g}k'
        return f'{x:g}'
        
    ax1.set_ylabel(f"Real World Value", fontsize=13, fontweight="bold", labelpad=10)
    if selected_rw_stat == "Public Opinion (Most Important Issue)":
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x)}%"))
    else:
        ax1.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_cn))
        
    ax1.set_xlim(time_range[0], time_range[1])
    ax1.set_xticks(np.arange(time_range[0], time_range[1] + 1))
    ax1.tick_params(axis='both', labelsize=11)

    # Right Axis: Narratives
    ax2 = ax1.twinx()
    ax2.spines['right'].set_visible(True); ax2.spines['right'].set_linewidth(1.2)
    ax2.spines['top'].set_visible(False)
    ax2.spines['left'].set_visible(False)
    ax2.spines['bottom'].set_visible(False)
    ax2.grid(False)

    narrative_colors = ["#d7191c", "#2c7bb6", "#2ca02c", "#ff7f0e", "#9467bd", "#e377c2"]
    color_idx = 0
    items_to_plot = [("theme", t) for t in selected_themes] + [("meso", m) for m in selected_mesos]

    for n_type, n_name in items_to_plot:
        
        df_base = df_themes if n_type == "theme" else df_meso
        
        df_n = fetch_narrative_evolution(domains_list, n_type, n_name, selected_model, selected_version, time_range, y_axis_metric, df_base, df_stance)
        
        if not df_n.empty:
            c_color = narrative_colors[color_idx % len(narrative_colors)]
            color_idx += 1
            
            x_p, y_p, x_s, y_s = get_smoothed_curves(df_n["year"].values, df_n["value"].values)
            # Make the narrative lines thin and dashed
            ax2.plot(x_s, y_s, color=c_color, linestyle="dashed", linewidth=2, zorder=4)
            ax2.scatter(x_p, y_p, color=c_color, s=40, marker="o", edgecolor='white', linewidth=0.6, zorder=5)
            
            short_n = n_name if len(n_name) < 40 else n_name[:40] + "..."
            ax2.plot([], [], color=c_color, linestyle="dashed", linewidth=2, label=f"[{n_type.capitalize()}] {short_n}")

    ax2.set_ylabel(f'Narratives {"Prevalence" if "Percentage" in y_axis_metric else "Count"}', fontsize=13, fontweight="bold", labelpad=10)
    if "Percentage" in y_axis_metric:
        ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
        ax2.set_ylim(narr_y_min, narr_y_max)
    ax2.tick_params(axis='y', labelsize=11)

    # Merge Legends cleanly
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    
    if lines_1 or lines_2:
        ax1.legend(
            lines_1 + lines_2, 
            labels_1 + labels_2, 
            fontsize=10, 
            loc="upper right",
            frameon=True,
            facecolor='white',
            framealpha=0.9,
            edgecolor='#cccccc',
            borderpad=0.8
        )

    plt.tight_layout()
    return fig

# -------------------------------
# Four-Chart Cross Comparison UI
# -------------------------------

col1, col2 = st.columns(2)

# Pass scalar parameters into cache
_narr_y_min = narr_y_min if "Percentage" in y_axis_metric else 0
_narr_y_max = narr_y_max if "Percentage" in y_axis_metric else 0


with col1:
    st.markdown("##### **Source Domains** - Chart 1 (Default: *Left-Leaning Media*)")
    doms_1 = st.multiselect("Source Domains", options=all_domains, default=UK_LEFT, key="dom1_sel", label_visibility="collapsed")
    if doms_1: st.pyplot(draw_dual_chart(tuple(doms_1), tuple(selected_categories), tuple(selected_themes), tuple(selected_mesos), time_range, selected_rw_stat, y_axis_metric, _narr_y_min, _narr_y_max, rw_data, themes_df, meso_df, stance_df, selected_model, selected_version))

with col2:
    st.markdown("##### **Source Domains** - Chart 2 (Default: *Right-Leaning Media*)")
    doms_2 = st.multiselect("Source Domains", options=all_domains, default=UK_RIGHT, key="dom2_sel", label_visibility="collapsed")
    if doms_2: st.pyplot(draw_dual_chart(tuple(doms_2), tuple(selected_categories), tuple(selected_themes), tuple(selected_mesos), time_range, selected_rw_stat, y_axis_metric, _narr_y_min, _narr_y_max, rw_data, themes_df, meso_df, stance_df, selected_model, selected_version))

st.markdown("---")
col3, col4 = st.columns(2)

with col3:
    st.markdown("##### **Source Domains** - Chart 3 (Default: *Labour Party*)")
    doms_3 = st.multiselect("Source Domains", options=all_domains, default=UK_LABOUR, key="dom3_sel", label_visibility="collapsed")
    if doms_3: st.pyplot(draw_dual_chart(tuple(doms_3), tuple(selected_categories), tuple(selected_themes), tuple(selected_mesos), time_range, selected_rw_stat, y_axis_metric, _narr_y_min, _narr_y_max, rw_data, themes_df, meso_df, stance_df, selected_model, selected_version))

with col4:
    st.markdown("##### **Source Domains** - Chart 4 (Default: *Conservative Party*)")
    doms_4 = st.multiselect("Source Domains", options=all_domains, default=UK_CONS, key="dom4_sel", label_visibility="collapsed")
    if doms_4: st.pyplot(draw_dual_chart(tuple(doms_4), tuple(selected_categories), tuple(selected_themes), tuple(selected_mesos), time_range, selected_rw_stat, y_axis_metric, _narr_y_min, _narr_y_max, rw_data, themes_df, meso_df, stance_df, selected_model, selected_version))

# -------------------------------
# Footer logic and metadata
# -------------------------------
st.markdown("---")
st.markdown("### Source Information")
info = DATASETS_METADATA.get(selected_rw_stat, {})
st.info(f"**Dataset:** {selected_rw_stat}\n\n**Source/Publisher**: {info.get('source', 'Unknown')}\n\n**Link**: {info.get('link', 'No link provided')}")
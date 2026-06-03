"""Figure 8 — Migration discourse vs real-world statistics (2016–2025)."""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from . import rw_data as RW
    from . import style as S
    from .data import load_all, theme_prevalence
except ImportError:
    import rw_data as RW
    import style as S
    from data import load_all, theme_prevalence

DOMAINS = [
    ("left_media", S.UK_LEFT_WING, "Left-leaning media", S.LEFT_MEDIA),
    ("right_media", S.UK_RIGHT_WING, "Right-leaning media", S.RIGHT_MEDIA),
    ("labour", S.UK_LABOUR, "Labour (UK Parliament)", S.LABOUR),
    ("conservative", S.UK_CONSERVATIVE, "Conservative (UK Parliament)", S.CONSERVATIVE),
]
NEWS_DASH = "3px,2px"
YEAR_TICKS = [2016, 2018, 2020, 2022, 2024]

PANELS = [
    ("Small-boat arrivals", RW.small_boats, "small boats and Channel crossings", "count"),
    ("Immigration as 'top issue'", RW.public_opinion, "public opinion on migration", "pct"),
    ("Asylum claims", RW.asylum_claims, "asylum seeking", "count"),
    ("Immigration detention", RW.detention, "detention and deportation of migrants", "count"),
    ("Non-citizen convictions", RW.convictions, "migrants and crimes", "count"),
]


def build():
    stance, themes, _meso, _total = load_all()

    def theme_lines(theme):
        out = {}
        for key, doms, _lbl, _c in DOMAINS:
            d = theme_prevalence(themes, stance, doms, [theme])
            d = d[d["theme"] == theme].sort_values("year")
            out[key] = d[["year", "prevalence"]]
        return out

    fig = make_subplots(
        rows=2, cols=5,
        horizontal_spacing=0.04,
        vertical_spacing=0.14,
        subplot_titles=[p[0] for p in PANELS] + [""] * len(PANELS),
    )

    for idx, (title, loader, theme, scale) in enumerate(PANELS):
        c = idx + 1
        rw = loader()
        lines = theme_lines(theme)
        corr_acc = []

        fig.add_trace(go.Scatter(
            x=rw["year"], y=rw["value"], mode="lines",
            line=dict(width=0.9, color=S.REAL_WORLD),
            fill="tozeroy", fillcolor="rgba(120,128,138,0.18)",
            name="Real-world statistic", legendgroup="rw",
            showlegend=False,
            hovertemplate="real-world: %{y:,.0f}<extra></extra>"),
            row=1, col=c)

        for key, _doms, lbl, color in DOMAINS:
            d = lines[key]
            if d.empty:
                continue
            fig.add_trace(go.Scatter(
                x=d["year"], y=d["prevalence"], mode="lines",
                line=dict(
                    color=color,
                    width=2.0,
                    dash=(NEWS_DASH if "media" in key else "solid"),
                    shape="spline",
                    smoothing=0.7,
                ),
                name=lbl, legendgroup=lbl, showlegend=(idx == 0),
                hovertemplate=f"{lbl}: %{{y:.1%}}<extra></extra>"),
                row=2, col=c)
            corr_acc.append(d.set_index("year")["prevalence"])

        if corr_acc:
            disc = pd.concat(corr_acc, axis=1).mean(axis=1)
            m = pd.DataFrame({"rw": rw.set_index("year")["value"], "d": disc}).dropna()
            if len(m) >= 3:
                rr = spearmanr(m["rw"], m["d"]).statistic
                sign = "+" if rr >= 0 else "−"
                fig.add_annotation(
                    xref=f"x{idx + 1 if idx else ''} domain",
                    yref="paper",
                    x=0.5, y=0.5,
                    text=f"Spearman ρ = {sign}{abs(rr):.2f}",
                    showarrow=False,
                    font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
                )

    for idx, (_title, _loader, _theme, scale) in enumerate(PANELS):
        c = idx + 1
        fig.update_xaxes(
            range=[2016, 2025],
            tickvals=YEAR_TICKS,
            showticklabels=False,
            row=1, col=c,
        )
        fig.update_xaxes(
            range=[2016, 2025],
            tickvals=YEAR_TICKS,
            row=2, col=c,
        )
        fig.update_yaxes(
            row=1, col=c,
            tickformat=("~s" if scale == "count" else None),
            ticksuffix=("%" if scale == "pct" else None),
            rangemode="tozero",
            nticks=4,
            color=S.REAL_WORLD,
        )
        fig.update_yaxes(
            row=2, col=c,
            tickformat=".0%",
            rangemode="tozero",
            nticks=4,
            color=S.COLOR_MUTED,
        )

    for ann in fig.layout.annotations[:len(PANELS)]:
        ann.font = dict(family=S.FONT_FAMILY, size=S.FS_PANEL, color=S.COLOR_SUBHEAD)

    fig.update_layout(**S.base_layout(
        1420, 500,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center",
                    x=0.5, font=dict(size=S.FS_LEGEND)),
        margin=dict(l=72, r=28, t=70, b=45),
    ))
    S.style_axes(fig)
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=False)

    fig.add_annotation(text="Real-world statistics", textangle=-90,
                       xref="paper", yref="paper", x=-0.052, y=0.79,
                       showarrow=False, font=dict(size=S.FS_AXIS_TITLE, color=S.REAL_WORLD))
    fig.add_annotation(text="Narrative density", textangle=-90,
                       xref="paper", yref="paper", x=-0.052, y=0.21,
                       showarrow=False, font=dict(size=S.FS_AXIS_TITLE, color=S.COLOR_MUTED))
    return fig


if __name__ == "__main__":
    f = build()
    S.save(f, "fig8_realworld_vs_discourse")
    print("saved fig8_realworld_vs_discourse")

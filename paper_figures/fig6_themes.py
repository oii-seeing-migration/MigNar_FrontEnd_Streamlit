"""Figure 6 — Theme prevalence over time (2016–2025)."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from . import style as S
    from .data import load_all, theme_prevalence
except ImportError:
    import style as S
    from data import load_all, theme_prevalence

THEMES = [
    "EU migration to and from the UK",
    "small boats and Channel crossings",
    "migrants and crimes",
    "public opinion on migration",
    "migrants, economy, and labour market",
    "migrants and human rights",
    "detention and deportation of migrants",
    "work visas and sponsorship",
]
SHORT = {
    "EU migration to and from the UK": "EU migration",
    "small boats and Channel crossings": "Small boats & Channel crossings",
    "migrants and crimes": "Migrants & crime",
    "public opinion on migration": "Public opinion on migration",
    "migrants, economy, and labour market": "Economy & labour market",
    "migrants and human rights": "Human rights",
    "detention and deportation of migrants": "Detention & deportation",
    "work visas and sponsorship": "Work visas & sponsorship",
}

DOMAINS = [
    ("left_media", S.UK_LEFT_WING, "Left-leaning media", S.LEFT_MEDIA),
    ("right_media", S.UK_RIGHT_WING, "Right-leaning media", S.RIGHT_MEDIA),
    ("labour", S.UK_LABOUR, "Labour (UK Parliament)", S.LABOUR),
    ("conservative", S.UK_CONSERVATIVE, "Conservative (UK Parliament)", S.CONSERVATIVE),
]
NEWS_DASH = "3px,2px"
Y_MAX = 0.60
YEAR_TICKS = [2016, 2018, 2020, 2022, 2024]


def build():
    stance, themes, _meso, _total = load_all()

    data = {}
    for key, doms, _lbl, _c in DOMAINS:
        data[key] = theme_prevalence(themes, stance, doms, THEMES)

    ncol = 4
    nrow = 2
    fig = make_subplots(
        rows=nrow, cols=ncol,
        subplot_titles=[SHORT[t] for t in THEMES],
        horizontal_spacing=0.055, vertical_spacing=0.16,
    )

    for i, theme in enumerate(THEMES):
        r, c = i // ncol + 1, i % ncol + 1
        for key, _doms, lbl, color in DOMAINS:
            d = data[key]
            d = d[d["theme"] == theme].sort_values("year")
            if d.empty:
                continue
            fig.add_trace(go.Scatter(
                x=d["year"], y=d["prevalence"], mode="lines",
                name=lbl, legendgroup=lbl, showlegend=(i == 0),
                line=dict(
                    color=color,
                    width=2.4,
                    dash=(NEWS_DASH if "media" in key else "solid"),
                    shape="spline",
                    smoothing=0.7,
                ),
                hovertemplate=f"{lbl}: %{{y:.1%}} (%{{x}})<extra></extra>",
            ), row=r, col=c)

    for i in range(len(THEMES)):
        r, c = i // ncol + 1, i % ncol + 1
        fig.update_xaxes(range=[2016, 2025], tickvals=YEAR_TICKS,
                         row=r, col=c)
        fig.update_yaxes(
            tickformat=".0%",
            range=[0, Y_MAX],
            tickvals=np.arange(0, Y_MAX + 0.001, 0.10),
            row=r, col=c,
        )

    fig.add_annotation(text="Share of migration-relevant documents", textangle=-90,
                       xref="paper", yref="paper", x=-0.072, y=0.5,
                       showarrow=False, font=dict(size=S.FS_AXIS_TITLE, color=S.COLOR_INK))

    _X_2017 = 1 / 9  # domain coordinate of year 2017 on a [2016, 2025] axis
    _takeaway = dict(
        showarrow=False,
        align="center",
        font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
        xanchor="left",
        yanchor="middle",
    )
    _cues = {
        "EU migration to and from the UK":       "<i>Brexit-era peak,<br>then fades</i>",
        "small boats and Channel crossings":     "<i>Surges<br>after 2021</i>",
        "migrants and crimes":                   "<i>Climbs to a<br>2025 high</i>",
        "public opinion on migration":           "<i>Dips, then<br>recovers</i>",
        "migrants, economy, and labour market":  "<i>Declining salience<br>post-2018</i>",
        "migrants and human rights":             "<i>Left-leaning sources<br>consistently higher</i>",
        "detention and deportation of migrants": "<i>Rises sharply<br>after 2022</i>",
        "work visas and sponsorship":            "<i>Peaks as points-based<br>system beds in</i>",
    }
    for i, theme in enumerate(THEMES):
        r, c = i // ncol + 1, i % ncol + 1
        fig.add_annotation(xref="x domain", yref="y domain", x=_X_2017, y=0.85,
                           text=_cues[theme], row=r, col=c, **_takeaway)

    for ann in fig.layout.annotations[:len(THEMES)]:
        ann.font = dict(family=S.FONT_FAMILY, size=S.FS_PANEL, color=S.COLOR_SUBHEAD)

    fig.update_layout(**S.base_layout(
        1080, 540,
        legend=dict(orientation="h", yanchor="bottom", y=1.07, xanchor="center",
                    x=0.5, font=dict(size=S.FS_LEGEND)),
        margin=dict(l=115, r=25, t=70, b=45),
    ))
    S.style_axes(fig)
    return fig


if __name__ == "__main__":
    f = build()
    S.save(f, "fig6_theme_prevalence")
    print("saved fig6_theme_prevalence")

"""Figure 5 — Net attitude towards immigration (UK Parliament vs US Congress)."""

from scipy.stats import pearsonr
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from . import style as S
    from .data import load_all, yearly_net_stance
except ImportError:
    import style as S
    from data import load_all, yearly_net_stance

START, END = 1950, 2025
ZERO_LINE_COLOR = "#74808B"
UK_ALL_PARTIES = [
    "UK Parliament (Lab)",
    "UK Parliament (Con)",
    "UK Parliament (LD)",
    "UK Parliament (Green)",
    "UK Parliament (Reform)",
]
US_ALL_PARTIES = ["US Congress (Dem)", "US Congress (Rep)"]
UK_MINOR_PARTIES = [
    ("UK Parliament (LD)", "Lib Dems", "#CBAA68"),
    ("UK Parliament (Green)", "Green", "#89A970"),
    ("UK Parliament (Reform)", "Reform", "#7FA8B2"),
]
MINOR_LINE_WIDTH = 1.8
MINOR_MARKER_SIZE = 4
MINOR_OPACITY = 0.56


def _series(net, domain, y0=START, y1=END):
    d = net[net["source_domain"] == domain].sort_values("year")
    d = d[(d["year"] >= y0) & (d["year"] <= y1)]
    return d["year"].values, d["score"].values


def _corr(net, dom_a, dom_b):
    a = net[net["source_domain"] == dom_a][["year", "score"]]
    b = net[net["source_domain"] == dom_b][["year", "score"]]
    m = a.merge(b, on="year", suffixes=("_a", "_b"))
    if len(m) < 3:
        return None
    return pearsonr(m["score_a"], m["score_b"])[0]


def build():
    stance, *_ = load_all()
    net = yearly_net_stance(
        stance,
        UK_ALL_PARTIES + US_ALL_PARTIES,
        start="1950-01-01", end="2025-12-31",
    )

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.09,
        subplot_titles=None,
    )

    panels = [
        (1, [("UK Parliament (Lab)", "Labour", S.LABOUR),
             ("UK Parliament (Con)", "Conservative", S.CONSERVATIVE)],
         _corr(net, "UK Parliament (Con)", "UK Parliament (Lab)"), "UK Parliament"),
        (2, [("US Congress (Dem)", "Democrat", S.DEMOCRAT),
             ("US Congress (Rep)", "Republican", S.REPUBLICAN)],
         _corr(net, "US Congress (Rep)", "US Congress (Dem)"), "US Congress"),
    ]

    for col, series, corr, _name in panels:
        legend_id = "legend" if col == 1 else "legend2"
        if col == 1:
            for dom, label, color in UK_MINOR_PARTIES:
                x, y = _series(net, dom, y0=2000)
                if len(x) == 0:
                    continue
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode="lines+markers", name=label, showlegend=True, legend=legend_id,
                    line=dict(color=color, width=MINOR_LINE_WIDTH, shape="spline", smoothing=0.6),
                    marker=dict(color=color, size=MINOR_MARKER_SIZE, line=dict(color="white", width=0.6)),
                    opacity=MINOR_OPACITY,
                    legendrank={"Lib Dems": 3, "Green": 4, "Reform": 5}[label],
                    hovertemplate=f"{label}: %{{y:.2f}} (%{{x}})<extra></extra>",
                ), row=1, col=col)
        for dom, label, color in series:
            x, y = _series(net, dom)
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines+markers", name=label, showlegend=True, legend=legend_id,
                line=dict(color=color, width=2.5, shape="spline", smoothing=0.6),
                marker=dict(color=color, size=5, line=dict(color="white", width=0.8)),
                legendrank={"Labour": 1, "Conservative": 2, "Democrat": 1, "Republican": 2}[label],
                hovertemplate=f"{label}: %{{y:.2f}} (%{{x}})<extra></extra>",
            ), row=1, col=col)

        fig.add_hline(y=0, line=dict(color=ZERO_LINE_COLOR, width=1.15, dash="dot"),
                      row=1, col=col)
        if corr is not None:
            sign = "+" if corr >= 0 else "−"
            fig.add_annotation(
                xref=f"x{'' if col==1 else col} domain", yref=f"y{'' if col==1 else col}",
                x=0.04, y=-0.9, xanchor="left",
                text=f"cross-party Pearson r = {sign}{abs(corr):.2f}",
                showarrow=False, font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
                row=1, col=col,
            )

    ytv = [-1, -0.5, 0, 0.5, 1]
    ytt = ["−1", "−0.5", "0", "+0.5", "+1"]
    for col in (1, 2):
        fig.update_xaxes(range=[START - 0.5, END + 0.5], dtick=10,
                         row=1, col=col)
        fig.update_yaxes(range=[-1.12, 1.12], tickvals=ytv, row=1, col=col)
    fig.update_yaxes(title_text="Net stance toward migration",
                     ticktext=ytt, tickvals=ytv, row=1, col=1)
    fig.update_yaxes(ticktext=["−1", "−0.5", "0", "+0.5", "+1"], tickvals=ytv,
                     row=1, col=2)

    fig.add_annotation(
        xref="x domain", yref="y domain", x=0.5, y=1.03,
        text="UK Parliament 🇬🇧", showarrow=False,
        xanchor="center", yanchor="bottom",
        font=dict(family=S.FONT_FAMILY, size=S.FS_PANEL, color=S.COLOR_SUBHEAD),
        row=1, col=1,
    )
    fig.add_annotation(
        xref="x2 domain", yref="y2 domain", x=0.5, y=1.03,
        text="US Congress 🇺🇸", showarrow=False,
        xanchor="center", yanchor="bottom",
        font=dict(family=S.FONT_FAMILY, size=S.FS_PANEL, color=S.COLOR_SUBHEAD),
        row=1, col=2,
    )

    cue = dict(
        showarrow=False,
        font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
        xanchor="right",
        align="right",
    )
    fig.add_annotation(
        xref="x domain", yref="y domain", x=-0.06, y=1.0,
        text="<i>open</i>", row=1, col=1, **cue,
    )
    fig.add_annotation(
        xref="x domain", yref="y domain", x=-0.06, y=0.0,
        text="<i>restrictive</i>", row=1, col=1, **cue,
    )

    takeaway = dict(
        showarrow=False,
        align="center",
        font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
        xanchor="center",
        yanchor="middle",
    )
    fig.add_annotation(
        xref="x domain", yref="y domain", x=0.50, y=0.85,
        text="<i>Both parties lean restrictive<br>and move together</i>",
        row=1, col=1, **takeaway,
    )
    fig.add_annotation(
        xref="x2 domain", yref="y2 domain", x=0.50, y=0.85,
        text="<i>Parties pull apart over time<br>as polarisation grows</i>",
        row=1, col=2, **takeaway,
    )

    fig.update_layout(**S.base_layout(
        980, 450,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.16, xanchor="center", x=0.295,
            font=dict(size=S.FS_LEGEND), traceorder="normal",
        ),
        legend2=dict(
            orientation="h", yanchor="bottom", y=1.16, xanchor="center", x=0.771,
            font=dict(size=S.FS_LEGEND), traceorder="normal",
        ),
        margin=dict(l=95, r=30, t=92, b=55),
    ))
    S.style_axes(fig)
    return fig


if __name__ == "__main__":
    f = build()
    S.save(f, "fig5_net_stance")
    print("saved fig5_net_stance")

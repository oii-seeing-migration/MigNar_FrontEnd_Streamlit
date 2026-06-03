"""Figure 7 — Comparative prevalence of specific meso-narratives (diverging tornado)."""

import textwrap
import numpy as np
import plotly.graph_objects as go

try:
    from . import style as S
    from .data import load_all, meso_prevalence
except ImportError:
    import style as S
    from data import load_all, meso_prevalence

TARGET = {
    "EU migration": [
        "EU migration enhances labour mobility and economic growth",
        "EU migration takes jobs from local workers",
    ],
    "Migrants & crime": [
        "Most migrants are law-abiding citizens",
        "Migrants are involved in violent crimes",
        "Migrants sell illegal drugs",
        "Migrants are involved in fraud",
    ],
    "Detention & deportation": [
        "Current detention practices violate human rights",
        "Deportations separate families and harm children",
        "Current detention practices are legitimate and necessary",
    ],
    "Human rights": [
        "Migrants face systemic human rights abuses",
        "Human rights claims by migrants are often exaggerated",
    ],
    "Economy & labour market": [
        "Migrants fill critical labour shortages",
        "Migrants take jobs away from local workers",
    ],
    "Small boats & Channel crossings": [
        "Stopping the boats should be a government priority",
        "People crossing the Channel are desperate, not criminals",
    ],
    "Healthcare system": [
        "Migrants burden the healthcare system",
        "Migrants are necessary for the NHS to function",
    ],
    "Public opinion": [
        "Public opinion supports welcoming migrants",
        "Public opinion supports restricting migration",
    ],
    "Asylum seeking": [
        "Offering asylum saves lives",
        "The UK is hosting too many asylum seekers",
        "Asylum seekers’ claims are fraudulent",
    ],
}


def _wrap(s, w=40):
    return "<br>".join(textwrap.wrap(s, w))


def _add_legend_item(fig, cx, cy, color, label, patterned=False):
    sw = 0.024
    sh = 0.015
    x0 = cx - sw / 2
    x1 = x0 + sw
    y0 = cy - sh / 2
    y1 = cy + sh / 2

    fig.add_shape(
        type="rect",
        xref="paper",
        yref="paper",
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        line=dict(color=color, width=1.3),
        fillcolor=color,
        opacity=1.0,
    )
    if patterned:
        for dx in (-0.004, 0.001, 0.006, 0.011, 0.016):
            fig.add_shape(
                type="line",
                xref="paper",
                yref="paper",
                x0=x0 + dx,
                y0=y0 + 0.002,
                x1=x0 + dx + 0.014,
                y1=y1 - 0.002,
                line=dict(color="white", width=1.6),
            )
    fig.add_annotation(
        x=cx,
        y=y0 - 0.006,
        xref="paper",
        yref="paper",
        text=label,
        showarrow=False,
        font=dict(size=S.FS_LEGEND, color=S.COLOR_INK),
        xanchor="center",
        yanchor="top",
        align="center",
    )


def build():
    stance, _themes, meso, _total = load_all()
    prev = meso_prevalence(stance, meso, TARGET)
    prev = prev.set_index("narrative")

    ROW = 1.0
    GAP = 1.05
    OFF = 0.21
    H = 0.34

    y = 0.0
    rows = []
    theme_blocks = []
    for theme, claims in TARGET.items():
        y -= GAP
        header_y = y
        first_claim_y = None
        for claim in claims:
            y -= ROW
            rows.append((y, claim))
            if first_claim_y is None:
                first_claim_y = y
        theme_blocks.append((theme, header_y, first_claim_y, y))

    ys = {n: yp for yp, n in rows}

    def vals(col, narrs):
        return [prev.loc[n, col] if n in prev.index else 0.0 for n in narrs]

    narrs = [n for _, n in rows]
    base_y = np.array([ys[n] for n in narrs])

    fig = go.Figure()

    for j, (_theme, header_y, _first_claim_y, last_claim_y) in enumerate(theme_blocks):
        if j % 2 == 0:
            continue
        y_hi = header_y + 0.16
        y_lo = last_claim_y - 0.44
        fig.add_hrect(y0=y_lo, y1=y_hi, fillcolor="#F4F6F8",
                      line_width=0, layer="below")

    fig.add_bar(orientation="h", y=base_y + OFF, x=[-v for v in vals("left_media", narrs)],
                marker=dict(color=S.LEFT_MEDIA,
                            pattern=dict(shape="/", fgcolor="white", size=6, solidity=0.24)),
                width=H, name="Left-leaning media",
                hovertemplate="Left media: %{customdata:.2%}<extra></extra>",
                customdata=vals("left_media", narrs))
    fig.add_bar(orientation="h", y=base_y + OFF, x=vals("right_media", narrs),
                marker=dict(color=S.RIGHT_MEDIA,
                            pattern=dict(shape="/", fgcolor="white", size=6, solidity=0.24)),
                width=H, name="Right-leaning media",
                hovertemplate="Right media: %{x:.2%}<extra></extra>")
    fig.add_bar(orientation="h", y=base_y - OFF, x=[-v for v in vals("labour", narrs)],
                marker_color=S.LABOUR,
                width=H, name="Labour (UK)",
                hovertemplate="Labour: %{customdata:.2%}<extra></extra>",
                customdata=vals("labour", narrs))
    fig.add_bar(orientation="h", y=base_y - OFF, x=vals("conservative", narrs),
                marker_color=S.CONSERVATIVE,
                width=H, name="Conservative (UK)",
                hovertemplate="Conservative: %{x:.2%}<extra></extra>")

    fig.update_yaxes(
        tickmode="array",
        tickvals=[ys[n] for n in narrs],
        ticktext=[_wrap(n) for n in narrs],
        tickfont=dict(size=S.FS_TICK, color=S.COLOR_INK),
    )
    xmax = max(prev[["left_media", "right_media", "labour", "conservative"]].max()) * 1.18
    for theme, header_y, _first_claim_y, _last_claim_y in theme_blocks:
        fig.add_annotation(
            xref="x", yref="y",
            x=0, y=header_y - 0.10,
            text=theme,
            showarrow=False,
            align="center",
            bgcolor="rgba(255,255,255,0.92)",
            font=dict(family=S.FONT_FAMILY, size=S.FS_PANEL, color=S.COLOR_SUBHEAD),
            xanchor="center", yanchor="middle",
        )

    fig.add_vline(x=0, line=dict(color=S.ZERO_LINE, width=1, dash="dot"))
    guide_y = base_y.min() - 0.62
    fig.add_annotation(
        x=-0.05, y=guide_y,
        text="<i>◄ more prevalent on the left</i>",
        showarrow=False, xanchor="right",
        font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
    )
    fig.add_annotation(
        x=0.05, y=guide_y,
        text="<i>more prevalent on the right ►</i>",
        showarrow=False, xanchor="left",
        font=dict(size=S.FS_ANNOT, color=S.COLOR_MUTED),
    )

    tick = 0.02
    ticks = np.arange(0, xmax + tick, tick)
    fig.update_xaxes(
        range=[-xmax, xmax],
        tickvals=np.concatenate([-ticks[::-1], ticks[1:]]),
        ticktext=[f"{abs(t):.0%}" for t in np.concatenate([-ticks[::-1], ticks[1:]])],
        title_text="Prevalence (share of migration-relevant texts)",
    )

    nclaims = len(narrs)
    fig.update_layout(**S.base_layout(
        960, 120 + nclaims * 46,
        barmode="overlay", bargap=0,
        showlegend=False,
        margin=dict(l=290, r=40, t=80, b=55),
    ))
    S.style_axes(fig)
    fig.update_yaxes(
        showline=False,
        ticks="",
        range=[base_y.min() - 1.18, theme_blocks[0][1] + 0.55],
    )
    legend_y = 1.048
    _add_legend_item(fig, 0.14, legend_y, S.LEFT_MEDIA, "Left-leaning<br>media", patterned=True)
    _add_legend_item(fig, 0.39, legend_y, S.RIGHT_MEDIA, "Right-leaning<br>media", patterned=True)
    _add_legend_item(fig, 0.64, legend_y, S.LABOUR, "Labour<br>(UK Parliament)")
    _add_legend_item(fig, 0.86, legend_y, S.CONSERVATIVE, "Conservative<br>(UK Parliament)")
    return fig


if __name__ == "__main__":
    f = build()
    S.save(f, "fig7_meso_diverging")
    print("saved fig7_meso_diverging")

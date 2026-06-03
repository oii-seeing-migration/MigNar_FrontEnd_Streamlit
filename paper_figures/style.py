"""Shared visual design system for the MigNar paper figures."""

import os
import importlib.metadata
import kaleido

FONT_FAMILY = "Arial, Helvetica, sans-serif"
COLOR_INK = "#222222"
COLOR_MUTED = "#6B6B6B"
COLOR_SUBHEAD = "#4A4F55"

FS_TICK = 13
FS_AXIS_TITLE = 14
FS_LEGEND = 13
FS_ANNOT = 12
FS_PANEL = 14

LEFT_MEDIA = "#E08A8A"         # soft coral-red  (left-leaning news)
RIGHT_MEDIA = "#8FB0D6"        # soft blue       (right-leaning news)
LABOUR = "#B23A48"             # deep rose       (Labour)
CONSERVATIVE = "#2F5C8A"       # deep blue       (Conservative)

DEMOCRAT = "#7BA7CC"
REPUBLICAN = "#D98A8A"

REAL_WORLD = "#33373B"
SUBCAT = "#A9AEB3"
ZERO_LINE = "#B9BEC4"

DOMAIN_COLORS = {
    "left_media": LEFT_MEDIA,
    "right_media": RIGHT_MEDIA,
    "labour": LABOUR,
    "conservative": CONSERVATIVE,
}
DOMAIN_LABELS = {
    "left_media": "Left-leaning media",
    "right_media": "Right-leaning media",
    "labour": "Labour (Parliament)",
    "conservative": "Conservative (Parliament)",
}

PASTEL_SEQ = [
    "#6E9BC5",  # blue
    "#E08A8A",  # coral
    "#9BC59B",  # green
    "#E6B873",  # amber
    "#B79BD0",  # lilac
    "#79C4C4",  # teal
    "#D49AC0",  # pink
    "#A9AEB3",  # grey
]

UK_LEFT_WING = [
    "theguardian.com", "mirror.co.uk", "independent.co.uk",
    "huffingtonpost.co.uk", "dailyrecord.co.uk", "thenational.scot",
    "heraldscotland.com",
]
UK_RIGHT_WING = [
    "telegraph.co.uk", "dailymail.co.uk", "express.co.uk",
    "thesun.co.uk", "spectator.co.uk", "thetimes.co.uk",
    "thescottishsun.co.uk",
]
UK_LABOUR = ["UK Parliament (Lab)"]
UK_CONSERVATIVE = ["UK Parliament (Con)"]


def base_layout(width, height, **kw):
    """Return a dict of layout defaults shared by every figure."""
    layout = dict(
        template="simple_white",
        width=width,
        height=height,
        font=dict(family=FONT_FAMILY, size=FS_TICK, color=COLOR_INK),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=70, r=30, t=30, b=55),
    )
    layout.update(kw)
    return layout


def style_axes(fig, **kw):
    """Apply the no-grid, thin-baseline axis treatment everywhere."""
    fig.update_xaxes(
        showgrid=False, zeroline=False, showline=True,
        linecolor=COLOR_INK, linewidth=1, ticks="outside",
        tickcolor=COLOR_INK, ticklen=5,
        title_font=dict(size=FS_AXIS_TITLE), tickfont=dict(size=FS_TICK),
    )
    fig.update_yaxes(
        showgrid=False, zeroline=False, showline=True,
        linecolor=COLOR_INK, linewidth=1, ticks="outside",
        tickcolor=COLOR_INK, ticklen=5,
        title_font=dict(size=FS_AXIS_TITLE), tickfont=dict(size=FS_TICK),
    )
    return fig


def panel_tag(text):
    return dict(
        text=f"<b>{text}</b>", showarrow=False,
        font=dict(family=FONT_FAMILY, size=FS_PANEL, color=COLOR_INK),
        xanchor="left", yanchor="bottom",
    )


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
LOCAL_BROWSER = os.path.join(os.path.dirname(__file__), ".chrome", "chrome-linux64", "chrome")


def _browser_path():
    """Return the browser executable to use for Plotly export."""
    if os.environ.get("BROWSER_PATH"):
        return os.environ["BROWSER_PATH"]
    if os.path.isfile(LOCAL_BROWSER) and os.access(LOCAL_BROWSER, os.X_OK):
        return LOCAL_BROWSER
    return None


def _kaleido_major():
    return int(importlib.metadata.version("kaleido").split(".", 1)[0])


def save(fig, name, scale=3):
    """Write `name` to output/{png,svg,pdf}. PNG is rasterised at `scale`x."""
    browser_path = _browser_path()
    for sub in ("png", "svg", "pdf"):
        os.makedirs(os.path.join(OUTPUT_DIR, sub), exist_ok=True)
    paths = {
        "png": os.path.join(OUTPUT_DIR, "png", f"{name}.png"),
        "svg": os.path.join(OUTPUT_DIR, "svg", f"{name}.svg"),
        "pdf": os.path.join(OUTPUT_DIR, "pdf", f"{name}.pdf"),
    }
    try:
        if _kaleido_major() == 0:
            fig.write_image(paths["png"], scale=scale)
            fig.write_image(paths["svg"])
            fig.write_image(paths["pdf"])
        else:
            kopts = {"path": browser_path} if browser_path else None
            kaleido.write_fig_sync(fig, path=paths["png"], opts={"scale": scale}, kopts=kopts)
            kaleido.write_fig_sync(fig, path=paths["svg"], kopts=kopts)
            kaleido.write_fig_sync(fig, path=paths["pdf"], kopts=kopts)
    except Exception as exc:
        raise RuntimeError(
            "Plotly export needs a working Kaleido setup. The simplest option is "
            "`pip install 'kaleido<1'`. For Kaleido v1+, install Chrome/Chromium "
            "and set `BROWSER_PATH`, or run `../.venv/bin/kaleido_get_chrome --path .chrome` "
            "from `paper_figures/`."
        ) from exc
    return paths

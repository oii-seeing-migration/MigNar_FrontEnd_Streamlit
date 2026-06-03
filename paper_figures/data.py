"""Data loaders and prevalence helpers for the paper figures."""

import os
import numpy as np
import pandas as pd

try:
    from .style import UK_LEFT_WING, UK_RIGHT_WING, UK_LABOUR, UK_CONSERVATIVE
except ImportError:
    from style import UK_LEFT_WING, UK_RIGHT_WING, UK_LABOUR, UK_CONSERVATIVE

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MODEL = "Ensemble"


def _load(fp):
    df = pd.read_parquet(fp)
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"] + "-01", errors="coerce")
    for col in ["source_domain", "model", "stance", "theme", "meso_narrative"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
    return df


def load_all():
    stance = _load(os.path.join(DATA_DIR, "stance_monthly.parquet"))
    themes = _load(os.path.join(DATA_DIR, "themes_monthly.parquet"))
    meso = _load(os.path.join(DATA_DIR, "meso_monthly.parquet"))
    total = pd.read_parquet(os.path.join(DATA_DIR, "total_docs.parquet"))
    total["start_time"] = pd.to_datetime(total["start_time"], errors="coerce")
    total["year"] = total["start_time"].dt.year
    return stance, themes, meso, total


def yearly_net_stance(stance, domains, start="1950-01-01", end="2026-12-31"):
    """Net stance = (OPEN - RESTRICTIVE) / (OPEN+RESTRICTIVE+NEUTRAL),
    computed directly from yearly aggregate counts per domain.

    This mirrors the manuscript equation and the original
    `plots_for_paper.ipynb` logic: yearly net tone is calculated from annual
    OPEN / RESTRICTIVE / NEUTRAL totals, not by averaging monthly ratios.
    """
    f = stance[
        (stance["model"] == MODEL)
        & (stance["month"] >= pd.to_datetime(start))
        & (stance["month"] <= pd.to_datetime(end))
        & (stance["source_domain"].isin(domains))
        & (stance["stance"].isin(["OPEN", "RESTRICTIVE", "NEUTRAL"]))
    ].copy()
    if f.empty:
        return pd.DataFrame(columns=["year", "source_domain", "score"])

    f["year"] = f["month"].dt.year
    piv = (
        f.groupby(["year", "source_domain", "stance"], as_index=False)["count"].sum()
        .pivot_table(index=["year", "source_domain"], columns="stance",
                     values="count", fill_value=0)
        .reset_index()
    )
    for c in ["OPEN", "RESTRICTIVE", "NEUTRAL"]:
        if c not in piv.columns:
            piv[c] = 0
    piv["total"] = piv[["OPEN", "RESTRICTIVE", "NEUTRAL"]].sum(axis=1)
    piv = piv[piv["total"] > 0].copy()
    piv["score"] = (piv["OPEN"] - piv["RESTRICTIVE"]) / piv["total"]
    return piv[["year", "source_domain", "score"]].sort_values(["source_domain", "year"])


def _latest_version(df):
    if "version" in df.columns:
        vv = pd.to_numeric(df["version"], errors="coerce").dropna()
        if not vv.empty:
            return int(vv.max())
    return None


def theme_prevalence(themes, stance, domains, target_themes,
                     start="2016-01-01", end="2025-12-31"):
    """Yearly theme prevalence with the *local* denominator used in the paper:
    prevalence = (#docs tagged with theme) / (#migration-relevant docs) for the
    domain that year. The denominator is the stance total (OPEN+RESTRICTIVE+
    NEUTRAL+MIXED), i.e. the share of migration-relevant texts on each theme."""
    ver = _latest_version(themes)
    t = themes[
        (themes["model"] == MODEL)
        & (themes["source_domain"].isin(domains))
        & (themes["month"] >= pd.to_datetime(start))
        & (themes["month"] <= pd.to_datetime(end))
    ].copy()
    if ver is not None and "version" in t.columns:
        t = t[pd.to_numeric(t["version"], errors="coerce") == ver]
    t = t[t["theme"].isin(target_themes)].copy()
    t["year"] = t["month"].dt.year
    counts = t.groupby(["year", "theme"], as_index=False)["count"].sum() \
              .rename(columns={"count": "articles"})

    s = stance[
        (stance["model"] == MODEL)
        & (stance["source_domain"].isin(domains))
        & (stance["month"] >= pd.to_datetime(start))
        & (stance["month"] <= pd.to_datetime(end))
        & (stance["stance"].isin(["OPEN", "RESTRICTIVE", "NEUTRAL", "MIXED"]))
    ].copy()
    s["year"] = s["month"].dt.year
    base = s.groupby("year", as_index=False)["count"].sum() \
            .rename(columns={"count": "total"})

    out = counts.merge(base, on="year", how="left")
    out["prevalence"] = np.where(out["total"] > 0, out["articles"] / out["total"], 0.0)
    return out.sort_values(["theme", "year"])


def _norm(s):
    import re
    return re.sub(r"\s+", " ", str(s).strip().lower()) if s else ""


def meso_prevalence(stance, meso, target_narratives, version=2):
    """For each target meso-narrative return its prevalence (share of
    migration-relevant texts) in each of the four domains."""
    def total_docs(domains):
        return stance[
            (stance["model"] == MODEL)
            & (stance["source_domain"].isin(domains))
            & (stance["month"] >= pd.to_datetime("2016-01-01"))
            & (stance["month"] <= pd.to_datetime("2025-12-31"))
        ]["count"].sum()

    totals = {
        "left_media": total_docs(UK_LEFT_WING),
        "right_media": total_docs(UK_RIGHT_WING),
        "labour": total_docs(UK_LABOUR),
        "conservative": total_docs(UK_CONSERVATIVE),
    }
    domain_map = {
        "left_media": UK_LEFT_WING, "right_media": UK_RIGHT_WING,
        "labour": UK_LABOUR, "conservative": UK_CONSERVATIVE,
    }

    keys = {}
    for theme, mesos in target_narratives.items():
        for raw in mesos:
            keys[_norm(raw)] = (theme, raw)

    m = meso.copy()
    if "version" in m.columns:
        m = m[m["version"] == version]
    m["k"] = m["meso_narrative"].map(_norm)
    m = m[m["k"].isin(keys)]
    m = m[
        (m["model"] == MODEL)
        & (m["month"] >= pd.to_datetime("2016-01-01"))
        & (m["month"] <= pd.to_datetime("2025-12-31"))
    ]

    counts = {dom: m[m["source_domain"].isin(domain_map[dom])].groupby("k")["count"].sum()
              for dom in domain_map}

    rows = []
    for theme, mesos in target_narratives.items():
        for raw in mesos:
            k = _norm(raw)
            row = {"theme": theme, "narrative": raw}
            for dom in domain_map:
                tot = totals[dom]
                row[dom] = (counts[dom].get(k, 0) / tot) if tot else 0.0
            rows.append(row)
    return pd.DataFrame(rows)

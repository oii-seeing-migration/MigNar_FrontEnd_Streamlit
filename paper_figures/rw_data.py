"""
Real-world statistics loaders for Figure 8.

Each function returns a tidy yearly DataFrame (2016-2025/26). Parsing mirrors
the analysis notebook so the numbers are unchanged.
"""

import os
import pandas as pd

RW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "real-stats")


def _clip(df, col="Year", lo=2016, hi=2026):
    return df[(df[col] >= lo) & (df[col] <= hi)].copy()


def foreign_born():
    """EU vs Non-EU foreign-born population (count)."""
    df = pd.read_excel(os.path.join(RW_DIR, "foreign-born-share.xlsx"))
    df = df.rename(columns=lambda x: str(x).strip().lower())
    df["value"] = pd.to_numeric(
        df["value"].astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["cob"] = df["cob"].astype(str).str.strip()
    df = df.dropna(subset=["year", "cob", "value"])
    df["year"] = df["year"].astype(int)
    df = df[(df["year"] >= 2016) & (df["year"] <= 2026)]
    eu = df[df["cob"] == "EU"].groupby("year")["value"].mean()
    non = df[df["cob"] == "Non-EU"].groupby("year")["value"].mean()
    out = pd.DataFrame({"eu": eu, "non_eu": non}).reset_index()
    return out.sort_values("year")


def small_boats():
    df = pd.read_excel(
        os.path.join(RW_DIR, "illegal-entry-routes-to-the-uk-dataset-dec-2025.xlsx"),
        sheet_name="Data_IER_D02", header=1)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Arrivals"] = pd.to_numeric(df["Arrivals"], errors="coerce").fillna(0)
    df = df.dropna(subset=["Year"])
    out = df.groupby("Year", as_index=False)["Arrivals"].sum()
    return _clip(out).sort_values("Year").rename(columns={"Year": "year", "Arrivals": "value"})


def public_opinion():
    df = pd.read_excel(
        os.path.join(RW_DIR, "opinion-polls-most-important-issue-in-UK-Ipsos.xlsx"),
        sheet_name="Sheet1", header=0)
    df.columns = ["Date", "EU", "Defence", "Economy", "Housing", "NHS", "Immigration"]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=["Date", "Immigration"])
    df["Year"] = df["Date"].dt.year
    out = df.groupby("Year", as_index=False)["Immigration"].mean()
    return _clip(out).sort_values("Year").rename(columns={"Year": "year", "Immigration": "value"})


def asylum_claims():
    df = pd.read_excel(
        os.path.join(RW_DIR, "asylum-claims-datasets-dec-2025.xlsx"),
        sheet_name="Data_Asy_D01", header=1)
    df.columns = df.columns.str.strip()
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Claims"] = pd.to_numeric(df["Claims"], errors="coerce")
    df = df.dropna(subset=["Year", "Claims"])
    out = df.groupby("Year", as_index=False)["Claims"].sum()
    return _clip(out).sort_values("Year").rename(columns={"Year": "year", "Claims": "value"})


def detention():
    df = pd.read_excel(
        os.path.join(RW_DIR, "Detention detailed datasets, year ending December 2025.xlsx"),
        sheet_name="Data_Det_D01", header=14)
    df.columns = ["Year", "Quarter", "Nationality", "Region", "Sex", "Age", "Facility", "Count"]
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
    df["Count"] = pd.to_numeric(df["Count"], errors="coerce")
    df = df.dropna(subset=["Year", "Count"])
    out = df.groupby("Year", as_index=False)["Count"].sum()
    return _clip(out).sort_values("Year").rename(columns={"Year": "year", "Count": "value"})


def convictions():
    df = pd.read_excel(
        os.path.join(RW_DIR, "OII conviction rates.xlsx"),
        sheet_name="Conviction rates", header=0)
    df = df.dropna(subset=["Year", "Offence", "Total"])
    df["Year"] = df["Year"].astype(int)
    out = df[df["Offence"] == "All offences"].groupby("Year", as_index=False)["Total"].sum()
    return _clip(out).sort_values("Year").rename(columns={"Year": "year", "Total": "value"})


if __name__ == "__main__":
    for fn in [foreign_born, small_boats, public_opinion, asylum_claims, detention, convictions]:
        try:
            d = fn()
            print(f"{fn.__name__:16s} OK  rows={len(d)}  cols={list(d.columns)}")
            print("   ", d.head(3).to_dict("records"))
        except Exception as e:
            print(f"{fn.__name__:16s} FAIL  {type(e).__name__}: {e}")

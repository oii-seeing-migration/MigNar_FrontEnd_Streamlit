import os
import pandas as pd
import streamlit as st

DATA_DIR = os.path.expanduser("./data")
STANCE_PATH = os.path.join(DATA_DIR, "stance_monthly.parquet")
THEMES_PATH = os.path.join(DATA_DIR, "themes_monthly.parquet")
MESO_PATH = os.path.join(DATA_DIR, "meso_monthly.parquet")

# Set to True to drop all data before 2016 to save memory
FILTER_PRE_2016 = True


@st.cache_data(ttl="24h", show_spinner=True, max_entries=1)
def load_parquets():
    def _read_parquet(fp: str) -> pd.DataFrame:
        if not os.path.exists(fp):
            return pd.DataFrame()

        df = pd.read_parquet(fp)

        if "month" in df.columns:
            df["month"] = pd.to_datetime(df["month"] + "-01", errors="coerce")
            df["year"] = df["month"].dt.year
            # --- MEMORY SAVER: Filter out pre-2016 data ---
        if FILTER_PRE_2016:
            df = df[df["year"] >= 2016]

        if "source_domain" in df.columns:
            df["source_domain"] = df["source_domain"].fillna("").astype(str)
        if "model" in df.columns:
            df["model"] = df["model"].fillna("").astype(str)
        if "count" in df.columns:
            df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)

        for col in ["stance", "theme", "meso_narrative"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str)

        return df

    stance_df = _read_parquet(STANCE_PATH)
    themes_df = _read_parquet(THEMES_PATH)
    meso_df = _read_parquet(MESO_PATH)
    return stance_df, themes_df, meso_df
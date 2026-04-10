import os
import pandas as pd

DATASETS_METADATA = {
    "Foreign National Offender Returns": {
        "source": "Home Office - returns-datasets-dec-2025.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    },
    "Offence Convictions": {
        "source": "OII conviction rates.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    },
    "Immigration Demographics (Foreign-born)": {
        "source": "foreign-born-share.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    },
    "Immigration Detention": {
        "source": "Home Office - Detention detailed datasets, year ending December 2025.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    },
    "Sponsored Work Visas": {
        "source": "Home Office - Sponsored work entry clearance visas by occupation and industry (SOC 2020), year ending December 2025.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    },
    "Public Opinion (Most Important Issue)": {
        "source": "Ipsos - opinion-polls-most-important-issue-in-UK-Ipsos.xlsx",
        "link": "PLACEHOLDER_LINK_HERE"
    }
}

# Determines what themes/mesos prepopulate the right-side macro when a dataset is chosen
DEFAULT_NARRATIVES = {
    "Foreign National Offender Returns": {"themes": ["migrants and crimes"], "mesos": []},
    "Offence Convictions": {"themes": ["migrants and crimes"], "mesos": []},
    "Immigration Demographics (Foreign-born)": {"themes": ["demographic aspects of migration"], "mesos": []},
    "Immigration Detention": {"themes": ["detention and deportation of migrants"], "mesos": []},
    "Sponsored Work Visas": {"themes": ["work visas and sponsorship"], "mesos": []},
    "Public Opinion (Most Important Issue)": {"themes": ["public opinion on migration"], "mesos": []}
}

def load_real_world_data(dataset_name, data_dir="data/real-stats/"):
    """
    Standardizes loading logic for all specific real-world datasets.
    Returns: A DataFrame where INDEX is 'Year' (int) and COLUMNS are available categories.
    """
    if dataset_name == "Foreign National Offender Returns":
        fp = os.path.join(data_dir, "returns-datasets-dec-2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_Ret_D03", header=1)
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df["Total FNO Returns"] = pd.to_numeric(df["Number of foreign national offender returns"], errors="coerce")
        df = df.dropna(subset=["Year", "Total FNO Returns"])
        return df.groupby("Year")["Total FNO Returns"].sum().to_frame()

    elif dataset_name == "Offence Convictions":
        fp = os.path.join(data_dir, "OII conviction rates.xlsx")
        df = pd.read_excel(fp, sheet_name="Conviction rates", header=0)
        df = df.dropna(subset=["Year", "Offence", "Total"])
        df["Year"] = df["Year"].astype(int)
        
        target_offences = ["All offences", "Sexual offences", "Violence against the person"]
        df = df[df["Offence"].isin(target_offences)]
        pivot = df.pivot_table(index="Year", columns="Offence", values="Total", aggfunc='sum')
        return pivot

    elif dataset_name == "Immigration Demographics (Foreign-born)":
        fp = os.path.join(data_dir, "foreign-born-share.xlsx")
        df = pd.read_excel(fp)
        df = df.rename(columns=lambda x: str(x).strip().lower())
        df["value"] = df["value"].astype(str).str.replace(",", "", regex=False).str.strip()
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["cob"] = df["cob"].astype(str).str.strip()
        df = df.dropna(subset=["year", "cob", "value"])
        df["year"] = df["year"].astype(int)
        
        target_cobs = ["All foreign-born", "Non-EU", "EU"]
        df = df[df["cob"].isin(target_cobs)]
        pivot = df.pivot_table(index="year", columns="cob", values="value", aggfunc='sum')
        pivot.index.name = "Year"
        return pivot

    elif dataset_name == "Immigration Detention":
        fp = os.path.join(data_dir, "Detention detailed datasets, year ending December 2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_Det_D02", header=14)
        df.columns = ["Date", "Nationality", "Region", "Sex", "Age", "Facility", "Duration", "Count"]
        df["Count"] = pd.to_numeric(df["Count"], errors="coerce").fillna(0)
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        
        df_dec = df[df["Date"].dt.month == 12].copy()
        df_dec["Year"] = df_dec["Date"].dt.year
        return df_dec.groupby("Year")["Count"].sum().to_frame(name="Total People Detained")

    elif dataset_name == "Sponsored Work Visas":
        fp = os.path.join(data_dir, "Sponsored work entry clearance visas by occupation and industry (SOC 2020), year ending December 2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_Occ_D02", header=3)
        df.columns = df.columns.str.strip()
        df["Grants"] = pd.to_numeric(df["Grants"], errors="coerce")
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df = df.dropna(subset=["Year", "Grants"])
        
        total_visas = df.groupby("Year")["Grants"].sum().to_frame(name="Total Sponsored Work Visas")
        industry_visas = df.pivot_table(index="Year", columns="Industry", values="Grants", aggfunc='sum')
        return pd.concat([total_visas, industry_visas], axis=1).fillna(0)

    elif dataset_name == "Public Opinion (Most Important Issue)":
        fp = os.path.join(data_dir, "opinion-polls-most-important-issue-in-UK-Ipsos.xlsx")
        df = pd.read_excel(fp, sheet_name="Sheet1", header=0)
        df.columns = ["Date", "EU", "Defence", "Economy", "Housing", "NHS", "Immigration"]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date", "Immigration"])
        df["Year"] = df["Date"].dt.year
        avg_yearly = df.groupby("Year")[["Immigration", "NHS", "Economy", "EU", "Housing", "Defence"]].mean()
        return avg_yearly

    return pd.DataFrame()
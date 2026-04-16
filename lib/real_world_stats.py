import os
import pandas as pd

DATASETS_METADATA = {
    "Foreign National Offender Returns": {
        "source": "gov.uk - Returns datasets, year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables"
    },
    "Offence Convictions": {
        "source": "Migration Observatory - conviction rates",
        "link": "https://migrationobservatory.ox.ac.uk/resources/commentaries/migrant-convictions-and-prison-population/"
    },
    "Immigration Demographics (Foreign-born)": {
        "source": "Migration Observatory - Immigration Demographics (Foreign-born)",
        "link": "https://migrationobservatory.ox.ac.uk/resources/briefings/migrants-in-the-uk-an-overview/"
    },
    "Immigration Detention": {
        "source": "gov.uk - Detention detailed datasets, year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables#entry-clearance-visas-granted-outside-the-uk"
    },
    "Immigration Returns": {
        "source": "gov.uk - Returns datasets, year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables"
    },
    "Sponsored Work Visas": {
        "source": "gov.uk - Sponsored work entry clearance visas by occupation and industry (SOC 2020), year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables#entry-clearance-visas-granted-outside-the-uk"
    },
    "Public Opinion (Most Important Issue)": {
        "source": "Ipsos - opinion-polls-most-important-issue-in-UK-Ipsos",
        "link": "https://migrationobservatory.ox.ac.uk/resources/briefings/uk-public-opinion-toward-immigration-overall-attitudes-and-level-of-concern/"
    },
    "Asylum Claims": {
        "source": "gov.uk - Asylum claims datasets, year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables"
    },
    "Small Boat Arrivals": {
        "source": "gov.uk - Illegal entry routes to the UK detailed dataset, year ending December 2025",
        "link": "https://www.gov.uk/government/statistical-data-sets/immigration-system-statistics-data-tables#illegal-entry-routes"
    }
}

# Determines what themes/mesos prepopulate the right-side macro when a dataset is chosen
DEFAULT_NARRATIVES = {
    "Foreign National Offender Returns": {"themes": ["migrants and crimes"], "mesos": []},
    "Offence Convictions": {"themes": ["migrants and crimes"], "mesos": ["Migrants are involved in violent crimes"]},
    "Immigration Demographics (Foreign-born)": {"themes": ["demographic aspects of migration"], "mesos": []},
    "Immigration Detention": {"themes": ["detention and deportation of migrants"], "mesos": []},
    "Immigration Returns": {"themes": ["detention and deportation of migrants"], "mesos": []},
    "Sponsored Work Visas": {"themes": ["work visas and sponsorship"], "mesos": []},
    "Public Opinion (Most Important Issue)": {"themes": ["public opinion on migration"], "mesos": []},
    "Asylum Claims": {"themes": ["asylum seeking"], "mesos": []},
    "Small Boat Arrivals": {"themes": ["small boats and Channel crossings"], "mesos": []},
}

DEFAULT_INCLUDED_CATEGORIES = {
    "Foreign National Offender Returns": ["Total FNO Returns"],
    "Offence Convictions": ["All offences", "Sexual offences", "Violence against the person"],
    "Immigration Demographics (Foreign-born)": ["All foreign-born", "Non-EU", "EU"],
    "Immigration Detention": ["Total People Detained"],
    "Immigration Returns": ["Total Returns"],
    "Sponsored Work Visas": ["Total Sponsored Work Visas","Information and communication", "Professional, scientific and technical activities", "Manufacturing","Construction", "Human health and social work activities"],
    "Public Opinion (Most Important Issue)": ["Immigration","NHS", "Economy", "EU", "Housing", "Defence"],
    "Asylum Claims": ["Ukraine", "Iran", "Total Asylum Claims", "Somalia", "Syria", "Eritrea"],
    "Small Boat Arrivals": ["Total Small Boat Arrivals"],
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
        df = df[df['source'].str.contains("aps", case=False, na=False)].reset_index(drop=True)
        
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

    elif dataset_name == "Immigration Returns":
        fp = os.path.join(data_dir, "returns-datasets-dec-2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_Ret_D01", header=1)
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df["Total Returns"] = pd.to_numeric(df["Number of returns"], errors="coerce")
        
        df = df.dropna(subset=["Year", "Total Returns"])
        df["Year"] = df["Year"].astype(int)
        
        # Aggregate by year
        return df.groupby("Year")["Total Returns"].sum().to_frame()


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
    
    elif dataset_name == "Asylum Claims":
        fp = os.path.join(data_dir, "asylum-claims-datasets-dec-2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_Asy_D01", header=1)
        df.columns = df.columns.str.strip()
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df["Claims"] = pd.to_numeric(df["Claims"], errors="coerce")
        df = df.dropna(subset=["Year", "Claims"])
        df["Year"] = df["Year"].astype(int)
        
        # 1. Get the total aggregation
        total_claims = df.groupby("Year")["Claims"].sum().to_frame(name="Total Asylum Claims")
        
        # 2. Pivot by Region
        if "Nationality" in df.columns:
            region_claims = df.pivot_table(index="Year", columns="Nationality", values="Claims", aggfunc='sum')
            # Combine the two so the multiselect gets the Total + all specific regions
            return pd.concat([total_claims, region_claims], axis=1).fillna(0)
        
        return total_claims
    
    elif dataset_name == "Small Boat Arrivals":
        fp = os.path.join(data_dir, "illegal-entry-routes-to-the-uk-dataset-dec-2025.xlsx")
        df = pd.read_excel(fp, sheet_name="Data_IER_D02", header=1)
        
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
        df["Arrivals"] = pd.to_numeric(df["Arrivals"], errors="coerce").fillna(0)
        df = df.dropna(subset=["Year"])
        
        # Restrict to 2016-2025 based on the original notebook logic
        df = df[(df["Year"] >= 2016) & (df["Year"] <= 2025)].copy()
        df["Year"] = df["Year"].astype(int)
        
        return df.groupby("Year")["Arrivals"].sum().to_frame(name="Total Small Boat Arrivals")
    
    return pd.DataFrame()
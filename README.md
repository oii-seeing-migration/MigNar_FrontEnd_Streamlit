# MigNar Application
Streamlit application to explore migration‑related narrative frames and meso narratives in UK news and Parliamentary documents.
The repo also contains a few codes for generating the plots and numeric results for the publication coming out of the analyses. Thus, we organise the sections in two sections 

## Live App Link in Streamlit Cloud
**https://mignar.streamlit.app/**


## App Files

- **`navigation_page.py`**: The login page of the app. It's also the main script of the app meaning that Streamlit Cloud identifies the app based on it. This, **it should not be renamed**.
- **`pages/`**: The directory containing all the pages in the app. Each script is a separate page. Read the `pages/00_App_Instructions.py` for page by page explanation.
- **`taxonomy/meso_narratives_revision_[0|1|2].py`**: The narratives taxonomy, all versions. It's in dict format, where the `themes` are the `keys` and `values` are lists of `[meso-narrative, natural stance of the narrative]`.
- **`data/`**: `data/stance_monthly.parquet`, `data/themes_monthly.parquet`, `data/meso_monthly.parquet` monthly aggregates of the narratives/stances created by the backend of the project. They are the backbone of all the plots in this repo/app. I have the aggregates to post-2016 to make the app lighter and avoid crashes. Later, you can change it in `lib/data_loader.py`.
`data/meso_samples.parquet` is sample of documents per meso-narrative used for the page `pages/03_Narratives_on_Articles.py` to visualise the detected narratives on documents. `data/real-stats/` contains real-world migration-related stats in the UK used in the page `pages/07_RealWorldStats_Dashboard.py`.
- **`.streamlit/`**: The directory for essential settings files. `.streamlit/config.toml` configures some Streamlit built-in settings such as theme colour.
- **`lib/`**: Essential repetitive scripts frequently reused in the repo.
    - **`lib/auth.py`**: The authentication process for connecting to the supabase database; used for login, taxonomy evaluation, and validation of LLM labels.
    - **`lib/data_loader.py`**: Loads the major data with approperiate caching.
    - **`lib/real_world_stats.py`**: Configures some essential settings for the page `pages/07_RealWorldStats_Dashboard.py`; such as defaults and descriptions per real-world stat.
    - **`lib/sidebar_style.py`**: Configures the style of sidebar in the app, which includes the shown names of pages, the pages' icons, and the order of pages.

## Paper Files

- **`plots_for_paper.ipynb`**: The plots for the paper.
- **`validation_and_model_comparison.ipynb`**: The code for validation and model comparison. Hidden for double-blind revision.
- **`data/validation/`**: The Excel files for validation. Hidden for double-blind revision.
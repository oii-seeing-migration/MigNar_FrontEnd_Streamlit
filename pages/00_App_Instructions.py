import streamlit as st

st.set_page_config(
    page_title="Instructions - MigNar",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png"
)

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()

st.title("📖 MigNar Platform Instructions")

st.markdown("""
Welcome to the **MigNar Platform**! This application is designed to help researchers explore, validate, and refine artificial intelligence extractions of migration narratives.

Below is a step-by-step guide to the functionalities of the core pages of the platform and how you can use them.
""")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Page 1: Annotator Guide
# ═══════════════════════════════════════════════════════════════════════════
st.header("📝 Annotator Guide")

st.markdown("""
**Purpose**:  
If you are an annotator willing to participate in the evaluation and refinement of whether migration-related narratives taxonomy or the validation of AI-extracted narratives per article, this page serves as your required reference manual. Before performing any evaluation tasks on the platform, you should read this guide to understand the project's goals, standard terminologies, and the rules of the road. 

**Key Functionalities & How to Use**:
- **Understand the Hierarchy**: Learn the difference between high-level **Themes** (e.g., *"Migrants & Crime"*) and granular **Meso Narratives** (e.g., *"Migration brings dangerous offenders"*).
- **Learn the Rating Criteria**: Get familiar with the exact definitions of the labels you will be applying later, such as *"Good"*, *"Too Broad"*, *"Too Narrow"*, or *"Duplicate"*.
- **Best Practices**: Rely on this document as a reminder to avoid normative political judgments during annotation. Your goal is to assess if the narrative structure cleanly explains the text, not if you agree with the text itself.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Page 2: Narratives Taxonomy
# ═══════════════════════════════════════════════════════════════════════════
st.header("📚 Narratives Taxonomy")

st.markdown("""
**Purpose**:  
This is the workspace for observing, evaluating, and refining the structure of the *Taxonomy itself*. You are not grading individual news articles here; you are determining whether the overall list of narratives proposed by the researchers and AI makes logical sense entirely as universal categories.

**Key Functionalities & How to Use**:
- **Login to Save**: You must be logged in to save your annotations. Unauthenticated users have view-only access.
- **Filtering & Navigation**: Use the sidebar to filter the dataset by specific "Taxonomy Revision Versions", "Source Domains", or "Models".
- **Annotate Narratives**: For each Meso Narrative under a Theme, use the dropdown to assign a label (e.g., *Good*, *Duplicate*, *Wrong Theme*). You can also leave comments if you choose a problematic label to explain your reasoning.
- **Suggest Additions**: If an important theme or narrative is missing, use the "➕ Suggest New" fields at the bottom of a specific theme block or at the very bottom of the page.
- **Jump to Context**: If a narrative's wording confuses you, click the **"View on Articles"** button next to it. This redirects you to real-world textual examples of that narrative in our database.
- **Save**: Never forget to click the floating **"💾 Save All Changes"** button at the bottom right before navigating away to log your progress!
""")

# ═══════════════════════════════════════════════════════════════════════════
# Page 3: Narratives on Articles
# ═══════════════════════════════════════════════════════════════════════════
st.header("📰 Narratives on Articles")

st.markdown("""
**Purpose**:  
This page allows you to dig into the raw data. It shows actual news articles and parliamentary transcripts alongside the specific text fragments the AI models highlighted to justify their extractions, allowing you to both view and understand narratives in potential contexts and grade empirical AI performance.

**Key Functionalities & How to Use**:
- **Filter the Corpus**: Use the sidebar to drill down by `Source Table`, `Stance`, `Theme`, or `Meso Narrative`. You can also use the minimum agreement slider (e.g., "Only show me articles where at least 3 models agreed on this narrative").
- **Select an Article**: Use the "Record" dropdown to pick a specific article or transcript to review.
- **Review Highlights**: The body of the article will feature colored highlights. Hovering your mouse over a highlighted text segment reveals exactly which AI model flagged it and what Meso Narrative it mapped to.
- **Validate the AI (Grade the Models)**: 
    - **Stance Verification**: Scroll to the bottom to see how the group of models voted on the overarching "Stance" (`Open`, `Restrictive`, `Neutral`, and `Irrelevant`) of the document, and log your independent human judgment to grade them.
    - **Narrative Verification**: For each extracted Meso Narrative, review the highlighted text, then assign the model a score from 0 to 5 based on how perfectly it interpreted the text segment. 
""")

# ═══════════════════════════════════════════════════════════════════════════
# Dashboards Section
# ═══════════════════════════════════════════════════════════════════════════
st.header("📊⚖️📈 Analytic Dashboards")

st.markdown("""
The platform includes three distinct dashboards to analyse the migration discourse from different analytical angles. 
""")

st.subheader("📊 Aggregative Dashboard")
st.markdown("""
**Purpose**:  
Get a broad, big-picture understanding of the total volume and distribution of stances, themes, and meso narratives across the entire corpus.

**Key Functionalities & How to Use**:
- **Filters**: Use the sidebar to restrict the data to a specific `Model` (or the `Ensemble` consensus), a `Taxonomy Version`, a `Date range`, and specific `Source domains`.
- **Macros**: Adjust the "Min articles per label" to hide infrequent, noisy narrative detections, and adjust the "Top N items" to expand or contract the bar charts.
- **Visuals**: 
  - **Stance Bubble Chart**: See how different media outlets lean overall (Open vs. Restrictive).
  - **Bar Charts**: Instantly identify the most common Themes and Meso Narratives within your filtered parameters.
""")

st.subheader("⚖️ Comparative Dashboard")
st.markdown("""
**Purpose**:  
Contrast how different groups, media sources, or time periods discuss migration. For example, you can compare narrative usage between left-leaning and right-leaning UK media.

**Key Functionalities & How to Use**:
- **Define Filter A & Filter B**: In the sidebar, set up two distinct groups. For instance, set Filter A to right-wing domains and Filter B to left-wing domains.
- **Adjust Macros**: Set up a minimum support threshold to ensure you are only comparing narratives with sufficient data.
- **Analyse Divergence**: The dashboard generates diverging bar charts for both Themes and Meso Narratives. Bars extending to the left show narratives structurally favoured by Group A, while bars to the right show those heavily favoured by Group B.
""")

st.subheader("📈 Temporal Dashboard")
st.markdown("""
**Purpose**:  
Track the temporal evolution, rise, and decline of specific stances, themes, and meso narratives over time to understand how real-world events shape the discourse.

**Key Functionalities & How to Use**:
- **Granularity & Metrics**: Toggle between `Monthly` or `Yearly` granularity. Choose to view the Y-axis as raw `Count` (absolute volume) or `Percentage` (prevalence relative to the total discourse in that period).
- **Domain Split**: Note that you can filter the domain for "Stance" independently from the domain for "Narratives".
- **Interactive Line Charts**: Hover over lines to trace how specific issues (e.g., discussions around border security or specific policies) spike or diminish across your selected date range.
""")



# ═══════════════════════════════════════════════════════════════════════════
# Page 7: Real-World Stats Dashboard
# ═══════════════════════════════════════════════════════════════════════════
st.header("🌍 𝗗𝗮𝘀𝗵𝗯𝗼𝗮𝗿𝗱: Real-World Stats")

st.markdown("""
**Purpose**:  
Correlate real-world migration statistics (such as visa issuances, demographics, or public polling) directly against the prevalence of media and political narratives over time. This allows you to visually investigate whether the volume of specific migration narratives is driven by actual real-world events or by ideological framing.

**Key Functionalities & How to Use**:
- **Select Datasets**: Choose a real-world statistic from the sidebar (e.g., Public Opinion or Work Visas) to plot on the left Y-axis.
- **Overlay Narratives**: Pick specific Themes and Meso Narratives to overlay on the right Y-axis. The dashboard automatically suggests relevant theoretical narratives based on the real-world dataset you selected.
- **Four-Panel Comparison**: Simultaneously compare these dual-axis trends across four distinct domain clusters (Defaulting to Left-Leaning Media, Right-Leaning Media, Labour, and Conservatives) to see how different factions react to the same real-world data.
- **Dynamic Scaling**: Use the sidebar sliders to constrain the time range and adjust the narrative Y-axis range (minimum and maximum percentages) to proportionally align and compare the relationship between the separate curves.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Page 8: Feedback
# ═══════════════════════════════════════════════════════════════════════════
st.header("💬 Feedback")

st.markdown("""
**Purpose**:  
A direct line to the platform developers to report bugs, suggest features, flag usability issues, or share general thoughts about the data quality.

**Key Functionalities & How to Use**:
- **Submit Feedback (Authentication Required)**: Select the type of feedback (Bug, Feature, Usability, etc.), link it to a specific page if applicable, mark the severity, and provide a clear description.
- **Track Submissions**: Use the "My Submissions" tab to view the history of your feedback and see its current status (e.g., Open, In Progress, Resolved).
""")

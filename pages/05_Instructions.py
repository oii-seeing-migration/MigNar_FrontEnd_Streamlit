import streamlit as st

st.set_page_config(
    page_title="Instructions - MigNar",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png"
)

st.title("📖 MigNar Platform Instructions")

st.markdown("""
Welcome to the MigNar platform! This guide explains how to use the different features of this application.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Hierarchical Labeling System
# ═══════════════════════════════════════════════════════════════════════════
st.header("1. Understanding the Hierarchical Labeling System")

st.markdown("""
MigNar uses a **three-level hierarchical approach** to analyze migration narratives in news articles:

### 🔹 Level 1: Stance
The **stance** represents the overall sentiment or position toward migration expressed in an article. The system identifies three types:
- **Pro-migration**: Articles that express positive views toward migration, migrants, or migration policies
- **Anti-migration**: Articles that express negative views or opposition to migration
- **Neutral/Mixed**: Articles that present balanced perspectives or don't express a clear stance

### 🔹 Level 2: Themes
**Themes** are high-level topics or frames used to discuss migration. Each article may contain multiple themes. Examples include:
- *Economic Impact*
- *Security and Crime*
- *Humanitarian Concerns*
- *Cultural Integration*
- *Border Control*
- *Political Debate*

Themes organize narratives into broad categories that help understand the primary focus of discourse.

### 🔹 Level 3: Meso Narratives
**Meso narratives** are specific storylines or arguments within each theme. They represent the concrete ways themes are discussed. For example, under the "Economic Impact" theme, you might find:
- "Migrants take jobs from native workers"
- "Migrants contribute to economic growth"
- "Migrants burden the welfare system"

Meso narratives are the most granular level and capture the actual narrative content being communicated.

### Hierarchical Structure
The relationship works as follows:

Article
├── Stance: Anti-migration
├── Theme: Economic Impact
│ ├── Meso Narrative: "Migrants burden the welfare system"
│ └── Meso Narrative: "Economic strain from uncontrolled migration"
└── Theme: Security and Crime
└── Meso Narrative: "Border security is insufficient"
            

Each article can have:
- **One stance** (the dominant position)
- **Multiple themes** (different topics discussed)
- **Multiple meso narratives** (specific storylines within each theme)
""")

# ═══════════════════════════════════════════════════════════════════════════
# Section 2: Using the Dashboard Pages
# ═══════════════════════════════════════════════════════════════════════════
st.header("2. Using the Dashboard Pages")

st.markdown("""
The MigNar platform includes three main dashboard views for analyzing migration narratives across different dimensions.
""")

st.subheader("📊 Aggregative Dashboard")
st.markdown("""
**Purpose**: View overall volume and distribution of narratives across all articles in your dataset.

**What you can do**:
- See the total count of articles by stance (pro-migration, anti-migration, neutral)
- Explore which themes appear most frequently
- Identify the most common meso narratives
- Compare narrative volume across different news sources
- Filter by model (if multiple AI models were used for analysis)

**Best for**: Getting a big-picture understanding of what narratives dominate the discourse.

**How to use**:
1. Select your preferred model from the sidebar (if applicable)
2. Choose a date range to focus on specific time periods
3. Optionally filter by news source domain
4. View the bar charts showing top themes and meso narratives by article count
""")

st.subheader("⚖️ Contrastive Dashboard")
st.markdown("""
**Purpose**: Compare how narratives differ across different categories (e.g., news sources, stances, time periods).

**What you can do**:
- Compare theme distribution between pro-migration and anti-migration stances
- Analyze how different news outlets frame migration differently
- Identify narratives unique to certain sources vs. those appearing everywhere
- Spot narrative contrasts and similarities across dimensions

**Best for**: Understanding diversity and polarization in migration discourse.

**How to use**:
1. Select the comparison dimension (e.g., stance, source)
2. Choose specific categories to compare
3. Examine side-by-side visualizations showing narrative differences
4. Look for exclusive narratives (appearing in only one category) vs. shared narratives
""")

st.subheader("📈 Temporal Dashboard")
st.markdown("""
**Purpose**: Track how narratives change over time.

**What you can do**:
- See trends in stance distribution over months or years
- Identify when specific themes or narratives emerge or decline
- Correlate narrative shifts with real-world events
- Analyze seasonality or cyclical patterns in migration discourse

**Best for**: Understanding narrative evolution and event-driven changes.

**How to use**:
1. Select the time aggregation level (daily, weekly, monthly, yearly)
2. Choose specific themes or meso narratives to track
3. Use the date range selector to zoom into periods of interest
4. Examine line charts showing narrative frequency over time
""")

# ═══════════════════════════════════════════════════════════════════════════
# Section 3: Annotation Instructions
# ═══════════════════════════════════════════════════════════════════════════
st.header("3. Annotation Instructions for Taxonomy Quality Control", anchor="annotation-guide")

st.markdown("""
The **Narratives Taxonomy** page allows you to review and rate the quality of meso narratives identified by our AI system. 
Your annotations help improve the taxonomy by identifying issues with how narratives have been extracted or categorized.
""")

st.info("**💡 Before you start**: Sign in using the main page to save your annotations. Unsigned users can browse but cannot save ratings.")

st.subheader("🏷️ What Each Label Means")

st.markdown("""
When reviewing each meso narrative, you'll choose from the following quality labels:

---

### ✅ **Good**
**Select this when**: The narrative is well-formed, specific enough to be meaningful, distinct from others, and correctly categorized.

**Criteria**:
- ✓ Clear and coherent statement
- ✓ Represents a specific, identifiable storyline
- ✓ Is distinct from other narratives (not a duplicate)
- ✓ Has appropriate specificity (not too generic, not too narrow)
- ✓ Placed in the correct theme

**Example**:
- Theme: *Economic Impact*
- Meso Narrative: "Migrants contribute to economic growth through entrepreneurship"
- ✅ This is **good** because it's specific, actionable, and clearly distinct.

---

### 🔄 **Duplicate Narrative**
**Select this when**: This narrative is essentially the same as another narrative already in the taxonomy, just worded differently.

**Criteria**:
- Two or more narratives express the same core idea
- Minor wording differences don't change the meaning
- Should be merged into a single narrative

**Example**:
- Narrative A: "Migrants take jobs from native workers"
- Narrative B: "Migrants compete with locals for employment"
- 🔄 These are **duplicates** — they express the same underlying narrative.

**What happens**: Duplicate narratives will be reviewed for merging in future taxonomy revisions.

---

### 🔬 **Too Specific**
**Select this when**: The narrative is so narrowly defined that it applies to very few articles or situations.

**Criteria**:
- Overly detailed or contextually limited
- References specific events, individuals, or locations unnecessarily
- Could be generalized without losing meaning
- Has very low article count relative to similar narratives

**Example**:
- ❌ Too specific: "Boris Johnson's 2019 proposal to limit EU migration after Brexit"
- ✅ Better: "Post-Brexit immigration policy proposals"

**Why it matters**: Meso narratives should be generalizable across multiple contexts while still being meaningful.

---

### 🌐 **Too Generic**
**Select this when**: The narrative is so broad or vague that it doesn't provide meaningful analytical value.

**Criteria**:
- Could apply to almost any migration discussion
- Lacks specificity about what's actually being said
- Essentially just restates the theme itself
- Doesn't identify a distinct storyline

**Example**:
- ❌ Too generic: "Migration is discussed in political debates"
- ✅ Better: "Politicians exploit migration fears for electoral gain"

**Why it matters**: Generic narratives don't help us understand the actual arguments being made.

---

### ⚠️ **Leave Blank**
**Select this when**: You're unsure, need more context, or want to skip this narrative.

**When to use**:
- You don't have enough information to judge
- You need to see example articles first
- The narrative is edge-case and you're uncertain

**Note**: Blank annotations are not saved to the database.

---
""")

st.subheader("📋 Annotation Workflow")

st.markdown("""
**Step-by-step process**:

1. **Sign in** via the main page (required to save annotations)

2. **Navigate** to the "Narratives Taxonomy" page

3. **Select** the revision you want to review (usually the latest)

4. **Browse** through themes — they're sorted by article count (most common first)

5. **For each narrative**:
   - Read the meso narrative text
   - Check the article count (how many articles contain this narrative)
   - Click "View on Articles" to see examples if needed
   - Select the appropriate quality label from the dropdown
   - Your choice is **automatically saved** when you select an option

6. **Track progress** — Your annotation count is shown at the bottom of the page

7. **Use filters** to focus:
   - Filter by source domain to see outlet-specific narratives
   - Filter by model to compare different AI analyses
   - Adjust "Min count" to hide rare narratives (marked as "NEW")

---

### 🎯 Tips for Good Annotation

- **View examples**: When in doubt, click "View on Articles" to see how the narrative appears in actual articles
- **Think hierarchically**: Remember that meso narratives should be more specific than their parent theme, but not so specific they only apply once
- **Consider mergeability**: If two narratives could be combined without loss of meaning, mark one as duplicate
- **Be consistent**: Try to apply the same standards across all narratives in a session
- **Take breaks**: Annotation fatigue can reduce quality — review in focused sessions

---

### 🔢 Understanding "NEW" Narratives

Narratives marked with a **(NEW)** tag weren't in the original taxonomy but appeared frequently in the data. These might be:
- Genuinely new storylines that should be added
- Variations of existing narratives (potential duplicates)
- Overly specific phrases that shouldn't be separate narratives
- Noise from the extraction process

Pay special attention to NEW narratives — your annotations are especially valuable here!

---

### ❓ Questions or Issues?

If you encounter narratives that don't fit any category, or if you notice systemic issues with the taxonomy, please contact the research team.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Additional Resources
# ═══════════════════════════════════════════════════════════════════════════
st.header("4. Additional Resources")

st.markdown("""
### 🔗 Quick Links
- **Narratives Taxonomy**: Review and annotate narrative quality
- **Narratives on Articles**: Explore individual articles and their extracted narratives
- **Aggregative Dashboard**: View overall narrative distribution
- **Contrastive Dashboard**: Compare narratives across categories
- **Temporal Dashboard**: Track narrative trends over time

### 📧 Support
For technical issues, questions about the methodology, or suggestions for improvement, please contact the MigNar research team.

### 🔄 Taxonomy Versions
The taxonomy is versioned and periodically updated based on:
- New data collection
- Annotator feedback
- Refinement of extraction algorithms
- Merging of duplicate narratives

Always check which revision you're working with on the Taxonomy page.
""")

st.divider()

st.caption("MigNar Platform — Migration Narratives Analysis Tool")
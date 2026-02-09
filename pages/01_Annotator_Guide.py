import streamlit as st

st.set_page_config(
    page_title="Annotator Guide - MigNar",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png"
)

from lib.sidebar_style import apply_sidebar_names
apply_sidebar_names()


st.title("📝 Instructions for Annotators")

st.info("These notes guide annotators working on the **[Seeing Migration Narratives (MigNar)](https://mignar.streamlit.app/)** project.")

# ═══════════════════════════════════════════════════════════════════════════
# Introduction
# ═══════════════════════════════════════════════════════════════════════════
st.header("Introduction")

st.markdown("""
The **Seeing Migration Narratives** project uses AI tools to build a detailed picture of what narratives about migration 
exist in public debates (media and policy) in the UK. 

Through a process of prompting Large Language Models (LLMs), we have collated millions of pieces of text dealing with 
migration and extracted narratives from them in a hierarchical form:

- **Narrative Themes**: represent high-level topical categories under which migration is discussed.
- **Meso Narratives**: are semi-specific storylines or arguments within each theme.

There are **two distinct annotation tasks** in this project:
""")

col1, col2 = st.columns(2)
with col1:
    st.info("""
    **Task 1: Annotating the Taxonomy**
    
    Review and refine the *list* of themes and meso narratives itself—ensuring the taxonomy is comprehensive, well-organised, and free of duplicates.
    """)

with col2:
    st.warning("""
    **Task 2: Validating LLM Labels**
    
    Check whether the LLMs have *correctly applied* taxonomy labels to specific articles and text fragments.
    """)

st.markdown("---")
st.markdown("---")
st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# TASK 1: ANNOTATING THE TAXONOMY
# ═══════════════════════════════════════════════════════════════════════════
st.header("Task 1: Annotating the Taxonomy")

st.success("""
**What this task is about:**

You are evaluating the *taxonomy itself*—the structured list of themes and meso narratives. Your job is to assess whether each narrative entry is:
- Well-worded and clear
- Neither too broad nor too narrow
- Not a duplicate of another entry
- Correctly placed under its theme

**What this task is NOT about:**

You are **not** judging whether the LLM correctly labelled a specific article with a narrative. That is a separate task (Task 2). Here, you're only assessing whether the narrative *as a concept* belongs in the taxonomy.
""")

# ── What is the Narrative Taxonomy? ────────────────────────────────────────────
st.subheader("What is the Narrative Taxonomy?")

st.markdown("""
The **taxonomy** is the structured list of themes and meso narratives that the LLMs use when annotating texts.

**Your role as annotators** is to refine this list into a comprehensive and well-organised collection that embraces 
all possible recurring narratives about migration to the UK.

Currently, we have instructed LLMs to **suggest new narratives** when they encounter content that doesn't fit 
existing entries. Your task is to review both:
- The **predefined narratives** (numbered for easy reference)
- The **LLM-suggested additions** (marked as NEW, not numbered)

You will decide which narratives to **keep**, **merge**, **generalise**, or **discard**.

Once finalised, the taxonomy becomes **fixed**—the LLMs will only select from this approved list, ensuring 
consistent annotation across all documents.
""")

# ── Numbering System ───────────────────────────────────────────────────────────
st.subheader("Numbering System")

st.markdown("""
All predefined themes and meso narratives are **numbered** for easy reference:

- **Themes** are numbered as `T1`, `T2`, `T3`, etc.
- **Meso narratives** are numbered as `1.1`, `1.2`, `2.1`, `2.2`, etc. (theme number + narrative number)

**Example:**
- `T5` refers to the 5th theme
- `5.3` refers to the 3rd meso narrative under theme 5

You can use these numbers in your comments to refer to other narratives. For example:
> *"This is a duplicate of 3.7"* or *"Should be moved to T2"*

**Note:** NEW narratives (suggested by LLMs) and NEW themes are **not numbered** since they haven't been added to the official taxonomy yet.
""")

# ── Broad Objectives ───────────────────────────────────────────────────────────
st.subheader("Broad Objectives")

st.markdown("""
Your role at this stage of the project is to:
""")

objectives = [
    "**Review narrative themes and meso narratives** to ensure that themes correctly describe the set of meso narratives beneath them and are not duplicates of other (perhaps slightly differently worded) themes.",
    "**Clarify that meso narratives are specific and relevant** to the themes under which they sit.",
    "**Ensure meso narratives are MESO (not macro or micro)**, meaning that they are broad enough to cover various situations/stories—and not so specific that they only describe one particular story.",
    "**Validate that the LLMs are correctly tagging** narrative elements (i.e., ideas/stories) to specific meso narratives.",
]

for obj in objectives:
    st.markdown(f"- {obj}")

st.warning("""
**Important — Hierarchical Process**: 

The LLM narrative extraction is hierarchical:
1. **First iteration**: The LLM selects themes *without* being exposed to meso narratives.
2. **Second iteration**: The LLM is fed the selected themes in the first iteration and the meso narratives that fall under them.

This means **theme wording must hint sufficiently to the meso narratives**. If a meso narrative's wording does not 
clearly associate with its theme in the first round, it may never get the chance to be selected later.
""")

# ── Avoiding Normative Judgements ──────────────────────────────────────────────
st.subheader("Avoiding Normative Judgements")

st.error("""
**We are NOT trying to:**
- Make judgements about the articles
- Challenge assumptions, facts, or terminology
- Criticise the political language used

Your role is to assess the taxonomy structure and quality—not to evaluate the content of the narratives themselves.
""")

# ── Annotation Process ─────────────────────────────────────────────────────────
st.subheader("Annotation Process")

st.markdown("#### Step 1: Sign In and Navigate")
st.markdown("""
1. Sign in to the [MigNar app](https://mignar.streamlit.app/)
2. Navigate to the **[Narratives Taxonomy](https://mignar.streamlit.app/Narratives_Taxonomy)** page
3. You will see **themes highlighted in blue** (with numbers like T1, T2, etc.), with a list of numbered meso narratives underneath each one
""")

st.markdown("#### Step 2: Initial Read-Through")
st.markdown("""
**Before making any changes or suggestions**, read through the **full list of themes** and ideally skim through the meso narratives so you have a reasonable 
sense of the whole.""")

st.markdown("#### Step 3: Annotate Each Theme and Its Meso Narratives")
st.markdown("""
Once you've completed the initial read-through, look at the themes and the meso narratives below them.

Immediately underneath each blue-highlighted theme, you will see:
- A **dropdown menu** for your assessment (Label)
- A **comments box**
""")

st.markdown("**Use the dropdown to select one of the following:**")

# Row 1: Good, Too Broad, Too Narrow
col1, col2, col3 = st.columns(3)

with col1:
    st.success("**✅ Good**")
    st.markdown("The theme/narrative is well-formed, specific, distinct, and correctly placed.")

with col2:
    st.warning("**🔄 Too Broad**")
    st.markdown("Too vague or generic—doesn't mean anything clear.")

with col3:
    st.info("**🔬 Too Narrow**")
    st.markdown("Too specific—will only apply to one particular story or event.")

# Row 2: Duplicate, Wrong Theme, Poor Wording
col4, col5, col6 = st.columns(3)

with col4:
    st.error("**📋 Duplicate**")
    st.markdown("Same as another entry (even if phrased slightly differently).")

with col5:
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; border: 1px solid #9e9e9e; background-color: #f5f5f5;">
    <strong>🔀 Wrong Theme</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("The meso narrative should be under a different theme.")

with col6:
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; border: 1px solid #6c5ce7; background-color: #e8e4fc;">
    <strong>✏️ Poor Wording</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("The meaning is unclear or awkwardly phrased—suggest a reword in comments.")

# Row 3: Other Issues
col7, col8, col9 = st.columns(3)

with col7:
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; border: 1px solid #636e72; background-color: #dfe6e9;">
    <strong>⚠️ Other Issues</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("Out of scope of migration, or problematic for any other reason—explain in comments.")

st.markdown("""
**What is a good theme or meso narrative?**
- An **ideal good theme** would be specific enough to hint at a distinct set of meso narratives under a certain topic, but not so specific that it only applies to one particular story. More importantly, the theme should NOT have a loaded language that misses one side of the debate (e.g., "Migrants as Criminals" may only reflect the anti-migration stance under this topic and should be reworded to something more neutral like "Migrants & Crime" which captures the topic without bias).
- An **ideal good meso narrative** should be specific enough to capture a clear storyline or argument, but broad enough to apply to multiple stories/events. For example, "Migrants take jobs from native workers" is a good meso narrative because it captures a specific idea but can apply to many different articles and contexts. In contrast, "Migrants take jobs from native workers in the UK hospitality industry in 2023" would be too narrow because it only applies to one specific story. Unlike themes, meso narratives should have a clear stance (pro-migration, anti-migration, or neutral) since they represent specific storylines that are often inherently biased.
""")

st.markdown("""
**When to leave a comment:**
- If you think the theme could be reworded to better capture the meso narratives, note this in the comment box
- If you marked something as **"Duplicate"**, leave a comment mentioning the exact narrative (e.g., *"duplicate of 3.7"*)
- If you chose **"Wrong Theme"**, suggest the theme it should be moved to (e.g., *"should be under T2"*), or propose a new theme
- If you chose **"Poor Wording"**, suggest how you would reword it in the comments
- If you chose **"Other Issues"**, explain the problem (e.g., out of scope, factually incorrect, etc.)
""")


# st.markdown("#### Step 4: Assess Meso Narratives")
# st.markdown("""
# After assessing the theme, look at its **meso narratives** (numbered like 1.1, 1.2, etc.) and undertake the same actions:
# - Use the dropdown to select: **Good**, **Too Broad**, **Too Narrow**, **Duplicate**, **Wrong Theme**, **Poor Wording**, or **Other Issues**
# - Add any comments as needed
# - Use the numbering system to reference other narratives in your comments
# """)

st.info("""
**📰 Optional: View Narratives Articles**

If you wish to see a random selection of the content used to generate these meso narratives:
1. Click the **"View on Articles"** button (this will take you to the **[Narratives on Articles](https://mignar.streamlit.app/Narratives_on_Articles)** page)
2. Use the Record menu to browse the articles
3. See the text the LLMs have identified as relevant to those meso narratives

You do **not** need to look at every article, but they may help you orient yourself or understand confusing meso narratives.

**Remember:** When viewing articles, you're checking whether the *narrative concept* makes sense—not whether the LLM correctly applied it to that specific article.

If the content is confusing or obviously wrong—even after reviewing articles—please note this in the comment.
""")


st.success("""
**💡 Optional: Suggest New Themes + Meso Narratives**

- **New Meso Narratives**: Use the "➕ Suggest New" row at the bottom of each theme. Separate multiple suggestions with semicolons (`;`).
- **New Themes**: Use the "🌟 Suggest New Themes" section at the very bottom of the page. Provide a theme name and its meso narratives.
""")

st.error("""
**⚠️ SAVE FREQUENTLY!**

There is a **"💾 Save Progress"** button at the end of each theme. **Click it after finishing each theme!**

The app may occasionally log you out due to session timeouts. If you don't save frequently, **you may lose your work**. 

**Best practice:** Complete one theme → Click Save → Move to the next theme.
""")

# ── Quick Reference Card ───────────────────────────────────────────────────────
st.subheader("📋 Quick Reference Card")

st.markdown("""
| Label | When to Use | Comment Required? |
|-------|-------------|-------------------|
| **Good** | Well-formed, specific, distinct, and correctly placed | No |
| **Too Broad** | Too vague or generic—doesn't mean anything clear | **Optional** — write a narrowed down version if needed |
| **Too Narrow** | Too specific—only describes one particular story or event | **Optional** — write a broadened down version if needed |
| **Duplicate** | Same as another entry (even if worded differently) | **Encouraged** — specify which (e.g., "duplicate of 3.7") |
| **Wrong Theme** | Meso narrative belongs under a different theme | **Encouraged** — suggest where (e.g., "move to T2") |
| **Poor Wording** | Meaning is unclear or awkwardly phrased | **Encouraged** — suggest reword |
| **Other Issues** | Out of scope of migration or problematic for other reasons | Optional |
""")

st.markdown("""
**Numbering Reference:**
- Themes: `T1`, `T2`, `T3`, ...
- Meso narratives: `1.1`, `1.2`, `2.1`, `2.2`, ...
- Use these in comments to cross-reference other items
""")

st.markdown("---")
st.markdown("---")
st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════
# TASK 2: VALIDATING LLM LABELS
# ═══════════════════════════════════════════════════════════════════════════
st.header("Task 2: Validating LLM Labels")

st.warning("""
**What this task is about:**

Now that we have a taxonomy, we need to verify that the LLMs are *correctly applying* the labels to articles. In this task, you will:

- Review articles that have been labelled by multiple LLMs
- Judge whether the LLM's **narrative labels** are correct for each article
- Optionally suggest **missing narratives** that the LLMs failed to identify
- Provide your own **stance assessment** (*open*, *restrictive*, *neutral*, or *irrelevant*) to compare against the LLMs' stance predictions
""")

# st.markdown("""
# **Key difference from Task 1:**

# | Task 1: Taxonomy Annotation | Task 2: Label Validation |
# |-----------------------------|--------------------------|
# | Is this narrative *well-defined*? | Is this narrative *correctly applied* to this article? |
# | Does it belong in the taxonomy? | Does the article actually express this narrative? |
# | Is the wording clear? | Did the LLM identify the right text fragment? |
# """)

# ── Getting Started ────────────────────────────────────────────────────────────
st.subheader("Getting Started")

st.markdown("""
You will receive an **Excel spreadsheet** containing a random sample of articles to validate. Each row in the spreadsheet contains a link that takes you directly to that article's validation page.

**Your workflow is simple:**
1. Open the Excel file
2. Click on a link to open an article
3. Complete the validation on the webpage
4. Return to Excel and move to the next article
""")

st.info("""
**📋 You don't need to edit anything in the Excel file** — it's just a list of links to help you navigate through your assigned articles.
""")

# ── The Validation Page ────────────────────────────────────────────────────────
st.subheader("The Validation Page")

st.markdown("""
When you click a link from the Excel file, you'll be taken to the **[Narratives on Articles](https://mignar.streamlit.app/Narratives_on_Articles)** page showing that specific article.

**What you'll see:**
1. **Article title and source** at the top
2. **Article body** with highlighted text fragments (yellow = narrative detected, blue = selected narrative filter)
3. **Validation form** below the article with three sections to complete
""")

# ── Signing In ─────────────────────────────────────────────────────────────────
st.subheader("Step 1: Sign In")

st.markdown("""
Before you can save any validations, you must be signed in.

1. Check the **sidebar** on the left — it will show whether you're signed in
2. If not signed in, click the link to go to the **Sign In page**
3. Once signed in, return to the article (click the link from Excel again)
""")

st.error("""
**⚠️ Important:** If you're not signed in, you can view the article but **cannot save your validations**. Always check that you see the green "✅ Signed in" message before starting.
""")

# ── Understanding the Article View ─────────────────────────────────────────────
st.subheader("Step 2: Read the Article")

st.markdown("""
The article body will display with **highlighted text fragments**:
""")

col1, col2 = st.columns(2)
with col1:
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #fff59d;">
    <strong>Yellow highlights</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("Text fragments where LLMs detected a narrative")

with col2:
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #80deea;">
    <strong>Blue highlights</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("The currently selected meso narrative (if filtered)")

st.markdown("""
**Tip:** Hover over any highlighted text to see which model identified it and what narrative theme/meso narrative was assigned.

Read through the article to understand its content and stance toward migration before moving to the validation form.
""")

# ── Validating Narratives ──────────────────────────────────────────────────────
st.subheader("Step 3: Validate Narrative Annotations")

st.markdown("""
Below the article, you'll see a table listing all the narrative annotations made by the LLMs.

**The table shows:**
| Column | Description |
|--------|-------------|
| **Model** | Which LLM made this annotation (hidden by default to avoid bias) |
| **Theme** | The narrative theme identified |
| **Meso Narrative** | The specific meso narrative assigned |
| **Fragment** | The text fragment from the article |
| **Score** | Your validation score (you fill this in) |
""")

st.info("""
**👁️ Spoiler Feature:** To avoid bias, **model names are hidden** behind an expander (👁️ icon). 

**Best practice:** Score the annotation first based on Theme, Meso Narrative, and Fragment — then reveal the model name if you're curious.
""")

st.markdown("""
**Scoring Guide:**

For each annotation, select a score from **0 to 5**:
""")

score_col1, score_col2 = st.columns(2)
with score_col1:
    st.error("**0-2 = Incorrect**")
    st.markdown("""
    - **0**: Completely wrong — the narrative doesn't appear in the article at all
    - **1**: Mostly wrong — very weak or tangential connection
    - **2**: Partially wrong — some connection but misapplied
    """)

with score_col2:
    st.success("**3-5 = Correct**")
    st.markdown("""
    - **3**: Acceptable — the narrative is present but could be better matched
    - **4**: Good — clear and appropriate annotation
    - **5**: Perfect — exactly right narrative for this text
    """)

st.markdown("""
**Leave blank (—)** if you want to skip a particular annotation.
""")

# ── Suggesting Missing Narratives ──────────────────────────────────────────────
st.subheader("Step 4: Suggest Missing Narratives (Optional)")

st.markdown("""
If you notice a narrative in the article that the LLMs **failed to identify**, you can suggest it.

There are **3 slots** available for suggestions. For each:

| Field | What to enter |
|-------|---------------|
| **Theme** | The narrative theme (e.g., "Economic Impact") |
| **Meso Narrative** | The specific narrative (e.g., "Migrants contribute to tax revenue") |
| **Text Fragment** | The relevant quote from the article (optional but helpful) |
| **Confidence** | How confident you are: 3 (somewhat), 4 (confident), 5 (very confident) |

Leave unused slots empty — only filled entries will be saved.
""")

# ── Validating Stance ──────────────────────────────────────────────────────────
st.subheader("Step 5: Validate Stance")

st.markdown("""
The final section asks you to assess the **overall stance** of the article toward migration.
""")

st.markdown("**Select one of the following:**")

stance_col1, stance_col2 = st.columns(2)
with stance_col1:
    st.success("**OPEN**")
    st.markdown("The article is generally positive or welcoming toward migration")
    
    st.error("**RESTRICTIVE**")
    st.markdown("The article is generally negative or critical of migration")

with stance_col2:
    st.warning("**NEUTRAL**")
    st.markdown("The article presents balanced views or no clear stance")
    
    st.markdown("""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: #e0e0e0;">
    <strong>IRRELEVANT</strong>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("The article is not actually about migration")

st.info("""
**👁️ Avoiding Bias:** The LLM stance predictions are hidden by default.

**Best practice:** Make your own stance assessment **first**, then click the expander to reveal what the LLMs predicted. This ensures your judgement isn't influenced by the models.
""")

st.markdown("""
You can also add an optional **comment** to explain your reasoning or note anything unusual about the article.
""")

# ── Saving Your Work ───────────────────────────────────────────────────────────
st.subheader("Step 6: Save Your Validations")

st.error("""
**⚠️ IMPORTANT: Click "💾 Save Validations" when you're done with each article!**

Your work is **not automatically saved**. You must click the save button at the bottom of the form.
""")

st.markdown("""
After saving:
- You'll see a success message confirming how many validations were saved
- You can then return to your Excel file and click the next article link
- If you return to the same article later, your previous responses will be pre-filled
""")

# ── Quick Reference ────────────────────────────────────────────────────────────
st.subheader("📋 Quick Reference Card")

st.markdown("""
| Step | Action |
|------|--------|
| **1** | Click article link from Excel |
| **2** | Verify you're signed in (check sidebar) |
| **3** | Read the article and highlighted fragments |
| **4** | Score each narrative annotation (0-5) |
| **5** | Suggest any missing narratives (optional) |
| **6** | Select your stance assessment |
| **7** | Click "💾 Save Validations" |
| **8** | Return to Excel, click next link |
""")

st.markdown("""
**Scoring Quick Guide:**
- **0-2** = Incorrect (narrative doesn't fit the article)
- **3-5** = Correct (narrative appropriately applied)
- **—** = Skip (no judgement)

**Stance Options:**
- **OPEN** = Pro-migration
- **RESTRICTIVE** = Anti-migration
- **NEUTRAL** = Balanced/no stance
- **IRRELEVANT** = Not about migration
""")

st.success("""
**💡 Tips for Efficient Validation:**
- Read the article fully before scoring
- Score annotations before revealing model names
- Make your stance judgement before revealing LLM predictions
- Save after each article — don't batch multiple articles
- If unsure, leave the score blank and move on
""")

st.divider()
st.caption("MigNar — Seeing Migration Narratives Project")
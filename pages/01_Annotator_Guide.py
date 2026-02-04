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

- **Narrative Themes**: General discussions about fairly broad topics
- **Meso Narratives**: Commonly occurring ideas or stories within those themes

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
1. **First iteration**: The LLM selects themes *without* being exposed to meso narratives
2. **Second iteration**: The LLM is fed themes and the meso narratives that fall under them

This means **theme wording must hint sufficiently to the meso narratives**. If a meso narrative's wording does not 
clearly associate with its theme in the first round, it may never get the chance to be selected later.
""")

# ── Avoiding Normative Judgements ──────────────────────────────────────────────
st.subheader("Avoiding Normative Judgements")

st.error("""
**We are NOT trying to:**
- Make judgements about the articles
- Challenge assumptions, facts, or terminology
- Correct or criticise the language used

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
Once you've completed the initial read-through, look at the **first theme** and the meso narratives below it.

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
**Comments:**
- If you think the theme could be reworded to better capture the meso narratives, note this in the comment box
- If you marked something as **"Duplicate"**, leave a comment mentioning the exact narrative (e.g., *"duplicate of 3.7"*)
- If you chose **"Wrong Theme"**, suggest the theme it should be moved to (e.g., *"should be under T2"*), or propose a new theme
- If you chose **"Poor Wording"**, suggest how you would reword it in the comments
- If you chose **"Other Issues"**, explain the problem (e.g., out of scope, factually incorrect, etc.)
""")

st.markdown("#### Step 4: Assess Meso Narratives")
st.markdown("""
After assessing the theme, look at its **meso narratives** (numbered like 1.1, 1.2, etc.) and undertake the same actions:
- Use the dropdown to select: **Good**, **Too Broad**, **Too Narrow**, **Duplicate**, **Wrong Theme**, **Poor Wording**, or **Other Issues**
- Add any comments as needed
- Use the numbering system to reference other narratives in your comments
""")

st.info("""
**📰 Viewing Articles**

If you wish to see a random selection of the content used to generate these meso narratives:
1. Click the **"View on Articles"** button (this will take you to the **[Narratives on Articles](https://mignar.streamlit.app/Narratives_on_Articles)** page)
2. Use the Record menu to browse the articles
3. See the text the LLMs have identified as relevant to those meso narratives

You do **not** need to look at every article, but they may help you orient yourself or understand confusing meso narratives.

**Remember:** When viewing articles, you're checking whether the *narrative concept* makes sense—not whether the LLM correctly applied it to that specific article.

If the content is confusing or obviously wrong—even after reviewing articles—please note this in the comment.
""")

st.markdown("#### Step 5: Suggest New Meso Narratives")
st.markdown("""
At the bottom of each theme's meso narratives, you'll find a **"➕ Suggest New"** row. If you believe there are meso narratives missing from the theme, you can suggest them here:

- Enter your suggested narratives in the text box
- Separate multiple suggestions with a semicolon (`;`)
- Example: *"Migrants enrich local cuisine; Migrants revive dying industries"*

Your suggestions will be saved and reviewed for inclusion in future taxonomy revisions.
""")

st.markdown("#### Step 6: Suggest Entirely New Themes")
st.markdown("""
At the **very bottom of the page** (after all existing themes), you'll find a special **"🌟 Suggest New Themes"** section.

Use this if you believe there's a **completely new theme** missing from the taxonomy—one that doesn't fit under any existing theme.

For each new theme suggestion:
1. **Theme Name**: Enter a clear, descriptive name for the theme
2. **Meso Narratives**: List the meso narratives that would fall under this theme, separated by semicolons (`;`)

**Example:**
- Theme Name: *"Environmental Impact of Migration"*
- Meso Narratives: *"Migrants contribute to urban sprawl; Migration affects local ecosystems; Migrants bring sustainable practices"*

There are multiple slots available if you have several theme suggestions. Leave unused slots empty—only filled entries will be saved.
""")

st.markdown("#### Step 7: Save Your Work — IMPORTANT!")

st.error("""
**⚠️ SAVE FREQUENTLY!**

There is a **"💾 Save Progress"** button at the end of each theme. **Click it after finishing each theme!**

The app may occasionally log you out due to session timeouts. If you don't save frequently, **you may lose your work**. 

**Best practice:** Complete one theme → Click Save → Move to the next theme.
""")

st.success("""
**💾 After completing annotations for a theme, click the "Save Progress" button at the bottom of that theme.**

Your annotations are valuable—don't forget to save after each theme!
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

**Suggestion Features:**
- **Suggest New Meso**: Add missing meso narratives to an existing theme (bottom of each theme)
- **Suggest New Themes**: Propose entirely new themes with their meso narratives (bottom of the page)
""")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# TASK 2: VALIDATING LLM LABELS
# ═══════════════════════════════════════════════════════════════════════════
st.header("Task 2: Validating LLM Labels")

st.warning("🚧 **This section is under construction** — Instructions to be completed.")

st.markdown("""
**What this task is about:**

Once the taxonomy is finalised, we need to verify that the LLMs are *correctly applying* the taxonomy labels to articles. In this task, you will:

- Review articles that have been labelled with specific **stances** (pro-migration, anti-migration, neutral)
- Review articles that have been labelled with specific **themes** and **meso narratives**
- Judge whether the LLM's labels are **correct**, **incorrect**, or **partially correct**
- Identify cases where the LLM missed a label or applied an irrelevant one

**Key difference from Task 1:**

| Task 1: Taxonomy Annotation | Task 2: Label Validation |
|-----------------------------|--------------------------|
| Is this narrative *well-defined*? | Is this narrative *correctly applied* to this article? |
| Does it belong in the taxonomy? | Does the article actually express this narrative? |
| Is the wording clear? | Did the LLM identify the right text fragment? |

**Coming soon:**
- Detailed instructions for the validation interface
- Guidelines for edge cases
- Examples of correct vs. incorrect labels
""")

st.divider()
st.caption("MigNar — Seeing Migration Narratives Project")
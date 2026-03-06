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
st.header("Task 2: Validating LLM Labels on Articles")

st.warning("""
**What this task is about:**

We prompted multiple LLMs to annotate articles with (a) **meso narrative labels** and (b) **stance labels**. 
Your job is to judge whether the LLMs got it right, and to suggest narratives they may have missed.
""")

# ── How the LLMs were prompted ─────────────────────────────────────────────
st.subheader("How the LLMs Were Prompted")

st.markdown("""
To ensure consistency between the LLM annotations and your validation, below are the **exact prompts** 
we gave the models. Your judgement criteria should mirror these instructions.
""")

with st.expander("📝 Meso Narrative Prompt (click to expand)", expanded=False):
    st.code(r"""
You are an expert political discourse analyst. Given a text, identify which
meso narratives about migration to the UK it contains.

Select all applicable meso narratives from the list below, grouped by their
narrative themes. If you discover meso narratives that are not listed, include
them too. But it should be a semi-general narrative (meso-level) that could be
used in multiple texts, not something very specific to this text only.

Here is the list of known meso narratives grouped by their narrative themes:
[... taxonomy themes and meso narratives are inserted here ...]

INSTRUCTIONS:
Return only a valid JSON array of objects with exactly these keys:
- "narrative theme": The narrative theme the meso narrative belongs to.
- "meso narrative": The specific meso-level generic narrative identified.
- "text fragment": A verbatim substring from the text that corresponds to
  the meso narrative.

Note: Use British English.
""", language="text")

with st.expander("🎯 Stance Prompt (click to expand)", expanded=False):
    st.code(r"""
You are an expert political discourse analyst. Classify the stance that the
AUTHOR/SPEAKER of the following article/statement expresses toward immigration
to the UK. Use one of the following categories: OPEN, RESTRICTIVE, NEUTRAL,
or IRRELEVANT. Be careful that I am asking about the AUTHOR'S stance, not the
policy or news that it may be mentioning.

### CATEGORY DEFINITIONS

- OPEN: The author advocates direct or indirect support for maintaining or
  expanding immigration. This can also be in the form of mentioning and
  criticising RESTRICTIVE policies or opinions.

- RESTRICTIVE: The author advocates direct or indirect support for limiting,
  controlling, or reducing immigration. This can also be in the form of
  mentioning and criticising OPEN policies or opinions.

- NEUTRAL: The text is fully or at least partially related to immigration,
  but the author remains impartial and does not express any OPEN or
  RESTRICTIVE stance.

- IRRELEVANT: The text is not even partially relevant to immigration to/from
  the UK. Relevance can be explicit or implicit (e.g. mentioning the
  nationality of individuals doing something positive or negative in the UK).
""", language="text")

st.info("""
**Key point:** The meso narrative prompt asks for a **verbatim text fragment** from the article. 
Yet, the narratives may be scattered across the article and not neatly summarised in one sentence. Thus, do not base your judgement on the correctness of the text fragment alone. Instead, use your judgement to assess whether the article as a whole contains the narrative.
""")

# ── Workflow ───────────────────────────────────────────────────────────────
st.subheader("Workflow")

st.markdown("""
1. **[Sign in](https://mignar.streamlit.app/)**.
2. Open the **Excel file** you received — each row has a clickable link to an article or parliamentary statement.
3. Click a link → the **[Narratives on Articles](https://mignar.streamlit.app/Narratives_on_Articles)** page opens.
4. Complete the three validation sections described below.
5. Click **💾 Save Validations**.
6. Return to Excel → Write *done* in front of the article → next article.
""")

# ── Section A: Score LLM Narrative Annotations ────────────────────────────
st.subheader("A. Score LLM Narrative Annotations")

st.markdown("""
A table lists every narrative annotation made by the LLMs. Each row shows a **theme**, 
**meso narrative**, and **text fragment**. Model names are hidden behind a 👁️ spoiler to avoid bias.

For each row, assign two scores:
""")

col_t, col_m = st.columns(2)
with col_t:
    st.markdown("""
    **Score<sub>theme</sub>** — Is the **theme** correct for this article?
    
    | Score | Meaning |
    |-------|---------|
    | 0 | Completely wrong |
    | 1–2 | Mostly / partially wrong |
    | 3 | Acceptable but imprecise |
    | 4 | Good |
    | 5 | Exactly right |
    | — | Skip |
    """, unsafe_allow_html=True)

with col_m:
    st.markdown("""
    **Score<sub>meso</sub>** — Is the **meso narrative + fragment** correct?
    
    | Score | Meaning |
    |-------|---------|
    | 0 | Completely wrong |
    | 1–2 | Mostly / partially wrong |
    | 3 | Acceptable but imprecise |
    | 4 | Good |
    | 5 | Exactly right |
    | — | Skip |
    """, unsafe_allow_html=True)

st.caption("You may also leave an optional comment per row (e.g. \"fragment is truncated\", \"wrong theme, should be T3\").")

# ── Section B: Suggest Missing Narratives ─────────────────────────────────
st.subheader("B. Suggest Missing Narratives")

st.markdown("""
If the article contains a narrative the LLMs **failed to detect**, you can suggest it in two ways:

| Method | Slots | How |
|--------|-------|-----|
| **From taxonomy** | 3 slots | Pick a theme and meso narrative from dropdown lists |
| **Free text** | 2 slots | Type a new theme and meso narrative not in the taxonomy |

For each suggestion, optionally paste the supporting **text fragment**, assign a confidence score 
(3 = somewhat confident, 4 = confident, 5 = very confident), and add a comment.

Leave unused slots empty — only filled entries are saved.
""")

# ── Section C: Validate Stance ────────────────────────────────────────────
st.subheader("C. Validate Stance")

st.markdown("""
Select the **overall stance** of the article's author toward migration:
""")

s1, s2 = st.columns(2)
with s1:
    st.success("**OPEN** — supports or defends migration / criticises restrictive positions")
    st.error("**RESTRICTIVE** — supports limiting migration / criticises open positions")
with s2:
    st.warning("**NEUTRAL** — related to migration but no clear directional stance")
    st.markdown("""
    <div style="padding:1rem;border-radius:.5rem;background:#e0e0e0;">
    <strong>IRRELEVANT</strong> — not about migration at all
    </div>
    """, unsafe_allow_html=True)

# st.info("""
# **👁️ Bias prevention:** Make your stance choice **before** expanding the LLM predictions spoiler.
# """)

# ── Saving & Tips ─────────────────────────────────────────────────────────
st.subheader("Saving & Tips")

st.error("""
**⚠️ Click "💾 Save Validations" after each article.** Work is not auto-saved.
""")

# st.markdown("""
# - Score annotations **before** revealing model names.
# - Assess stance **before** revealing LLM predictions.
# - If unsure, leave the score as **—** and move on.
# - The article body highlights fragments in 
#   <span style="background:#fff59d;padding:2px 4px;border-radius:3px">yellow</span> (any narrative) and 
#   <span style="background:#80deea;padding:2px 4px;border-radius:3px">blue</span> (selected meso filter). 
#   Hover to see details.
# """, unsafe_allow_html=True)

st.divider()
st.caption("MigNar — Seeing Migration Narratives Project")
import streamlit as st

st.set_page_config(
    page_title="Annotator Guide - MigNar",
    layout="wide",
    page_icon=".streamlit/static/MigNar_icon.png"
)

st.title("📝 Instructions for Annotators")

st.info("These notes guide annotators assessing themes and meso narratives in the **Seeing Migration Narratives (MigNar)** app.")

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
""")

# ═══════════════════════════════════════════════════════════════════════════
# What is the Narrative Taxonomy?
# ═══════════════════════════════════════════════════════════════════════════
st.header("What is the Narrative Taxonomy?")

st.markdown("""
The **taxonomy** is the structured list of themes and meso narratives that the LLMs use when annotating texts.

**Your role as annotators** is to refine this list into a comprehensive and well-organised collection that embraces 
all possible recurring narratives about migration to the UK.

Currently, we have instructed LLMs to **suggest new narratives** when they encounter content that doesn't fit 
existing entries. Your task is to review both:
- The **predefined narratives**
- The **LLM-suggested additions**

You will decide which narratives to **keep**, **merge**, **generalise**, or **discard**.

Once finalised, the taxonomy becomes **fixed**—the LLMs will only select from this approved list, ensuring 
consistent annotation across all documents.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Broad Objectives
# ═══════════════════════════════════════════════════════════════════════════
st.header("Broad Objectives for Annotators")

st.markdown("""
Your role at this stage of the project is to:
""")

objectives = [
    "**Review narrative themes and meso narratives** to ensure that themes correctly describe the set of meso narratives beneath them and are not duplicates of other (perhaps slightly differently worded) themes.",
    "**Clarify that meso narratives are specific and relevant** to the themes under which they sit.",
    "**Ensure meso narratives are broad enough** to cover various situations/stories—and not so specific that they only describe one particular story.",
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

# ═══════════════════════════════════════════════════════════════════════════
# Avoiding Normative Judgements
# ═══════════════════════════════════════════════════════════════════════════
st.header("Avoiding Normative Judgements")

st.error("""
**We are NOT trying to:**
- Make judgements about the articles
- Challenge assumptions, facts, or terminology
- Correct or criticise the language used

Your role is to assess the taxonomy structure and quality—not to evaluate the content of the narratives themselves.
""")

# ═══════════════════════════════════════════════════════════════════════════
# Process
# ═══════════════════════════════════════════════════════════════════════════
st.header("Annotation Process")

st.subheader("Step 1: Sign In and Navigate")
st.markdown("""
1. Sign in to the MigNar Streamlit app
2. Navigate to the **"Narratives Taxonomy"** page
3. You will see **themes highlighted in blue**, with a list of meso narratives underneath each one
""")

st.subheader("Step 2: Initial Read-Through")
st.markdown("""
**Before making any changes or suggestions**, read through the **full list of themes** so you have a reasonable 
sense of the whole.

> 💡 For this initial read-through, you do **not** need to look at the meso narratives—just the theme headings.
""")

st.subheader("Step 3: Assess Each Theme")
st.markdown("""
Once you've completed the initial read-through, look at the **first theme** and the meso narratives below it.

Immediately underneath each blue-highlighted theme, you will see:
- A **comments box**
- A **dropdown menu** for your assessment
""")

st.markdown("**Use the dropdown to select one of the following:**")

col1, col2 = st.columns(2)

with col1:
    st.success("**✅ Good**")
    st.markdown("The theme realistically describes the overall content of the meso narratives listed below.")
    
    st.warning("**🔄 Too Broad**")
    st.markdown("The theme doesn't mean anything clear—it's too vague.")

with col2:
    st.info("**🔬 Too Narrow**")
    st.markdown("The theme is too specific and will limit the meso narratives to only one story or event.")
    
    st.error("**📋 Duplicate**")
    st.markdown("The theme exists elsewhere (even if phrased slightly differently).")

st.markdown("""
**Additional options:**
- **Wrong Theme**: You believe the meso narrative should be under a different theme

**Comments:**
- If you think the theme could be reworded to better capture the meso narratives, note this in the comment box
- If you marked something as **"Duplicate"**, leave a comment mentioning the exact narrative you believe it duplicates
- If you chose **"Wrong Theme"**, suggest the theme it should be moved to, or propose a new theme
""")

st.subheader("Step 4: Assess Meso Narratives")
st.markdown("""
After assessing the theme, look at its **meso narratives** and undertake the same actions:
- Use the dropdown to select: **Good**, **Too Broad**, **Too Narrow**, or **Duplicate**
- Add any comments as needed
""")

st.info("""
**📰 Viewing Articles**

If you wish to see a random selection of the content used to generate these meso narratives:
1. Click the **"View on Articles"** button
2. Use the Record menu to browse the articles
3. See the text the LLMs have identified as relevant to those meso narratives

You do **not** need to look at every article, but they may help you orient yourself or understand confusing meso narratives.

If the content is confusing or obviously wrong—even after reviewing articles—please note this in the comment.
""")

st.subheader("Step 5: Save Your Work")
st.success("""
**💾 After completing a batch of annotations, click the Save button to save your work.**

Your annotations are valuable—don't forget to save regularly!
""")

# ═══════════════════════════════════════════════════════════════════════════
# Quick Reference Card
# ═══════════════════════════════════════════════════════════════════════════
st.divider()
st.header("📋 Quick Reference Card")

st.markdown("""
| Label | When to Use |
|-------|-------------|
| **Good** | Theme/narrative is well-formed, specific, distinct, and correctly placed |
| **Too Broad** | Too vague or generic—doesn't mean anything clear |
| **Too Narrow** | Too specific—only describes one particular story or event |
| **Duplicate** | Same as another entry (even if worded differently)—leave comment specifying which |
| **Wrong Theme** | Meso narrative belongs under a different theme—suggest where in comment |
""")

st.divider()
st.caption("MigNar — Seeing Migration Narratives Project")
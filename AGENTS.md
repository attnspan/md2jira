# AI Agent Guidelines for md2jira Project

This document provides critical guidance for AI assistants working with the md2jira project to prevent common errors and ensure proper Markdown formatting for JIRA issue creation.

## Critical: Markdown Header Syntax vs. Lists

### ⚠️ NEVER USE `#` FOR LISTS

The `#` symbol in Markdown is **ONLY** for headers, not lists. Using `#` for list items will create extraneous JIRA Epic issues, which is absolutely not desirable.

### Correct Syntax

**Headers (Issue Creation):**
```markdown
# Epic Title                  → Creates JIRA Epic
## Story Title                → Creates JIRA Story  
### Sub-task Title            → Creates JIRA Sub-task
```

**Lists (Content within issues):**
```markdown
* Bullet point item          → Bulleted list (CORRECT)
- Bullet point item          → Bulleted list (not currently supported by md2jira, but valid JIRA)
1. Numbered item             → Numbered list (if supported)
```

### ❌ WRONG - DO NOT DO THIS:
```markdown
# User clicks the button      → Would create an unwanted Epic!
# System processes request    → Would create another unwanted Epic!
```

### ✅ CORRECT:
```markdown
* User clicks the button      → Bulleted list item
* System processes request    → Bulleted list item
```

## JIRA-Specific Formatting

### Headers within Issue Descriptions

Use JIRA's `h3.` syntax for section headers within issue descriptions:

```markdown
h3. Summary
h3. Technical Details
h3. Acceptance Criteria
```

### Code Blocks

Use JIRA's code block syntax with language specification:

```markdown
{code:python}
def example():
    return "Hello"
{code}

{code:javascript}
const example = () => "Hello";
{code}

{code:sql}
SELECT * FROM users;
{code}
```

### Checklists

Use checkbox syntax for checklists within issues:

```markdown
* [ ] Pending task
* [>] In-progress task
* [x] Completed task
```

**Note:** Do NOT add `h3. Checklist` headers before checklists. The checkbox formatting alone creates the checklist in JIRA.

### Tables

Use pipe syntax for tables:

```markdown
| Column 1 | Column 2 | Column 3 |
| --- | --- | --- |
| Value A | Value B | Value C |
| Value D | Value E | Value F |
```

### Links

Use JIRA link syntax:

```markdown
[Link Text|https://example.com/url]
```

### Text Formatting

```markdown
*bold text*
_italic text_
```

## Issue Hierarchy

The md2jira tool creates JIRA issues based on Markdown header levels:

- **H1 (`#`)**: Creates an Epic
- **H2 (`##`)**: Creates a Story (linked to the preceding Epic)
- **H3 (`###`)**: Creates a Sub-task (linked to the preceding Story)

### Example Structure

```markdown
# Epic: User Authentication System

Epic description and business value...

## Story: User Registration

Story description...

### Sub-task: Backend API

Sub-task details...

### Sub-task: Frontend Form

Sub-task details...

## Story: User Login

Story description...

### Sub-task: Authentication Token

Sub-task details...
```

## Content Guidelines

### What to Include in Each Issue Type

**Epics (H1):**
- High-level business objective
- Business value and goals
- Overall acceptance criteria
- Scope and timeline

**Stories (H2):**
- User-facing feature or requirement
- Detailed acceptance criteria
- Technical requirements
- API endpoints, database schemas
- Security requirements
- User stories ("As a user, I want...")

**Sub-tasks (H3):**
- Specific implementation tasks
- Technical approach and code examples
- Task checklists with `* [ ]`, `* [>]`, `* [x]`
- Dependencies and prerequisites
- Testing requirements

## Common Mistakes to Avoid

### 1. Using `#` for Lists ❌
```markdown
# This creates an Epic, not a list item!
```

### 2. Adding Unnecessary Headers ❌
```markdown
h3. Checklist   ← Not needed; checkboxes create the checklist automatically
* [ ] Task 1
* [ ] Task 2
```

### 3. Mixing Markdown and JIRA Syntax ❌
```markdown
### h3. Section Title   ← Don't mix; use one or the other
```

### 4. Using Markdown Code Blocks ❌
```markdown
\`\`\`python          ← Use JIRA syntax instead
code here
\`\`\`
```

Should be:
```markdown
{code:python}
code here
{code}
```

## Pre-Creation Checklist

Before creating or modifying md2jira Markdown files, verify:

- [ ] All headers use correct levels (# for Epic, ## for Story, ### for Sub-task)
- [ ] No `#` symbols used for list items
- [ ] Code blocks use `{code:language}` syntax, not backticks
- [ ] Checklists use `* [ ]`, `* [>]`, `* [x]` without extra headers
- [ ] Links use `[text|url]` JIRA syntax
- [ ] Section headers within issues use `h3.` prefix
- [ ] Tables use pipe `|` syntax
- [ ] Text formatting uses `*bold*` and `_italic_`

## Testing New Content

When creating example or test files:

1. Prefix all titles with a test identifier (e.g., `TESTING 2025-11-20 -- `)
2. Keep hierarchy consistent (Epic → Stories → Sub-tasks)
3. Include diverse formatting examples to demonstrate capabilities
4. Verify no unintended issue creation before running md2jira

## Additional Resources

- Review `example.md` for basic usage patterns
- Review `example-full.md` for comprehensive formatting examples
- Check the main README for project-specific requirements
- Consult JIRA documentation for supported text formatting

---

## Summary: The Golden Rules

1. **`#` is ONLY for headers (issue creation), NEVER for lists**
2. **Use `*` for bulleted lists within issue descriptions**
3. **Use JIRA syntax (`h3.`, `{code}`, `[text|url]`) for formatting within issues**
4. **Follow strict hierarchy: H1=Epic, H2=Story, H3=Sub-task**
5. **Test content before creating real JIRA issues**

Following these guidelines will ensure proper JIRA issue creation without unwanted artifacts or structural problems.


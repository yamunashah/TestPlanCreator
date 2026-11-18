# SOP: Test Plan Generation

## Purpose
Defines how a normalized Jira dict is converted into a Test Plan document without duplicate sections, and how reports are saved to file paths.

## Inputs
- `jira_data`: normalized dict (output of `jira_client.py`)
- `template`: string (contents of `TestPlanTemplate.md`)
- `file_path`: optional target file path to save the generated test plan report

## Mapping Rules & Deduplication Invariants

| Template Section | Jira Source | Fallback / Deduplication Rule |
|-----------------|-------------|-------------------------------|
| Title | `summary` | "— Not specified —" |
| Jira ID & URL | `id`, `url` | issue ID only |
| Objective | `description` (pre-AC text) | Factual testing objective for `summary`; never repeats Acceptance Criteria |
| Issue Context | `issue_type`, `priority`, etc. | Tabular issue metadata |
| Scope (In/Out) | `summary`, `components` | Structured testing scope boundaries; does NOT duplicate description |
| Acceptance Criteria | `description` (parsed AC) | Dedicated section rendered ONCE; fallback: "— Not specified in Jira issue —" |
| Test Scenarios | `subtasks` | "— No subtasks found —" |
| Test Approach | Standards | Functional, Integration, Regression matrix |
| Risks & Assumptions | `priority` | Priority-based risk assessment |
| Additional Context | `comments` (first 5) | "— No comments —" |
| Reference Docs | `attachments` | "— No attachments —" |
| Sign-off | Roles | Pending approval block |

## Deduplication Rule
- **No Duplicate Sections:** The Jira description must never be blindly repeated across Objective and Scope.
- When description contains an Acceptance Criteria header (e.g. `Acceptance Criteria:`, `AC:`), the text is partitioned into Objective (User Story) and Acceptance Criteria. Acceptance Criteria appears ONLY in its dedicated section.

## Empty Field Rule
If a Jira field is `None`, empty list `[]`, or empty string `""`:
→ Render: `*— Not specified —*` in the output

## Output & Persistence Formats
1. **Markdown string** — for download as `.md` file
2. **HTML string** — for rendering in the browser (converted from markdown)
3. **Local File Persistence** — saves markdown report automatically to:
   `TestPlanReport/TestPlan{JIRANAME}.md` (e.g. `TestPlanReport/TestPlanKAN-1.md`)
   Custom target paths can also be specified via the API or Web UI.



"""
testplan_generator.py — Jira Data → Test Plan Markdown/HTML
Layer 3 Tool: Pure function, no Flask dependency, no side effects.
Generates a test plan conforming to TestPlanTemplate.md structure.
"""

import os
import re
from datetime import datetime
from tools.jira_client import extract_jira_key


EMPTY = "*— Not specified —*"
EMPTY_LIST = "*— None —*"
EMPTY_DESC = "*— No description provided —*"
EMPTY_CRITERIA = "*— No explicit acceptance criteria specified in Jira issue —*"
EMPTY_SUBTASKS = "*— No subtasks/test scenarios found in this Jira issue —*"
EMPTY_COMMENTS = "*— No comments found —*"
EMPTY_ATTACHMENTS = "*— No attachments found —*"


def split_description_and_criteria(raw_text: str):
    """
    Splits Jira description into (objective_text, acceptance_criteria).
    Ensures NO duplicate sections between Objective, Scope, and Acceptance Criteria.
    """
    if not raw_text or not raw_text.strip():
        return "", ""
    text = raw_text.strip()
    # Match headers like "Acceptance Criteria", "Acceptance Criteria:", "h2. Acceptance Criteria", "## Acceptance Criteria"
    pattern = r'(?i)(?:^|\n)(?:#+\s*|\*{1,2}|h[1-6]\.\s*)?(?:acceptance\s+criteria|ac|acceptance\s+tests)(?:\*{1,2}|:)?\s*(?:\n|:|$)'
    match = re.search(pattern, text)
    if match:
        objective = text[:match.start()].strip()
        criteria = text[match.end():].strip()
        return objective, criteria
    return text, ""


def _val(s: str, fallback: str = EMPTY) -> str:
    """Return value if non-empty, else fallback."""
    return s.strip() if s and s.strip() else fallback


def _list_val(lst: list, fallback: str = EMPTY_LIST) -> str:
    """Return comma-joined list or fallback."""
    cleaned = [item for item in (lst or []) if item and item.strip()]
    return ", ".join(cleaned) if cleaned else fallback


def _bullet_list(lst: list, key: str = None) -> str:
    """Return a markdown bullet list from a list of strings or dicts."""
    if not lst:
        return EMPTY_LIST
    lines = []
    for item in lst:
        if isinstance(item, dict):
            text = item.get(key, str(item)) if key else str(item)
        else:
            text = str(item)
        lines.append(f"- {text}")
    return "\n".join(lines) if lines else EMPTY_LIST


def generate_test_plan_markdown(jira_data: dict) -> str:
    """
    Generates a full Test Plan in Markdown format from normalized Jira data.
    Conforms to TestPlanTemplate.md structure with strictly NO duplicate sections.
    """
    d = jira_data
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    issue_id = d.get("id", "")
    issue_url = d.get("url", "")
    summary = _val(d.get("summary", ""), "— Untitled —")
    raw_desc = d.get("description", "")
    issue_type = _val(d.get("issue_type", ""))
    priority = _val(d.get("priority", ""))
    status = _val(d.get("status", ""))
    assignee = _val(d.get("assignee", ""), "*— Unassigned —*")
    reporter = _val(d.get("reporter", ""))
    labels = _list_val(d.get("labels", []))
    components = _list_val(d.get("components", []))
    fix_versions = _list_val(d.get("fix_versions", []))

    # Split description into objective and acceptance criteria to avoid duplicates
    obj_part, crit_part = split_description_and_criteria(raw_desc)
    if obj_part:
        objective_section = obj_part
    elif raw_desc and not crit_part:
        objective_section = raw_desc
    else:
        objective_section = EMPTY_DESC

    if crit_part:
        acceptance_criteria_section = crit_part
    else:
        acceptance_criteria_section = EMPTY_CRITERIA

    # Subtasks → Test Scenarios
    subtasks = d.get("subtasks", [])
    if subtasks:
        subtask_lines = []
        for i, sub in enumerate(subtasks, 1):
            sub_id = sub.get("id", f"#{i}")
            sub_sum = sub.get("summary", "No summary")
            sub_status = sub.get("status", "Unknown")
            subtask_lines.append(
                f"| {i} | [{sub_id}] {sub_sum} | | | {sub_status} |"
            )
        subtasks_section = (
            "| # | Test Scenario | Expected Result | Priority | Status |\n"
            "|---|--------------|-----------------|----------|--------|\n"
            + "\n".join(subtask_lines)
        )
    else:
        subtasks_section = EMPTY_SUBTASKS

    # Comments → Additional Context
    comments = d.get("comments", [])
    if comments:
        comment_lines = []
        for c in comments:
            author = c.get("author", "Unknown")
            created = c.get("created", "")[:10] if c.get("created") else ""
            body = c.get("body", "").strip()[:300]
            if body:
                comment_lines.append(f"**{author}** ({created}):\n> {body}\n")
        comments_section = "\n".join(comment_lines) if comment_lines else EMPTY_COMMENTS
    else:
        comments_section = EMPTY_COMMENTS

    # Attachments → Reference Documents
    attachments = d.get("attachments", [])
    if attachments:
        att_lines = [
            f"- [{att.get('filename', 'file')}]({att.get('url', '#')})"
            for att in attachments
            if att.get("filename")
        ]
        attachments_section = "\n".join(att_lines) if att_lines else EMPTY_ATTACHMENTS
    else:
        attachments_section = EMPTY_ATTACHMENTS

    # Issue ID link
    if issue_url:
        issue_ref = f"[{issue_id}]({issue_url})"
    else:
        issue_ref = issue_id or EMPTY

    # ── Assemble Test Plan ────────────────────────────────────────────────────
    plan = f"""# Test Plan: {summary}

---

## 📋 Document Information

| Field | Value |
|-------|-------|
| **Jira Issue** | {issue_ref} |
| **Test Plan Title** | {summary} |
| **Generated On** | {now} |
| **Generated From** | Jira Test Plan Generator |

---

## 1. 🎯 Objective

{objective_section}

---

## 2. 📌 Issue Context

| Field | Value |
|-------|-------|
| **Issue Type** | {issue_type} |
| **Priority / Risk Level** | {priority} |
| **Current Status** | {status} |
| **Test Owner / Assignee** | {assignee} |
| **Stakeholder / Reporter** | {reporter} |
| **Components (System Under Test)** | {components} |
| **Release Target / Fix Version** | {fix_versions} |
| **Labels / Tags** | {labels} |

---

## 3. 🔍 Scope

### In Scope
- Functional, integration, and regression validation of **{summary}**
- Components under test: {components}
- Execution of test scenarios and verification of acceptance criteria

### Out of Scope
*— Define explicitly based on business requirements —*

---

## 4. 📋 Acceptance Criteria

{acceptance_criteria_section}

---

## 5. 🧪 Test Scenarios

{subtasks_section}

---

## 6. ✅ Test Approach

| Approach | Details |
|----------|---------|
| **Test Types** | Functional, Integration, Regression |
| **Test Environment** | *— Specify environment (Dev / QA / Staging) —* |
| **Test Tools** | *— Specify testing tools —* |
| **Entry Criteria** | *— Define when testing can begin —* |
| **Exit Criteria** | *— Define when testing is considered complete —* |

---

## 7. ⚠️ Risks & Assumptions

| Risk | Impact | Mitigation |
|------|--------|------------|
| Priority: **{priority}** | *— Assess impact based on priority —* | *— Define mitigation —* |
| *— Add more risks —* | | |

**Assumptions:**
- *— List assumptions here —*

---

## 8. 💬 Additional Context (from Jira Comments)

{comments_section}

---

## 9. 📎 Reference Documents

{attachments_section}

---

## 10. 📊 Sign-off

| Role | Name | Status | Date |
|------|------|--------|------|
| Test Owner | {assignee} | ⬜ Pending | |
| Stakeholder | {reporter} | ⬜ Pending | |
| QA Lead | *— TBD —* | ⬜ Pending | |

---

*Generated by Jira Test Plan Generator • {now}*
"""
    return plan.strip()


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_report_path(jira_id: str = "", base_dir: str = "") -> str:
    """
    Returns the standardized file path for a test plan report following the convention:
    TestPlanReport/TestPlan{JIRANAME}.md
    Anchors to the project root directory unless base_dir is explicitly specified.
    """
    clean_id = extract_jira_key(jira_id) if jira_id else ""
    filename = f"TestPlan{clean_id}.md" if clean_id else "TestPlanReport.md"
    target_dir = os.path.join(base_dir if base_dir else PROJECT_ROOT, "TestPlanReport")
    return os.path.join(target_dir, filename)


def save_test_plan(markdown_content: str, file_path: str = None, jira_id: str = "") -> str:
    """
    Saves the generated test plan markdown to the specified file path.
    If no file_path is provided, defaults to TestPlanReport/TestPlan{JIRANAME}.md.
    Creates parent directories if necessary and returns the resolved absolute path.
    """
    if not file_path or not file_path.strip():
        file_path = get_report_path(jira_id)
    resolved_path = os.path.abspath(file_path.strip())
    parent_dir = os.path.dirname(resolved_path)
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    with open(resolved_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    return resolved_path


def markdown_to_html(markdown_text: str) -> str:
    """
    Converts markdown to HTML.
    Uses a simple regex-based converter for headers, bold, italic,
    tables, lists, code blocks, blockquotes, and links.
    No external library dependency needed.
    """
    html = markdown_text

    # Code blocks (fenced)
    html = re.sub(
        r'```(\w*)\n(.*?)```',
        lambda m: f'<pre><code class="language-{m.group(1)}">{_escape_html(m.group(2))}</code></pre>',
        html, flags=re.DOTALL
    )

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Tables
    def convert_table(m):
        lines = m.group(0).strip().split('\n')
        result = ['<table class="test-plan-table">']
        for i, line in enumerate(lines):
            if re.match(r'\|[\s\-:]+\|', line):
                continue  # skip separator row
            cells = [c.strip() for c in line.strip('|').split('|')]
            tag = 'th' if i == 0 else 'td'
            result.append('<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>')
        result.append('</table>')
        return '\n'.join(result)

    html = re.sub(r'(\|.+\|\n?)+', convert_table, html)

    # Headings
    html = re.sub(r'^######\s+(.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
    html = re.sub(r'^#####\s+(.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
    html = re.sub(r'^####\s+(.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Horizontal rule
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)

    # Blockquote
    html = re.sub(r'^>\s*(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Unordered list
    def convert_ul(m):
        items = re.findall(r'^[-*]\s+(.+)$', m.group(0), re.MULTILINE)
        return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'
    html = re.sub(r'(^[-*]\s+.+$\n?)+', convert_ul, html, flags=re.MULTILINE)

    # Bold + italic
    html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', html)

    # Paragraphs (lines not already in tags)
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('<'):
            result.append(f'<p>{stripped}</p>')
        else:
            result.append(line)
    html = '\n'.join(result)

    return html


def _escape_html(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


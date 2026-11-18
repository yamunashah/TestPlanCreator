# 🔎 Findings — Jira Test Plan Generator

> **Last Updated:** 2026-10-22T16:20:00+05:30
> **Status:** ✅ Research Complete — Ready for Build

---

## 1. Project Summary

Build a **locally-hosted web application** that:
- Accepts a **Jira Issue ID** (e.g., `PROJECT-123`) from the user
- Lets the user configure **Jira Base URL** and **API Token** via a settings/configure button
- Fetches the Jira issue details via the Jira REST API
- Generates a structured **Test Plan** using the `TestPlanTemplate.md` as the output format
- Clearly shows "Empty / No Data" messages when Jira fields are missing

---

## 2. Jira REST API — Key Findings

### 2.1 Authentication Methods
Jira Cloud supports two auth mechanisms:

| Method | Header | Notes |
|--------|--------|-------|
| API Token (Basic Auth) | `Authorization: Basic base64(email:token)` | Recommended for Cloud |
| Bearer Token (PAT) | `Authorization: Bearer <token>` | For Jira Server/Data Center |

We will support **both** — detect by URL pattern: `*.atlassian.net` → Cloud (Basic), else → Bearer.

---

### 2.2 API Endpoints We Use

#### Fetch a Single Issue
```
GET {base_url}/rest/api/3/issue/{issueIdOrKey}
```

**Query params used:**
```
?fields=summary,description,issuetype,priority,status,assignee,reporter,labels,components,fixVersions,subtasks,comment,attachment,customfield_10014
```

**curl example (Cloud — Basic Auth):**
```bash
curl -u "user@example.com:YOUR_API_TOKEN" \
     -H "Accept: application/json" \
     "https://yourcompany.atlassian.net/rest/api/3/issue/PROJECT-123?fields=summary,description,issuetype,priority,status,assignee,reporter,labels,components,fixVersions,subtasks,comment"
```

**curl example (Server/DC — Bearer Token):**
```bash
curl -H "Authorization: Bearer YOUR_PERSONAL_ACCESS_TOKEN" \
     -H "Accept: application/json" \
     "https://jira.yourcompany.com/rest/api/3/issue/PROJECT-123?fields=summary,description,issuetype,priority,status,assignee,reporter,labels,components,fixVersions,subtasks,comment"
```

**Python requests equivalent:**
```python
import requests, base64

# Cloud
token = base64.b64encode(f"{email}:{api_token}".encode()).decode()
headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

# Server/DC
headers = {"Authorization": f"Bearer {pat_token}", "Accept": "application/json"}

resp = requests.get(
    f"{base_url}/rest/api/3/issue/{issue_id}",
    headers=headers,
    params={"fields": "summary,description,issuetype,priority,status,assignee,reporter,labels,components,fixVersions,subtasks,comment"}
)
data = resp.json()
```

---

#### Fetch Issue Comments
```
GET {base_url}/rest/api/3/issue/{issueIdOrKey}/comment
```

#### Fetch Linked Issues
```
GET {base_url}/rest/api/3/issue/{issueIdOrKey}?fields=issuelinks
```

#### Fetch Epic Children (if issue is an Epic)
```
GET {base_url}/rest/api/3/search?jql="Epic Link"={issueKey}&fields=summary,status,assignee
```

---

### 2.3 Key Jira Fields Mapped to Test Plan Sections

| Jira Field | JSON Path | Maps to Test Plan Section |
|-----------|-----------|--------------------------|
| Summary | `fields.summary` | Test Plan Title |
| Description | `fields.description` (ADF format) | Scope / Objective |
| Issue Type | `fields.issuetype.name` | Context |
| Priority | `fields.priority.name` | Risk Level |
| Status | `fields.status.name` | Current State |
| Assignee | `fields.assignee.displayName` | Test Owner |
| Reporter | `fields.reporter.displayName` | Stakeholder |
| Labels | `fields.labels[]` | Tags / Categories |
| Components | `fields.components[].name` | System Under Test |
| Fix Versions | `fields.fixVersions[].name` | Release Target |
| Subtasks | `fields.subtasks[]` | Test Scenarios / Cases |
| Comments | `fields.comment.comments[]` | Additional Context |
| Attachments | `fields.attachment[]` | Reference Docs |

---

### 2.4 Jira Description Format — ADF (Atlassian Document Format)

Jira Cloud returns description as **ADF (JSON)**, not plain text. Need to convert ADF → plain text.

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    { "type": "paragraph", "content": [{ "type": "text", "text": "This is the description" }] }
  ]
}
```

**Strategy:** Write a recursive ADF → plain text converter function.

---

### 2.5 Error Scenarios & Handling

| Scenario | HTTP Code | UI Response |
|----------|-----------|-------------|
| Invalid credentials | 401 | "Authentication failed. Check your email/token." |
| Issue not found | 404 | "Jira issue `{id}` not found." |
| No access to issue | 403 | "You don't have permission to view this issue." |
| Empty field | N/A | Show "—" or "Not specified" in test plan |
| Network error | N/A | "Cannot reach Jira. Check your Base URL." |

---

## 3. Architecture Decision

- **Backend:** Python Flask (lightweight, easy local hosting)
- **Frontend:** Single HTML page with vanilla JS + CSS (no framework dependency)
- **Config Storage:** Browser `localStorage` (Jira URL + token persisted client-side, never sent to any third party)
- **Template Engine:** Jinja2 (server-side) or JS string interpolation (client-side)
- **Test Plan Output:** Rendered HTML on page + downloadable Markdown file
- **Port:** `localhost:5000`

---

## 4. Helpful GitHub References Found

- `jira-python` library: https://github.com/pycontribs/jira — mature client but heavy dependency
- **Decision:** Use raw `requests` to keep it minimal and dependency-light
- Atlassian REST API docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/

---

## 5. Constraints

- No database — stateless per request
- Credentials stored in browser localStorage only (not on server)
- Must work fully offline except for the Jira API call
- `TestPlanTemplate.md` is the canonical template — all output must conform to it

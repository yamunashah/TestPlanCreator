# 📜 LLM.md — Project Constitution
## Jira Test Plan Generator

> ⚠️ Single source of truth. All code must conform to this document.
> Changes require explicit user approval.
> **Last Updated:** 2026-11-17T22:22:00+05:30

---

## 1. 🧠 My Thinking Process — The Full Reasoning

### 1.1 How I framed the problem

When I first read the requirement — "generate a test plan from a Jira ID" — I had to decompose it into three distinct sub-problems:

1. **Data acquisition** — How do I reliably extract structured data from Jira?
2. **Data transformation** — How do I turn messy, variable Jira data into a clean test plan?
3. **Delivery** — How does the user interact with the tool and consume the output?

Each of these has very different failure modes, and that's what drove the architecture.

### 1.2 Why I chose the stack I chose

**Flask over FastAPI:**
I considered FastAPI first because it auto-generates OpenAPI docs and has type validation via Pydantic. But for a locally-hosted tool with 2 endpoints and no concurrent load, that's over-engineering. Flask gives us a working server in ~60 lines of `app.py`. The user will `python app.py` and have it running. No async complexity, no dependency on `uvicorn`, no Pydantic models for what amounts to 3 JSON fields. I'd switch to FastAPI if this ever needed WebSocket support, background jobs, or multi-user auth.

**Vanilla JS + CSS over React/Vue:**
This was a deliberate constraint. The user's requirement is a tool, not a product. Adding `npm`, `node_modules`, a build step, and a bundler for a single-page form-to-output flow would be absurd. The JS file is ~250 lines. If the UI complexity grows beyond 2 views or needs state management, then yes, migrate to a framework. Right now, `localStorage` + `fetch()` + DOM manipulation handles everything.

**Raw `requests` over the `jira` Python library:**
The `jira` package (pycontribs/jira on GitHub) is 15,000+ lines with 30+ transitive dependencies. It wraps the entire Jira API surface when we use exactly one endpoint. Our `jira_client.py` is ~160 lines and does exactly what we need. The tradeoff is we handle auth headers and error codes ourselves — but that's maybe 20 lines of code vs. a dependency that could break on upgrade.

**localStorage over .env files:**
This is the decision I thought hardest about. `.env` is the standard for server-side secrets. But this tool runs on the user's own machine; there's no deployment, no CI, no environment separation. Making the user edit a `.env` file, restart the server, and remember where it is — that's friction. With localStorage, the user opens a modal, pastes their token once, and it persists across browser sessions. The token never leaves the browser except in the POST body to our own localhost Flask server. If this were deployed to a shared server, I'd immediately switch to `.env` with server-side storage.

### 1.3 The hardest design problem: ADF

Jira Cloud doesn't return description as plain text. It returns **Atlassian Document Format (ADF)**, which is a nested JSON tree like this:

```json
{
  "type": "doc",
  "content": [
    {
      "type": "paragraph",
      "content": [
        { "type": "text", "text": "As a user, I want to..." },
        { "type": "text", "text": "login with SSO", "marks": [{"type": "strong"}] }
      ]
    }
  ]
}
```

This is structurally similar to ProseMirror (which Jira's editor is built on). My options were:
1. **Strip to plain text** — lose all formatting, links, tables in the description
2. **Convert to Markdown** — preserve formatting in a readable way
3. **Render as HTML** — most faithful but then the test plan has two rendering paths

I chose option 2 (ADF → Markdown) because the test plan output is itself Markdown, so the description flows naturally. The `adf_converter.py` recursively walks the ADF tree and applies marks (bold, italic, code, link, strike) while handling block-level nodes (headings, lists, tables, code blocks, blockquotes). It handles 15+ node types.

**The edge case I worried about most:** nested lists inside a table cell inside a blockquote. ADF supports arbitrary nesting. My converter handles 2 levels of list nesting and flattens deeper structures. This is a known limitation — if a Jira description has a 4-level nested list inside a table, the formatting won't be perfect. But it'll still be readable, and that's the tradeoff I accepted.

### 1.4 How I think about empty fields

This is a core design philosophy, not just a default value. Jira issues are incredibly variable:
- An issue might have no description (someone just typed a summary and hit Create)
- An issue might have no assignee (backlog item)
- An issue might have no components, no labels, no fix version
- An issue might have zero subtasks (a standalone bug)
- An issue might have no comments

The wrong approach: show nothing. The user would wonder "did it fetch the data or not?"
The right approach: **explicitly show that the field is empty.** Every empty field renders as `*— Not specified —*` in the test plan. This is a deliberate UX signal: "I fetched this issue, and this field genuinely has no value in Jira."

This is enforced at the tool layer (`testplan_generator.py`) through helper functions:
- `_val(s, fallback)` — returns the string if non-empty, else the fallback
- `_list_val(lst, fallback)` — joins a list or returns "— None —"

And at the data layer (`jira_client.py`), every `.get()` call has a default of `""` or `[]` — never `None` leaking out.

### 1.5 What I would do differently if I could start over

1. **Use Pydantic models** for the normalized Jira data. Right now it's a plain dict, which works but doesn't give us runtime validation. If a Jira API response changes shape, we'd get a KeyError deep in the generator instead of a clean validation error at the boundary.

2. **Template engine for the test plan.** Currently `testplan_generator.py` builds the markdown as a big f-string. This works because we control the template, but if users want to customize the template structure, we'd need to read `TestPlanTemplate.md` at runtime and do placeholder substitution. This is a future enhancement.

3. **Separate the HTML rendering.** Right now `markdown_to_html()` is a regex-based converter in `testplan_generator.py`. It handles 80% of Markdown well but doesn't handle edge cases (nested emphasis, reference-style links). A proper solution would use the `markdown` or `mistune` library — I avoided it to keep dependencies at 2 (flask + requests) but it's the first thing I'd add if the HTML output has rendering issues.

---

## 2. 📐 Data Schema — What I Think About Each Shape

### 2.1 Input Schema (Browser → Flask `/generate`)

```json
{
  "jira_id":   "PROJECT-123",
  "base_url":  "https://yourcompany.atlassian.net",
  "auth_type": "cloud",
  "email":     "user@example.com",
  "token":     "your_api_token_here"
}
```

**Why these fields and not others:**

- `jira_id` — The only user-provided input per request. Everything else comes from saved config. I considered making this a URL (`https://company.atlassian.net/browse/PROJECT-123`) and parsing it, but that's error-prone — users copy-paste issue keys from conversations, not full URLs.

- `auth_type` — Either `"cloud"` or `"server"`. I debated auto-detecting this from the URL (if it ends in `.atlassian.net` → cloud, else → server). I chose explicit selection because: (a) some companies have custom domains pointing to Atlassian Cloud, (b) auto-detection creates invisible logic that confuses users when it guesses wrong.

- `email` — Only needed for Cloud (Basic Auth = email:token). Server/DC uses just a PAT. The UI hides the email field when "Server" is selected.

- `token` — Sent in every request body. I considered sending it as an `Authorization` header from the browser, but that would require the Flask server to proxy auth headers, and CORS preflight would add complexity. Sending it in the JSON body is simpler and equally secure over localhost.

**What's NOT in this schema (and why):**
- No `project_key` — extracted from the issue ID itself
- No `api_version` — hardcoded to v3 (latest stable)
- No `expand` parameter — we don't need changelogs or rendered HTML from Jira
- No `timeout` — hardcoded to 15s, which is generous for a single issue fetch

### 2.2 Normalized Jira Data (Internal — output of `jira_client.py`)

```json
{
  "id":           "PROJECT-123",
  "summary":      "string",
  "description":  "string (ADF → markdown converted)",
  "issue_type":   "Bug | Story | Epic | Task | Sub-task",
  "priority":     "Highest | High | Medium | Low | Lowest",
  "status":       "To Do | In Progress | Done | <custom>",
  "assignee":     "string (display name)",
  "reporter":     "string (display name)",
  "labels":       ["label1", "label2"],
  "components":   ["component1"],
  "fix_versions": ["v1.0"],
  "subtasks": [
    { "id": "SUB-1", "summary": "string", "status": "string" }
  ],
  "comments": [
    { "author": "string", "body": "string (ADF converted)", "created": "ISO 8601" }
  ],
  "attachments": [
    { "filename": "string", "url": "string" }
  ],
  "url": "https://yourcompany.atlassian.net/browse/PROJECT-123"
}
```

**My reasoning for this normalization layer:**

The raw Jira API response is deeply nested. `fields.assignee.displayName`, `fields.priority.name`, `fields.status.statusCategory.name` — these are 3-4 levels deep. If `testplan_generator.py` had to navigate this tree directly, it would be:
1. Fragile — any Jira API change breaks the generator
2. Unreadable — `jira_data["fields"]["assignee"]["displayName"]` everywhere
3. Untestable — you'd need a full Jira API mock to test the generator

By normalizing in `jira_client.py`, the generator only sees flat, simple keys. I can test the generator with a hand-crafted dict. The jira_client is the only file that knows about the Jira API shape.

**Fields I chose NOT to include (and my reasoning):**

| Excluded Field | Why |
|----------------|-----|
| `fields.created` / `fields.updated` | Not useful in a test plan — we show our own generation timestamp |
| `fields.resolution` | Redundant with status for test planning purposes |
| `fields.watches` / `fields.votes` | Noise — irrelevant to test planning |
| `fields.environment` | Rarely populated, and our template has a manual "Test Environment" section |
| `fields.timetracking` | Not relevant to test plan generation |
| `fields.issuelinks` | Could be useful (linked bugs, blocks/is-blocked-by) but adds complexity; deferred to v2 |
| Custom fields (`customfield_*`) | Too company-specific to handle generically; deferred |

**Fields I debated including:**

- **`issuelinks`** — Linked issues could map to "Dependencies" in a test plan. I decided against it because: (a) it requires fetching each linked issue's summary (another API call per link), (b) link types are configurable per Jira instance, (c) it's a "nice to have" that adds real complexity. Future enhancement.

- **Epic children** — If the issue is an Epic, we could fetch all stories under it and list them as test scenarios. This requires a JQL search (`"Epic Link" = {key}`), which is a separate endpoint. Deferred to v2.

### 2.3 Output Schema (Flask → Browser)

**Success:**
```json
{
  "success": true,
  "test_plan_html":     "<rendered HTML string>",
  "test_plan_markdown": "# Test Plan: ...\n...",
  "jira_data":          { ... normalized dict ... },
  "issue_id":           "PROJECT-123",
  "summary":            "Human-readable summary"
}
```

**Why I return both HTML and Markdown:**
- HTML → rendered in the browser immediately
- Markdown → used for "Copy" and "Download .md" buttons
- Sending both avoids the browser doing any markdown parsing

**Why I include `jira_data` in the response:**
- Allows the frontend to display raw field values if needed
- Enables future features like "edit and re-generate"
- Debugging aid — user can see exactly what was fetched

**Error:**
```json
{
  "success": false,
  "error":      "Human-readable message",
  "error_code": "AUTH_FAILED | NOT_FOUND | FORBIDDEN | NETWORK_ERROR | MISSING_CONFIG | EMPTY_ID"
}
```

**Why typed error codes:**
The frontend uses `error_code` to decide behavior — `MISSING_CONFIG` and `AUTH_FAILED` auto-open the config modal. `NOT_FOUND` just shows the banner. Without typed codes, the frontend would have to regex-match error messages, which is brittle.

---

## 3. 📏 Behavioral Rules — With My Reasoning

| # | Rule | Rationale | What happens if violated |
|---|------|-----------|--------------------------|
| R1 | Every Jira field access uses `.get()` with a fallback | Jira fields can be null, missing, or structurally different across instances | `TypeError: 'NoneType' has no attribute 'name'` crash on a null assignee |
| R2 | Empty `jira_id` → return error immediately, no API call | Fail fast — don't waste a network round-trip on something we know is invalid | Jira returns a confusing 404 or 405 error |
| R3 | Missing credentials → return `MISSING_CONFIG` error | Don't make unauthorized requests that might trigger rate limits or lockouts | 401 from Jira, possibly account lockout after repeated failures |
| R4 | Never log or store tokens server-side | The server is on localhost but the principle matters — if someone adds logging later, tokens shouldn't be in the logs | Token appears in `flask.log`, gets committed to git, or shown in a debug traceback |
| R5 | ADF description must be converted before rendering | Raw ADF JSON is a wall of nested objects — useless to a human reader | Test plan shows `{"type":"doc","content":[{"type":"paragraph",...}]}` |
| R6 | Empty fields show explicit "— Not specified —" message | User must distinguish between "field exists but is empty" and "field wasn't fetched" | Blank space in the test plan — user thinks the tool is broken |
| R7 | All HTTP errors are caught and returned as structured JSON | Never show raw Python tracebacks in the browser | User sees `Internal Server Error` with a stack trace |
| R8 | `tools/` scripts are atomic and independently testable | A.N.T. Layer 3 requirement — tools must work without Flask running | Can't unit test the Jira client without spinning up a Flask app |
| R9 | Config lives in browser localStorage only | Privacy — no server-side persistence means no `.env` to accidentally commit | Token in `.env` → `git add .` → token pushed to GitHub |
| R10 | Test plan structure follows `TestPlanTemplate.md` | The template is the user's specification — deviating from it is a bug | Output doesn't match what user expects / uses in their workflow |

### Rules I considered but decided against:

- **"Always retry failed requests once"** — Rejected. For a user-driven tool, retries add latency and confusion. If Jira is down, fail fast and let the user click again.

- **"Cache Jira responses for 5 minutes"** — Rejected. This tool is for one-off test plan generation, not continuous monitoring. Caching adds stale-data risk and complexity.

- **"Validate that jira_id matches `[A-Z]+-\d+` pattern"** — Rejected. While most Jira keys follow this pattern, custom Jira instances can have different key formats. Let Jira itself reject invalid keys — it gives a better error message.

---

## 4. 🏗️ Architecture — The A.N.T. 3-Layer Design and My Thinking

### 4.1 Why 3 layers? Why not just a monolithic Flask app?

A monolithic `app.py` that handles routes, calls Jira, parses ADF, and generates markdown would work. For a ~400-line project, it's tempting. Here's why I didn't:

**Testability:** I can test `adf_converter.py` by passing it a JSON dict — no HTTP, no Flask, no Jira. I can test `testplan_generator.py` by passing it a normalized dict — no API call needed. I can test `jira_client.py` by mocking `requests.get`. Each tool has exactly one job.

**Replaceability:** If the user later wants to generate test plans from GitHub Issues instead of Jira, I replace `jira_client.py` with `github_client.py` that returns the same normalized dict. The generator doesn't change. The Flask app doesn't change.

**Debuggability:** When something breaks, the layer tells me where:
- Bad data in the test plan? → `testplan_generator.py`
- Wrong field from Jira? → `jira_client.py`
- ADF formatting garbled? → `adf_converter.py`
- Routing or HTTP issue? → `app.py`

### 4.2 Layer Breakdown

```
┌───────────────────────────────────────────────────────────┐
│  LAYER 1: Architecture (SOPs)                             │
│  architecture/sop_jira_fetch.md                           │
│  architecture/sop_testplan_generation.md                  │
│                                                           │
│  Purpose: Human-readable specifications that define       │
│  the WHAT and WHY. If logic changes, update SOP first.    │
│  Code implements the SOP, not the other way around.       │
├───────────────────────────────────────────────────────────┤
│  LAYER 2: Navigation (Flask — app.py)                     │
│                                                           │
│  POST /generate  → validate inputs                        │
│                  → call jira_client.fetch_jira_issue()    │
│                  → call testplan_generator.generate()     │
│                  → return JSON response                   │
│                                                           │
│  POST /validate  → call jira_client.validate_connection() │
│                  → return JSON response                   │
│                                                           │
│  GET /           → render templates/index.html            │
│                                                           │
│  Purpose: Routing and orchestration ONLY. Zero business   │
│  logic. app.py should read like a table of contents.      │
├───────────────────────────────────────────────────────────┤
│  LAYER 3: Tools (tools/)                                  │
│                                                           │
│  adf_converter.py      → ADF JSON dict → Markdown string │
│  jira_client.py        → (url, auth, id) → normalized {} │
│  testplan_generator.py → normalized {} → (markdown, html) │
│                                                           │
│  Purpose: Deterministic, pure functions. No Flask import, │
│  no HTTP awareness, no side effects. Accept data in,      │
│  return data out. Independently testable.                 │
└───────────────────────────────────────────────────────────┘
```

### 4.3 Architectural Invariants (non-negotiable rules)

| Invariant | Why it matters |
|-----------|---------------|
| Layer 3 tools **never import Flask** | Tools must be usable from CLI, tests, or any other context |
| Layer 2 (Flask) has **zero business logic** | `app.py` should be ~100 lines of routing, not 500 lines of mixed concerns |
| Layer 1 SOPs are **updated before code** when logic changes | The SOP is the spec; code implements it. If you update code without updating the SOP, they drift and the SOP becomes useless documentation |
| Tools accept **plain Python types** (dict, str, list) and return **plain Python types** | No request objects, no response objects — just data in, data out |
| Errors are **raised as custom exceptions**, caught at the Flask layer | Tools don't know about HTTP status codes. `JiraNotFoundError` is raised by the tool; Flask maps it to 404 |

### 4.4 Data flow through the layers

```
User types "PROJECT-123" in browser
       │
       ▼
[Frontend: app.js]
  - reads config from localStorage
  - POST /generate { jira_id, base_url, auth_type, email, token }
       │
       ▼
[Layer 2: app.py — POST /generate]
  - validates inputs (empty check)
  - calls Layer 3 ↓
       │
       ▼
[Layer 3: jira_client.py — fetch_jira_issue()]
  - builds auth headers
  - GET {base_url}/rest/api/3/issue/{jira_id}
  - handles HTTP errors (401, 403, 404, 5xx)
  - normalizes fields
  - calls adf_converter for description + comments
  - returns normalized dict
       │
       ▼
[Layer 3: testplan_generator.py — generate_test_plan_markdown()]
  - receives normalized dict
  - maps each field to test plan sections
  - applies empty-field fallbacks
  - returns (markdown_string, html_string)
       │
       ▼
[Layer 2: app.py]
  - wraps in JSON response { success: true, test_plan_html, test_plan_markdown }
       │
       ▼
[Frontend: app.js]
  - renders HTML in page
  - stores markdown for download/copy
  - shows issue badge + title
```

### 4.5 Error flow

```
Any Layer 3 tool raises an exception
  │
  ├─ JiraAuthError       → app.py catches → HTTP 401 + { error_code: "AUTH_FAILED" }
  ├─ JiraNotFoundError   → app.py catches → HTTP 404 + { error_code: "NOT_FOUND" }
  ├─ JiraForbiddenError  → app.py catches → HTTP 403 + { error_code: "FORBIDDEN" }
  ├─ JiraNetworkError    → app.py catches → HTTP 503 + { error_code: "NETWORK_ERROR" }
  ├─ JiraServerError     → app.py catches → HTTP 502 + { error_code: "SERVER_ERROR" }
  ├─ ValueError          → app.py catches → HTTP 400 + { error_code: "VALIDATION_ERROR" }
  └─ Exception (catch-all) → app.py catches → HTTP 500 + { error_code: "UNKNOWN" }
       │
       ▼
  Frontend receives JSON → shows error banner
  If error_code is AUTH or CONFIG → auto-opens config modal
```

---

## 5. 🔐 Security Model — My Reasoning

### What we protect:
- **Jira API tokens** — full access to the user's Jira instance. If leaked, an attacker could read, modify, or delete Jira issues.

### How we protect them:

| Concern | Approach | Alternative considered |
|---------|----------|----------------------|
| Storage | Browser `localStorage` | `.env` file — rejected (accidental git commit risk) |
| Transport | POST body over `localhost:5000` | Auth header — rejected (CORS preflight complexity) |
| Server logging | Never log request bodies | Flask debug mode shows routes but not POST data |
| Disk persistence | Token never touches the server filesystem | No server-side session, no database, no temp files |
| Network exposure | Flask binds to `0.0.0.0:5000` (local only by usage) | Could bind to `127.0.0.1` for stricter isolation |

### Acknowledged risks:
1. **localStorage is accessible to any JS on the page** — but since we serve our own static files with no third-party scripts, CDNs, or analytics, there's no XSS vector
2. **Flask debug mode shows tracebacks** — these could theoretically leak internal paths. This is acceptable for a local dev tool. In production, disable debug mode.
3. **`0.0.0.0` binding** — anyone on the same network could access the tool. For stricter security, bind to `127.0.0.1` only.

---

## 6. ✅ Approved Blueprint

**Confirmed by user request on 2026-10-22.**

- **Stack:** Python Flask + HTML/CSS/JS (vanilla, no framework)
- **Input:** Jira Issue ID + Jira Config (Base URL + Email + Token)
- **Output:** Rendered Test Plan (HTML on page + downloadable Markdown)
- **Template:** `TestPlanTemplate.md` (canonical structure)
- **Hosting:** `localhost:5000`
- **Auth:** Cloud = Basic (email:token), Server = Bearer PAT
- **Dependencies:** flask, requests (2 packages total)
- **Config storage:** Browser localStorage (client-side only)
- **Architecture:** A.N.T. 3-layer (SOPs → Flask orchestrator → Pure tool functions)

---

## 7. 🔮 Future Considerations (not in current scope)

| Enhancement | Effort | Value | When |
|-------------|--------|-------|------|
| Pydantic models for Jira data | Medium | High — runtime validation | v2 |
| `issuelinks` → Dependencies section | Medium | Medium — useful for complex stories | v2 |
| Epic children → auto-populate test scenarios | Medium | High — biggest value-add for Epics | v2 |
| Custom field mapping via config | High | High — every Jira instance is different | v2 |
| `mistune`/`markdown` library for HTML rendering | Low | Medium — fixes edge cases | v1.1 |
| Bind to `127.0.0.1` only | Trivial | Low — security hardening | v1.1 |
| Template-driven output (read `TestPlanTemplate.md` at runtime) | Medium | High — user customization | v2 |
| PDF export | Medium | Medium — some teams need PDFs | v2 |
| Batch mode (multiple Jira IDs) | Low | Medium — generate multiple plans at once | v2 |

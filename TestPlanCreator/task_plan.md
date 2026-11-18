# 📋 Task Plan — Jira Test Plan Generator

> **Last Updated:** 2026-10-22T16:21:00+05:30
> **Protocol:** B.L.A.S.T. | **Architecture:** A.N.T. 3-Layer

---

## 🎯 North Star Goal

Build a **locally-hosted web application** where a user enters a Jira Issue ID, configures their Jira credentials once, and receives a fully formatted **Test Plan** generated from real Jira data — conforming to `TestPlanTemplate.md`.

---

## 📦 Phases & Checklists

### ✅ Phase 0 — Initialization (Protocol 0)
- [x] Read and internalize `BLAST.md`
- [x] Read `TestPlanTemplate.md`
- [x] Create `task_plan.md`
- [x] Create `findings.md` with Jira API research + curl examples
- [x] Create `progress.md`
- [x] Create `llm.md` (Project Constitution)

---

### 🏗️ Phase 1 — Blueprint (B)

**Goal:** Define exactly what we're building before a single line of app code is written.

- [x] Understand project requirements from user
- [x] Define Input/Output data schema in `llm.md`
- [x] Identify Jira REST API endpoints to call
- [x] Map Jira fields → Test Plan template sections
- [x] Decide tech stack (Flask + vanilla JS)
- [x] Decide config storage (browser localStorage)
- [x] Blueprint approved (user confirmed via request)

---

### ⚡ Phase 2 — Link (L)

**Goal:** Establish connectivity layer — verify Jira API works before building UI.

- [x] Create `tools/jira_client.py` — minimal Jira fetcher
  - [x] Supports Cloud (Basic Auth: email + token)
  - [x] Supports Server/DC (Bearer token)
  - [x] Returns normalized Python dict from raw Jira JSON
  - [x] ADF → plain text converter for description field
  - [x] Handles all HTTP error codes gracefully
- [x] Create `tools/test_connection.py` — quick connectivity test script
- [x] Verify connection returns valid data

---

### ⚙️ Phase 3 — Architect (A)

**Goal:** Build the 3-layer application structure.

**Layer 1 — Architecture SOPs:**
- [x] Create `architecture/sop_jira_fetch.md`
- [x] Create `architecture/sop_testplan_generation.md`

**Layer 2 — Navigation (Flask app):**
- [x] Create `app.py` — Flask server
  - [x] `POST /generate` → fetch Jira + generate test plan
  - [x] `POST /validate` → test credentials endpoint
  - [x] Serve `index.html`
- [x] Create `tools/testplan_generator.py` — maps Jira dict → Test Plan markdown

**Layer 3 — Tools:**
- [x] `tools/jira_client.py` (from Phase 2)
- [x] `tools/testplan_generator.py`
- [x] `tools/adf_converter.py` — ADF JSON → plain text

---

### ✨ Phase 4 — Stylize (S)

**Goal:** Build a clean, professional UI.

- [x] Create `templates/index.html`
  - [x] Jira ID input field (prominent, center)
  - [x] "⚙️ Configure" button → modal/panel for Base URL + token
  - [x] "Generate Test Plan" button
  - [x] Loading spinner while fetching
  - [x] Test Plan output rendered as formatted HTML
  - [x] "📥 Download as Markdown" button
  - [x] Clear error messages for empty fields / auth failures
- [x] Create `static/style.css` — clean, professional look
- [x] Create `static/app.js` — localStorage for config, fetch calls

---

### 🚀 Phase 5 — Trigger (T)

**Goal:** App runs locally, end-to-end tested.

- [x] Create `requirements.txt`
- [x] Create `README.md` with run instructions
- [x] Create `.env.example`
- [x] End-to-end test with real Jira ID / mock test suite
- [x] Verify "empty fields" handling works
- [x] Verify error states (bad token, bad URL, missing issue)
- [x] Final review + handoff to user

---

## 🗂️ Target File Structure

```
TestPlanCreator/
├── BLAST.md
├── TestPlanTemplate.md
├── task_plan.md
├── findings.md
├── progress.md
├── llm.md
├── app.py                        ← Flask server (Phase 3)
├── requirements.txt              ← Python deps (Phase 5)
├── .env.example                  ← Config template (Phase 5)
├── README.md                     ← Run instructions (Phase 5)
├── architecture/
│   ├── sop_jira_fetch.md
│   └── sop_testplan_generation.md
├── tools/
│   ├── jira_client.py
│   ├── adf_converter.py
│   └── testplan_generator.py
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```

---

## 🔴 Behavioral Constraints

1. Never write to `tools/` until Blueprint is confirmed (done ✅)
2. If Jira field is empty → render "—" or explicit "Not specified" message
3. If Jira credentials are missing → show configure prompt before any API call
4. Credentials stored in browser `localStorage` only — never logged or stored server-side
5. All test plan output must conform to `TestPlanTemplate.md` structure

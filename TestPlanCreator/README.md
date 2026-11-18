# 🧪 Jira Test Plan Generator

A deterministic, locally-hosted web application that extracts structured data from Jira issues and automatically generates comprehensive, audit-ready **Test Plans** conforming to QA best practices.

Built using the **B.L.A.S.T.** protocol and **A.N.T.** 3-layer architecture.

---

## ✨ Features

- **Multi-Platform Jira Support:** Works seamlessly with both **Jira Cloud** (Email + API Token) and **Jira Server / Data Center** (Personal Access Token).
- **Smart Key Extraction:** Accepts raw Jira IDs (`KAN-1`), natural language queries (`"create test plan for JIRA KAN-1"`), or full Jira URLs (`https://company.atlassian.net/browse/KAN-1`).
- **No Duplicate Sections:** Intelligently partitions Jira descriptions into **Objective** and **Acceptance Criteria (Section 4)** so requirements are never duplicated in Scope or Objective.
- **Auto-Persistence to Convention:** Automatically persists generated reports following the standard convention:  
  📁 `TestPlanReport/TestPlan{JIRANAME}.md` (e.g. `TestPlanReport/TestPlanKAN-1.md`).
- **Rich Interactive UI:** Real-time markdown rendering in browser, instant clipboard copying, one-click file downloads, and custom file path saving.
- **macOS Friendly:** Auto-detects port conflicts (such as macOS AirPlay Receiver on port 5000) and smoothly falls back to port 5001 or custom ports.
- **Secure by Design:** Credentials are saved exclusively in your browser's `localStorage` and never written to server logs or databases.

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd TestPlanCreator
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

> **Note for macOS users:** macOS occupies port 5000 by default for AirPlay Receiver. The server will **automatically switch to port 5001** (or the next free port).
> You can also specify an explicit port:
> ```bash
> python app.py --port 5001
> # or
> PORT=5001 python app.py
> ```

### 3. Open in Browser

Navigate to the URL displayed in your terminal (typically `http://localhost:5001` or `http://localhost:5000`).

---

## ⚙️ Jira Credentials Configuration

1. Click the **⚙️ Configure** button in the top-right corner.
2. Select your deployment type:
   - **Cloud** (`*.atlassian.net`): Enter your Atlassian Email and [API Token](https://id.atlassian.com/manage-profile/security/api-tokens).
   - **Server / Data Center**: Enter your Personal Access Token (PAT).
3. Enter your **Jira Base URL** (e.g., `https://yourcompany.atlassian.net`).
4. Click **🔌 Test Connection** to verify connectivity.
5. Click **💾 Save** — credentials are stored securely in browser `localStorage`.

---

## 📋 Generating Test Plans

1. Enter a **Jira Issue ID**, natural text, or issue URL in the search bar:
   - `KAN-1`
   - `create test plan for JIRA KAN-1`
   - `https://yourcompany.atlassian.net/browse/KAN-1`
2. Press **Enter** or click **Generate Test Plan**.
3. The report is automatically generated and saved to:
   ```text
   TestPlanReport/TestPlan{JIRANAME}.md
   ```
4. You can also edit the file path and click **💾 Save to File**, click **📥 Download .md**, or click **📋 Copy Markdown**.

---

## 📁 Repository Structure

```
TestPlanCreator/
├── app.py                         ← Flask server (entry point & routes)
├── requirements.txt               ← Dependencies (Flask, requests)
├── .env.example                   ← Configuration reference
├── .gitignore                     ← Git ignore rules
├── TestPlanTemplate.md            ← Master Test Plan layout
├── README.md                      ← Documentation
├── architecture/                  ← Layer 1: Standard Operating Procedures
│   ├── sop_jira_fetch.md
│   └── sop_testplan_generation.md
├── tools/                         ← Layer 3: Deterministic Tools
│   ├── __init__.py
│   ├── jira_client.py             ← Jira REST API fetcher & error handling
│   ├── adf_converter.py           ← Atlassian Document Format (ADF) parser
│   ├── testplan_generator.py      ← Markdown generator & file persistence
│   └── test_connection.py         ← CLI connectivity test tool
├── templates/
│   └── index.html                 ← Web application frontend
├── static/
│   ├── style.css                  ← UI styling
│   └── app.js                     ← UI logic & API orchestration
├── tests/
│   └── test_suite.py              ← Automated test suite (25 unit/integration tests)
└── TestPlanReport/                ← Generated Test Plan storage directory
    └── TestPlanKAN-1.md           ← Standardized report output
```

---

## 🧪 Testing & Verification

Run the full automated test suite (covering ADF parsing, Jira client, error codes, port fallback, deduplication, and file saving):

```bash
python tests/test_suite.py
```

To test Jira connectivity directly from the command line:

```bash
python tools/test_connection.py --url https://yourcompany.atlassian.net --email user@example.com --token API_TOKEN --issue KAN-1
```

---

## 📤 Pushing to GitHub Remote

To push this repository to GitHub:

```bash
# From workspace root
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git branch -M main
git push -u origin main
```

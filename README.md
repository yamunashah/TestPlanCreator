# AI-Agents

A collection of deterministic, AI-driven developer automation tools built using the **B.L.A.S.T.** protocol and **A.N.T.** 3-layer architecture.

---

## 📂 Projects

| Project | Description | Tech Stack | Status |
|---------|-------------|------------|--------|
| [TestPlanCreator](./TestPlanCreator) | **Jira Test Plan Generator** — Automatically generates structured, audit-ready Test Plans from Jira issues with zero duplicate sections and auto-saves to `TestPlanReport/TestPlan{JIRANAME}.md`. | Python, Flask, Vanilla JS, Jira REST API v3 | ✅ Complete & Tested |

---

## 🚀 Getting Started with TestPlanCreator

```bash
# Navigate to project
cd TestPlanCreator

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the web application
python app.py
```

Open `http://localhost:5001` (or `http://localhost:5000`) in your browser.

For complete details, see [`TestPlanCreator/README.md`](./TestPlanCreator/README.md).

---

## 🧪 Running Automated Tests

```bash
cd TestPlanCreator
python tests/test_suite.py
```

---

## 📤 Pushing to Remote GitHub Repository

```bash
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git branch -M main
git add .
git commit -m "Initial commit: Jira Test Plan Generator with auto-save to TestPlanReport"
git push -u origin main
```


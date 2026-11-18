# SOP: Jira Issue Fetch

## Purpose
Defines exactly how the application fetches data from a Jira instance.

## Inputs
- `base_url`: string (e.g., `https://company.atlassian.net` or `https://jira.company.com`)
- `auth_type`: `"cloud"` or `"server"`
- `email`: string (Cloud only)
- `token`: string (API token for Cloud, PAT for Server)
- `issue_id`: string (e.g., `PROJECT-123`)

## Auth Logic
```
if auth_type == "cloud":
    header = Basic base64(email:token)
else:
    header = Bearer {token}
```

## Endpoint
```
GET {base_url}/rest/api/3/issue/{issue_id}
Query: fields=summary,description,issuetype,priority,status,assignee,reporter,
             labels,components,fixVersions,subtasks,comment,attachment,issuelinks
```

## Field Extraction Rules
- All fields accessed via `.get()` with None fallback
- `description` field is ADF JSON → pass through `adf_converter.py`
- `assignee`, `reporter` → extract `.displayName`
- `components`, `labels`, `fixVersions` → extract as lists
- `subtasks` → extract id, summary, status for each
- `comment.comments` → extract author.displayName, body (ADF convert), created

## Error Handling
| HTTP Status | Action |
|-------------|--------|
| 200 | Parse and normalize |
| 401 | Raise AuthError("Invalid credentials") |
| 403 | Raise AuthError("No permission to view issue") |
| 404 | Raise NotFoundError("Issue not found") |
| 5xx | Raise JiraServerError("Jira server error") |
| Timeout | Raise NetworkError("Cannot reach Jira") |

## Output
Normalized Python dict matching schema defined in `llm.md § 2`


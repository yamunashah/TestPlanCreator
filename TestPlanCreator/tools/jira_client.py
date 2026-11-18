"""
jira_client.py — Jira REST API Client
Layer 3 Tool: Pure function, no Flask dependency, no side effects.
Fetches a Jira issue and returns a normalized Python dict.
"""

import base64
import re
import requests
from tools.adf_converter import safe_convert_description


# ── Custom Exceptions ────────────────────────────────────────────────────────

class JiraAuthError(Exception):
    pass

class JiraNotFoundError(Exception):
    pass

class JiraForbiddenError(Exception):
    pass

class JiraNetworkError(Exception):
    pass

class JiraServerError(Exception):
    pass


# ── Auth Header Builder ───────────────────────────────────────────────────────

def build_auth_headers(auth_type: str, email: str, token: str) -> dict:
    """
    Builds the Authorization header for Jira API calls.
    - Cloud: Basic base64(email:token)
    - Server/DC: Bearer token
    """
    if auth_type == "cloud":
        if not email or not token:
            raise JiraAuthError("Email and API token are required for Jira Cloud.")
        creds = base64.b64encode(f"{email}:{token}".encode()).decode()
        return {
            "Authorization": f"Basic {creds}",
            "Accept": "application/json",
        }
    else:
        if not token:
            raise JiraAuthError("Personal Access Token is required for Jira Server/DC.")
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }


# ── Field Normalizers ─────────────────────────────────────────────────────────

def _safe_str(val) -> str:
    """Return string value or empty string."""
    return str(val) if val is not None else ""


def _extract_display_name(obj) -> str:
    if not obj:
        return ""
    return obj.get("displayName") or obj.get("name") or ""


def _extract_list_names(lst) -> list:
    if not lst:
        return []
    return [item.get("name", "") for item in lst if item]


def _normalize_subtasks(subtasks: list) -> list:
    result = []
    for sub in (subtasks or []):
        fields = sub.get("fields", {})
        result.append({
            "id": sub.get("key", ""),
            "summary": fields.get("summary", ""),
            "status": (fields.get("status") or {}).get("name", ""),
        })
    return result


def _normalize_comments(comment_obj) -> list:
    comments_list = (comment_obj or {}).get("comments", [])
    result = []
    for c in comments_list[:5]:  # cap at 5 comments
        body_raw = c.get("body", "")
        body_text = safe_convert_description(body_raw)
        result.append({
            "author": _extract_display_name(c.get("author")),
            "body": body_text,
            "created": c.get("created", ""),
        })
    return result


def _normalize_attachments(attachments: list) -> list:
    result = []
    for att in (attachments or []):
        result.append({
            "filename": att.get("filename", ""),
            "url": att.get("content", ""),
        })
    return result


# ── Key Extraction ────────────────────────────────────────────────────────────

def extract_jira_key(raw_input: str) -> str:
    """
    Extracts a normalized Jira issue key (e.g. 'KAN-1') from raw input or URL.
    Examples:
        'create test plan for JIRA KAN-1' -> 'KAN-1'
        'KAN-1' -> 'KAN-1'
        'kan-1' -> 'KAN-1'
        'https://company.atlassian.net/browse/KAN-1' -> 'KAN-1'
    """
    if not raw_input:
        return ""
    text = str(raw_input).strip()
    match = re.search(r'\b([A-Za-z][A-Za-z0-9]+-\d+)\b', text)
    if match:
        return match.group(1).upper()
    return text.upper()


# ── Main Fetcher ──────────────────────────────────────────────────────────────

def fetch_jira_issue(base_url: str, auth_type: str, email: str, token: str, issue_id: str) -> dict:
    """
    Fetches a Jira issue by ID and returns a normalized dict.

    Args:
        base_url:  Jira base URL (no trailing slash)
        auth_type: "cloud" or "server"
        email:     User email (Cloud only)
        token:     API token (Cloud) or PAT (Server)
        issue_id:  Jira issue key or phrase, e.g. "PROJECT-123" or "create test plan for JIRA KAN-1"

    Returns:
        Normalized dict conforming to llm.md § 2 schema.

    Raises:
        JiraAuthError, JiraNotFoundError, JiraForbiddenError,
        JiraNetworkError, JiraServerError, ValueError
    """
    if not issue_id or not str(issue_id).strip():
        raise ValueError("Jira issue ID cannot be empty.")

    clean_id = extract_jira_key(issue_id)
    if not clean_id or not re.match(r'^[A-Z][A-Z0-9]+-\d+$', clean_id):
        raise ValueError(
            f"Invalid Jira Issue ID '{issue_id}'. Expected format like PROJECT-123 or KAN-1."
        )

    base_url = base_url.rstrip("/")
    headers = build_auth_headers(auth_type, email, token)

    fields = (
        "summary,description,issuetype,priority,status,"
        "assignee,reporter,labels,components,fixVersions,"
        "subtasks,comment,attachment,issuelinks"
    )
    url = f"{base_url}/rest/api/3/issue/{clean_id}"

    try:
        response = requests.get(
            url,
            headers=headers,
            params={"fields": fields},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        raise JiraNetworkError(
            f"Cannot connect to Jira at '{base_url}'. Check the Base URL."
        )
    except requests.exceptions.Timeout:
        raise JiraNetworkError("Jira request timed out after 15 seconds.")
    except requests.exceptions.RequestException as e:
        raise JiraNetworkError(f"Network error: {str(e)}")

    # Handle HTTP errors
    if response.status_code == 401:
        raise JiraAuthError("Authentication failed. Check your email and API token.")
    if response.status_code == 403:
        raise JiraForbiddenError(f"Access denied. You don't have permission to view '{clean_id}'.")
    if response.status_code == 404:
        raise JiraNotFoundError(f"Issue '{clean_id}' not found in Jira.")
    if response.status_code >= 500:
        raise JiraServerError(f"Jira server error (HTTP {response.status_code}). Try again later.")
    if response.status_code != 200:
        raise JiraServerError(f"Unexpected response from Jira (HTTP {response.status_code}).")

    raw = response.json()
    f = raw.get("fields", {})

    # Build the normalized output
    return {
        "id": raw.get("key", clean_id),
        "summary": f.get("summary") or "",
        "description": safe_convert_description(f.get("description")),
        "issue_type": (f.get("issuetype") or {}).get("name") or "",
        "priority": (f.get("priority") or {}).get("name") or "",
        "status": (f.get("status") or {}).get("name") or "",
        "assignee": _extract_display_name(f.get("assignee")),
        "reporter": _extract_display_name(f.get("reporter")),
        "labels": f.get("labels") or [],
        "components": _extract_list_names(f.get("components")),
        "fix_versions": _extract_list_names(f.get("fixVersions")),
        "subtasks": _normalize_subtasks(f.get("subtasks")),
        "comments": _normalize_comments(f.get("comment")),
        "attachments": _normalize_attachments(f.get("attachment")),
        "url": f"{base_url}/browse/{raw.get('key', clean_id)}",
    }


def validate_connection(base_url: str, auth_type: str, email: str, token: str) -> dict:
    """
    Tests Jira connectivity and auth without fetching a specific issue.
    Calls the /rest/api/3/myself endpoint.
    """
    base_url = base_url.rstrip("/")
    try:
        headers = build_auth_headers(auth_type, email, token)
        response = requests.get(
            f"{base_url}/rest/api/3/myself",
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "user": data.get("displayName", "Unknown")}
        elif response.status_code == 401:
            return {"success": False, "error": "Invalid credentials. Check email and token."}
        elif response.status_code == 403:
            return {"success": False, "error": "Forbidden. Token may lack required permissions."}
        else:
            return {"success": False, "error": f"Unexpected response: HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


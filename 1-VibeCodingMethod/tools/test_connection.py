"""
test_connection.py — CLI tool to test Jira connectivity
Layer 3 Tool: Verifies Jira credentials and network connectivity from the terminal.
Usage:
    python tools/test_connection.py --url https://yourcompany.atlassian.net --email user@example.com --token API_TOKEN
    python tools/test_connection.py --url https://jira.yourcompany.com --auth-type server --token PAT
"""

import sys
import os
import argparse

# Ensure tools can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.jira_client import validate_connection, fetch_jira_issue


def parse_args():
    parser = argparse.ArgumentParser(description="Test Jira API connection and credentials.")
    parser.add_argument("--url", help="Jira Base URL (e.g., https://yourcompany.atlassian.net)")
    parser.add_argument("--auth-type", choices=["cloud", "server"], default="cloud", help="Authentication type (cloud or server)")
    parser.add_argument("--email", default="", help="Jira account email (required for cloud)")
    parser.add_argument("--token", help="Jira API token (Cloud) or PAT (Server)")
    parser.add_argument("--issue", default=None, help="Optional Jira issue ID to test fetching (e.g., PROJECT-123)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Fallback to environment variables if arguments not provided
    url = args.url or os.environ.get("JIRA_BASE_URL", "").strip()
    auth_type = args.auth_type or os.environ.get("JIRA_AUTH_TYPE", "cloud").strip()
    email = args.email or os.environ.get("JIRA_EMAIL", "").strip()
    token = args.token or os.environ.get("JIRA_API_TOKEN", os.environ.get("JIRA_PAT", "")).strip()

    if not url:
        print("❌ Error: Jira Base URL is required (--url or JIRA_BASE_URL)")
        sys.exit(1)
    if not token:
        print("❌ Error: Jira token is required (--token, JIRA_API_TOKEN, or JIRA_PAT)")
        sys.exit(1)
    if auth_type == "cloud" and not email:
        print("❌ Error: Email is required for Jira Cloud (--email or JIRA_EMAIL)")
        sys.exit(1)

    print(f"🔌 Testing connection to: {url} ({auth_type.upper()})...")
    res = validate_connection(base_url=url, auth_type=auth_type, email=email, token=token)

    if res.get("success"):
        print(f"✅ Connection successful! Authenticated as: {res.get('user', 'Unknown')}")
    else:
        print(f"❌ Connection failed: {res.get('error', 'Unknown error')}")
        sys.exit(1)

    if args.issue:
        print(f"\n📋 Fetching issue '{args.issue}'...")
        try:
            issue_data = fetch_jira_issue(url, auth_type, email, token, args.issue)
            print(f"✅ Successfully fetched issue: {issue_data.get('id')} - {issue_data.get('summary')}")
            print(f"   Status: {issue_data.get('status')} | Priority: {issue_data.get('priority')}")
            print(f"   Assignee: {issue_data.get('assignee')} | Reporter: {issue_data.get('reporter')}")
        except Exception as e:
            print(f"❌ Failed to fetch issue '{args.issue}': {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    main()


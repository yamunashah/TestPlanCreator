"""
test_suite.py — Comprehensive Test Suite for Jira Test Plan Generator
Tests all 3 layers:
1. Tools: adf_converter, jira_client, testplan_generator
2. Navigation: Flask endpoints (/generate, /validate, /)
3. Edge cases: empty fields, null values, invalid credentials, malformed ADF
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.adf_converter import (
    adf_to_markdown,
    safe_convert_description
)
from tools.jira_client import (
    build_auth_headers,
    fetch_jira_issue,
    extract_jira_key,
    validate_connection,
    JiraAuthError,
    JiraNotFoundError,
    JiraForbiddenError,
    JiraNetworkError,
    JiraServerError,
)
from tools.testplan_generator import (
    generate_test_plan_markdown,
    markdown_to_html,
    split_description_and_criteria,
    save_test_plan,
    get_report_path,
    EMPTY,
    EMPTY_DESC,
    EMPTY_CRITERIA,
    EMPTY_SUBTASKS
)
from app import app, is_port_available, find_available_port


class TestADFConverter(unittest.TestCase):
    def test_plain_text(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Hello world"}]
                }
            ]
        }
        res = adf_to_markdown(adf)
        self.assertIn("Hello world", res)

    def test_marks_formatting(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Bold", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": " "},
                        {"type": "text", "text": "Italic", "marks": [{"type": "em"}]},
                        {"type": "text", "text": " "},
                        {"type": "text", "text": "Code", "marks": [{"type": "code"}]},
                        {"type": "text", "text": " "},
                        {"type": "text", "text": "Link", "marks": [{"type": "link", "attrs": {"href": "https://example.com"}}]}
                    ]
                }
            ]
        }
        res = adf_to_markdown(adf)
        self.assertIn("**Bold**", res)
        self.assertIn("*Italic*", res)
        self.assertIn("`Code`", res)
        self.assertIn("[Link](https://example.com)", res)

    def test_headings_and_lists(self):
        adf = {
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": "Heading 2"}]
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Item 1"}]}]
                        }
                    ]
                }
            ]
        }
        res = adf_to_markdown(adf)
        self.assertIn("## Heading 2", res)
        self.assertIn("- Item 1", res)

    def test_safe_convert_string_or_none(self):
        self.assertEqual(safe_convert_description(None), "")
        self.assertEqual(safe_convert_description("Plain text fallback"), "Plain text fallback")
        self.assertEqual(safe_convert_description(123), "123")


class TestJiraClient(unittest.TestCase):
    def test_extract_jira_key(self):
        self.assertEqual(extract_jira_key("create test plan for JIRA KAN-1"), "KAN-1")
        self.assertEqual(extract_jira_key("KAN-1"), "KAN-1")
        self.assertEqual(extract_jira_key("kan-1"), "KAN-1")
        self.assertEqual(extract_jira_key("https://domain.atlassian.net/browse/KAN-1"), "KAN-1")
        self.assertEqual(extract_jira_key("https://domain.atlassian.net/browse/PROJ-456?filter=1"), "PROJ-456")

    def test_auth_headers_cloud(self):
        headers = build_auth_headers("cloud", "test@test.com", "token123")
        self.assertIn("Authorization", headers)
        self.assertTrue(headers["Authorization"].startswith("Basic "))

    def test_auth_headers_server(self):
        headers = build_auth_headers("server", "", "pat123")
        self.assertEqual(headers["Authorization"], "Bearer pat123")

    def test_auth_headers_missing_cloud(self):
        with self.assertRaises(JiraAuthError):
            build_auth_headers("cloud", "", "token")

    @patch("requests.get")
    def test_fetch_jira_issue_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "key": "PROJ-101",
            "fields": {
                "summary": "Sample Issue",
                "description": "Simple description",
                "issuetype": {"name": "Story"},
                "priority": {"name": "High"},
                "status": {"name": "In Progress"},
                "assignee": {"displayName": "John Doe"},
                "reporter": {"displayName": "Jane Smith"},
                "labels": ["backend", "api"],
                "components": [{"name": "Auth"}],
                "fixVersions": [{"name": "v1.0"}],
                "subtasks": [
                    {"key": "PROJ-102", "fields": {"summary": "Sub 1", "status": {"name": "Done"}}}
                ],
                "comment": {
                    "comments": [
                        {"author": {"displayName": "Dev 1"}, "body": "Working on it", "created": "2026-11-18T10:00:00Z"}
                    ]
                },
                "attachment": [
                    {"filename": "spec.pdf", "content": "https://jira.com/spec.pdf"}
                ]
            }
        }
        mock_get.return_value = mock_resp

        data = fetch_jira_issue("https://jira.example.com", "cloud", "a@b.com", "tok", "PROJ-101")
        self.assertEqual(data["id"], "PROJ-101")
        self.assertEqual(data["summary"], "Sample Issue")
        self.assertEqual(data["assignee"], "John Doe")
        self.assertEqual(data["labels"], ["backend", "api"])
        self.assertEqual(len(data["subtasks"]), 1)
        self.assertEqual(len(data["comments"]), 1)

    @patch("requests.get")
    def test_fetch_jira_errors(self, mock_get):
        # 401 Auth Error
        mock_resp = MagicMock(status_code=401)
        mock_get.return_value = mock_resp
        with self.assertRaises(JiraAuthError):
            fetch_jira_issue("https://jira.example.com", "cloud", "a@b.com", "tok", "PROJ-101")

        # 404 Not Found
        mock_resp = MagicMock(status_code=404)
        mock_get.return_value = mock_resp
        with self.assertRaises(JiraNotFoundError):
            fetch_jira_issue("https://jira.example.com", "cloud", "a@b.com", "tok", "PROJ-101")

        # 403 Forbidden
        mock_resp = MagicMock(status_code=403)
        mock_get.return_value = mock_resp
        with self.assertRaises(JiraForbiddenError):
            fetch_jira_issue("https://jira.example.com", "cloud", "a@b.com", "tok", "PROJ-101")


class TestTestPlanGenerator(unittest.TestCase):
    def test_generator_full_data(self):
        jira_data = {
            "id": "PROJ-1",
            "url": "https://jira.example.com/browse/PROJ-1",
            "summary": "Implement OAuth2 login",
            "description": "Users should be able to log in with Google OAuth.",
            "issue_type": "Story",
            "priority": "High",
            "status": "In Progress",
            "assignee": "Alice",
            "reporter": "Bob",
            "labels": ["auth", "security"],
            "components": ["Login Module"],
            "fix_versions": ["v2.0"],
            "subtasks": [{"id": "PROJ-2", "summary": "Setup OAuth client", "status": "Done"}],
            "comments": [{"author": "Bob", "created": "2026-11-18", "body": "Ready for review"}],
            "attachments": [{"filename": "oauth.png", "url": "https://example.com/oauth.png"}]
        }
        md = generate_test_plan_markdown(jira_data)
        self.assertIn("# Test Plan: Implement OAuth2 login", md)
        self.assertIn("[PROJ-1](https://jira.example.com/browse/PROJ-1)", md)
        self.assertIn("Implement OAuth2 login", md)
        self.assertIn("Users should be able to log in with Google OAuth.", md)
        self.assertIn("PROJ-2", md)
        self.assertIn("oauth.png", md)

        html = markdown_to_html(md)
        self.assertIn("<h1>Test Plan: Implement OAuth2 login</h1>", html)
        self.assertIn("<table class=\"test-plan-table\">", html)

    def test_generator_empty_fields(self):
        jira_data = {
            "id": "PROJ-999",
            "url": "",
            "summary": "",
            "description": "",
            "issue_type": "",
            "priority": "",
            "status": "",
            "assignee": "",
            "reporter": "",
            "labels": [],
            "components": [],
            "fix_versions": [],
            "subtasks": [],
            "comments": [],
            "attachments": []
        }
        md = generate_test_plan_markdown(jira_data)
        self.assertIn(EMPTY, md)
        self.assertIn(EMPTY_DESC, md)
        self.assertIn(EMPTY_SUBTASKS, md)

    def test_split_description_and_criteria(self):
        desc = "As a user, I want SSO.\n\nAcceptance Criteria:\n- Google login works\n- Session valid"
        obj, crit = split_description_and_criteria(desc)
        self.assertEqual(obj, "As a user, I want SSO.")
        self.assertIn("Google login works", crit)

    def test_no_duplicate_acceptance_criteria_in_markdown(self):
        jira_data = {
            "id": "KAN-1",
            "summary": "Implement user login",
            "description": "User Story: Log in with credentials.\n\nAcceptance Criteria:\n- Verify valid email\n- Verify password length",
            "components": ["Auth"],
        }
        md = generate_test_plan_markdown(jira_data)
        # Verify Acceptance Criteria text appears strictly once, under Section 4
        self.assertEqual(md.count("Verify valid email"), 1)
        self.assertEqual(md.count("Verify password length"), 1)
        self.assertIn("## 4. 📋 Acceptance Criteria", md)
        self.assertIn("## 1. 🎯 Objective\n\nUser Story: Log in with credentials.", md)

    def test_get_report_path_convention(self):
        self.assertTrue(get_report_path("KAN-1").endswith("TestPlanReport/TestPlanKAN-1.md"))
        self.assertTrue(get_report_path("PROJ-123").endswith("TestPlanReport/TestPlanPROJ-123.md"))
        self.assertTrue(get_report_path("").endswith("TestPlanReport/TestPlanReport.md"))
        self.assertEqual(get_report_path("KAN-1", base_dir="custom"), "custom/TestPlanReport/TestPlanKAN-1.md")

    def test_save_test_plan(self):
        test_path = "/tmp/test_plan_output.md"
        content = "# Sample Test Plan Content"
        saved = save_test_plan(content, test_path)
        self.assertEqual(saved, test_path)
        self.assertTrue(os.path.exists(test_path))
        with open(test_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), content)
        os.remove(test_path)

        # Test default path with jira_id
        saved_default = save_test_plan(content, jira_id="KAN-99")
        self.assertTrue(saved_default.endswith("TestPlanReport/TestPlanKAN-99.md"))
        self.assertTrue(os.path.exists(saved_default))
        os.remove(saved_default)


class TestAppEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Jira Test Plan Generator", response.data)

    def test_generate_missing_config(self):
        response = self.client.post("/generate", json={"jira_id": "TEST-1"})
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "MISSING_CONFIG")

    def test_generate_empty_id(self):
        response = self.client.post("/generate", json={
            "jira_id": "",
            "base_url": "https://jira.example.com",
            "token": "tok"
        })
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error_code"], "EMPTY_ID")

    @patch("app.fetch_jira_issue")
    def test_generate_success(self, mock_fetch):
        mock_fetch.return_value = {
            "id": "PROJ-100",
            "url": "https://jira.example.com/browse/PROJ-100",
            "summary": "Fix checkout bug",
            "description": "Bug fix description",
            "issue_type": "Bug",
            "priority": "Critical",
            "status": "Open",
            "assignee": "Dev",
            "reporter": "Tester",
            "labels": [],
            "components": [],
            "fix_versions": [],
            "subtasks": [],
            "comments": [],
            "attachments": []
        }

        response = self.client.post("/generate", json={
            "jira_id": "PROJ-100",
            "base_url": "https://jira.example.com",
            "auth_type": "server",
            "token": "secret_pat"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["issue_id"], "PROJ-100")
        self.assertIn("Fix checkout bug", data["test_plan_markdown"])
        self.assertIn("test-plan-table", data["test_plan_html"])
        if data.get("saved_to") and os.path.exists(data["saved_to"]):
            os.remove(data["saved_to"])

    @patch("app.validate_connection")
    def test_validate_endpoint(self, mock_validate):
        mock_validate.return_value = {"success": True, "user": "Admin User"}
        response = self.client.post("/validate", json={
            "base_url": "https://jira.example.com",
            "auth_type": "server",
            "token": "valid_token"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"], "Admin User")

    def test_save_endpoint(self):
        test_path = "/tmp/test_plan_report_api.md"
        response = self.client.post("/save", json={
            "markdown": "# Header\nContent",
            "file_path": test_path
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(os.path.exists(test_path))
        if os.path.exists(test_path):
            os.remove(test_path)

    @patch("app.fetch_jira_issue")
    def test_generate_with_file_path(self, mock_fetch):
        mock_fetch.return_value = {
            "id": "KAN-1",
            "summary": "Sample Issue",
            "description": "Some description",
        }
        test_path = "/tmp/test_plan_generate_saved.md"
        response = self.client.post("/generate", json={
            "jira_id": "KAN-1",
            "base_url": "https://jira.example.com",
            "auth_type": "server",
            "token": "tok",
            "file_path": test_path
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("saved_to", data)
        self.assertTrue(os.path.exists(test_path))
        if os.path.exists(test_path):
            os.remove(test_path)


class TestPortUtilities(unittest.TestCase):
    def test_find_available_port(self):
        port = find_available_port(5000)
        self.assertIsInstance(port, int)
        self.assertTrue(is_port_available(port))
        self.assertGreaterEqual(port, 5000)

    @patch("socket.socket")
    def test_is_port_available_false_on_oserror(self, mock_socket_class):
        mock_sock = MagicMock()
        mock_sock.bind.side_effect = OSError("Address already in use")
        mock_socket_class.return_value.__enter__.return_value = mock_sock
        self.assertFalse(is_port_available(5000))


if __name__ == "__main__":
    unittest.main()

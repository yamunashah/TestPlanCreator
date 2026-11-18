"""
app.py — Flask Application Server
Layer 2 (Navigation): Orchestrates requests between the UI and tool layer.
No business logic here — only routing and error handling.
"""

import sys
import os
import socket
import argparse

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, render_template, send_from_directory
from tools.jira_client import (
    fetch_jira_issue,
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
    save_test_plan,
    get_report_path,
)

app = Flask(__name__, template_folder="templates", static_folder="static")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """
    Main endpoint: fetch Jira issue → generate test plan.
    Expects JSON body with: jira_id, base_url, auth_type, email, token
    """
    data = request.get_json(force=True) or {}

    jira_id  = (data.get("jira_id") or "").strip()
    base_url = (data.get("base_url") or "").strip()
    auth_type = (data.get("auth_type") or "cloud").strip()
    email    = (data.get("email") or "").strip()
    token    = (data.get("token") or "").strip()

    # ── Input validation ──
    if not jira_id:
        return jsonify({"success": False, "error": "Please enter a Jira Issue ID.", "error_code": "EMPTY_ID"}), 400

    if not base_url:
        return jsonify({"success": False, "error": "Jira Base URL is not configured. Click ⚙️ Configure.", "error_code": "MISSING_CONFIG"}), 400

    if not token:
        return jsonify({"success": False, "error": "Jira API token is not configured. Click ⚙️ Configure.", "error_code": "MISSING_CONFIG"}), 400

    if auth_type == "cloud" and not email:
        return jsonify({"success": False, "error": "Email is required for Jira Cloud. Click ⚙️ Configure.", "error_code": "MISSING_CONFIG"}), 400

    # ── Fetch from Jira ──
    try:
        jira_data = fetch_jira_issue(base_url, auth_type, email, token, jira_id)
    except JiraAuthError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "AUTH_FAILED"}), 401
    except JiraNotFoundError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "NOT_FOUND"}), 404
    except JiraForbiddenError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "FORBIDDEN"}), 403
    except JiraNetworkError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "NETWORK_ERROR"}), 503
    except JiraServerError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "SERVER_ERROR"}), 502
    except ValueError as e:
        return jsonify({"success": False, "error": str(e), "error_code": "VALIDATION_ERROR"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Unexpected error: {str(e)}", "error_code": "UNKNOWN"}), 500

    # ── Generate Test Plan ──
    try:
        test_plan_md = generate_test_plan_markdown(jira_data)
        test_plan_html = markdown_to_html(test_plan_md)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to generate test plan: {str(e)}", "error_code": "GENERATION_ERROR"}), 500

    # ── Auto-save to TestPlanReport/TestPlan{JIRANAME}.md ──
    issue_key = jira_data.get("id", jira_id)
    file_path = (data.get("file_path") or "").strip()
    if not file_path:
        file_path = get_report_path(issue_key)

    saved_path = None
    try:
        saved_path = save_test_plan(test_plan_md, file_path, jira_id=issue_key)
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to save test plan to {file_path}: {str(e)}", "error_code": "FILE_SAVE_ERROR"}), 500

    resp = {
        "success": True,
        "test_plan_html": test_plan_html,
        "test_plan_markdown": test_plan_md,
        "jira_data": jira_data,
        "issue_id": issue_key,
        "summary": jira_data.get("summary", ""),
        "saved_to": saved_path,
    }

    return jsonify(resp)


@app.route("/save", methods=["POST"])
def save_report():
    """
    Saves test plan markdown directly to a specified local file path.
    Expects JSON with: markdown, file_path (optional), jira_id (optional).
    Default convention: TestPlanReport/TestPlan{JIRANAME}.md
    """
    data = request.get_json(force=True) or {}
    markdown = data.get("markdown", "")
    jira_id  = (data.get("jira_id") or "").strip()
    file_path = (data.get("file_path") or "").strip()

    if not file_path:
        file_path = get_report_path(jira_id)

    if not markdown:
        return jsonify({"success": False, "error": "No test plan content to save."}), 400

    try:
        saved_path = save_test_plan(markdown, file_path, jira_id=jira_id)
        return jsonify({
            "success": True,
            "file_path": saved_path,
            "message": f"Successfully saved test plan to: {saved_path}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to save file: {str(e)}"}), 500


@app.route("/validate", methods=["POST"])
def validate():
    """
    Tests Jira credentials without fetching a specific issue.
    Calls /rest/api/3/myself endpoint.
    """
    data = request.get_json(force=True) or {}
    base_url  = (data.get("base_url") or "").strip()
    auth_type = (data.get("auth_type") or "cloud").strip()
    email     = (data.get("email") or "").strip()
    token     = (data.get("token") or "").strip()

    if not base_url or not token:
        return jsonify({"success": False, "error": "Base URL and token are required."}), 400

    result = validate_connection(base_url, auth_type, email, token)
    status_code = 200 if result["success"] else 401
    return jsonify(result), status_code


# ── Port & Server Utilities ───────────────────────────────────────────────────

def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(preferred_port: int, host: str = "0.0.0.0", max_attempts: int = 50) -> int:
    """Find the next available port starting from preferred_port."""
    for port in range(preferred_port, preferred_port + max_attempts):
        if is_port_available(port, host):
            return port
    return preferred_port


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jira Test Plan Generator Flask Server")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="Port to listen on (default: 5000, or auto-fallback to 5001+ if in use)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Disable Flask debug mode",
    )
    args = parser.parse_args()

    host = args.host
    debug_mode = not args.no_debug

    # Check if port was already selected in parent process (for Werkzeug reloader)
    if "APP_PORT" in os.environ:
        port = int(os.environ["APP_PORT"])
    else:
        env_port = os.environ.get("PORT")
        user_specified = args.port is not None or env_port is not None
        preferred_port = args.port if args.port is not None else (int(env_port) if env_port else 5000)

        if is_port_available(preferred_port, host):
            port = preferred_port
        else:
            if preferred_port == 5000 and not user_specified:
                port = find_available_port(5001, host)
                print(f"\n⚠️  Port 5000 is currently in use (common on macOS due to AirPlay Receiver).")
                print(f"🔄 Automatically switched to port {port}.")
                print("ℹ️  To free port 5000 on macOS, turn off 'AirPlay Receiver' in:")
                print("   System Settings > General > AirDrop & AirPlay > AirPlay Receiver\n")
            else:
                port = find_available_port(preferred_port + 1, host)
                print(f"\n⚠️  Port {preferred_port} is already in use.")
                print(f"🔄 Automatically switched to port {port}.\n")

        os.environ["APP_PORT"] = str(port)

    # Print startup banner
    display_host = "localhost" if host in ("0.0.0.0", "127.0.0.1") else host
    print("\n🚀 Jira Test Plan Generator")
    print("=" * 45)
    print(f"📡 Running at: http://{display_host}:{port}")
    print("⚙️  Click 'Configure' to set your Jira credentials")
    print("=" * 45 + "\n")

    app.run(debug=debug_mode, host=host, port=port)

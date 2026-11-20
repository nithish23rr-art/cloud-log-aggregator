"""M&K Nexus Cloud - Log Hub blueprint.

Two ways to analyse a company's logs:
  1) POST /api/v3/hub/ingest  -> X-API-Key + a .log/.txt file upload   (unchanged)
  2) POST /api/v3/hub/pull    -> X-API-Key ONLY (NEW). The server uses the log source
     registered for that key in api_keys.py (log_dir folder and/or source_url) to read the
     company's logs itself, categorise them and return the report.
"""
import os
import urllib.request
import urllib.error
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from api_keys import HUB_KEYS

log_hub_bp = Blueprint('log_hub_bp', __name__)

VALID_API_KEYS = HUB_KEYS          # kept name for backward compatibility
ALLOWED_EXT = ('.log', '.txt')
MAX_FILES = 50                     # per pull
MAX_LINES_PER_FILE = 5000
MAX_REMOTE_BYTES = 5 * 1024 * 1024
REMOTE_TIMEOUT = 15
CATEGORIES = ("CRITICAL", "SECURITY", "ERROR", "WARNING", "INFO", "DEBUG", "OTHER")


def advanced_categorize_and_score(line):
    upper_line = line.upper()
    if "FATAL" in upper_line or "CRITICAL" in upper_line:
        return "CRITICAL", 0.95
    elif "SECURITY" in upper_line or "UNAUTHORIZED" in upper_line or "AUTH_FAIL" in upper_line:
        return "SECURITY", 0.90
    elif "ERROR" in upper_line:
        return "ERROR", 0.80
    elif "WARN" in upper_line or "WARNING" in upper_line:
        return "WARNING", 0.50
    elif "DEBUG" in upper_line:
        return "DEBUG", 0.05
    elif "INFO" in upper_line:
        return "INFO", 0.10
    return "OTHER", 0.01


def build_report(lines, company, extra=None):
    """Categorise lines and build the JSON the dashboard expects."""
    buckets = {c: [] for c in CATEGORIES}
    total_score = 0.0
    total = 0
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        category, score = advanced_categorize_and_score(line)
        buckets[category].append({"message": line, "threat_score": score, "timestamp": now})
        total_score += score
        total += 1
    report = {
        "status": "success",
        "cluster_hub": company,
        "total_logs_analyzed": total,
        "cluster_threat_index": round(total_score / total, 2) if total else 0.0,
        "category_summary": {c.lower(): len(buckets[c]) for c in CATEGORIES},
        "categorized_data": buckets,
    }
    if extra:
        report.update(extra)
    return report


def _auth():
    key = request.headers.get('X-API-Key')
    if not key or key not in VALID_API_KEYS:
        return None
    return VALID_API_KEYS[key]


@log_hub_bp.route('/api/v3/hub/ingest', methods=['POST'])
def ingest_log_hub_data():
    client = _auth()
    if not client:
        return jsonify({"error": "Unauthorized: Invalid or missing API Key"}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No log file attached in 'file' field"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Selected file is empty"}), 400
    try:
        lines = file.read().decode('utf-8', errors='ignore').splitlines()
        return jsonify(build_report(lines, client["company"])), 200
    except Exception as e:
        return jsonify({"error": f"Log parsing failed: {str(e)}"}), 500


def _read_folder(folder):
    """Read .log/.txt files directly inside the configured folder (no sub-folder / traversal)."""
    lines, sources = [], []
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"log_dir not found on server: {folder}")
    names = sorted(n for n in os.listdir(folder) if n.lower().endswith(ALLOWED_EXT))[:MAX_FILES]
    for name in names:
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
            file_lines = fh.read().splitlines()[-MAX_LINES_PER_FILE:]   # newest lines
        lines.extend(file_lines)
        sources.append({"type": "folder", "name": name, "lines": len(file_lines)})
    return lines, sources


def _read_remote(url, token):
    """GET the company's own log endpoint. Accepts plain text or JSON {"logs": [...]}."""
    if not url.lower().startswith(("https://", "http://")):
        raise ValueError("source_url must be http(s)")
    req = urllib.request.Request(url, headers={"Accept": "text/plain, application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=REMOTE_TIMEOUT) as resp:
        body = resp.read(MAX_REMOTE_BYTES + 1)
        if len(body) > MAX_REMOTE_BYTES:
            raise ValueError("remote log response too large")
        text = body.decode('utf-8', errors='ignore')
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("logs"), list):
            file_lines = [str(x) for x in data["logs"]]
        else:
            file_lines = text.splitlines()
    except ValueError:
        file_lines = text.splitlines()
    file_lines = file_lines[-MAX_LINES_PER_FILE:]
    return file_lines, [{"type": "remote", "name": url, "lines": len(file_lines)}]


@log_hub_bp.route('/api/v3/hub/pull', methods=['POST', 'GET'])
def pull_company_logs():
    """API key only: server reads the company's registered log source and categorises it."""
    client = _auth()
    if not client:
        return jsonify({"error": "Unauthorized: Invalid or missing API Key"}), 401
    folder, url = client.get("log_dir"), client.get("source_url")
    if not folder and not url:
        return jsonify({"error": "No log source is registered for this API key. "
                                 "Ask the admin to set log_dir or source_url for it."}), 404
    lines, sources, errors = [], [], []
    if folder:
        try:
            l, s = _read_folder(folder); lines += l; sources += s
        except Exception as e:
            errors.append(f"folder: {e}")
    if url:
        try:
            l, s = _read_remote(url, client.get("source_token")); lines += l; sources += s
        except (urllib.error.URLError, ValueError, OSError) as e:
            errors.append(f"remote: {e}")
    if not lines and errors:
        return jsonify({"error": "Could not read company logs", "details": errors}), 502
    extra = {"sources": sources}
    if errors:
        extra["warnings"] = errors
    return jsonify(build_report(lines, client["company"], extra)), 200

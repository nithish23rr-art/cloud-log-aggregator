import os
import time
from datetime import datetime
from flask import Flask, Blueprint, request, jsonify
from flask_socketio import SocketIO, emit
from api_keys import ENTERPRISE_KEYS

# 1. Flask Blueprint for Enterprise Log Hub
enterprise_bp = Blueprint('enterprise_bp', __name__)

# Keys come from api_keys.py (override with NEXUS_ENTERPRISE_KEYS)
VALID_API_KEYS = ENTERPRISE_KEYS

# 2. Function to categorize and score logs based on severity and threat level
def categorize_and_score_log(line):
    upper_line = line.upper()
    
    if "FATAL" in upper_line or "CRITICAL" in upper_line:
        return "CRITICAL", 0.95
    elif "ERROR" in upper_line:
        return "ERROR", 0.80
    elif "WARN" in upper_line or "WARNING" in upper_line:
        return "WARNING", 0.50
    elif "SECURITY" in upper_line or "UNAUTHORIZED" in upper_line or "AUTH" in upper_line:
        return "SECURITY", 0.90
    elif "DEBUG" in upper_line:
        return "DEBUG", 0.05
    elif "INFO" in upper_line:
        return "INFO", 0.10
    else:
        return "OTHER", 0.01

# 3. API Endpoint for log ingestion and processing
@enterprise_bp.route('/api/v2/ingest-logs', methods=['POST'])
def ingest_and_process_logs():
    # API Key validation
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key not in VALID_API_KEYS:
        return jsonify({"error": "Unauthorized: Invalid or missing API Key"}), 401
    
    client_info = VALID_API_KEYS[api_key]
    company_name = client_info["company"]

    # Rate limiting logic (simple example, can be enhanced with Redis or database)
    if 'file' not in request.files:
        return jsonify({"error": "No log file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        categorized_results = {
            "CRITICAL": [],
            "ERROR": [],
            "WARNING": [],
            "SECURITY": [],
            "INFO": [],
            "DEBUG": [],
            "OTHER": []
        }
        
        file_lines = file.read().decode('utf-8', errors='ignore').splitlines()
        total_threat_score = 0.0

        for line in file_lines:
            category, score = categorize_and_score_log(line)
            categorized_results[category].append({
                "message": line,
                "threat_score": score,
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            })
            total_threat_score += score

        # Calculate average threat score
        avg_threat = round(total_threat_score / len(file_lines), 2) if file_lines else 0.0

        #   Prepare response data
        response_data = {
            "status": "success",
            "company": company_name,
            "total_logs_processed": len(file_lines),
            "cluster_threat_index": avg_threat,
            "summary": {
                "critical": len(categorized_results["CRITICAL"]),
                "error": len(categorized_results["ERROR"]),
                "warning": len(categorized_results["WARNING"]),
                "security": len(categorized_results["SECURITY"]),
                "info": len(categorized_results["INFO"]),
                "debug": len(categorized_results["DEBUG"]),
                "other": len(categorized_results["OTHER"])
            },
            "detailed_logs": categorized_results
        }

        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({"error": f"Internal processing error: {str(e)}"}), 500

# 4. SocketIO event handlers for real-time log streaming
def register_socket_events(socketio_instance):
    @socketio_instance.on('subscribe_live_logs')
    def handle_live_logs(data):
        company = data.get('company', 'Default-Cluster')
        emit('live_response', {"status": f"Connected to live telemetry stream for {company}"})
        
        # Simulate live log streaming for demonstration purposes
        for i in range(3):
            time.sleep(1)
            emit('new_live_log', {
                "cluster": company,
                "log": f"Live telemetry packet {i+1} received securely.",
                "timestamp": datetime.utcnow().strftime('%H:%M:%S')
            })

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, request, jsonify
from functools import wraps
from intelligen_iog_analyzer import IntelligentLogAnalyzer
from api_keys import ALERT_KEYS

alert_gateway_bp = Blueprint('alert_gateway_bp', __name__)

# Keys come from api_keys.py (override with NEXUS_ALERT_KEYS)
ENTERPRISE_API_KEYS = ALERT_KEYS

def require_enterprise_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in ENTERPRISE_API_KEYS:
            return jsonify({"error": "Unauthorized: Invalid or missing API Key"}), 401
        
        request.developer_email = ENTERPRISE_API_KEYS[api_key]["email"]
        return f(*args, **kwargs)
    return decorated_function

def dispatch_developer_alert(developer_email, log_data):
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")

    if not sender_email or not sender_password or not developer_email:
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = developer_email
        msg['Subject'] = f"🚨 SECURITY ALERT: {log_data['severity']} Detected!"

        body = f"""
        Enterprise Alert System:
        
        A high-priority issue requires your attention.
        
        - Severity: {log_data['severity']}
        - Tag: {log_data['tag']}
        - Threat Score: {log_data['threat_score']}
        - Message: {log_data['message']}
        - Timestamp: {log_data['timestamp']}
        """
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, developer_email, msg.as_string())
    except Exception as e:
        print(f"Alert Dispatch Failed: {str(e)}")

@alert_gateway_bp.route('/api/v3/ingest', methods=['POST'])
@require_enterprise_api_key
def ingest_and_alert():
    data = request.get_json()
    if not data or 'logs' not in data:
        return jsonify({"error": "Invalid payload format."}), 400

    raw_logs = data['logs']
    processed_logs = []

    for line in raw_logs:
        processed = IntelligentLogAnalyzer.parse_log_line(line)
        processed_logs.append(processed)

        # லாகின் செய்த மெயிலுக்கு அலர்ட் அனுப்புதல்
        if processed['severity'] in ['CRITICAL', 'SECURITY']:
            dispatch_developer_alert(request.developer_email, processed)

    ai_summary = IntelligentLogAnalyzer.generate_smart_summary(processed_logs)

    return jsonify({
        "status": "success",
        "developer_notified": request.developer_email,
        "ai_summary": ai_summary,
        "data": processed_logs
    }), 200
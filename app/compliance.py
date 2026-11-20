import csv
import io
from flask import Blueprint, request, make_response, jsonify
from flask_login import login_required

compliance_bp = Blueprint('compliance_bp', __name__)


def generate_csv_report(log_data_list):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Severity', 'Tag', 'Message', 'Threat Score'])

    for log in log_data_list:
        writer.writerow([
            log.get('timestamp'),
            log.get('severity'),
            log.get('tag'),
            log.get('message'),
            log.get('threat_score')
        ])

    return output.getvalue()


@compliance_bp.route('/api/v3/reports/export-csv', methods=['POST'])
@login_required
def export_compliance_csv():
    data = request.get_json(silent=True) or {}
    logs = data.get('logs', [])

    if not logs:
        return jsonify({"error": "No log data provided for export"}), 400

    csv_data = generate_csv_report(logs)

    response = make_response(csv_data)
    response.headers["Content-Disposition"] = "attachment; filename=enterprise_compliance_report.csv"
    response.headers["Content-Type"] = "text/csv"
    return response
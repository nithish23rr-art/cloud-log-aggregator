import re
from datetime import datetime

class IntelligentLogAnalyzer:
    @staticmethod
    def calculate_threat_score(severity, message):
        score = 0.0
        msg_lower = message.lower()

        if severity == 'CRITICAL':
            score = 9.5
        elif severity == 'SECURITY':
            score = 9.0
        elif severity == 'ERROR':
            score = 7.5
        elif severity == 'WARNING':
            score = 4.0
        elif severity == 'INFO':
            score = 1.0
        else:
            score = 0.5

        # AI/Pattern based anomaly detection keywords
        keywords = ['unauthorized', 'breach', 'sql injection', 'overflow', 'fatal', 'crash', 'exploit', 'brute-force']
        if any(kw in msg_lower for kw in keywords):
            score = min(10.0, score + 2.5)

        return round(score, 2)

    @classmethod
    def parse_log_line(cls, line):
        pattern = r'\[(.*?)\]\s*\[(.*?)\]\s*(?:\[(.*?)\])?\s*(.*)'
        match = re.match(pattern, line.strip())

        if match:
            timestamp, severity, tag, message = match.groups()
            severity = severity.upper() if severity else 'INFO'
            tag = tag if tag else 'GENERAL'
            threat_score = cls.calculate_threat_score(severity, message)

            return {
                "timestamp": timestamp,
                "severity": severity,
                "tag": tag,
                "message": message,
                "threat_score": threat_score,
                "parsed_at": datetime.utcnow().isoformat()
            }
        
        return {
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "severity": "INFO",
            "tag": "RAW",
            "message": line.strip(),
            "threat_score": 1.0,
            "parsed_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def generate_smart_summary(logs):
        total = len(logs)
        critical_count = sum(1 for l in logs if l['severity'] in ['CRITICAL', 'SECURITY'])
        error_count = sum(1 for l in logs if l['severity'] == 'ERROR')
        
        return f"AI Summary: Total Parsed: {total} | Critical/Security Risks: {critical_count} | Standard Errors: {error_count}"
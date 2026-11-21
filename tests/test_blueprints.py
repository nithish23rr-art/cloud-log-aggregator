import io, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))
from flask import Flask
from compliance import compliance_bp
from alert_gateway import alert_gateway_bp
from log_hup import log_hub_bp
from intelligen_iog_analyzer import IntelligentLogAnalyzer

HUB = {'X-API-Key': 'nexus_comp_a_key_123'}


class BlueprintTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        for bp in (compliance_bp, alert_gateway_bp, log_hub_bp):
            app.register_blueprint(bp)
        self.c = app.test_client()

    def test_upload_requires_key(self):
        r = self.c.post('/api/v3/hub/ingest')
        self.assertEqual(r.status_code, 401)

    def test_upload_categorises(self):
        data = b"INFO ok\nERROR bad\nFATAL boom\nUNAUTHORIZED x\n\n"
        r = self.c.post('/api/v3/hub/ingest', headers=HUB, content_type='multipart/form-data',
                        data={'file': (io.BytesIO(data), 'a.log')})
        j = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(j['total_logs_analyzed'], 4)          # blank line not counted
        self.assertEqual(j['category_summary']['critical'], 1)
        self.assertEqual(j['category_summary']['security'], 1)

    def test_pull_with_key_only(self):
        r = self.c.post('/api/v3/hub/pull', headers=HUB)
        j = r.get_json()
        self.assertEqual(r.status_code, 200)
        self.assertGreater(j['total_logs_analyzed'], 0)
        self.assertTrue(j['sources'])

    def test_pull_bad_key_and_no_source(self):
        self.assertEqual(self.c.post('/api/v3/hub/pull', headers={'X-API-Key': 'x'}).status_code, 401)
        r = self.c.post('/api/v3/hub/pull', headers={'X-API-Key': 'nexus_comp_b_key_456'})
        self.assertEqual(r.status_code, 404)

    def test_analyzer_regex(self):
        p = IntelligentLogAnalyzer.parse_log_line('[2026-01-01 10:00] [ERROR] [DB] connection lost')
        self.assertEqual((p['severity'], p['tag'], p['message']), ('ERROR', 'DB', 'connection lost'))
        p = IntelligentLogAnalyzer.parse_log_line('[2026-01-01] [CRITICAL] crash')
        self.assertEqual(p['severity'], 'CRITICAL')
        self.assertEqual(IntelligentLogAnalyzer.parse_log_line('plain text')['tag'], 'RAW')

    def test_csv_export(self):
        r = self.c.post('/api/v3/reports/export-csv', json={'logs': [{'timestamp': 't', 'severity': 'INFO',
                        'tag': 'x', 'message': 'm', 'threat_score': 1}]})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Timestamp,Severity', r.data)


if __name__ == '__main__':
    unittest.main()

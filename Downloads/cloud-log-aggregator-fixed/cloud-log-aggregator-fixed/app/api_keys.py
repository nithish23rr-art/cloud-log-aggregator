"""M&K Nexus Cloud - API key registry (NEW FILE).
Keys no longer live inside each blueprint. Defaults below keep the demo working;
in production set the env vars (JSON) so real keys never sit in source code:
  NEXUS_HUB_KEYS, NEXUS_ENTERPRISE_KEYS, NEXUS_ALERT_KEYS

Hub key entry fields (all optional except company):
  company, tier,
  log_dir      -> folder on THIS server that holds the company's .log/.txt files
  source_url   -> company's own HTTPS log endpoint (returns plain text lines or {"logs":[...]})
  source_token -> Bearer token sent to source_url
These are read ONLY from server config, never from the request (no SSRF / path tricks).
"""
import json
import os

_BASE = os.path.abspath(os.path.dirname(__file__))


def _load(env_name, default):
    raw = os.getenv(env_name)
    if raw:
        try:
            return json.loads(raw)
        except ValueError:
            print(f"[api_keys] {env_name} is not valid JSON - using defaults")
    return default


HUB_KEYS = _load("NEXUS_HUB_KEYS", {
    "nexus_comp_a_key_123": {"company": "Company_A", "tier": "Enterprise",
                             "log_dir": os.path.join(_BASE, "company_logs", "Company_A")},
    "nexus_comp_b_key_456": {"company": "Company_B", "tier": "Standard"},
})

ENTERPRISE_KEYS = _load("NEXUS_ENTERPRISE_KEYS", {
    "comp_a_key_12345": {"company": "Company_A", "rate_limit_remaining": 60},
    "comp_b_key_67890": {"company": "Company_B", "rate_limit_remaining": 60},
})

ALERT_KEYS = _load("NEXUS_ALERT_KEYS", {
    "mk_live_sec_99887766": {"email": os.getenv("ALERT_DEFAULT_EMAIL", "your_login_email@enterprise.com"),
                             "role": "ADMIN"},
})

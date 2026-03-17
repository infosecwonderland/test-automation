# Security tests

Pytest-based security checks: XSS, JWT tampering, auth bypass, rate limiting, and **OWASP ZAP** automation.

## OWASP ZAP automation

ZAP runs as a separate process. Tests drive it via the ZAP API (spider + active scan) and assert on reported alerts.

### 1. Start ZAP (Docker)

```bash
docker run -u zap -p 8080:8080 ghcr.io/zaproxy/zaproxy:stable zap.sh -daemon -host 0.0.0.0 -port 8080 -config api.key=changeme
```

### 2. (Optional) Start the app under test

Ensure the app is reachable at `SECURITY_BASE_URL` (default `http://localhost:3000`).

### 3. Run ZAP tests

```bash
cd security-tests/python
pip install -r requirements.txt
pytest test_zap_scan.py -v
```

If ZAP is not running, ZAP tests are skipped.

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ZAP_PROXY` | `http://127.0.0.1:8080` | ZAP API base URL |
| `ZAP_API_KEY` | `changeme` | ZAP API key (match `-config api.key=...`) |
| `SECURITY_BASE_URL` | `http://localhost:3000` | Target URL to scan |
| `ZAP_FAIL_ON` | `High,Critical` | Comma-separated risk levels that fail the build |
| `ZAP_MAX_MEDIUM` | (none) | If set, fail when Medium alert count exceeds this number |

### What the ZAP tests do

- **test_zap_is_accessible** – Checks ZAP API is reachable.
- **test_zap_scan_no_high_or_critical_alerts** – Runs a full scan (spider → passive wait → active scan), then fails if any alert has a risk level in `ZAP_FAIL_ON`.
- **test_zap_scan_alert_summary** – Prints alert counts by risk; optionally fails if Medium count &gt; `ZAP_MAX_MEDIUM`.

Scan time depends on the app size (defaults: spider 5 min, passive wait 2 min, active scan 15 min). Adjust in `zap_utils.run_full_scan` or add env-based tuning if needed.

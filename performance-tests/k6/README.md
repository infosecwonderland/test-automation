## k6 Performance Tests – E-commerce Flow

This folder contains k6 scripts for Part 5 – Performance and Load Testing of the assessment.

### Scenario

- 1000 virtual users (VUs) simulating:
  - login (shared in `setup` to avoid overloading auth)
  - search/get products
  - add product to cart
  - create order
  - payment/charge

### Script

- Main script: `ecommerce_load_test.js`
- Defaults:
  - `BASE_URL = http://localhost:3000`
  - `USER_EMAIL = test@example.com`
  - `USER_PASSWORD = password123`
  - `CARD_NUMBER = 4111111111111111`

You can override these via environment variables when running k6.

### Load Profile

Configured in `options`:

- 1 minute ramp-up from 0 → 1000 VUs
- 3 minutes sustained at 1000 VUs
- 1 minute ramp-down to 0

### Metrics and Thresholds

- **Thresholds**
  - `http_req_duration`: P95 < 2000 ms
  - `http_req_failed`: error rate < 1%
  - custom `errors` rate < 1%

- **Custom metrics**
  - `login_duration` – duration of login call
  - `purchase_flow_duration` – end-to-end flow (products → cart → order → payment)

### How to Run

1. Ensure the SUT is running locally on `http://localhost:3000` (same as API tests).
2. Install k6:
   - Mac (Homebrew): `brew install k6`
   - Or use Docker: `docker run -i grafana/k6 run - < ecommerce_load_test.js`
3. Run the test:

```bash
cd performance-tests/k6

# Basic run with defaults
k6 run ecommerce_load_test.js

# Custom base URL and credentials
BASE_URL=http://localhost:3000 \
USER_EMAIL=test@example.com \
USER_PASSWORD=password123 \
CARD_NUMBER=4111111111111111 \
k6 run ecommerce_load_test.js
```

### Integrating with CI / Reporting

- Use `k6 run --out json=results.json ecommerce_load_test.js` to export raw metrics for CI or dashboards.
- For advanced setups, you can push to Prometheus, InfluxDB, or Grafana Cloud using the standard k6 outputs.


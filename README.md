# Enterprise Test Automation Framework

A comprehensive, production-grade test automation ecosystem for a microservices-based e-commerce platform. Covers UI, API, security, performance, and AI-assisted testing — all integrated into a single GitHub Actions CI/CD pipeline with unified Allure reporting.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [System Under Test (SUT)](#system-under-test-sut)
- [Running Tests Locally](#running-tests-locally)
  - [Prerequisites](#prerequisites)
  - [Start the SUT](#start-the-sut)
  - [UI Tests](#ui-tests-playwright)
  - [Self-Healing UI Tests](#self-healing-ui-tests)
  - [API Tests](#api-tests)
  - [Security Tests](#security-tests)
  - [Performance Tests](#performance-tests)
  - [AI-Assisted Tests](#ai-assisted-tests)
- [CI/CD Pipeline](#cicd-pipeline)
- [Allure Reporting](#allure-reporting)
- [Environment Variables](#environment-variables)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                        │
│                  (GitHub Actions)                        │
│                                                          │
│   ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│   │   SAST   │  │   SCA    │  │     Run All Tests      │ │
│   │ Semgrep  │  │  Trivy   │  │                        │ │
│   └────┬─────┘  └────┬─────┘  │  UI → API → Security  │ │
│        │             │        │  Performance → AI      │ │
│        └──────┬──────┘        └───────────┬───────────┘ │
│               └──────────────┬────────────┘             │
│                        ┌─────▼──────┐                   │
│                        │   Allure   │                    │
│                        │   Report   │                    │
│                        └────────────┘                    │
└─────────────────────────────────────────────────────────┘

SUT: Express.js e-commerce API (port 3000)
  Auth → Products → Cart → Order → Payment → Notifications
  PostgreSQL (in-memory) + Kafka (event bus mock)
```

---

## Tech Stack

| Layer | Tool | Version |
|---|---|---|
| UI Automation | Playwright + TypeScript | ^1.58.2 |
| Self-Healing UI | browser-use + Claude API | Python |
| API Automation | pytest + Python | ^8.3.3 |
| API Automation | Karate DSL | 1.4.0 |
| API Automation | Newman (Postman) | CLI |
| Security Testing | pytest + Python | custom payloads |
| SAST | Semgrep | p/nodejs + p/jwt + custom |
| SCA | Trivy | filesystem scan |
| Performance | k6 | JavaScript |
| AI-Assisted | Python + Claude API | claude-opus-4-6 |
| Reporting | Allure Framework | 2.27.0 |
| CI/CD | GitHub Actions | — |
| SUT | Express.js (Node.js) | ^4.19.2 |

---

## Repository Structure

```
test-automation/
├── .github/workflows/
│   └── test-automation.yml      # CI/CD pipeline definition
│
├── sut/                         # System Under Test (Express.js)
│   ├── index.js                 # API gateway + all services
│   ├── services/                # Auth, Products, Cart, Order, Payment
│   ├── lib/                     # In-memory DB + Kafka bus
│   ├── openapi/gateway.yaml     # OpenAPI 3.0 spec (single source of truth)
│   └── public/                  # Frontend HTML pages
│
├── ui-tests/
│   ├── playwright/              # Playwright + TypeScript E2E tests
│   │   ├── pages/               # Page Object Models (7 pages)
│   │   ├── tests/e2e/           # Test specs (login, register, cart, checkout…)
│   │   ├── fixtures/            # Test data (users.json)
│   │   └── playwright.config.ts
│   └── browseruse-self-healing/ # AI self-healing UI tests
│       ├── agents.py            # Claude-powered healing agent
│       ├── healer.py            # Selector repair logic
│       ├── pages/               # Page objects with fallback selectors
│       └── tests/               # Self-healing test specs
│
├── api-tests/
│   ├── pytest/                  # Python API tests (12 tests, 5 modules)
│   │   ├── client.py            # Reusable HTTP client wrapper
│   │   ├── conftest.py          # Shared fixtures
│   │   └── tests/               # test_auth, products, cart, order, payment
│   ├── karate/                  # Karate DSL (28 tests, contract validation)
│   │   └── src/test/            # Feature files + runners
│   └── newman/                  # Postman collection (17 requests, 32 assertions)
│
├── security-tests/
│   ├── Pytest/                  # 94 security tests
│   │   ├── test_sql_injection.py
│   │   ├── test_xss.py
│   │   ├── test_auth_bypass.py
│   │   ├── test_authz_bypass.py
│   │   ├── test_jwt_tampering.py
│   │   └── test_rate_limit.py
│   ├── semgrep/                 # SAST: custom rules + p/nodejs + p/jwt
│   └── trivy/                   # SCA: CVE filesystem scan
│
├── performance-tests/
│   └── k6/
│       └── ecommerce_load_test.js  # 1000 VU load scenario
│
├── ai-tests/
│   ├── test-generation/
│   │   ├── data_generator.py        # Synthetic test data via Claude
│   │   ├── scenario_generator.py    # Generate pytest tests from OpenAPI spec
│   │   ├── negative_test_generator.py  # Auto-generate negative test cases
│   │   ├── failure_analyzer.py      # AI-driven failure analysis + triage
│   │   ├── conftest.py              # Fixtures for generated tests
│   │   └── generated/              # Runtime output (gitignored)
│   └── reports/                    # failure_analysis.json + allure-results/
│
├── utils/
│   ├── contract_loader.py       # OpenAPI spec parser (shared by all test suites)
│   ├── convert_to_allure.py     # Converts Semgrep/Trivy JSON → Allure format
│   └── gates/
│       ├── semgrep_gate.py      # Fails CI on HIGH/CRITICAL SAST findings
│       └── trivy_gate.py        # Fails CI on CRITICAL/HIGH CVEs
│
└── reports/allure/              # Unified Allure HTML report output
```

---

## System Under Test (SUT)

A mock microservices e-commerce platform served as a single Express.js app on **port 3000**.

### API Endpoints

| Method | Path | Auth Required | Rate Limited |
|---|---|---|---|
| `POST` | `/auth/register` | No | No |
| `POST` | `/auth/login` | No | Yes |
| `GET` | `/auth/me` | Yes | No |
| `GET` | `/products` | No | No |
| `POST` | `/cart/add` | Yes | Yes |
| `GET` | `/cart` | Yes | No |
| `POST` | `/cart/clear` | Yes | No |
| `POST` | `/order/create` | Yes | Yes |
| `GET` | `/order/:orderId` | Yes | No |
| `POST` | `/payment/charge` | Yes | Yes |
| `GET` | `/health` | No | No |

The full OpenAPI 3.0 specification is at [`sut/openapi/gateway.yaml`](sut/openapi/gateway.yaml) and is used as the single source of truth across all test suites via `utils/contract_loader.py`.

---

## Running Tests Locally

### Prerequisites

| Tool | Version |
|---|---|
| Node.js | 20+ |
| Python | 3.11+ |
| Java | 21 |
| Maven | 3.8+ |
| k6 | latest |

Create a `.env` file in the project root (copy from `.env.example` if present):

```
SUT_JWT_SECRET=your-local-secret
SUT_BASE_URL=http://localhost:3000
ANTHROPIC_API_KEY=your-anthropic-api-key   # only for AI tests
```

---

### Start the SUT

```bash
cd sut
npm install
node index.js
# API is now available at http://localhost:3000
# Health check: curl http://localhost:3000/health
```

---

### UI Tests (Playwright)

```bash
cd ui-tests/playwright
npm install
npx playwright install --with-deps
npx playwright test

# With Allure results
npx playwright test --reporter=allure-playwright
```

Full E2E scenarios: register → login → search products → add to cart → checkout → payment → order confirmation.

---

### Self-Healing UI Tests

Requires `ANTHROPIC_API_KEY` set in environment.

```bash
cd ui-tests/browseruse-self-healing
pip install -r requirements.txt
python -m playwright install chromium --with-deps
python -m pytest tests/ -v
```

Uses [browser-use](https://github.com/browser-use/browser-use) with the Claude API to detect broken UI selectors and automatically suggest and apply fixes. When a locator fails, the AI agent inspects the live DOM and recovers using alternative selectors — no manual test maintenance required.

---

### API Tests

**pytest:**
```bash
cd api-tests/pytest
pip install -r requirements.txt
pytest -v
pytest -v --alluredir=allure-results   # with Allure
```

**Karate DSL:**
```bash
cd api-tests/karate
mvn test -B
```

**Newman (Postman):**
```bash
npm install -g newman newman-reporter-allure
newman run api-tests/newman/ecommerce-api.postman_collection.json \
  --environment api-tests/newman/local.postman_environment.json \
  --reporters cli,allure \
  --reporter-allure-export api-tests/newman/allure-results
```

---

### Security Tests

```bash
cd security-tests/Pytest
pip install -r requirements.txt
pytest -v --alluredir=allure-results
```

Covers: SQL injection, XSS, broken authentication, authorization bypass, JWT tampering, rate limiting.

**SAST (Semgrep):**
```bash
pip install semgrep
semgrep scan --config p/nodejs --config p/jwt \
  --config security-tests/semgrep/semgrep.yml \
  --json --output security-tests/semgrep/results.json sut/
python3 utils/convert_to_allure.py --type semgrep \
  security-tests/semgrep/results.json security-tests/semgrep/allure-results
```

**SCA (Trivy):**
```bash
trivy fs --format json --output security-tests/trivy/results.json sut/
python3 utils/convert_to_allure.py --type trivy \
  security-tests/trivy/results.json security-tests/trivy/allure-results
```

---

### Performance Tests

```bash
# Smoke run (1 VU, 1 min)
k6 run --env CI_PROFILE=smoke \
  --summary-export performance-tests/k6/results/summary.json \
  performance-tests/k6/ecommerce_load_test.js

# Full load (1000 VUs, 5 min)
k6 run performance-tests/k6/ecommerce_load_test.js
```

Thresholds: P95 latency < 2000 ms, error rate < 1%.

---

### AI-Assisted Tests

Requires `ANTHROPIC_API_KEY` set in environment.

```bash
cd ai-tests/test-generation
pip install -r requirements.txt

# Step 1: Generate synthetic test data
python data_generator.py

# Step 2: Generate scenario tests from OpenAPI spec
python scenario_generator.py

# Step 3: Generate negative/edge-case tests
python negative_test_generator.py

# Step 4: Run all generated tests + AI failure analysis
python failure_analyzer.py --suite generated --alluredir ../reports/allure-results
```

Generated files appear in `ai-tests/test-generation/generated/` (gitignored).
Failure analysis report is saved to `ai-tests/reports/failure_analysis.json`.

---

## CI/CD Pipeline

Defined in [`.github/workflows/test-automation.yml`](.github/workflows/test-automation.yml).

### Stages

```
┌────────────────────────────────────────────────────────────┐
│  SAST (Semgrep)    SCA (Trivy)          [run in parallel]  │
└──────────┬──────────────┬───────────────────────────────── ┘
           │              │
           └──────┬───────┘
                  │
         ┌────────▼─────────────────────────────────────────┐
         │  Run All Tests                                    │
         │                                                   │
         │  1. Install runtimes (Node 20, Python 3.11, Java) │
         │  2. Start SUT (health-check readiness wait)       │
         │  3. UI Tests (Playwright)         continue-on-err │
         │  4. UI Tests (Self-Healing)       continue-on-err │
         │  5. API Tests (pytest)            continue-on-err │
         │  6. API Tests (Karate)            continue-on-err │
         │  7. API Tests (Newman)            continue-on-err │
         │  8. Security Tests (pytest)       continue-on-err │
         │  9. Performance Tests (k6)        continue-on-err │
         │  10. AI Tests (4-step pipeline)   continue-on-err │
         │  11. Failure Gate (all must pass)                 │
         │  12. Stop SUT                                     │
         └────────────────────────┬─────────────────────────┘
                                  │
                         ┌────────▼────────┐
                         │  Allure Report  │
                         │  (unified HTML) │
                         └─────────────────┘
```

### Failure Gates

| Gate | Condition |
|---|---|
| SAST gate | Fails if Semgrep finds HIGH or CRITICAL severity issues |
| SCA gate | Fails if Trivy finds CRITICAL or HIGH CVEs |
| Test gate | Fails if any test suite has a non-success outcome |

### Artifacts

| Artifact | Contents | Retention |
|---|---|---|
| `allure-report` | Unified Allure HTML report | 30 days |
| `allure-tests` | Raw Allure results from all test suites | — |
| `allure-sast` | Semgrep findings in Allure format | — |
| `allure-sca` | Trivy CVE findings in Allure format | — |
| `k6-results` | k6 summary JSON | 30 days |
| `ai-test-reports` | Generated tests + failure analysis JSON | — |

### Required Secrets

| Secret | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API access for AI-assisted test steps |

---

## Allure Reporting

All test suites write Allure result files during CI. The `report` job aggregates them into a single HTML report.

To view the report locally after downloading the `allure-report` artifact:

```bash
# Install Allure CLI
brew install allure        # macOS
# or download from https://github.com/allure-framework/allure2/releases

# Serve the report
allure open path/to/allure-report/
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SUT_BASE_URL` | `http://localhost:3000` | SUT base URL for all test clients |
| `SUT_JWT_SECRET` | `dev-secret` | JWT signing secret for the SUT |
| `CORS_ORIGIN` | `http://localhost:3000` | Allowed CORS origin |
| `SUT_TEST_EMAIL` | `test@example.com` | Default test user email |
| `SUT_TEST_PASSWORD` | `password123` | Default test user password |
| `ANTHROPIC_API_KEY` | — | Required for AI-assisted tests |

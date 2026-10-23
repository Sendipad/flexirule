# FlexiRule Playwright E2E Testing Infrastructure

This directory contains the Python Playwright End-to-End (E2E) testing suite for FlexiRule.

## Structure

```
e2e/
├── smoke/
│   ├── test_desk.py
│   ├── test_rule_list.py
│   └── test_rule_builder_load.py
├── rule-builder/
│   ├── test_nodes.py
│   ├── test_connections.py
│   ├── test_action_configuration.py
│   ├── test_validation.py
│   ├── test_persistence.py
│   └── test_layout.py
├── conftest.py
└── README.md
```

## Prerequisites

1. Active Frappe v15 + FlexiRule site running (default: `http://127.0.0.1:8000`).
2. Python 3.10+ virtual environment (e.g. `/home/jules/frappe-bench/env`).
3. Installed Python dependencies:
   ```sh
   pip install playwright pytest pytest-playwright pytest-xdist pytest-html requests
   playwright install chromium
   ```

## Environment Variables

- `FRAPPE_SITE_URL`: Base URL of the target site (default: `http://127.0.0.1:8000`).
- `FRAPPE_USER`: Username for testing (default: `Administrator`).
- `FRAPPE_PASSWORD`: Password for authentication (**required**).

## Running Tests

### 1. Run Smoke Tests Only
```sh
FRAPPE_PASSWORD=admin pytest e2e/smoke/ -v
```

### 2. Run All Tests (Serial)
```sh
FRAPPE_PASSWORD=admin pytest e2e/ -v
```

### 3. Run Tests in Parallel (`pytest-xdist`)
```sh
FRAPPE_PASSWORD=admin pytest e2e/ -n 4
```

### 4. Customizing Reports
By default, execution generates JUnit XML and HTML reports into `artifacts/`:
- `artifacts/junit.xml`
- `artifacts/report.html`

To specify custom report output paths:
```sh
FRAPPE_PASSWORD=admin pytest e2e/ --junitxml=custom_artifacts/results.xml --html=custom_artifacts/report.html
```

## Failure Diagnostics

When a test fails, `conftest.py` automatically captures:
- Full page screenshot at `artifacts/failure_diagnostics/<test_name>.png`.
- Console logs and network error HTTP statuses at `artifacts/failure_diagnostics/<test_name>_diagnostics.txt`.

All test state (`.auth/`), reports (`artifacts/`, `htmlreport.html`, `pytest_report.xml`), and diagnostics are excluded from Git repository tracking via `.gitignore`.

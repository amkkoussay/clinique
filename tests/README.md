# Tests

Automated tests for the Clinic Management Platform, built with `pytest`.

## Setup

```bash
pip install -r requirements-test.txt
```

## Running the tests

Run everything:
```bash
pytest
```

Run one file:
```bash
pytest tests/test_auth.py
```

Run one test, with verbose output:
```bash
pytest tests/test_auth.py::TestLogin::test_login_success_redirects_to_dashboard -v
```

Run with a short summary of failures only:
```bash
pytest -q
```

## What's covered

| File | Covers |
|---|---|
| `test_models.py` | `User`, `Patient`, `Appointment` model behavior (passwords, roles, age calculation, uniqueness constraints, relationships) |
| `test_auth.py` | Login, logout, registration (including the `accountant` role) |
| `test_permissions.py` | The `@role_required` decorator across appointments, patients, medical records, and billing |
| `test_patients.py` | Patient list/search, create, view, edit, soft-delete |
| `test_appointments.py` | Appointment list, create (with doctor/patient choices), view, cancel, status updates |
| `test_billing.py` | Invoice listing and creation, invoice number generation |
| `test_seed.py` | The `seed.py` helper functions (3 doctors / 10 patients / 5 appointments) |
| `test_error_pages.py` | 400/403/404/500 error templates render without `TemplateNotFound` |

## Notes

- Tests run against an **in-memory SQLite database** (`TestingConfig` in `config.py`), so they never touch `clinic.db`.
- CSRF protection is disabled in `TestingConfig`, so form posts in tests don't need a CSRF token.
- `conftest.py` provides ready-made users for each role (`admin_user`, `doctor_user`,
  `receptionist_user`, `accountant_user`) and a `login_as(client, user)` helper.

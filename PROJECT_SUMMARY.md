# Clinique — Project Summary

## Overview

Clinique is a portfolio-scale clinic management prototype built with Flask, SQLAlchemy, and vanilla web technologies. It explores patient, appointment, medical-record, billing, and role-based workflows in a small health-information system.

> **Status:** Prototype / educational project. It is not a certified medical device, production healthcare service, or compliance-certified system, and it must not be used with real patient data.

## Architecture

The application is organised around a Flask application, SQLAlchemy models, route blueprints, Jinja templates, and static assets. The structure is intended to demonstrate modular design and explicit workflow boundaries rather than claim production readiness.

### Backend

- `app.py`: Main application entry point and configuration wiring.
- `config.py`: Environment-based configuration.
- `models.py`: Database models and relationships.
- `forms.py`: WTForms definitions and validation.
- `routes/`: Route blueprints for authentication, dashboard, patients, appointments, medical records, billing, chatbot, API, and reports.

### Frontend

- Jinja2 templates with shared base layouts.
- Vanilla JavaScript and CSS variables for interaction and themes.
- Responsive layout foundations for desktop and mobile-sized screens.

### Database

SQLite is used for local development. A real deployment would require a managed database, migration strategy, access controls, backups, monitoring, privacy review, and a formal security assessment.

## Demonstrated workflows

The current codebase explores authentication, role-aware navigation, dashboard summaries, patient records, appointments, medical notes, prescriptions, billing screens, reports, CSV export paths, and an audit-trail concept for local development review. Some screens and integrations are portfolio experiments and should be validated independently before being considered complete.

The health-data model includes ICD-10-oriented fields where represented in the current code. This is not a claim of coding-system certification or clinical validation.

## Security foundations and boundaries

The project includes security-oriented foundations such as CSRF protection, Werkzeug password hashing, input validation, session handling, and basic upload checks. These are implementation features for a prototype, not evidence of compliance with HIPAA, GDPR, or any other regulatory framework.

Before any real-world use, the application would require threat modelling, independent security testing, privacy and data-governance review, clinical safety review, audit-control verification, access-management hardening, secure deployment, and jurisdiction-specific legal analysis.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python seed.py
python app.py
```

The initialization and seed scripts are intended for local demo data only. Development credentials, databases, logs, uploaded files, Python bytecode, and other runtime artifacts are intentionally excluded from version control.

## Repository hygiene

The repository `.gitignore` excludes local databases, database journals, runtime logs, Python bytecode, virtual environments, secrets, generated uploads, exports, and editor caches. This keeps sample data and machine-specific artifacts out of the public repository.

## Technology stack

- **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-WTF.
- **Frontend:** Jinja2, vanilla JavaScript, CSS3, HTML5.
- **Database:** SQLite for local development.
- **Charts and calendar:** Chart.js and FullCalendar.js.
- **Utilities:** ReportLab and QR-code generation.

## License

MIT License — see [LICENSE](./LICENSE).

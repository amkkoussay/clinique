"""
Pytest configuration and shared fixtures for the Clinic Management Platform.
=============================================================================
Run all tests with:  pytest
Run one file with:   pytest tests/test_models.py
Run one test with:   pytest tests/test_auth.py::test_login_success -v
"""

import sys
import os
from datetime import date, time, timedelta

import pytest

# Make sure the project root (parent of tests/) is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db as _db, User, Patient, Appointment


@pytest.fixture()
def app():
    """Create a Flask app configured for testing (in-memory SQLite)."""
    application = create_app('testing')

    with application.app_context():
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    """Expose the SQLAlchemy db handle bound to the test app context."""
    return _db


@pytest.fixture()
def client(app):
    """A Flask test client."""
    return app.test_client()


@pytest.fixture()
def runner(app):
    """A Flask CLI test runner."""
    return app.test_cli_runner()


# ---------------------------------------------------------------------------
# User factory fixtures
# ---------------------------------------------------------------------------

def _make_user(db, email, role, password='Password123!', **extra):
    user = User(
        email=email,
        first_name=extra.pop('first_name', role.title()),
        last_name=extra.pop('last_name', 'Test'),
        role=role,
        **extra
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture()
def admin_user(db):
    return _make_user(db, 'admin@test.com', 'admin')


@pytest.fixture()
def doctor_user(db):
    return _make_user(db, 'doctor@test.com', 'doctor',
                       specialization='General Medicine', license_number='MD1001')


@pytest.fixture()
def receptionist_user(db):
    return _make_user(db, 'reception@test.com', 'receptionist')


@pytest.fixture()
def accountant_user(db):
    return _make_user(db, 'accountant@test.com', 'accountant')


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------

def login(client, email, password='Password123!'):
    """POST to the login route and return the response (follows redirects)."""
    return client.post('/auth/login', data={
        'email': email,
        'password': password,
    }, follow_redirects=True)


@pytest.fixture()
def login_as():
    """Return a helper `login_as(client, user)` usable inside a test."""
    def _login(client, user, password='Password123!'):
        return login(client, user.email, password)
    return _login


# ---------------------------------------------------------------------------
# Domain object factories
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_patient(db):
    patient = Patient(
        patient_id='P20260001',
        first_name='John',
        last_name='Doe',
        date_of_birth=date(1990, 1, 1),
        gender='male',
        phone='555-1000',
        email='john.doe@example.com',
    )
    db.session.add(patient)
    db.session.commit()
    return patient


@pytest.fixture()
def sample_appointment(db, sample_patient, doctor_user):
    appointment = Appointment(
        patient_id=sample_patient.id,
        doctor_id=doctor_user.id,
        appointment_date=date.today() + timedelta(days=1),
        start_time=time(9, 0),
        end_time=time(9, 30),
        appointment_type='consultation',
        status='scheduled',
        reason='Routine checkup',
    )
    db.session.add(appointment)
    db.session.commit()
    return appointment

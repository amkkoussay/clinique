"""
Tests for the seed.py quick-seed helper functions.

These call the individual seed_* functions directly against the
pytest in-memory test database, rather than running seed.py's main()
(which targets a real on-disk SQLite file via create_app('development')).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import seed as seed_module
from models import User, Patient, Appointment


class TestSeedFunctions:

    def test_seed_admin_creates_one_admin(self, app, db):
        with app.app_context():
            admin = seed_module.seed_admin()
            assert admin.role == 'admin'
            assert User.query.filter_by(role='admin').count() == 1

    def test_seed_admin_is_idempotent(self, app, db):
        with app.app_context():
            seed_module.seed_admin()
            seed_module.seed_admin()
            assert User.query.filter_by(role='admin').count() == 1

    def test_seed_doctors_creates_three_doctors(self, app, db):
        with app.app_context():
            doctors = seed_module.seed_doctors()
            assert len(doctors) == 3
            assert User.query.filter_by(role='doctor').count() == 3

    def test_seed_patients_creates_requested_count(self, app, db):
        with app.app_context():
            patients = seed_module.seed_patients(10)
            assert len(patients) == 10
            assert Patient.query.count() == 10

    def test_seed_appointments_creates_requested_count(self, app, db):
        with app.app_context():
            doctors = seed_module.seed_doctors()
            patients = seed_module.seed_patients(10)
            appointments = seed_module.seed_appointments(doctors, patients, 5)
            assert len(appointments) == 5
            assert Appointment.query.count() == 5

    def test_full_seed_matches_expected_counts(self, app, db):
        """End-to-end: 3 doctors, 10 patients, 5 appointments, as documented."""
        with app.app_context():
            seed_module.seed_admin()
            doctors = seed_module.seed_doctors()
            patients = seed_module.seed_patients(10)
            seed_module.seed_appointments(doctors, patients, 5)

            assert User.query.filter_by(role='admin').count() == 1
            assert User.query.filter_by(role='doctor').count() == 3
            assert Patient.query.count() == 10
            assert Appointment.query.count() == 5

"""
Tests for core model behavior: User, Patient, Appointment.
"""

from datetime import date

from models import User, Patient


class TestUserModel:

    def test_set_password_hashes_value(self, db):
        user = User(email='a@test.com', first_name='A', last_name='B', role='doctor')
        user.set_password('mysecret')
        assert user.password_hash != 'mysecret'

    def test_check_password_correct(self, db):
        user = User(email='a@test.com', first_name='A', last_name='B', role='doctor')
        user.set_password('mysecret')
        assert user.check_password('mysecret') is True

    def test_check_password_incorrect(self, db):
        user = User(email='a@test.com', first_name='A', last_name='B', role='doctor')
        user.set_password('mysecret')
        assert user.check_password('wrongpass') is False

    def test_get_full_name(self, db):
        user = User(email='a@test.com', first_name='Jane', last_name='Smith', role='doctor')
        assert user.get_full_name() == 'Jane Smith'

    def test_role_helper_methods(self, admin_user, doctor_user, receptionist_user, accountant_user):
        assert admin_user.is_admin() is True
        assert admin_user.is_doctor() is False

        assert doctor_user.is_doctor() is True
        assert doctor_user.is_admin() is False

        assert receptionist_user.is_receptionist() is True
        assert accountant_user.is_accountant() is True

    def test_email_must_be_unique(self, db, admin_user):
        duplicate = User(
            email=admin_user.email,
            first_name='Dup',
            last_name='User',
            role='doctor',
        )
        duplicate.set_password('whatever123')
        db.session.add(duplicate)

        with __import__('pytest').raises(Exception):
            db.session.commit()


class TestPatientModel:

    def test_get_full_name(self, sample_patient):
        assert sample_patient.get_full_name() == 'John Doe'

    def test_get_age_computes_from_dob(self, db):
        patient = Patient(
            patient_id='P20260099',
            first_name='Old',
            last_name='Timer',
            date_of_birth=date(1950, 6, 15),
            gender='male',
            phone='555-9999',
        )
        db.session.add(patient)
        db.session.commit()

        age = patient.get_age()
        expected_min_age = date.today().year - 1950 - 1
        expected_max_age = date.today().year - 1950
        assert expected_min_age <= age <= expected_max_age

    def test_allergies_list_defaults_to_empty(self, sample_patient):
        assert sample_patient.get_allergies_list() == []

    def test_allergies_list_round_trips_json(self, db, sample_patient):
        import json
        sample_patient.allergies = json.dumps(['Penicillin', 'Peanuts'])
        db.session.commit()
        assert sample_patient.get_allergies_list() == ['Penicillin', 'Peanuts']

    def test_patient_id_must_be_unique(self, db, sample_patient):
        duplicate = Patient(
            patient_id=sample_patient.patient_id,
            first_name='Other',
            last_name='Person',
            date_of_birth=date(1985, 3, 3),
            gender='female',
            phone='555-2000',
        )
        db.session.add(duplicate)

        with __import__('pytest').raises(Exception):
            db.session.commit()


class TestAppointmentModel:

    def test_appointment_links_patient_and_doctor(self, sample_appointment, sample_patient, doctor_user):
        assert sample_appointment.patient_id == sample_patient.id
        assert sample_appointment.doctor_id == doctor_user.id

    def test_appointment_default_status(self, db, sample_patient, doctor_user):
        from datetime import time, timedelta
        from models import Appointment

        appointment = Appointment(
            patient_id=sample_patient.id,
            doctor_id=doctor_user.id,
            appointment_date=date.today() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(10, 30),
        )
        db.session.add(appointment)
        db.session.commit()

        assert appointment.status == 'scheduled'

    def test_appointment_backref_on_patient(self, sample_appointment, sample_patient):
        assert sample_appointment in list(sample_patient.appointments)

    def test_appointment_backref_on_doctor(self, sample_appointment, doctor_user):
        assert sample_appointment in list(doctor_user.doctor_appointments)

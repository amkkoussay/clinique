#!/usr/bin/env python3
"""
Clinic Management Platform - Quick Seed Script
================================================
Populates the database with a small, ready-to-use demo dataset:
3 doctors, 10 patients, and 5 appointments.

Run with:
    python seed.py
"""

import os
import sys
from datetime import date, time, timedelta
from random import choice, randint

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Patient, Appointment


_DEMO_DEFAULT_USED = set()


def _seed_password(env_var, default):
    """Seed password from the environment, or a clearly DEMO-ONLY default.

    Seeded accounts are demo-only: they must be changed or removed before
    any real deployment, and must never guard real patient data.
    Environment values are never printed; a default is printed, labelled
    DEMO-ONLY, only when it is actually the password in use.
    """
    value = os.environ.get(env_var)
    if value:
        return value
    _DEMO_DEFAULT_USED.add(env_var)
    print(f"  NOTE: {env_var} is not set — using a DEMO-ONLY default password.")
    return default


def seed_admin():
    """Create the default admin user if it doesn't exist."""
    admin = User.query.filter_by(email='admin@clinic.com').first()

    if not admin:
        admin = User(
            email='admin@clinic.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True
        )
        admin.set_password(_seed_password('CLINIQUE_SEED_ADMIN_PASSWORD', 'admin123'))
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created: admin@clinic.com (DEMO-ONLY password)")
    else:
        print("✓ Admin user already exists")

    return admin


def seed_doctors():
    """Create 3 sample doctor users."""
    doctors_data = [
        {
            'email': 'dr.smith@clinic.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'specialization': 'General Medicine',
            'license_number': 'MD10001'
        },
        {
            'email': 'dr.johnson@clinic.com',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'specialization': 'Cardiology',
            'license_number': 'MD10002'
        },
        {
            'email': 'dr.ahmed@clinic.com',
            'first_name': 'Yousef',
            'last_name': 'Ahmed',
            'specialization': 'Pediatrics',
            'license_number': 'MD10003'
        }
    ]

    doctors = []
    for data in doctors_data:
        doctor = User.query.filter_by(email=data['email']).first()

        if not doctor:
            doctor = User(
                email=data['email'],
                first_name=data['first_name'],
                last_name=data['last_name'],
                role='doctor',
                specialization=data['specialization'],
                license_number=data['license_number'],
                is_active=True
            )
            doctor.set_password(_seed_password('CLINIQUE_SEED_DOCTOR_PASSWORD', 'doctor123'))
            db.session.add(doctor)
            db.session.commit()
            print(f"✓ Doctor created: {data['email']}")
        else:
            print(f"✓ Doctor already exists: {data['email']}")

        doctors.append(doctor)

    return doctors


def seed_patients(count=10):
    """Create sample patients."""
    first_names = ['James', 'Mary', 'Robert', 'Patricia', 'John',
                   'Jennifer', 'Michael', 'Linda', 'David', 'Elizabeth']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones',
                  'Garcia', 'Miller', 'Davis', 'Wilson', 'Moore']
    genders = ['male', 'female']
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']

    patients = []
    for i in range(count):
        first_name = first_names[i % len(first_names)]
        last_name = last_names[i % len(last_names)]
        gender = choice(genders)

        years_ago = randint(18, 75)
        dob = date.today().replace(year=date.today().year - years_ago, day=1)

        patient_id = f"P{date.today().year}{i + 1:04d}"

        patient = Patient.query.filter_by(patient_id=patient_id).first()

        if not patient:
            patient = Patient(
                patient_id=patient_id,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                gender=gender,
                blood_type=choice(blood_types),
                phone=f"555-{randint(1000, 9999)}",
                email=f"{first_name.lower()}.{last_name.lower()}{i}@email.com",
                address=f"{randint(100, 999)} {choice(['Main', 'Oak', 'Pine'])} Street",
                is_active=True
            )
            db.session.add(patient)
            db.session.commit()
            print(f"✓ Patient created: {patient.get_full_name()} ({patient_id})")
        else:
            print(f"✓ Patient already exists: {patient_id}")

        patients.append(patient)

    return patients


def seed_appointments(doctors, patients, count=5):
    """Create sample appointments."""
    appointment_types = ['consultation', 'follow_up', 'routine_checkup']
    statuses = ['scheduled', 'confirmed']

    today = date.today()
    appointments = []

    for i in range(count):
        doctor = doctors[i % len(doctors)]
        patient = patients[i % len(patients)]

        apt_date = today + timedelta(days=i + 1)
        hour = 9 + i
        start_time = time(hour, 0)
        end_time = time(hour + 1, 0)

        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=apt_date,
            start_time=start_time,
            end_time=end_time,
            appointment_type=choice(appointment_types),
            status=choice(statuses),
            reason='Regular checkup'
        )
        db.session.add(appointment)
        appointments.append(appointment)

    db.session.commit()
    print(f"✓ Created {len(appointments)} sample appointments")
    return appointments


def main():
    """Run the quick seed."""
    print("=" * 50)
    print("Clinic Management Platform - Quick Seed")
    print("=" * 50)
    print()

    app = create_app('development')

    with app.app_context():
        db.create_all()

        admin = seed_admin()
        doctors = seed_doctors()
        patients = seed_patients(10)
        seed_appointments(doctors, patients, 5)

        print()
        print("=" * 50)
        print("Seed complete!")
        print("=" * 50)
        print()
        print("Login credentials (DEMO-ONLY):")
        print("  Admin:  admin@clinic.com")
        print("  Doctor: dr.smith@clinic.com")
        if 'CLINIQUE_SEED_ADMIN_PASSWORD' in _DEMO_DEFAULT_USED:
            print("  Admin password: DEMO-ONLY default 'admin123'")
        else:
            print("  Admin password: from CLINIQUE_SEED_ADMIN_PASSWORD (not printed)")
        if 'CLINIQUE_SEED_DOCTOR_PASSWORD' in _DEMO_DEFAULT_USED:
            print("  Doctor password: DEMO-ONLY default 'doctor123'")
        else:
            print("  Doctor password: from CLINIQUE_SEED_DOCTOR_PASSWORD (not printed)")
        print("  WARNING: seeded accounts are demo-only — change or remove")
        print("  them before any real deployment.")
        print()
        print("Run the app with: python app.py")


if __name__ == '__main__':
    main()

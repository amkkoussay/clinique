#!/usr/bin/env python3
"""
Clinic Management Platform - Database Initialization
====================================================
Script to initialize the database with sample data.
Run this script to set up the database for the first time.
"""

import os
import sys
from datetime import datetime, date, timedelta
from random import randint, choice

# Add the application directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Patient, Appointment, Service, Medicine
from config import Config


def create_admin_user():
    """Create the default admin user."""
    admin = User.query.filter_by(email='admin@clinic.com').first()
    
    if not admin:
        admin = User(
            email='admin@clinic.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created: admin@clinic.com / admin123")
    else:
        print("✓ Admin user already exists")
    
    return admin


def create_sample_doctors():
    """Create sample doctor users."""
    doctors_data = [
        {
            'email': 'dr.smith@clinic.com',
            'first_name': 'John',
            'last_name': 'Smith',
            'specialization': 'General Medicine',
            'license_number': 'MD12345'
        },
        {
            'email': 'dr.johnson@clinic.com',
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'specialization': 'Cardiology',
            'license_number': 'MD12346'
        },
        {
            'email': 'dr.williams@clinic.com',
            'first_name': 'Michael',
            'last_name': 'Williams',
            'specialization': 'Pediatrics',
            'license_number': 'MD12347'
        }
    ]
    
    doctors = []
    for doc_data in doctors_data:
        doctor = User.query.filter_by(email=doc_data['email']).first()
        
        if not doctor:
            doctor = User(
                email=doc_data['email'],
                first_name=doc_data['first_name'],
                last_name=doc_data['last_name'],
                role='doctor',
                specialization=doc_data['specialization'],
                license_number=doc_data['license_number'],
                is_active=True
            )
            doctor.set_password('doctor123')
            db.session.add(doctor)
            db.session.commit()
            print(f"✓ Doctor created: {doc_data['email']}")
        else:
            print(f"✓ Doctor already exists: {doc_data['email']}")
        
        doctors.append(doctor)
    
    return doctors


def create_sample_patients(count=20):
    """Create sample patients."""
    first_names = ['James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 
                   'Michael', 'Linda', 'David', 'Elizabeth', 'William', 'Barbara',
                   'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah',
                   'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa']
    
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                  'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez',
                  'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore',
                  'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White']
    
    genders = ['male', 'female']
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-', None]
    
    patients = []
    for i in range(count):
        first_name = choice(first_names)
        last_name = choice(last_names)
        gender = choice(genders)
        
        # Generate random date of birth (between 18 and 80 years ago)
        years_ago = randint(18, 80)
        dob = date.today().replace(year=date.today().year - years_ago)
        dob = dob.replace(day=randint(1, 28))
        
        patient_id = f"P{datetime.now().year}{i+1:04d}"
        
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
                email=f"{first_name.lower()}.{last_name.lower()}@email.com",
                address=f"{randint(100, 9999)} {choice(['Main', 'Oak', 'Pine', 'Maple'])} Street",
                is_active=True
            )
            db.session.add(patient)
            db.session.commit()
            patients.append(patient)
    
    print(f"✓ Created {len(patients)} sample patients")
    return patients


def create_sample_services():
    """Create sample medical services."""
    services_data = [
        {'code': 'CONS001', 'name': 'General Consultation', 'category': 'consultation', 'price': 100.00},
        {'code': 'FOLLOW001', 'name': 'Follow-up Visit', 'category': 'consultation', 'price': 75.00},
        {'code': 'EMERG001', 'name': 'Emergency Consultation', 'category': 'consultation', 'price': 200.00},
        {'code': 'BLOOD001', 'name': 'Complete Blood Count (CBC)', 'category': 'laboratory', 'price': 50.00},
        {'code': 'BLOOD002', 'name': 'Blood Glucose Test', 'category': 'laboratory', 'price': 30.00},
        {'code': 'XRAY001', 'name': 'Chest X-Ray', 'category': 'imaging', 'price': 150.00},
        {'code': 'XRAY002', 'name': 'Bone X-Ray', 'category': 'imaging', 'price': 120.00},
        {'code': 'VACC001', 'name': 'Flu Vaccination', 'category': 'vaccination', 'price': 40.00},
        {'code': 'VACC002', 'name': 'COVID-19 Vaccination', 'category': 'vaccination', 'price': 0.00},
        {'code': 'PROC001', 'name': 'Wound Dressing', 'category': 'procedure', 'price': 60.00},
        {'code': 'PROC002', 'name': 'Stitch Removal', 'category': 'procedure', 'price': 45.00},
        {'code': 'ECG001', 'name': 'ECG/EKG', 'category': 'procedure', 'price': 80.00}
    ]
    
    services = []
    for svc_data in services_data:
        service = Service.query.filter_by(service_code=svc_data['code']).first()
        
        if not service:
            service = Service(
                service_code=svc_data['code'],
                service_name=svc_data['name'],
                category=svc_data['category'],
                default_price=svc_data['price'],
                is_active=True
            )
            db.session.add(service)
            db.session.commit()
            services.append(service)
    
    print(f"✓ Created {len(services)} sample services")
    return services


def create_sample_medicines():
    """Create sample medicines."""
    medicines_data = [
        {
            'name': 'Amoxicillin',
            'generic_name': 'Amoxicillin',
            'category': 'Antibiotic',
            'dosage_forms': '["capsule", "suspension"]',
            'strengths': '["250mg", "500mg"]',
            'default_dosage': '500mg three times daily'
        },
        {
            'name': 'Ibuprofen',
            'generic_name': 'Ibuprofen',
            'category': 'NSAID',
            'dosage_forms': '["tablet", "capsule", "suspension"]',
            'strengths': '["200mg", "400mg", "600mg"]',
            'default_dosage': '400mg as needed'
        },
        {
            'name': 'Paracetamol',
            'generic_name': 'Acetaminophen',
            'category': 'Analgesic',
            'dosage_forms': '["tablet", "suspension", "suppository"]',
            'strengths': '["500mg", "650mg"]',
            'default_dosage': '500mg every 6 hours'
        },
        {
            'name': 'Lisinopril',
            'generic_name': 'Lisinopril',
            'category': 'Antihypertensive',
            'dosage_forms': '["tablet"]',
            'strengths': '["5mg", "10mg", "20mg"]',
            'default_dosage': '10mg once daily'
        },
        {
            'name': 'Metformin',
            'generic_name': 'Metformin',
            'category': 'Antidiabetic',
            'dosage_forms': '["tablet"]',
            'strengths': '["500mg", "850mg", "1000mg"]',
            'default_dosage': '500mg twice daily'
        },
        {
            'name': 'Omeprazole',
            'generic_name': 'Omeprazole',
            'category': 'PPI',
            'dosage_forms': '["capsule"]',
            'strengths': '["20mg", "40mg"]',
            'default_dosage': '20mg once daily before meals'
        },
        {
            'name': 'Amlodipine',
            'generic_name': 'Amlodipine',
            'category': 'Antihypertensive',
            'dosage_forms': '["tablet"]',
            'strengths': '["5mg", "10mg"]',
            'default_dosage': '5mg once daily'
        },
        {
            'name': 'Atorvastatin',
            'generic_name': 'Atorvastatin',
            'category': 'Statin',
            'dosage_forms': '["tablet"]',
            'strengths': '["10mg", "20mg", "40mg"]',
            'default_dosage': '20mg once daily at bedtime'
        }
    ]
    
    medicines = []
    for med_data in medicines_data:
        medicine = Medicine.query.filter_by(name=med_data['name']).first()
        
        if not medicine:
            medicine = Medicine(
                name=med_data['name'],
                generic_name=med_data['generic_name'],
                category=med_data['category'],
                dosage_forms=med_data['dosage_forms'],
                strengths=med_data['strengths'],
                default_dosage=med_data['default_dosage'],
                is_active=True
            )
            db.session.add(medicine)
            db.session.commit()
            medicines.append(medicine)
    
    print(f"✓ Created {len(medicines)} sample medicines")
    return medicines


def create_sample_appointments(doctors, patients):
    """Create sample appointments."""
    appointment_types = ['consultation', 'follow_up', 'routine_checkup', 'emergency']
    statuses = ['scheduled', 'confirmed', 'completed']
    
    today = date.today()
    appointments = []
    
    for i in range(30):
        doctor = choice(doctors)
        patient = choice(patients)
        
        # Random date within next 30 days
        apt_date = today + timedelta(days=randint(-5, 30))
        
        # Random time between 9 AM and 5 PM
        hour = randint(9, 16)
        minute = choice([0, 30])
        
        from datetime import time
        start_time = time(hour, minute)
        end_time = time(hour + 1, minute)
        
        appointment = Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=apt_date,
            start_time=start_time,
            end_time=end_time,
            appointment_type=choice(appointment_types),
            status=choice(statuses),
            reason=choice(['Regular checkup', 'Follow-up visit', 'New symptoms', 'Prescription refill'])
        )
        db.session.add(appointment)
        appointments.append(appointment)
    
    db.session.commit()
    print(f"✓ Created {len(appointments)} sample appointments")
    return appointments


def main():
    """Main initialization function."""
    print("=" * 60)
    print("Clinic Management Platform - Database Initialization")
    print("=" * 60)
    print()
    
    # Create Flask app
    app = create_app('development')
    
    with app.app_context():
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created")
        print()
        
        # Create sample data
        print("Creating sample data...")
        print("-" * 40)
        
        admin = create_admin_user()
        doctors = create_sample_doctors()
        patients = create_sample_patients(20)
        services = create_sample_services()
        medicines = create_sample_medicines()
        appointments = create_sample_appointments(doctors, patients)
        
        print("-" * 40)
        print()
        print("=" * 60)
        print("Database initialization complete!")
        print("=" * 60)
        print()
        print("Default Login Credentials:")
        print("  Admin:    admin@clinic.com / admin123")
        print("  Doctors:  dr.smith@clinic.com / doctor123")
        print("            dr.johnson@clinic.com / doctor123")
        print("            dr.williams@clinic.com / doctor123")
        print()
        print("You can now start the application with: python app.py")
        print()


if __name__ == '__main__':
    main()

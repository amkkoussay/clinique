"""
Clinic Management Platform - Database Models
============================================
SQLAlchemy models for the clinic management system.
"""

from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for admins, doctors, and staff."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='doctor')  # admin, doctor, patient, receptionist, accountant
    specialization = db.Column(db.String(100))  # For doctors
    license_number = db.Column(db.String(50))  # Medical license
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - explicitly specify foreign_keys to avoid ambiguity
    doctor_appointments = db.relationship(
        'Appointment', 
        foreign_keys='Appointment.doctor_id',
        backref='doctor', 
        lazy='dynamic'
    )
    created_appointments = db.relationship(
        'Appointment',
        foreign_keys='Appointment.created_by',
        backref='creator',
        lazy='dynamic'
    )
    prescriptions = db.relationship(
        'Prescription', 
        foreign_keys='Prescription.doctor_id',
        backref='doctor', 
        lazy='dynamic'
    )
    medical_records = db.relationship(
        'MedicalRecord', 
        foreign_keys='MedicalRecord.doctor_id',
        backref='doctor', 
        lazy='dynamic'
    )
    audit_logs = db.relationship(
        'AuditLog', 
        foreign_keys='AuditLog.user_id',
        backref='user', 
        lazy='dynamic'
    )
    ordered_lab_tests = db.relationship(
        'LabTest',
        foreign_keys='LabTest.ordered_by',
        backref='ordered_by_doctor',
        lazy='dynamic'
    )
    recorded_vital_signs = db.relationship(
        'VitalSigns',
        foreign_keys='VitalSigns.recorded_by',
        backref='recorded_by_user',
        lazy='dynamic'
    )
    uploaded_documents = db.relationship(
        'PatientDocument',
        foreign_keys='PatientDocument.uploaded_by',
        backref='uploaded_by_user',
        lazy='dynamic'
    )
    created_invoices = db.relationship(
        'Invoice',
        foreign_keys='Invoice.created_by',
        backref='creator',
        lazy='dynamic'
    )
    recorded_payments = db.relationship(
        'Payment',
        foreign_keys='Payment.recorded_by',
        backref='recorded_by_user',
        lazy='dynamic'
    )
    notifications = db.relationship(
        'Notification',
        foreign_keys='Notification.user_id',
        backref='recipient',
        lazy='dynamic'
    )
    assigned_tasks = db.relationship(
        'Task',
        foreign_keys='Task.assigned_to',
        backref='assignee',
        lazy='dynamic'
    )
    created_tasks = db.relationship(
        'Task',
        foreign_keys='Task.assigned_by',
        backref='assigner',
        lazy='dynamic'
    )
    
    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def get_full_name(self):
        """Return full name."""
        return f"{self.first_name} {self.last_name}"
    
    def is_admin(self):
        """Check if user is admin."""
        return self.role == 'admin'
    
    def is_doctor(self):
        """Check if user is doctor."""
        return self.role == 'doctor'
    
    def is_patient(self):
        return self.role == 'patient'

    def is_receptionist(self):
        """Check if user is receptionist."""
        return self.role == 'receptionist'
    
    def is_accountant(self):
        """Check if user is accountant."""
        return self.role == 'accountant'
    
    def __repr__(self):
        return f'<User {self.email}>'


class Patient(db.Model):
    """Patient model with full demographics and medical history."""
    
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    patient_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Personal Information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # male, female, other
    blood_type = db.Column(db.String(5))  # A+, B+, O+, etc.
    marital_status = db.Column(db.String(20))
    occupation = db.Column(db.String(100))
    
    # Contact Information
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Insurance Information
    insurance_provider = db.Column(db.String(100))
    insurance_policy_number = db.Column(db.String(50))
    insurance_group_number = db.Column(db.String(50))
    
    # Medical History (stored as JSON for flexibility)
    allergies = db.Column(db.Text)  # JSON list
    chronic_conditions = db.Column(db.Text)  # JSON list
    current_medications = db.Column(db.Text)  # JSON list
    family_history = db.Column(db.Text)  # JSON object
    surgical_history = db.Column(db.Text)  # JSON list
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy='dynamic')
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy='dynamic')
    prescriptions = db.relationship('Prescription', backref='patient', lazy='dynamic')
    invoices = db.relationship('Invoice', backref='patient', lazy='dynamic')
    vital_signs = db.relationship('VitalSigns', backref='patient', lazy='dynamic')
    documents = db.relationship('PatientDocument', backref='patient', lazy='dynamic')
    
    def get_full_name(self):
        """Return full name."""
        return f"{self.first_name} {self.last_name}"
    
    def get_age(self):
        """Calculate age from date of birth."""
        today = date.today()
        return today.year - self.date_of_birth.year - \
            ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
    
    def get_allergies_list(self):
        """Return allergies as list."""
        if self.allergies:
            return json.loads(self.allergies)
        return []
    
    def get_chronic_conditions_list(self):
        """Return chronic conditions as list."""
        if self.chronic_conditions:
            return json.loads(self.chronic_conditions)
        return []
    
    def to_fhir(self):
        """Return FHIR R4 Patient resource representation."""
        return {
            "resourceType": "Patient",
            "id": str(self.id),
            "identifier": [{"system": "http://clinic.example/patient", "value": self.patient_id}],
            "active": self.is_active,
            "name": [{"use": "official", "family": self.last_name, "given": [self.first_name]}],
            "telecom": [
                {"system": "phone", "value": self.phone},
                {"system": "email", "value": self.email}
            ] if self.phone or self.email else [],
            "gender": self.gender,
            "birthDate": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "address": [{"text": self.address}] if self.address else []
        }

    def __repr__(self):
        return f'<Patient {self.patient_id}: {self.get_full_name()}>'


class Appointment(db.Model):
    """Appointment model for scheduling."""
    
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    # Unique key for active 30-minute AI bookings. Nullable so cancelled bookings can free the slot.
    booking_key = db.Column(db.String(120), unique=True, nullable=True, index=True)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Appointment Details
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, confirmed, in_progress, completed, cancelled, no_show
    appointment_type = db.Column(db.String(50))  # consultation, follow_up, emergency, routine_checkup
    
    # Additional Information
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_pattern = db.Column(db.String(20))  # daily, weekly, monthly
    
    # Reminders
    reminder_sent = db.Column(db.Boolean, default=False)
    reminder_sent_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def get_status_color(self):
        """Return color code for status."""
        colors = {
            'scheduled': 'primary',
            'confirmed': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'cancelled': 'danger',
            'no_show': 'secondary'
        }
        return colors.get(self.status, 'primary')
    
    def to_fhir(self):
        """Return FHIR R4 Appointment resource representation."""
        start_iso = f"{self.appointment_date.isoformat()}T{self.start_time.isoformat()}Z" if self.appointment_date and self.start_time else None
        end_iso = f"{self.appointment_date.isoformat()}T{self.end_time.isoformat()}Z" if self.appointment_date and self.end_time else None
        return {
            "resourceType": "Appointment",
            "id": str(self.id),
            "status": self.status,
            "description": self.reason,
            "comment": self.notes,
            "start": start_iso,
            "end": end_iso,
            "participant": [
                {"actor": {"reference": f"Patient/{self.patient_id}"}},
                {"actor": {"reference": f"Practitioner/{self.doctor_id}"}}
            ]
        }

    def __repr__(self):
        return f'<Appointment {self.uuid}: {self.appointment_date} {self.start_time}>'


class MedicalRecord(db.Model):
    """Medical record model for patient visits."""
    
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'))
    
    # SOAP Notes
    subjective = db.Column(db.Text)  # Patient's symptoms and complaints
    objective = db.Column(db.Text)   # Doctor's observations and examination findings
    assessment = db.Column(db.Text)  # Diagnosis
    plan = db.Column(db.Text)        # Treatment plan
    
    # Diagnosis
    primary_diagnosis = db.Column(db.String(255))
    secondary_diagnosis = db.Column(db.String(255))
    icd10_codes = db.Column(db.Text)  # JSON list of ICD-10 codes
    
    # Visit Details
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lab_tests = db.relationship('LabTest', backref='medical_record', lazy='dynamic')
    
    def get_icd10_list(self):
        """Return ICD-10 codes as list."""
        if self.icd10_codes:
            return json.loads(self.icd10_codes)
        return []
    
    def to_fhir(self):
        """Return FHIR R4 Observation resource representation."""
        return {
            "resourceType": "Observation",
            "id": str(self.id),
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "8302-2", "display": self.primary_diagnosis or "Clinical Observation"}],
                "text": self.primary_diagnosis or "Clinical Observation"
            },
            "subject": {"reference": f"Patient/{self.patient_id}"},
            "effectiveDateTime": self.visit_date.isoformat() + "Z" if self.visit_date else None,
            "valueString": self.plan or self.assessment
        }

    def __repr__(self):
        return f'<MedicalRecord {self.uuid}>'


class Prescription(db.Model):
    """Prescription model for medications."""
    
    __tablename__ = 'prescriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    prescription_number = db.Column(db.String(20), unique=True, nullable=False)
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    
    # Prescription Details
    prescription_date = db.Column(db.Date, default=date.today)
    instructions = db.Column(db.Text)
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('PrescriptionItem', backref='prescription', lazy='dynamic')
    
    def __repr__(self):
        return f'<Prescription {self.prescription_number}>'


class PrescriptionItem(db.Model):
    """Individual medication items in a prescription."""
    
    __tablename__ = 'prescription_items'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescriptions.id'), nullable=False)
    
    # Medication Details
    medication_name = db.Column(db.String(100), nullable=False)
    generic_name = db.Column(db.String(100))
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    route = db.Column(db.String(20))  # oral, iv, im, topical, etc.
    instructions = db.Column(db.Text)
    
    def __repr__(self):
        return f'<PrescriptionItem {self.medication_name}>'


class LabTest(db.Model):
    """Lab test model for ordering and tracking tests."""
    
    __tablename__ = 'lab_tests'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Keys
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'))
    ordered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Test Details
    test_name = db.Column(db.String(100), nullable=False)
    test_category = db.Column(db.String(50))  # blood, urine, imaging, etc.
    test_code = db.Column(db.String(20))
    
    # Status
    status = db.Column(db.String(20), default='ordered')  # ordered, in_progress, completed, cancelled
    
    # Results
    results = db.Column(db.Text)
    result_values = db.Column(db.Text)  # JSON for structured data
    reference_range = db.Column(db.Text)
    abnormal_flags = db.Column(db.String(50))
    
    # Dates
    ordered_date = db.Column(db.DateTime, default=datetime.utcnow)
    collected_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
    
    # Notes
    clinical_notes = db.Column(db.Text)
    result_notes = db.Column(db.Text)
    
    def get_result_values_dict(self):
        """Return result values as dictionary."""
        if self.result_values:
            return json.loads(self.result_values)
        return {}
    
    def __repr__(self):
        return f'<LabTest {self.test_name}>'


class VitalSigns(db.Model):
    """Vital signs tracking model."""
    
    __tablename__ = 'vital_signs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Vital Signs
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Measurements
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    bmi = db.Column(db.Float)
    temperature_celsius = db.Column(db.Float)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)
    oxygen_saturation = db.Column(db.Float)
    blood_glucose = db.Column(db.Float)
    
    # Notes
    notes = db.Column(db.Text)
    
    def calculate_bmi(self):
        """Calculate BMI from height and weight."""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 2)
        return None
    
    def get_blood_pressure(self):
        """Return blood pressure as string."""
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return None
    
    def __repr__(self):
        return f'<VitalSigns {self.patient_id} {self.recorded_at}>'


class PatientDocument(db.Model):
    """Patient documents and files model."""
    
    __tablename__ = 'patient_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign Key
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Document Details
    document_type = db.Column(db.String(50))  # xray, lab_result, prescription_scan, id_card, other
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(50))
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<PatientDocument {self.title}>'


class Invoice(db.Model):
    """Invoice model for billing."""
    
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(20), unique=True, nullable=False)
    
    # Foreign Key
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    
    # Invoice Details
    invoice_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date)
    
    # Amounts
    subtotal = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_due = db.Column(db.Float, default=0.0)
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, paid, partial, overdue, cancelled
    payment_method = db.Column(db.String(20))  # cash, card, insurance, bank_transfer
    
    # Insurance
    insurance_claimed = db.Column(db.Boolean, default=False)
    insurance_amount = db.Column(db.Float, default=0.0)
    
    # Notes
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic')
    payments = db.relationship('Payment', backref='invoice', lazy='dynamic')
    
    def calculate_totals(self):
        """Calculate invoice totals."""
        self.subtotal = sum(item.total_price for item in self.items)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.balance_due = self.total_amount - self.paid_amount
        return self.total_amount
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


class InvoiceItem(db.Model):
    """Individual items in an invoice."""
    
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    # Item Details
    service_name = db.Column(db.String(100), nullable=False)
    service_code = db.Column(db.String(20))
    description = db.Column(db.Text)
    quantity = db.Column(db.Float, default=1.0)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    
    def calculate_total(self):
        """Calculate total price."""
        self.total_price = self.quantity * self.unit_price
        return self.total_price
    
    def __repr__(self):
        return f'<InvoiceItem {self.service_name}>'


class Payment(db.Model):
    """Payment tracking model."""
    
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    
    # Payment Details
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # cash, card, insurance, bank_transfer
    
    # Additional Information
    transaction_id = db.Column(db.String(100))
    reference_number = db.Column(db.String(50))
    notes = db.Column(db.Text)
    
    # Recorded by
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<Payment {self.amount}>'


class Service(db.Model):
    """Medical services catalog for billing."""
    
    __tablename__ = 'services'
    
    id = db.Column(db.Integer, primary_key=True)
    service_code = db.Column(db.String(20), unique=True, nullable=False)
    service_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    default_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Service {self.service_name}>'


class AuditLog(db.Model):
    """Audit log for compliance and tracking."""
    
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # User Information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user_email = db.Column(db.String(120))
    
    # Action Details
    action = db.Column(db.String(50), nullable=False)  # create, update, delete, login, logout, view
    entity_type = db.Column(db.String(50))  # patient, appointment, prescription, etc.
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    
    # Request Information
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}>'


class ChatbotConversation(db.Model):
    """Chatbot conversation history."""
    
    __tablename__ = 'chatbot_conversations'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Optional: Link to patient if authenticated
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'))
    
    # Message Details
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50))  # symptom_check, appointment_booking, faq, etc.
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChatbotConversation {self.session_id}>'


class Medicine(db.Model):
    """Medicine database for prescriptions."""
    
    __tablename__ = 'medicines'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    generic_name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    dosage_forms = db.Column(db.Text)  # JSON list: ["tablet", "capsule", "syrup"]
    strengths = db.Column(db.Text)  # JSON list: ["500mg", "1g"]
    default_dosage = db.Column(db.String(50))
    instructions = db.Column(db.Text)
    contraindications = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    
    def get_dosage_forms_list(self):
        """Return dosage forms as list."""
        if self.dosage_forms:
            return json.loads(self.dosage_forms)
        return []
    
    def __repr__(self):
        return f'<Medicine {self.name}>'


class Notification(db.Model):
    """User notifications model."""
    
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Recipient
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notification Details
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(20))  # info, warning, success, error
    
    # Link to entity
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    link = db.Column(db.String(255))
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'


class Task(db.Model):
    """Task/Todo model for staff."""
    
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Assigned to
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Task Details
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, cancelled
    
    # Dates
    due_date = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Related to
    related_to_type = db.Column(db.String(50))  # patient, appointment, etc.
    related_to_id = db.Column(db.Integer)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Task {self.title}>'

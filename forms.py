"""
Clinic Management Platform - Forms
==================================
WTForms for user input validation and rendering.
"""

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField, 
    DateField, TimeField, TextAreaField, FloatField, IntegerField,
    FileField, SubmitField, FieldList, FormField, HiddenField,
    EmailField, TelField, DateTimeField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, Optional, 
    NumberRange, ValidationError, Regexp
)
from datetime import date


class LoginForm(FlaskForm):
    """User login form."""
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, max=128)
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form."""
    first_name = StringField('First Name', validators=[
        DataRequired(),
        Length(max=50)
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(),
        Length(max=50)
    ])
    email = EmailField('Email', validators=[
        DataRequired(),
        Email(),
        Length(max=120)
    ])
    phone = TelField('Phone Number', validators=[
        Optional(),
        Length(max=20)
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        ('patient', 'Patient'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('accountant', 'Accountant')
    ], validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', validators=[Optional()], format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[('', 'Select gender'), ('male', 'Male'), ('female', 'Female'), ('other', 'Other')], validators=[Optional()])
    specialization = StringField('Specialization', validators=[Optional(), Length(max=100)])
    license_number = StringField('License Number', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Register')


class ResetPasswordRequestForm(FlaskForm):
    """Password reset request form."""
    email = EmailField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    """Password reset form."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8)
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    submit = SubmitField('Reset Password')


class PatientForm(FlaskForm):
    """Patient registration/editing form."""
    # Personal Information
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    date_of_birth = DateField('Date of Birth', validators=[DataRequired()], format='%Y-%m-%d')
    gender = SelectField('Gender', choices=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    blood_type = SelectField('Blood Type', choices=[
        ('', 'Select Blood Type'),
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-')
    ], validators=[Optional()])
    marital_status = SelectField('Marital Status', choices=[
        ('', 'Select Status'),
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed')
    ], validators=[Optional()])
    occupation = StringField('Occupation', validators=[Optional(), Length(max=100)])
    
    # Contact Information
    phone = TelField('Phone Number', validators=[DataRequired(), Length(max=20)])
    email = EmailField('Email', validators=[Optional(), Email(), Length(max=120)])
    address = TextAreaField('Address', validators=[Optional()])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional(), Length(max=100)])
    emergency_contact_phone = TelField('Emergency Contact Phone', validators=[Optional(), Length(max=20)])
    
    # Insurance Information
    insurance_provider = StringField('Insurance Provider', validators=[Optional(), Length(max=100)])
    insurance_policy_number = StringField('Policy Number', validators=[Optional(), Length(max=50)])
    insurance_group_number = StringField('Group Number', validators=[Optional(), Length(max=50)])
    
    # Medical History
    allergies = TextAreaField('Allergies (one per line)', validators=[Optional()])
    chronic_conditions = TextAreaField('Chronic Conditions (one per line)', validators=[Optional()])
    current_medications = TextAreaField('Current Medications (one per line)', validators=[Optional()])
    
    submit = SubmitField('Save Patient')


class AppointmentForm(FlaskForm):
    """Appointment scheduling form."""
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    doctor_id = SelectField('Doctor', coerce=int, validators=[DataRequired()])
    appointment_date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    start_time = TimeField('Start Time', validators=[DataRequired()], format='%H:%M')
    end_time = TimeField('End Time', validators=[DataRequired()], format='%H:%M')
    appointment_type = SelectField('Appointment Type', choices=[
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('routine_checkup', 'Routine Checkup'),
        ('vaccination', 'Vaccination'),
        ('procedure', 'Medical Procedure')
    ], validators=[DataRequired()])
    status = SelectField('Status', choices=[
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], default='scheduled')
    reason = TextAreaField('Reason for Visit', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    is_recurring = BooleanField('Recurring Appointment')
    recurring_pattern = SelectField('Recurring Pattern', choices=[
        ('', 'None'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-weekly'),
        ('monthly', 'Monthly')
    ], validators=[Optional()])
    submit = SubmitField('Save Appointment')


class MedicalRecordForm(FlaskForm):
    """Medical record (SOAP notes) form."""
    patient_id = HiddenField('Patient ID', validators=[DataRequired()])
    appointment_id = HiddenField('Appointment ID')
    
    # SOAP Notes
    subjective = TextAreaField('Subjective (Patient\'s symptoms)', validators=[Optional()])
    objective = TextAreaField('Objective (Examination findings)', validators=[Optional()])
    assessment = TextAreaField('Assessment (Diagnosis)', validators=[Optional()])
    plan = TextAreaField('Plan (Treatment)', validators=[Optional()])
    
    # Diagnosis
    primary_diagnosis = StringField('Primary Diagnosis', validators=[Optional(), Length(max=255)])
    secondary_diagnosis = StringField('Secondary Diagnosis', validators=[Optional(), Length(max=255)])
    icd10_codes = StringField('ICD-10 Codes (comma separated)', validators=[Optional()])
    
    # Follow-up
    follow_up_date = DateField('Follow-up Date', validators=[Optional()], format='%Y-%m-%d')
    follow_up_notes = TextAreaField('Follow-up Notes', validators=[Optional()])
    
    submit = SubmitField('Save Medical Record')


class PrescriptionForm(FlaskForm):
    """Prescription form."""
    patient_id = HiddenField('Patient ID', validators=[DataRequired()])
    medical_record_id = HiddenField('Medical Record ID')
    instructions = TextAreaField('General Instructions', validators=[Optional()])
    submit = SubmitField('Save Prescription')


class PrescriptionItemForm(FlaskForm):
    """Individual prescription item form."""
    medication_name = StringField('Medication', validators=[DataRequired(), Length(max=100)])
    generic_name = StringField('Generic Name', validators=[Optional(), Length(max=100)])
    dosage = StringField('Dosage', validators=[DataRequired(), Length(max=50)])
    frequency = SelectField('Frequency', choices=[
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily'),
        ('three_times_daily', 'Three Times Daily'),
        ('four_times_daily', 'Four Times Daily'),
        ('every_4_hours', 'Every 4 Hours'),
        ('every_6_hours', 'Every 6 Hours'),
        ('every_8_hours', 'Every 8 Hours'),
        ('every_12_hours', 'Every 12 Hours'),
        ('as_needed', 'As Needed (PRN)'),
        ('before_meals', 'Before Meals'),
        ('after_meals', 'After Meals'),
        ('at_bedtime', 'At Bedtime')
    ], validators=[DataRequired()])
    duration = StringField('Duration', validators=[DataRequired(), Length(max=50)])
    route = SelectField('Route', choices=[
        ('oral', 'Oral'),
        ('iv', 'IV'),
        ('im', 'IM'),
        ('sc', 'Subcutaneous'),
        ('topical', 'Topical'),
        ('inhalation', 'Inhalation'),
        ('sublingual', 'Sublingual'),
        ('rectal', 'Rectal'),
        ('ophthalmic', 'Ophthalmic'),
        ('otic', 'Otic'),
        ('nasal', 'Nasal')
    ], validators=[Optional()])
    instructions = TextAreaField('Special Instructions', validators=[Optional()])


class VitalSignsForm(FlaskForm):
    """Vital signs recording form."""
    patient_id = HiddenField('Patient ID', validators=[DataRequired()])
    
    height_cm = FloatField('Height (cm)', validators=[Optional(), NumberRange(min=0, max=300)])
    weight_kg = FloatField('Weight (kg)', validators=[Optional(), NumberRange(min=0, max=500)])
    temperature_celsius = FloatField('Temperature (°C)', validators=[Optional(), NumberRange(min=30, max=45)])
    blood_pressure_systolic = IntegerField('Blood Pressure Systolic', validators=[Optional(), NumberRange(min=50, max=250)])
    blood_pressure_diastolic = IntegerField('Blood Pressure Diastolic', validators=[Optional(), NumberRange(min=30, max=150)])
    heart_rate = IntegerField('Heart Rate (bpm)', validators=[Optional(), NumberRange(min=30, max=200)])
    respiratory_rate = IntegerField('Respiratory Rate (/min)', validators=[Optional(), NumberRange(min=8, max=40)])
    oxygen_saturation = FloatField('Oxygen Saturation (%)', validators=[Optional(), NumberRange(min=50, max=100)])
    blood_glucose = FloatField('Blood Glucose (mg/dL)', validators=[Optional(), NumberRange(min=20, max=600)])
    notes = TextAreaField('Notes', validators=[Optional()])
    
    submit = SubmitField('Save Vital Signs')


class LabTestForm(FlaskForm):
    """Lab test ordering form."""
    patient_id = HiddenField('Patient ID', validators=[DataRequired()])
    medical_record_id = HiddenField('Medical Record ID')
    
    test_name = StringField('Test Name', validators=[DataRequired(), Length(max=100)])
    test_category = SelectField('Category', choices=[
        ('blood', 'Blood Test'),
        ('urine', 'Urine Test'),
        ('imaging', 'Imaging'),
        ('microbiology', 'Microbiology'),
        ('pathology', 'Pathology'),
        ('cardiology', 'Cardiology'),
        ('other', 'Other')
    ], validators=[Optional()])
    test_code = StringField('Test Code', validators=[Optional(), Length(max=20)])
    clinical_notes = TextAreaField('Clinical Notes', validators=[Optional()])
    
    submit = SubmitField('Order Test')


class LabTestResultForm(FlaskForm):
    """Lab test results entry form."""
    results = TextAreaField('Results Summary', validators=[Optional()])
    result_values = TextAreaField('Result Values (JSON format)', validators=[Optional()])
    reference_range = TextAreaField('Reference Range', validators=[Optional()])
    abnormal_flags = StringField('Abnormal Flags', validators=[Optional(), Length(max=50)])
    result_notes = TextAreaField('Notes', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('ordered', 'Ordered'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='completed')
    
    submit = SubmitField('Save Results')


class InvoiceForm(FlaskForm):
    """Invoice creation form."""
    patient_id = SelectField('Patient', coerce=int, validators=[DataRequired()])
    invoice_date = DateField('Invoice Date', validators=[DataRequired()], format='%Y-%m-%d')
    due_date = DateField('Due Date', validators=[Optional()], format='%Y-%m-%d')
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Create Invoice')


class InvoiceItemForm(FlaskForm):
    """Invoice item form."""
    service_name = StringField('Service', validators=[DataRequired(), Length(max=100)])
    service_code = StringField('Service Code', validators=[Optional(), Length(max=20)])
    description = TextAreaField('Description', validators=[Optional()])
    quantity = FloatField('Quantity', validators=[DataRequired(), NumberRange(min=0.01)], default=1.0)
    unit_price = FloatField('Unit Price', validators=[DataRequired(), NumberRange(min=0)])


class PaymentForm(FlaskForm):
    """Payment recording form."""
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('insurance', 'Insurance'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check')
    ], validators=[DataRequired()])
    transaction_id = StringField('Transaction ID', validators=[Optional(), Length(max=100)])
    reference_number = StringField('Reference Number', validators=[Optional(), Length(max=50)])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Record Payment')


class ServiceForm(FlaskForm):
    """Service catalog form."""
    service_code = StringField('Service Code', validators=[DataRequired(), Length(max=20)])
    service_name = StringField('Service Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    category = SelectField('Category', choices=[
        ('consultation', 'Consultation'),
        ('procedure', 'Procedure'),
        ('laboratory', 'Laboratory'),
        ('imaging', 'Imaging'),
        ('vaccination', 'Vaccination'),
        ('medication', 'Medication'),
        ('other', 'Other')
    ], validators=[Optional()])
    default_price = FloatField('Default Price', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Save Service')


class DocumentUploadForm(FlaskForm):
    """Patient document upload form."""
    document_type = SelectField('Document Type', choices=[
        ('xray', 'X-Ray'),
        ('lab_result', 'Lab Result'),
        ('prescription_scan', 'Prescription Scan'),
        ('id_card', 'ID Card'),
        ('insurance_card', 'Insurance Card'),
        ('medical_report', 'Medical Report'),
        ('referral_letter', 'Referral Letter'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    file = FileField('Document File', validators=[DataRequired()])
    submit = SubmitField('Upload Document')


class MedicineForm(FlaskForm):
    """Medicine database entry form."""
    name = StringField('Medicine Name', validators=[DataRequired(), Length(max=100)])
    generic_name = StringField('Generic Name', validators=[Optional(), Length(max=100)])
    category = StringField('Category', validators=[Optional(), Length(max=50)])
    dosage_forms = TextAreaField('Dosage Forms (one per line)', validators=[Optional()])
    strengths = TextAreaField('Strengths (one per line)', validators=[Optional()])
    default_dosage = StringField('Default Dosage', validators=[Optional(), Length(max=50)])
    instructions = TextAreaField('Instructions', validators=[Optional()])
    contraindications = TextAreaField('Contraindications', validators=[Optional()])
    side_effects = TextAreaField('Side Effects', validators=[Optional()])
    submit = SubmitField('Save Medicine')


class TaskForm(FlaskForm):
    """Task creation form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    due_date = DateTimeField('Due Date', validators=[Optional()], format='%Y-%m-%d %H:%M')
    related_to_type = SelectField('Related To', choices=[
        ('', 'None'),
        ('patient', 'Patient'),
        ('appointment', 'Appointment'),
        ('invoice', 'Invoice')
    ], validators=[Optional()])
    related_to_id = IntegerField('Related ID', validators=[Optional()])
    submit = SubmitField('Save Task')


class SettingsForm(FlaskForm):
    """Clinic settings form."""
    clinic_name = StringField('Clinic Name', validators=[DataRequired(), Length(max=100)])
    clinic_address = TextAreaField('Clinic Address', validators=[Optional()])
    clinic_phone = TelField('Clinic Phone', validators=[Optional(), Length(max=20)])
    clinic_email = EmailField('Clinic Email', validators=[Optional(), Email(), Length(max=120)])
    
    # Mail settings
    mail_server = StringField('Mail Server', validators=[Optional(), Length(max=100)])
    mail_port = IntegerField('Mail Port', validators=[Optional()])
    mail_use_tls = BooleanField('Use TLS')
    mail_username = StringField('Mail Username', validators=[Optional(), Length(max=120)])
    mail_password = PasswordField('Mail Password', validators=[Optional()])
    
    submit = SubmitField('Save Settings')


class SearchForm(FlaskForm):
    """General search form."""
    search_query = StringField('Search', validators=[DataRequired(), Length(max=100)])
    search_type = SelectField('Search In', choices=[
        ('all', 'All'),
        ('patients', 'Patients'),
        ('appointments', 'Appointments'),
        ('prescriptions', 'Prescriptions')
    ], default='all')
    submit = SubmitField('Search')


class DateRangeForm(FlaskForm):
    """Date range filter form."""
    start_date = DateField('Start Date', validators=[Optional()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Filter')

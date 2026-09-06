"""
Clinic Management Platform - Patient Routes
===========================================
Routes for patient management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import json
import io
import os

from models import db, Patient, Appointment, MedicalRecord, Prescription, VitalSigns, PatientDocument, AuditLog
from forms import PatientForm, VitalSignsForm, DocumentUploadForm
from decorators import role_required

patients_bp = Blueprint('patients', __name__)


def can_access_patient(patient):
    if current_user.is_admin() or current_user.is_receptionist():
        return True

    if current_user.is_doctor():
        return Appointment.query.filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == current_user.id
        ).first() is not None

    return False

def log_action(action, entity_type=None, entity_id=None, description=None):
    """Log user action to audit log."""
    log = AuditLog(
        user_id=current_user.id,
        user_email=current_user.email,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None
    )
    db.session.add(log)
    db.session.commit()


def generate_patient_id():
    """Generate unique patient ID."""
    prefix = 'P'
    year = datetime.now().strftime('%Y')
    last_patient = Patient.query.filter(
        Patient.patient_id.like(f'{prefix}{year}%')
    ).order_by(Patient.id.desc()).first()
    
    if last_patient:
        last_num = int(last_patient.patient_id[-4:])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f'{prefix}{year}{new_num:04d}'


@patients_bp.route('/')
@login_required
def index():
    """Patient list route."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Patient.query
    
    if search:
        query = query.filter(
            db.or_(
                Patient.first_name.ilike(f'%{search}%'),
                Patient.last_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%'),
                Patient.email.ilike(f'%{search}%')
            )
        )
    
    patients = query.order_by(Patient.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('patients/index.html', 
                         patients=patients, 
                         search=search,
                         title='Patients')


@patients_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def create():
    """Create new patient route."""
    form = PatientForm()
    
    if form.validate_on_submit():
        patient = Patient(
            patient_id=generate_patient_id(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            date_of_birth=form.date_of_birth.data,
            gender=form.gender.data,
            blood_type=form.blood_type.data,
            marital_status=form.marital_status.data,
            occupation=form.occupation.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            emergency_contact_name=form.emergency_contact_name.data,
            emergency_contact_phone=form.emergency_contact_phone.data,
            insurance_provider=form.insurance_provider.data,
            insurance_policy_number=form.insurance_policy_number.data,
            insurance_group_number=form.insurance_group_number.data,
            allergies=json.dumps([a.strip() for a in form.allergies.data.split('\n') if a.strip()]) if form.allergies.data else '[]',
            chronic_conditions=json.dumps([c.strip() for c in form.chronic_conditions.data.split('\n') if c.strip()]) if form.chronic_conditions.data else '[]',
            current_medications=json.dumps([m.strip() for m in form.current_medications.data.split('\n') if m.strip()]) if form.current_medications.data else '[]'
        )
        
        db.session.add(patient)
        db.session.commit()
        
        log_action('create', 'Patient', patient.id, f"Created patient {patient.patient_id}")
        
        flash(f'Patient {patient.get_full_name()} created successfully.', 'success')
        return redirect(url_for('patients.view', patient_id=patient.id))
    
    return render_template('patients/create.html', form=form, title='New Patient')


@patients_bp.route('/<int:patient_id>')
@login_required
def view(patient_id):
    """View patient details route."""
    patient = Patient.query.get_or_404(patient_id)
    if not can_access_patient(patient):
        flash('You do not have permission to view this patient.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Get related data
    recent_appointments = Appointment.query.filter_by(
        patient_id=patient_id
    ).order_by(Appointment.appointment_date.desc()).limit(5).all()
    
    recent_records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicalRecord.visit_date.desc()).limit(5).all()
    
    recent_prescriptions = Prescription.query.filter_by(
        patient_id=patient_id
    ).order_by(Prescription.prescription_date.desc()).limit(5).all()
    
    vital_signs = VitalSigns.query.filter_by(
        patient_id=patient_id
    ).order_by(VitalSigns.recorded_at.desc()).limit(10).all()
    
    documents = PatientDocument.query.filter_by(
        patient_id=patient_id
    ).order_by(PatientDocument.uploaded_at.desc()).all()
    
    return render_template('patients/view.html',
                         patient=patient,
                         recent_appointments=recent_appointments,
                         recent_records=recent_records,
                         recent_prescriptions=recent_prescriptions,
                         vital_signs=vital_signs,
                         documents=documents,
                         title=patient.get_full_name())


@patients_bp.route('/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def edit(patient_id):
    """Edit patient route."""
    patient = Patient.query.get_or_404(patient_id)
    form = PatientForm(obj=patient)
    
    # Convert JSON fields to text for form
    if request.method == 'GET':
        form.allergies.data = '\n'.join(patient.get_allergies_list())
        form.chronic_conditions.data = '\n'.join(patient.get_chronic_conditions_list())
        form.current_medications.data = '\n'.join(
            json.loads(patient.current_medications) if patient.current_medications else []
        )
    
    if form.validate_on_submit():
        patient.first_name = form.first_name.data
        patient.last_name = form.last_name.data
        patient.date_of_birth = form.date_of_birth.data
        patient.gender = form.gender.data
        patient.blood_type = form.blood_type.data
        patient.marital_status = form.marital_status.data
        patient.occupation = form.occupation.data
        patient.phone = form.phone.data
        patient.email = form.email.data
        patient.address = form.address.data
        patient.emergency_contact_name = form.emergency_contact_name.data
        patient.emergency_contact_phone = form.emergency_contact_phone.data
        patient.insurance_provider = form.insurance_provider.data
        patient.insurance_policy_number = form.insurance_policy_number.data
        patient.insurance_group_number = form.insurance_group_number.data
        patient.allergies = json.dumps([a.strip() for a in form.allergies.data.split('\n') if a.strip()]) if form.allergies.data else '[]'
        patient.chronic_conditions = json.dumps([c.strip() for c in form.chronic_conditions.data.split('\n') if c.strip()]) if form.chronic_conditions.data else '[]'
        patient.current_medications = json.dumps([m.strip() for m in form.current_medications.data.split('\n') if m.strip()]) if form.current_medications.data else '[]'
        patient.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_action('update', 'Patient', patient.id, f"Updated patient {patient.patient_id}")
        
        flash('Patient updated successfully.', 'success')
        return redirect(url_for('patients.view', patient_id=patient.id))
    
    return render_template('patients/edit.html', form=form, patient=patient, title='Edit Patient')


@patients_bp.route('/<int:patient_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'receptionist')
def delete(patient_id):
    """Delete patient route (soft delete)."""
    patient = Patient.query.get_or_404(patient_id)
    
    patient.is_active = False
    patient.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_action('delete', 'Patient', patient.id, f"Deactivated patient {patient.patient_id}")
    
    flash('Patient deactivated successfully.', 'success')
    return redirect(url_for('patients.index'))


@patients_bp.route('/<int:patient_id>/vital-signs', methods=['GET', 'POST'])
@login_required
def add_vital_signs(patient_id):
    """Add vital signs route."""
    patient = Patient.query.get_or_404(patient_id)
    if not (current_user.is_admin() or current_user.is_doctor()):
        flash('You do not have permission to manage vital signs.', 'error')
        return redirect(url_for('patients.view', patient_id=patient_id))
    form = VitalSignsForm()
    
    if form.validate_on_submit():
        vital_signs = VitalSigns(
            patient_id=patient_id,
            recorded_by=current_user.id,
            height_cm=form.height_cm.data,
            weight_kg=form.weight_kg.data,
            temperature_celsius=form.temperature_celsius.data,
            blood_pressure_systolic=form.blood_pressure_systolic.data,
            blood_pressure_diastolic=form.blood_pressure_diastolic.data,
            heart_rate=form.heart_rate.data,
            respiratory_rate=form.respiratory_rate.data,
            oxygen_saturation=form.oxygen_saturation.data,
            blood_glucose=form.blood_glucose.data,
            notes=form.notes.data
        )
        
        # Calculate BMI
        vital_signs.bmi = vital_signs.calculate_bmi()
        
        db.session.add(vital_signs)
        db.session.commit()
        
        log_action('create', 'VitalSigns', vital_signs.id, f"Added vital signs for patient {patient.patient_id}")
        
        flash('Vital signs recorded successfully.', 'success')
        return redirect(url_for('patients.view', patient_id=patient_id))
    
    return render_template('patients/vital_signs.html', 
                         form=form, 
                         patient=patient, 
                         title='Record Vital Signs')


@patients_bp.route('/<int:patient_id>/documents', methods=['GET', 'POST'])
@login_required
def upload_document(patient_id):
    """Upload patient document route."""
    from flask import current_app
    import uuid
    
    patient = Patient.query.get_or_404(patient_id)
    if not (current_user.is_admin() or current_user.is_doctor()):
        flash('You do not have permission to manage patient documents.', 'error')
        return redirect(url_for('patients.view', patient_id=patient_id))
    form = DocumentUploadForm()
    
    if form.validate_on_submit():
        file = form.file.data
        if file:
            # Generate unique filename
            original_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{original_ext}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Save file
            file.save(file_path)
            
            # Create document record
            document = PatientDocument(
                patient_id=patient_id,
                uploaded_by=current_user.id,
                document_type=form.document_type.data,
                title=form.title.data,
                description=form.description.data,
                file_path=unique_filename,
                file_size=os.path.getsize(file_path),
                mime_type=file.content_type
            )
            
            db.session.add(document)
            db.session.commit()
            
            log_action('create', 'PatientDocument', document.id, 
                      f"Uploaded document {document.title} for patient {patient.patient_id}")
            
            flash('Document uploaded successfully.', 'success')
            return redirect(url_for('patients.view', patient_id=patient_id))
    
    return render_template('patients/upload_document.html', 
                         form=form, 
                         patient=patient, 
                         title='Upload Document')


@patients_bp.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download patient document route."""
    from flask import current_app
    
    document = PatientDocument.query.get_or_404(document_id)
    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], document.file_path)
    
    if os.path.exists(file_path):
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=document.title)
    else:
        flash('File not found.', 'error')
        return redirect(url_for('patients.view', patient_id=document.patient_id))


@patients_bp.route('/<int:patient_id>/id-card')
@login_required
def generate_id_card(patient_id):
    """Generate patient ID card with QR code."""
    patient = Patient.query.get_or_404(patient_id)
    
    # Termux build intentionally has no Pillow/qrcode dependency.
    # Keep the ID card route available and expose the patient ID as a
    # machine-readable text value instead of generating a QR image.
    return render_template('patients/id_card.html',
                         patient=patient,
                         qr_code=None,
                         title='Patient ID Card')


@patients_bp.route('/api/search')
@login_required
def api_search():
    """API endpoint for patient search."""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    patients = Patient.query.filter(
        db.or_(
            Patient.first_name.ilike(f'%{query}%'),
            Patient.last_name.ilike(f'%{query}%'),
            Patient.patient_id.ilike(f'%{query}%')
        ),
        Patient.is_active == True
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'patient_id': p.patient_id,
        'name': p.get_full_name(),
        'phone': p.phone,
        'age': p.get_age()
    } for p in patients])


@patients_bp.route('/<int:patient_id>/history')
@login_required
def medical_history(patient_id):
    """View complete medical history."""
    patient = Patient.query.get_or_404(patient_id)
    
    # Get all medical records with related data
    records = MedicalRecord.query.filter_by(
        patient_id=patient_id
    ).order_by(MedicalRecord.visit_date.desc()).all()
    
    return render_template('patients/medical_history.html',
                         patient=patient,
                         records=records,
                         title='Medical History')

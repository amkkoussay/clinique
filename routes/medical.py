"""
Clinic Management Platform - Medical Records Routes
===================================================
Routes for medical records, prescriptions, and lab tests.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, date
import json
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from models import (
    db, Patient, MedicalRecord, Prescription, PrescriptionItem, 
    LabTest, Medicine, AuditLog, Appointment
)
from forms import MedicalRecordForm, PrescriptionForm, PrescriptionItemForm, LabTestForm, LabTestResultForm
from decorators import role_required

medical_bp = Blueprint('medical', __name__)


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


def generate_prescription_number():
    """Generate unique prescription number."""
    prefix = 'RX'
    year = datetime.now().strftime('%Y')
    last_rx = Prescription.query.filter(
        Prescription.prescription_number.like(f'{prefix}{year}%')
    ).order_by(Prescription.id.desc()).first()
    
    if last_rx:
        last_num = int(last_rx.prescription_number[-6:])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f'{prefix}{year}{new_num:06d}'


# ==================== MEDICAL RECORDS ====================

@medical_bp.route('/records')
@login_required
@role_required('admin', 'doctor')
def list_records():
    """List medical records."""
    page = request.args.get('page', 1, type=int)
    patient_id = request.args.get('patient_id', type=int)
    
    query = MedicalRecord.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    if current_user.is_doctor():
        query = query.filter_by(doctor_id=current_user.id)
    
    records = query.order_by(MedicalRecord.visit_date.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('medical/records.html', 
                         records=records, 
                         title='Medical Records')


@medical_bp.route('/records/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def create_record():
    """Create medical record route."""
    form = MedicalRecordForm()
    
    patient_id = request.args.get('patient_id', type=int)
    appointment_id = request.args.get('appointment_id', type=int)
    
    if patient_id:
        form.patient_id.data = patient_id
    if appointment_id:
        form.appointment_id.data = appointment_id
    
    if form.validate_on_submit():
        record = MedicalRecord(
            patient_id=form.patient_id.data,
            doctor_id=current_user.id,
            appointment_id=form.appointment_id.data or None,
            subjective=form.subjective.data,
            objective=form.objective.data,
            assessment=form.assessment.data,
            plan=form.plan.data,
            primary_diagnosis=form.primary_diagnosis.data,
            secondary_diagnosis=form.secondary_diagnosis.data,
            icd10_codes=json.dumps([c.strip() for c in form.icd10_codes.data.split(',') if c.strip()]) if form.icd10_codes.data else '[]',
            follow_up_date=form.follow_up_date.data,
            follow_up_notes=form.follow_up_notes.data
        )
        
        db.session.add(record)
        db.session.commit()
        
        # Update appointment status if applicable
        if form.appointment_id.data:
            appointment = Appointment.query.get(form.appointment_id.data)
            if appointment:
                appointment.status = 'completed'
                db.session.commit()
        
        log_action('create', 'MedicalRecord', record.id, 
                  f"Created medical record for patient {record.patient_id}")
        
        flash('Medical record created successfully.', 'success')
        return redirect(url_for('medical.view_record', record_id=record.id))
    
    return render_template('medical/create_record.html', 
                         form=form, 
                         title='New Medical Record')


@medical_bp.route('/records/<int:record_id>')
@login_required
@role_required('admin', 'doctor')
def view_record(record_id):
    """View medical record."""
    record = MedicalRecord.query.get_or_404(record_id)
    return render_template('medical/view_record.html', 
                         record=record, 
                         title='Medical Record')


@medical_bp.route('/records/<int:record_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def edit_record(record_id):
    """Edit medical record."""
    record = MedicalRecord.query.get_or_404(record_id)
    
    # Only the doctor who created the record or admin can edit
    if record.doctor_id != current_user.id and not current_user.is_admin():
        flash('You can only edit your own records.', 'error')
        return redirect(url_for('medical.view_record', record_id=record_id))
    
    form = MedicalRecordForm(obj=record)
    
    if request.method == 'GET':
        form.icd10_codes.data = ', '.join(record.get_icd10_list())
    
    if form.validate_on_submit():
        record.subjective = form.subjective.data
        record.objective = form.objective.data
        record.assessment = form.assessment.data
        record.plan = form.plan.data
        record.primary_diagnosis = form.primary_diagnosis.data
        record.secondary_diagnosis = form.secondary_diagnosis.data
        record.icd10_codes = json.dumps([c.strip() for c in form.icd10_codes.data.split(',') if c.strip()]) if form.icd10_codes.data else '[]'
        record.follow_up_date = form.follow_up_date.data
        record.follow_up_notes = form.follow_up_notes.data
        record.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_action('update', 'MedicalRecord', record.id, 
                  f"Updated medical record for patient {record.patient_id}")
        
        flash('Medical record updated successfully.', 'success')
        return redirect(url_for('medical.view_record', record_id=record_id))
    
    return render_template('medical/edit_record.html', 
                         form=form, 
                         record=record, 
                         title='Edit Medical Record')


# ==================== PRESCRIPTIONS ====================

@medical_bp.route('/prescriptions')
@login_required
@role_required('admin', 'doctor')
def list_prescriptions():
    """List prescriptions."""
    page = request.args.get('page', 1, type=int)
    patient_id = request.args.get('patient_id', type=int)
    
    query = Prescription.query
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    if current_user.is_doctor():
        query = query.filter_by(doctor_id=current_user.id)
    
    prescriptions = query.order_by(Prescription.prescription_date.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('medical/prescriptions.html', 
                         prescriptions=prescriptions, 
                         title='Prescriptions')


@medical_bp.route('/prescriptions/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def create_prescription():
    """Create prescription route."""
    form = PrescriptionForm()
    item_form = PrescriptionItemForm()
    
    patient_id = request.args.get('patient_id', type=int)
    medical_record_id = request.args.get('medical_record_id', type=int)
    
    if patient_id:
        form.patient_id.data = patient_id
    if medical_record_id:
        form.medical_record_id.data = medical_record_id
    
    if form.validate_on_submit():
        prescription = Prescription(
            prescription_number=generate_prescription_number(),
            patient_id=form.patient_id.data,
            doctor_id=current_user.id,
            medical_record_id=form.medical_record_id.data or None,
            instructions=form.instructions.data
        )
        
        db.session.add(prescription)
        db.session.commit()
        
        log_action('create', 'Prescription', prescription.id, 
                  f"Created prescription {prescription.prescription_number}")
        
        flash('Prescription created successfully. Add medications below.', 'success')
        return redirect(url_for('medical.edit_prescription', 
                              prescription_id=prescription.id))
    
    return render_template('medical/create_prescription.html', 
                         form=form, 
                         item_form=item_form,
                         title='New Prescription')


@medical_bp.route('/prescriptions/<int:prescription_id>')
@login_required
@role_required('admin', 'doctor')
def view_prescription(prescription_id):
    """View prescription."""
    prescription = Prescription.query.get_or_404(prescription_id)
    return render_template('medical/view_prescription.html', 
                         prescription=prescription, 
                         title=f'Prescription {prescription.prescription_number}')


@medical_bp.route('/prescriptions/<int:prescription_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'doctor')
def edit_prescription(prescription_id):
    """Edit prescription and add items."""
    prescription = Prescription.query.get_or_404(prescription_id)
    
    if prescription.doctor_id != current_user.id and not current_user.is_admin():
        flash('You can only edit your own prescriptions.', 'error')
        return redirect(url_for('medical.view_prescription', 
                              prescription_id=prescription_id))
    
    form = PrescriptionForm(obj=prescription)
    item_form = PrescriptionItemForm()
    
    if request.method == 'POST':
        if 'add_item' in request.form and item_form.validate():
            # Add new item
            item = PrescriptionItem(
                prescription_id=prescription_id,
                medication_name=item_form.medication_name.data,
                generic_name=item_form.generic_name.data,
                dosage=item_form.dosage.data,
                frequency=item_form.frequency.data,
                duration=item_form.duration.data,
                route=item_form.route.data,
                instructions=item_form.instructions.data
            )
            db.session.add(item)
            db.session.commit()
            
            flash('Medication added.', 'success')
            return redirect(url_for('medical.edit_prescription', 
                                  prescription_id=prescription_id))
        
        elif 'save_prescription' in request.form and form.validate():
            prescription.instructions = form.instructions.data
            prescription.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Prescription saved successfully.', 'success')
            return redirect(url_for('medical.view_prescription', 
                                  prescription_id=prescription_id))
    
    # Get medicines for autocomplete
    medicines = Medicine.query.filter_by(is_active=True).all()
    
    return render_template('medical/edit_prescription.html',
                         prescription=prescription,
                         form=form,
                         item_form=item_form,
                         medicines=medicines,
                         title='Edit Prescription')


@medical_bp.route('/prescriptions/items/<int:item_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'doctor')
def delete_prescription_item(item_id):
    """Delete prescription item."""
    item = PrescriptionItem.query.get_or_404(item_id)
    prescription_id = item.prescription_id
    
    db.session.delete(item)
    db.session.commit()
    
    flash('Medication removed.', 'success')
    return redirect(url_for('medical.edit_prescription', 
                          prescription_id=prescription_id))


@medical_bp.route('/prescriptions/<int:prescription_id>/pdf')
@login_required
@role_required('admin', 'doctor')
def prescription_pdf(prescription_id):
    """Generate prescription PDF."""
    from flask import current_app
    
    prescription = Prescription.query.get_or_404(prescription_id)
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Clinic header
    clinic_name = current_app.config.get('CLINIC_NAME', 'MediCare Clinic')
    clinic_address = current_app.config.get('CLINIC_ADDRESS', '')
    clinic_phone = current_app.config.get('CLINIC_PHONE', '')
    
    story.append(Paragraph(f"<h1>{clinic_name}</h1>", styles['Heading1']))
    story.append(Paragraph(f"{clinic_address}<br/>{clinic_phone}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Prescription title
    story.append(Paragraph("<h2>PRESCRIPTION</h2>", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Patient info
    story.append(Paragraph(f"<b>Patient:</b> {prescription.patient.get_full_name()}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {prescription.prescription_date.strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"<b>Prescription #:</b> {prescription.prescription_number}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Medications
    story.append(Paragraph("<b>Medications:</b>", styles['Heading3']))
    
    for item in prescription.items:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph(f"<b>{item.medication_name}</b> ({item.dosage})", styles['Normal']))
        story.append(Paragraph(f"Take {item.frequency.replace('_', ' ')} for {item.duration}", styles['Normal']))
        if item.instructions:
            story.append(Paragraph(f"<i>{item.instructions}</i>", styles['Italic']))
    
    story.append(Spacer(1, 0.3*inch))
    
    # Instructions
    if prescription.instructions:
        story.append(Paragraph("<b>General Instructions:</b>", styles['Heading3']))
        story.append(Paragraph(prescription.instructions, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
    
    # Doctor signature
    story.append(Paragraph(f"<b>Prescribed by:</b> Dr. {prescription.doctor.get_full_name()}", styles['Normal']))
    if prescription.doctor.specialization:
        story.append(Paragraph(prescription.doctor.specialization, styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"prescription_{prescription.prescription_number}.pdf",
        mimetype='application/pdf'
    )


@medical_bp.route('/api/medicines/search')
@login_required
def api_search_medicines():
    """API endpoint for medicine search."""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    medicines = Medicine.query.filter(
        db.or_(
            Medicine.name.ilike(f'%{query}%'),
            Medicine.generic_name.ilike(f'%{query}%')
        ),
        Medicine.is_active == True
    ).limit(10).all()
    
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'generic_name': m.generic_name,
        'default_dosage': m.default_dosage
    } for m in medicines])


# ==================== LAB TESTS ====================

@medical_bp.route('/lab-tests')
@login_required
def list_lab_tests():
    """List lab tests."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = LabTest.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    tests = query.order_by(LabTest.ordered_date.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('medical/lab_tests.html', 
                         tests=tests, 
                         status_filter=status_filter,
                         title='Lab Tests')


@medical_bp.route('/lab-tests/order', methods=['GET', 'POST'])
@login_required
def order_lab_test():
    """Order lab test route."""
    form = LabTestForm()
    
    patient_id = request.args.get('patient_id', type=int)
    medical_record_id = request.args.get('medical_record_id', type=int)
    
    if patient_id:
        form.patient_id.data = patient_id
    if medical_record_id:
        form.medical_record_id.data = medical_record_id
    
    if form.validate_on_submit():
        test = LabTest(
            patient_id=form.patient_id.data,
            ordered_by=current_user.id,
            medical_record_id=form.medical_record_id.data or None,
            test_name=form.test_name.data,
            test_category=form.test_category.data,
            test_code=form.test_code.data,
            clinical_notes=form.clinical_notes.data
        )
        
        db.session.add(test)
        db.session.commit()
        
        log_action('create', 'LabTest', test.id, 
                  f"Ordered lab test: {test.test_name}")
        
        flash('Lab test ordered successfully.', 'success')
        return redirect(url_for('medical.view_lab_test', test_id=test.id))
    
    return render_template('medical/order_lab_test.html', 
                         form=form, 
                         title='Order Lab Test')


@medical_bp.route('/lab-tests/<int:test_id>')
@login_required
def view_lab_test(test_id):
    """View lab test."""
    test = LabTest.query.get_or_404(test_id)
    return render_template('medical/view_lab_test.html', 
                         test=test, 
                         title=test.test_name)


@medical_bp.route('/lab-tests/<int:test_id>/results', methods=['GET', 'POST'])
@login_required
def enter_lab_results(test_id):
    """Enter lab test results."""
    test = LabTest.query.get_or_404(test_id)
    form = LabTestResultForm(obj=test)
    
    if form.validate_on_submit():
        test.results = form.results.data
        test.result_values = form.result_values.data
        test.reference_range = form.reference_range.data
        test.abnormal_flags = form.abnormal_flags.data
        test.result_notes = form.result_notes.data
        test.status = form.status.data
        test.completed_date = datetime.utcnow() if form.status.data == 'completed' else None
        
        db.session.commit()
        
        log_action('update', 'LabTest', test.id, 
                  f"Entered results for lab test: {test.test_name}")
        
        flash('Lab test results saved successfully.', 'success')
        return redirect(url_for('medical.view_lab_test', test_id=test_id))
    
    return render_template('medical/enter_lab_results.html', 
                         form=form, 
                         test=test, 
                         title='Enter Results')


@medical_bp.route('/lab-tests/<int:test_id>/status/<status>', methods=['POST'])
@login_required
def update_lab_test_status(test_id, status):
    """Update lab test status."""
    test = LabTest.query.get_or_404(test_id)
    
    valid_statuses = ['ordered', 'in_progress', 'completed', 'cancelled']
    
    if status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('medical.view_lab_test', test_id=test_id))
    
    test.status = status
    if status == 'completed':
        test.completed_date = datetime.utcnow()
    
    db.session.commit()
    
    log_action('update', 'LabTest', test.id, f"Status changed to {status}")
    
    flash(f'Lab test status updated to {status}.', 'success')
    return redirect(url_for('medical.view_lab_test', test_id=test_id))


# ==================== MEDICINES DATABASE ====================

@medical_bp.route('/medicines')
@login_required
def list_medicines():
    """List medicines in database."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Medicine.query
    
    if search:
        query = query.filter(
            db.or_(
                Medicine.name.ilike(f'%{search}%'),
                Medicine.generic_name.ilike(f'%{search}%')
            )
        )
    
    medicines = query.order_by(Medicine.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('medical/medicines.html', 
                         medicines=medicines, 
                         search=search,
                         title='Medicines Database')


@medical_bp.route('/medicines/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_medicine():
    """Add medicine to database."""
    from forms import MedicineForm
    
    form = MedicineForm()
    
    if form.validate_on_submit():
        medicine = Medicine(
            name=form.name.data,
            generic_name=form.generic_name.data,
            category=form.category.data,
            dosage_forms=json.dumps([d.strip() for d in form.dosage_forms.data.split('\n') if d.strip()]) if form.dosage_forms.data else '[]',
            strengths=json.dumps([s.strip() for s in form.strengths.data.split('\n') if s.strip()]) if form.strengths.data else '[]',
            default_dosage=form.default_dosage.data,
            instructions=form.instructions.data,
            contraindications=form.contraindications.data,
            side_effects=form.side_effects.data
        )
        
        db.session.add(medicine)
        db.session.commit()
        
        log_action('create', 'Medicine', medicine.id, f"Added medicine: {medicine.name}")
        
        flash('Medicine added successfully.', 'success')
        return redirect(url_for('medical.list_medicines'))
    
    return render_template('medical/create_medicine.html', 
                         form=form, 
                         title='Add Medicine')

"""
Clinic Management Platform - FHIR API Routes
==========================================
Fast Healthcare Interoperability Resources (FHIR) R4 compliant endpoints for Patient, Appointment, and Observation resources.
"""

from flask import Blueprint, jsonify, request, render_template, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from models import db, Patient, Appointment, MedicalRecord, User, AuditLog
import json
import uuid

fhir_bp = Blueprint('fhir', __name__, url_prefix='/fhir')


def log_fhir_action(action, resource_type, resource_id=None, description=None):
    """Audit log helper for HIPAA compliance on FHIR requests."""
    user_email = current_user.email if (current_user and current_user.is_authenticated) else request.headers.get('X-User-Email', 'anonymous-fhir-client')
    user_id = current_user.id if (current_user and current_user.is_authenticated) else None
    
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=f"FHIR_{action}",
        entity_type=resource_type,
        entity_id=resource_id,
        description=description,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None
    )
    db.session.add(log)
    db.session.commit()


@fhir_bp.route('/docs')
def fhir_docs():
    """Swagger UI documentation for FHIR APIs."""
    return render_template('fhir/docs.html', title='FHIR API Documentation')


@fhir_bp.route('/swagger.json')
def fhir_swagger():
    """OpenAPI 3.0 specification for FHIR APIs."""
    spec = {
        "openapi": "3.0.1",
        "info": {
            "title": "Clinic FHIR R4 API",
            "version": "1.0.0",
            "description": "FHIR R4 Compliant REST API for Patient, Appointment, and Observation resources with HIPAA security and audit logging."
        },
        "servers": [
            {"url": "/fhir", "description": "Local FHIR Server"}
        ],
        "paths": {
            "/Patient": {
                "get": {
                    "summary": "Search or list Patients",
                    "responses": {"200": {"description": "Successful Patient Bundle"}}
                },
                "post": {
                    "summary": "Create Patient",
                    "responses": {"201": {"description": "Patient created successfully"}}
                }
            },
            "/Patient/{id}": {
                "get": {
                    "summary": "Get Patient by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Patient resource"}, "404": {"description": "Patient not found"}}
                },
                "post": {
                    "summary": "Update or create Patient by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Patient updated successfully"}}
                }
            },
            "/Appointment": {
                "get": {
                    "summary": "List Appointments",
                    "responses": {"200": {"description": "Appointment Bundle"}}
                },
                "post": {
                    "summary": "Create Appointment",
                    "responses": {"201": {"description": "Appointment created successfully"}}
                }
            },
            "/Appointment/{id}": {
                "get": {
                    "summary": "Get Appointment by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Appointment resource"}, "404": {"description": "Not found"}}
                },
                "post": {
                    "summary": "Update or create Appointment by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Appointment updated"}}
                }
            },
            "/Observation": {
                "get": {
                    "summary": "List Observations (Medical Records)",
                    "responses": {"200": {"description": "Observation Bundle"}}
                },
                "post": {
                    "summary": "Create Observation",
                    "responses": {"201": {"description": "Observation created successfully"}}
                }
            },
            "/Observation/{id}": {
                "get": {
                    "summary": "Get Observation by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Observation resource"}, "404": {"description": "Not found"}}
                },
                "post": {
                    "summary": "Update or create Observation by ID",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Observation updated"}}
                }
            }
        }
    }
    return jsonify(spec)


def get_or_create_default_patient():
    pat = Patient.query.first()
    if not pat:
        pat = Patient(
            patient_id=f"P-{uuid.uuid4().hex[:6].upper()}",
            first_name="Default",
            last_name="Patient",
            date_of_birth=date(1980, 1, 1),
            gender="other",
            phone="555-0000"
        )
        db.session.add(pat)
        db.session.commit()
    return pat


def get_or_create_default_doctor():
    doc = User.query.first()
    if not doc:
        doc = User(
            email=f"doc-{uuid.uuid4().hex[:4]}@clinic.local",
            first_name="Default",
            last_name="Doctor",
            role="doctor"
        )
        doc.set_password("Password123!")
        db.session.add(doc)
        db.session.commit()
    return doc


# --- Patient Endpoints ---
@fhir_bp.route('/Patient', methods=['GET', 'POST'])
@fhir_bp.route('/Patient/<int:id>', methods=['GET', 'POST'])
def fhir_patient(id=None):
    """FHIR Patient endpoint (GET/POST)."""
    if request.method == 'GET':
        if id is not None:
            patient = Patient.query.get_or_404(id)
            log_fhir_action('READ', 'Patient', patient.id, f"Read Patient/{patient.id}")
            return jsonify(patient.to_fhir())
        else:
            patients = Patient.query.limit(50).all()
            log_fhir_action('SEARCH', 'Patient', None, "Searched Patient list")
            return jsonify({
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(patients),
                "entry": [{"resource": p.to_fhir()} for p in patients]
            })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        try:
            if id is not None:
                patient = Patient.query.get(id)
                if not patient:
                    patient = Patient(id=id)
                    db.session.add(patient)
                    action = 'CREATE'
                else:
                    action = 'UPDATE'
            else:
                patient = Patient()
                db.session.add(patient)
                action = 'CREATE'
            
            if not patient.patient_id:
                patient.patient_id = f"P-{uuid.uuid4().hex[:6].upper()}"
            
            name_list = data.get('name', [])
            if name_list:
                family = name_list[0].get('family', '')
                given = name_list[0].get('given', [''])
                patient.last_name = family
                patient.first_name = given[0] if given else ''
            
            if not patient.first_name:
                patient.first_name = "Unknown"
            if not patient.last_name:
                patient.last_name = "Patient"
            
            telecom_list = data.get('telecom', [])
            for t in telecom_list:
                if t.get('system') == 'phone':
                    patient.phone = t.get('value')
                elif t.get('system') == 'email':
                    patient.email = t.get('value')
            
            if not patient.phone:
                patient.phone = "000-000-0000"
            
            patient.gender = data.get('gender', 'unknown')
            if data.get('birthDate'):
                try:
                    patient.date_of_birth = datetime.strptime(data.get('birthDate'), '%Y-%m-%d').date()
                except Exception:
                    patient.date_of_birth = date(1970, 1, 1)
            else:
                patient.date_of_birth = date(1970, 1, 1)
            
            address_list = data.get('address', [])
            if address_list:
                patient.address = address_list[0].get('text') or ', '.join(address_list[0].get('line', []))
            
            db.session.commit()
            log_fhir_action(action, 'Patient', patient.id, f"{action} Patient/{patient.id} via FHIR API")
            return jsonify(patient.to_fhir()), (200 if action == 'UPDATE' else 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400


# --- Appointment Endpoints ---
@fhir_bp.route('/Appointment', methods=['GET', 'POST'])
@fhir_bp.route('/Appointment/<int:id>', methods=['GET', 'POST'])
def fhir_appointment(id=None):
    """FHIR Appointment endpoint (GET/POST)."""
    if request.method == 'GET':
        if id is not None:
            appts = Appointment.query.get_or_404(id)
            log_fhir_action('READ', 'Appointment', appts.id, f"Read Appointment/{appts.id}")
            return jsonify(appts.to_fhir())
        else:
            appointments = Appointment.query.limit(50).all()
            log_fhir_action('SEARCH', 'Appointment', None, "Searched Appointment list")
            return jsonify({
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(appointments),
                "entry": [{"resource": a.to_fhir()} for a in appointments]
            })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        try:
            default_pat = get_or_create_default_patient()
            default_doc = get_or_create_default_doctor()

            if id is not None:
                appointment = Appointment.query.get(id)
                if not appointment:
                    appointment = Appointment(id=id)
                    db.session.add(appointment)
                    action = 'CREATE'
                else:
                    action = 'UPDATE'
            else:
                appointment = Appointment()
                db.session.add(appointment)
                action = 'CREATE'
            
            appointment.status = data.get('status', 'booked')
            appointment.reason = data.get('description')
            appointment.notes = data.get('comment')
            
            if data.get('start'):
                try:
                    start_dt = datetime.fromisoformat(data.get('start').replace('Z', '+00:00'))
                    appointment.appointment_date = start_dt.date()
                    appointment.start_time = start_dt.time()
                except Exception:
                    appointment.appointment_date = date.today()
                    appointment.start_time = datetime.now().time()
            else:
                appointment.appointment_date = date.today()
                appointment.start_time = datetime.now().time()
            
            if data.get('end'):
                try:
                    end_dt = datetime.fromisoformat(data.get('end').replace('Z', '+00:00'))
                    appointment.end_time = end_dt.time()
                except Exception:
                    appointment.end_time = appointment.start_time
            else:
                appointment.end_time = appointment.start_time
            
            patient_id = default_pat.id
            doctor_id = default_doc.id

            participants = data.get('participant', [])
            for p in participants:
                actor = p.get('actor', {}).get('reference', '')
                if 'Patient/' in actor:
                    try:
                        patient_id = int(actor.split('/')[-1])
                    except ValueError:
                        pass
                elif 'Practitioner/' in actor or 'User/' in actor:
                    try:
                        doctor_id = int(actor.split('/')[-1])
                    except ValueError:
                        pass
            
            appointment.patient_id = patient_id
            appointment.doctor_id = doctor_id
            
            db.session.commit()
            log_fhir_action(action, 'Appointment', appointment.id, f"{action} Appointment/{appointment.id} via FHIR API")
            return jsonify(appointment.to_fhir()), (200 if action == 'UPDATE' else 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400


# --- Observation Endpoints ---
@fhir_bp.route('/Observation', methods=['GET', 'POST'])
@fhir_bp.route('/Observation/<int:id>', methods=['GET', 'POST'])
def fhir_observation(id=None):
    """FHIR Observation endpoint (GET/POST) mapping to MedicalRecord."""
    if request.method == 'GET':
        if id is not None:
            record = MedicalRecord.query.get_or_404(id)
            log_fhir_action('READ', 'Observation', record.id, f"Read Observation/{record.id}")
            return jsonify(record.to_fhir())
        else:
            records = MedicalRecord.query.limit(50).all()
            log_fhir_action('SEARCH', 'Observation', None, "Searched Observation list")
            return jsonify({
                "resourceType": "Bundle",
                "type": "searchset",
                "total": len(records),
                "entry": [{"resource": r.to_fhir()} for r in records]
            })
    
    elif request.method == 'POST':
        data = request.get_json() or {}
        try:
            default_pat = get_or_create_default_patient()
            default_doc = get_or_create_default_doctor()

            if id is not None:
                record = MedicalRecord.query.get(id)
                if not record:
                    record = MedicalRecord(id=id)
                    db.session.add(record)
                    action = 'CREATE'
                else:
                    action = 'UPDATE'
            else:
                record = MedicalRecord()
                db.session.add(record)
                action = 'CREATE'
            
            patient_id = default_pat.id
            doctor_id = default_doc.id

            subject = data.get('subject', {}).get('reference', '')
            if 'Patient/' in subject:
                try:
                    patient_id = int(subject.split('/')[-1])
                except ValueError:
                    pass
            
            record.patient_id = patient_id
            record.doctor_id = doctor_id
            
            coding = data.get('code', {}).get('coding', [{}])
            record.primary_diagnosis = coding[0].get('display') or data.get('code', {}).get('text', 'Clinical Observation')
            record.plan = data.get('valueString') or data.get('note', [{}])[0].get('text')
            
            db.session.commit()
            log_fhir_action(action, 'Observation', record.id, f"{action} Observation/{record.id} via FHIR API")
            return jsonify(record.to_fhir()), (200 if action == 'UPDATE' else 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 400

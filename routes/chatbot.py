"""
AI chatbots for the clinic.

There is one chat UI, but the tools and permissions change with the logged-in
user's role. Qwen understands the request; Flask owns the real data and rules.
"""
from flask import Blueprint, render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
import json
import os
import uuid
import urllib.request
import urllib.error

from sqlalchemy.exc import IntegrityError

from models import (
    db, ChatbotConversation, Patient, Appointment, Service, User,
    MedicalRecord, VitalSigns, Prescription, PrescriptionItem, LabTest
)

chatbot_bp = Blueprint('chatbot', __name__)

ACTIVE_APPOINTMENT_STATUSES = ['scheduled', 'confirmed', 'in_progress']


def get_or_create_session():
    # Bind the chat history to the authenticated account. This prevents a
    # different user on the same browser session from seeing old chat data.
    prefix = f"user-{current_user.id}-"
    current = session.get('chatbot_session')
    if not current or not current.startswith(prefix):
        current = prefix + str(uuid.uuid4())
        session['chatbot_session'] = current
    return current


def linked_patient():
    """Find the patient account linked by email.

    This keeps the existing Patient table intact. A patient user is linked when
    their login email matches Patient.email. A future admin UI can make this an
    explicit link without changing the chatbot API.
    """
    if not current_user.is_authenticated:
        return None
    return Patient.query.filter_by(email=current_user.email, is_active=True).first()


def role_name():
    return getattr(current_user, 'role', None) or 'guest'


def patient_context():
    patient = linked_patient()
    return patient


def ai_config():
    key = current_app.config.get('QWEN_API_KEY')
    base = (current_app.config.get('QWEN_BASE_URL') or '').rstrip('/')
    model = current_app.config.get('QWEN_MODEL') or 'qwen3.8-max'
    provider = current_app.config.get('AI_PROVIDER', 'qwen')
    return key, base, model, provider


def qwen_chat(messages, tools=None):
    """Call the configured OpenAI-compatible chat endpoint server-side."""
    api_key, base_url, model, provider = ai_config()
    if not api_key:
        raise RuntimeError('No AI provider key is configured')
    if not base_url:
        raise RuntimeError('No AI provider base URL is configured')
    payload = {
        'model': model,
        'messages': messages,
    }
    if provider == 'qwen':
        payload['temperature'] = 0.2
        payload['enable_thinking'] = False
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        base_url + '/chat/completions',
        data=body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )
    timeout = current_app.config.get('QWEN_TIMEOUT', 45)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='replace')[:1000]
        raise RuntimeError(f'AI API error {exc.code}: {detail}')
    except urllib.error.URLError as exc:
        raise RuntimeError(f'AI connection error: {exc.reason}')


def tool(name, description, properties=None, required=None):
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': properties or {},
                'required': required or [],
            }
        }
    }


def patient_tools():
    return [
        tool('get_my_profile', 'Get the logged-in patient profile.', {}, []),
        tool('get_my_appointments', 'Get the logged-in patient upcoming appointments.', {
            'include_past': {'type': 'boolean', 'description': 'Include recent past appointments.'}
        }, []),
        tool('get_available_slots', 'Find real available appointment slots for a doctor on a date.', {
            'doctor_id': {'type': 'integer'},
            'date': {'type': 'string', 'description': 'Date in YYYY-MM-DD format.'}
        }, ['doctor_id', 'date']),
        tool('get_doctors', 'List active doctors and their specialties.', {}, []),
        tool('get_clinic_services', 'List active clinic services.', {}, []),
        tool('book_appointment', 'Book one appointment for the logged-in patient after checking conflicts.', {
            'doctor_id': {'type': 'integer'},
            'date': {'type': 'string'},
            'start_time': {'type': 'string', 'description': 'HH:MM'},
            'appointment_type': {'type': 'string'},
            'reason': {'type': 'string'}
        }, ['doctor_id', 'date', 'start_time']),
        tool('cancel_appointment', 'Cancel one of the logged-in patient active appointments.', {
            'appointment_id': {'type': 'integer'}
        }, ['appointment_id']),
        tool('reschedule_appointment', 'Move one of the logged-in patient active appointments to a new available slot.', {
            'appointment_id': {'type': 'integer'},
            'doctor_id': {'type': 'integer'},
            'date': {'type': 'string'},
            'start_time': {'type': 'string'}
        }, ['appointment_id', 'doctor_id', 'date', 'start_time']),
    ]


def doctor_tools():
    return [
        tool('get_my_schedule', 'Get the logged-in doctor schedule for a date.', {
            'date': {'type': 'string', 'description': 'YYYY-MM-DD'}
        }, ['date']),
        tool('get_my_appointments', 'Get the logged-in doctor upcoming appointments.', {
            'date': {'type': 'string', 'description': 'Optional YYYY-MM-DD. If omitted, upcoming appointments.'}
        }, []),
        tool('get_appointment_details', 'Get details of an appointment belonging to the logged-in doctor.', {
            'appointment_id': {'type': 'integer'}
        }, ['appointment_id']),
        tool('search_patient', 'Search patients that the doctor has an appointment with or has treated.', {
            'query': {'type': 'string'}
        }, ['query']),
        tool('get_patient_symptoms', 'Get symptoms/subjective notes for a patient seen by the logged-in doctor.', {
            'patient_id': {'type': 'integer'}
        }, ['patient_id']),
        tool('get_patient_history', 'Get recent medical records for a patient seen by the logged-in doctor.', {
            'patient_id': {'type': 'integer'},
            'limit': {'type': 'integer'}
        }, ['patient_id']),
        tool('get_patient_vitals', 'Get recent vital signs for a patient seen by the logged-in doctor.', {
            'patient_id': {'type': 'integer'},
            'limit': {'type': 'integer'}
        }, ['patient_id']),
        tool('get_patient_prescriptions', 'Get recent prescriptions and medicines for a patient seen by the logged-in doctor.', {
            'patient_id': {'type': 'integer'},
            'limit': {'type': 'integer'}
        }, ['patient_id']),
        tool('get_patient_lab_results', 'Get recent lab tests and results for a patient seen by the logged-in doctor.', {
            'patient_id': {'type': 'integer'},
            'limit': {'type': 'integer'}
        }, ['patient_id']),
        tool('add_medical_note', 'Add a clinical note to a patient visit. Only after the doctor clearly asks to save it.', {
            'patient_id': {'type': 'integer'},
            'appointment_id': {'type': 'integer'},
            'subjective': {'type': 'string'},
            'objective': {'type': 'string'},
            'assessment': {'type': 'string'},
            'plan': {'type': 'string'}
        }, ['patient_id', 'subjective']),
    ]


def patient_owns_appointment(patient, appointment_id):
    return Appointment.query.filter_by(id=appointment_id, patient_id=patient.id).first()


def doctor_can_access_patient(doctor_id, patient_id):
    return db.session.query(Appointment.id).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.patient_id == patient_id
    ).first() is not None or db.session.query(MedicalRecord.id).filter(
        MedicalRecord.doctor_id == doctor_id,
        MedicalRecord.patient_id == patient_id
    ).first() is not None


def parse_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except Exception:
        raise ValueError('Date must be YYYY-MM-DD.')


def parse_time(value):
    for fmt in ('%H:%M', '%H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            pass
    raise ValueError('Time must be HH:MM.')


def slot_available(doctor_id, selected_date, start, end, exclude_appointment_id=None):
    if selected_date < date.today():
        return False, 'The date is in the past.'
    if start >= end:
        return False, 'Invalid time range.'
    # Current clinic default. This can later be moved to a doctor schedule table.
    if start < time(9, 0) or end > time(17, 0):
        return False, 'The clinic slot must be between 09:00 and 17:00.'
    conflict_query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == selected_date,
        Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES),
        Appointment.start_time < end,
        Appointment.end_time > start,
    )
    if exclude_appointment_id is not None:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)
    conflict = conflict_query.first()
    return (False, 'That slot is already booked.') if conflict else (True, None)


def execute_tool(name, args):
    """Execute a tool with server-side authorization. The model cannot bypass this."""
    role = role_name()

    if role == 'patient':
        patient = patient_context()
        if not patient:
            return {'ok': False, 'error': 'No patient profile is linked to this account. Contact reception.'}

        if name == 'get_my_profile':
            return {'ok': True, 'patient': {
                'id': patient.id, 'patient_id': patient.patient_id,
                'name': patient.get_full_name(), 'email': patient.email,
                'phone': patient.phone, 'age': patient.get_age(), 'gender': patient.gender,
                'allergies': patient.get_allergies_list(),
                'chronic_conditions': patient.get_chronic_conditions_list(),
            }}

        if name == 'get_my_appointments':
            include_past = bool(args.get('include_past'))
            query = Appointment.query.filter_by(patient_id=patient.id)
            if not include_past:
                query = query.filter(Appointment.appointment_date >= date.today(), Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
            else:
                query = query.filter(Appointment.appointment_date >= date.today() - timedelta(days=90))
            items = query.order_by(Appointment.appointment_date, Appointment.start_time).limit(30).all()
            return {'ok': True, 'appointments': [serialize_appointment(a, include_patient=False) for a in items]}

        if name == 'get_doctors':
            doctors = User.query.filter_by(role='doctor', is_active=True).order_by(User.first_name).all()
            return {'ok': True, 'doctors': [{'id': d.id, 'name': d.get_full_name(), 'specialization': d.specialization} for d in doctors]}

        if name == 'get_clinic_services':
            services = Service.query.filter_by(is_active=True).limit(50).all()
            return {'ok': True, 'services': [{'id': s.id, 'name': s.service_name, 'price': float(s.default_price) if s.default_price is not None else None} for s in services]}

        if name == 'get_available_slots':
            selected_date = parse_date(args['date'])
            doctor = User.query.filter_by(id=args['doctor_id'], role='doctor', is_active=True).first()
            if not doctor:
                return {'ok': False, 'error': 'Doctor not found.'}
            slots = []
            current = datetime.combine(selected_date, time(9, 0))
            end_day = datetime.combine(selected_date, time(17, 0))
            while current < end_day:
                st = current.time(); en = (current + timedelta(minutes=30)).time()
                ok, _ = slot_available(doctor.id, selected_date, st, en)
                if ok:
                    slots.append(st.strftime('%H:%M'))
                current += timedelta(minutes=30)
            return {'ok': True, 'doctor': doctor.get_full_name(), 'date': selected_date.isoformat(), 'slots': slots}

        if name == 'book_appointment':
            selected_date = parse_date(args['date']); start = parse_time(args['start_time']); end = (datetime.combine(selected_date, start) + timedelta(minutes=30)).time()
            doctor = User.query.filter_by(id=args['doctor_id'], role='doctor', is_active=True).first()
            if not doctor:
                return {'ok': False, 'error': 'Doctor not found.'}
            active = Appointment.query.filter_by(patient_id=patient.id).filter(Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES), Appointment.appointment_date >= date.today()).first()
            if active:
                return {'ok': False, 'code': 'ACTIVE_APPOINTMENT_EXISTS', 'message': 'The patient already has an active upcoming appointment.', 'appointment': serialize_appointment(active)}
            ok, error = slot_available(doctor.id, selected_date, start, end)
            if not ok:
                return {'ok': False, 'code': 'SLOT_UNAVAILABLE', 'message': error}
            booking_key = f'{doctor.id}:{selected_date.isoformat()}:{start.strftime("%H:%M")}'
            appointment = Appointment(
                patient_id=patient.id, doctor_id=doctor.id, appointment_date=selected_date,
                start_time=start, end_time=end, booking_key=booking_key, status='confirmed',
                appointment_type=args.get('appointment_type') or 'consultation',
                reason=args.get('reason'), created_by=None
            )
            db.session.add(appointment)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                return {'ok': False, 'code': 'SLOT_UNAVAILABLE', 'message': 'That slot was just booked by another patient. Please choose another slot.'}
            notify_n8n('appointment.created', appointment)
            return {'ok': True, 'message': 'Appointment booked.', 'appointment': serialize_appointment(appointment)}

        if name == 'cancel_appointment':
            appointment = patient_owns_appointment(patient, int(args['appointment_id']))
            if not appointment:
                return {'ok': False, 'error': 'Appointment not found.'}
            if appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
                return {'ok': False, 'error': 'This appointment is already closed.'}
            appointment.status = 'cancelled'; appointment.booking_key = None; appointment.updated_at = datetime.utcnow(); db.session.commit()
            notify_n8n('appointment.cancelled', appointment)
            return {'ok': True, 'message': 'Appointment cancelled.', 'appointment': serialize_appointment(appointment)}

        if name == 'reschedule_appointment':
            appointment = patient_owns_appointment(patient, int(args['appointment_id']))
            if not appointment or appointment.status not in ACTIVE_APPOINTMENT_STATUSES:
                return {'ok': False, 'error': 'Active appointment not found.'}
            selected_date = parse_date(args['date']); start = parse_time(args['start_time']); end = (datetime.combine(selected_date, start) + timedelta(minutes=30)).time()
            doctor = User.query.filter_by(id=args['doctor_id'], role='doctor', is_active=True).first()
            if not doctor: return {'ok': False, 'error': 'Doctor not found.'}
            ok, error = slot_available(doctor.id, selected_date, start, end, exclude_appointment_id=appointment.id)
            if not ok: return {'ok': False, 'code': 'SLOT_UNAVAILABLE', 'message': error}
            old_status = appointment.status
            old_booking_key = appointment.booking_key
            old_doctor_id = appointment.doctor_id
            old_date = appointment.appointment_date
            old_start = appointment.start_time
            old_end = appointment.end_time
            new_booking_key = f'{doctor.id}:{selected_date.isoformat()}:{start.strftime("%H:%M")}'
            # Same slot: there is nothing to change.
            if old_doctor_id == doctor.id and old_date == selected_date and old_start == start:
                return {'ok': True, 'message': 'The appointment is already at that time.', 'appointment': serialize_appointment(appointment)}
            appointment.status = 'cancelled'
            appointment.booking_key = None
            replacement = Appointment(
                patient_id=patient.id, doctor_id=doctor.id, appointment_date=selected_date,
                start_time=start, end_time=end, booking_key=new_booking_key, status='confirmed',
                appointment_type=appointment.appointment_type, reason=appointment.reason
            )
            db.session.add(replacement)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # The rollback restores the old appointment in the current session.
                return {'ok': False, 'code': 'SLOT_UNAVAILABLE', 'message': 'That slot was just booked by another patient. Please choose another slot.'}
            notify_n8n('appointment.rescheduled', replacement)
            return {'ok': True, 'message': 'Appointment rescheduled.', 'appointment': serialize_appointment(replacement)}

        return {'ok': False, 'error': 'Tool is not available for patient accounts.'}

    if role == 'doctor':
        doctor = current_user
        if name in ('get_my_schedule', 'get_my_appointments'):
            selected_date = parse_date(args['date']) if args.get('date') else None
            query = Appointment.query.filter_by(doctor_id=doctor.id)
            if selected_date:
                query = query.filter_by(appointment_date=selected_date)
            else:
                query = query.filter(Appointment.appointment_date >= date.today(), Appointment.status.in_(ACTIVE_APPOINTMENT_STATUSES))
            items = query.order_by(Appointment.appointment_date, Appointment.start_time).limit(100).all()
            return {'ok': True, 'appointments': [serialize_appointment(a) for a in items]}

        if name == 'get_appointment_details':
            a = Appointment.query.filter_by(id=int(args['appointment_id']), doctor_id=doctor.id).first()
            return {'ok': True, 'appointment': serialize_appointment(a)} if a else {'ok': False, 'error': 'Appointment not found.'}

        if name == 'search_patient':
            q = (args.get('query') or '').strip()
            if len(q) < 2: return {'ok': False, 'error': 'Search query is too short.'}
            patient_query = Patient.query.join(
                Appointment, Appointment.patient_id == Patient.id
            ).filter(Appointment.doctor_id == doctor.id)
            # Let the assistant pass a full name while still matching each
            # part against the normalized first/last name fields.
            for term in q.split():
                patient_query = patient_query.filter(db.or_(
                    Patient.first_name.ilike(f'%{term}%'),
                    Patient.last_name.ilike(f'%{term}%'),
                    Patient.patient_id.ilike(f'%{term}%'),
                ))
            patients = patient_query.distinct().limit(20).all()
            return {'ok': True, 'patients': [{'id': p.id, 'patient_id': p.patient_id, 'name': p.get_full_name(), 'email': p.email, 'phone': p.phone} for p in patients]}

        if name in ('get_patient_symptoms', 'get_patient_history', 'get_patient_vitals', 'get_patient_prescriptions', 'get_patient_lab_results', 'add_medical_note'):
            patient_id = int(args['patient_id'])
            if not doctor_can_access_patient(doctor.id, patient_id):
                return {'ok': False, 'error': 'You are not authorized to access this patient.'}
            patient = Patient.query.get(patient_id)
            if not patient: return {'ok': False, 'error': 'Patient not found.'}
            if name == 'get_patient_symptoms':
                records = MedicalRecord.query.filter_by(doctor_id=doctor.id, patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).limit(10).all()
                return {'ok': True, 'patient': patient.get_full_name(), 'symptoms': [r.subjective for r in records if r.subjective]}
            if name == 'get_patient_history':
                limit = min(max(int(args.get('limit') or 10), 1), 30)
                records = MedicalRecord.query.filter_by(doctor_id=doctor.id, patient_id=patient_id).order_by(MedicalRecord.visit_date.desc()).limit(limit).all()
                return {'ok': True, 'patient': patient.get_full_name(), 'records': [{
                    'id': r.id, 'visit_date': r.visit_date.isoformat() if r.visit_date else None,
                    'subjective': r.subjective, 'objective': r.objective, 'assessment': r.assessment, 'plan': r.plan,
                    'primary_diagnosis': r.primary_diagnosis, 'follow_up_date': r.follow_up_date.isoformat() if r.follow_up_date else None,
                } for r in records]}
            if name == 'get_patient_vitals':
                limit = min(max(int(args.get('limit') or 10), 1), 30)
                vitals = VitalSigns.query.filter_by(patient_id=patient_id).order_by(VitalSigns.recorded_at.desc()).limit(limit).all()
                return {'ok': True, 'patient': patient.get_full_name(), 'vitals': [{
                    'recorded_at': v.recorded_at.isoformat() if v.recorded_at else None,
                    'height_cm': v.height_cm, 'weight_kg': v.weight_kg, 'bmi': v.bmi or v.calculate_bmi(),
                    'temperature_celsius': v.temperature_celsius, 'blood_pressure': v.get_blood_pressure(),
                    'heart_rate': v.heart_rate, 'respiratory_rate': v.respiratory_rate,
                    'oxygen_saturation': v.oxygen_saturation, 'blood_glucose': v.blood_glucose, 'notes': v.notes
                } for v in vitals]}
            if name == 'get_patient_prescriptions':
                limit = min(max(int(args.get('limit') or 10), 1), 30)
                prescriptions = Prescription.query.filter_by(doctor_id=doctor.id, patient_id=patient_id).order_by(Prescription.prescription_date.desc()).limit(limit).all()
                return {'ok': True, 'patient': patient.get_full_name(), 'prescriptions': [{
                    'id': p.id, 'number': p.prescription_number, 'date': p.prescription_date.isoformat() if p.prescription_date else None,
                    'status': p.status, 'instructions': p.instructions,
                    'medicines': [{'name': i.medication_name, 'generic_name': i.generic_name, 'dosage': i.dosage, 'frequency': i.frequency, 'duration': i.duration, 'route': i.route, 'instructions': i.instructions} for i in p.items.all()]
                } for p in prescriptions]}
            if name == 'get_patient_lab_results':
                limit = min(max(int(args.get('limit') or 10), 1), 30)
                labs = LabTest.query.filter_by(ordered_by=doctor.id, patient_id=patient_id).order_by(LabTest.ordered_date.desc()).limit(limit).all()
                return {'ok': True, 'patient': patient.get_full_name(), 'lab_results': [{
                    'id': l.id, 'test_name': l.test_name, 'category': l.test_category, 'status': l.status,
                    'ordered_date': l.ordered_date.isoformat() if l.ordered_date else None,
                    'completed_date': l.completed_date.isoformat() if l.completed_date else None,
                    'results': l.results, 'result_values': l.get_result_values_dict(), 'reference_range': l.reference_range,
                    'abnormal_flags': l.abnormal_flags, 'result_notes': l.result_notes
                } for l in labs]}
            appointment_id = int(args['appointment_id']) if args.get('appointment_id') else None
            if appointment_id and not Appointment.query.filter_by(id=appointment_id, doctor_id=doctor.id, patient_id=patient_id).first():
                return {'ok': False, 'error': 'Appointment is not linked to this doctor and patient.'}
            record = MedicalRecord(
                patient_id=patient_id, doctor_id=doctor.id, appointment_id=appointment_id,
                subjective=args.get('subjective'), objective=args.get('objective'),
                assessment=args.get('assessment'), plan=args.get('plan')
            )
            db.session.add(record); db.session.commit()
            return {'ok': True, 'message': 'Medical note saved.', 'record_id': record.id}

        return {'ok': False, 'error': 'Tool is not available for doctor accounts.'}

    return {'ok': False, 'error': 'Please sign in.'}


def serialize_appointment(a, include_patient=True):
    if not a: return None
    data = {
        'id': a.id, 'uuid': a.uuid, 'doctor_id': a.doctor_id,
        'doctor_name': a.doctor.get_full_name() if a.doctor else None,
        'date': a.appointment_date.isoformat(), 'start_time': a.start_time.strftime('%H:%M'),
        'end_time': a.end_time.strftime('%H:%M'), 'status': a.status,
        'type': a.appointment_type, 'reason': a.reason,
    }
    if include_patient:
        data.update({'patient_id': a.patient_id, 'patient_name': a.patient.get_full_name() if a.patient else None})
    return data


def notify_n8n(event, appointment):
    url = current_app.config.get('N8N_WEBHOOK_URL')
    key = current_app.config.get('N8N_API_KEY')
    if not url: return
    payload = json.dumps({'event': event, 'appointment': serialize_appointment(appointment)}).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if key: headers['X-N8N-API-Key'] = key
    req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        current_app.logger.exception('n8n notification failed')


def system_prompt():
    role = role_name()
    today = date.today().isoformat()
    if role == 'patient':
        return f"""You are the patient assistant for a clinic. Today is {today}. Reply in the user's language. Be concise and friendly. You can help with appointments, clinic services, and the patient's own information. Never invent appointment availability or medical-record facts; use tools. Never diagnose. For urgent symptoms, tell the user to seek appropriate emergency care. You may only use patient tools and only for the logged-in patient. If the account has no linked patient profile, say so. When booking, always check availability and confirm the exact date/time before or after the booking tool result. If the patient already has an active appointment, explain it instead of creating another."""
    if role == 'doctor':
        return f"""You are the private clinical assistant for the logged-in doctor. Today is {today}. Reply in the user's language. Be concise and practical. Use tools for schedules, appointments, patient symptoms, medical history, vitals, prescriptions, and lab results. You may only access patients connected to this doctor's appointments or records. Never reveal data from another doctor. Do not diagnose beyond the doctor's supplied record; summarize and organize existing information. Only save a medical note when the doctor clearly asks you to save it. Never invent clinical facts."""
    return "You are a clinic assistant. Ask the user to sign in before using private features."


def generate_ai_response(message, session_id):
    if not current_user.is_authenticated:
        return 'Please sign in first so I can help you with your clinic account.'
    if role_name() not in ('patient', 'doctor'):
        return 'This AI assistant is available for patient and doctor accounts.'
    if role_name() == 'patient' and not patient_context():
        return 'Your account is not linked to a patient profile yet. Please contact reception so they can link your account.'

    history = ChatbotConversation.query.filter_by(session_id=session_id).order_by(ChatbotConversation.created_at.desc()).limit(12).all()
    messages = [{'role': 'system', 'content': system_prompt()}]
    for item in reversed(history):
        messages.append({'role': 'user', 'content': item.message})
        messages.append({'role': 'assistant', 'content': item.response})
    messages.append({'role': 'user', 'content': message})
    tools = patient_tools() if role_name() == 'patient' else doctor_tools()

    # Allow several tool calls in one turn, but keep a hard limit.
    result = None
    for _ in range(4):
        result = qwen_chat(messages, tools=tools)
        msg = result['choices'][0]['message']
        tool_calls = msg.get('tool_calls') or []
        messages.append(msg)
        if not tool_calls:
            break
        for call in tool_calls:
            fn = call.get('function', {})
            name = fn.get('name')
            try:
                args = json.loads(fn.get('arguments') or '{}')
            except json.JSONDecodeError:
                args = {}
            try:
                tool_result = execute_tool(name, args)
            except Exception as exc:
                db.session.rollback()
                current_app.logger.exception('Chat tool failed: %s', name)
                tool_result = {'ok': False, 'error': str(exc)}
            messages.append({'role': 'tool', 'tool_call_id': call.get('id'), 'name': name, 'content': json.dumps(tool_result, ensure_ascii=False)})
    else:
        raise RuntimeError('Too many AI tool steps.')

    content = (result or {}).get('choices', [{}])[0].get('message', {}).get('content') or 'I could not complete that request.'
    conversation = ChatbotConversation(
        session_id=session_id,
        patient_id=patient_context().id if role_name() == 'patient' and patient_context() else None,
        message=message, response=content, intent='ai_tool_chat'
    )
    db.session.add(conversation); db.session.commit()
    return content


@chatbot_bp.route('/')
@login_required
def index():
    session_id = get_or_create_session()
    history = ChatbotConversation.query.filter_by(session_id=session_id).order_by(ChatbotConversation.created_at).all()
    return render_template('chatbot/index.html', history=history, title='AI Assistant')


@chatbot_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json(silent=True) or {}
    message = (data.get('message') or '').strip()
    if not message: return jsonify({'error': 'Message is required'}), 400
    session_id = get_or_create_session()
    try:
        response = generate_ai_response(message, session_id)
        return jsonify({'response': response, 'role': role_name(), 'model': current_app.config.get('QWEN_MODEL'), 'timestamp': datetime.utcnow().isoformat()})
    except Exception as exc:
        current_app.logger.exception('AI chatbot error')
        return jsonify({'error': 'The AI service is temporarily unavailable. Check the AI configuration.', 'detail': str(exc) if current_app.debug else None}), 503


@chatbot_bp.route('/api/history')
@login_required
def api_history():
    session_id = get_or_create_session()
    items = ChatbotConversation.query.filter_by(session_id=session_id).order_by(ChatbotConversation.created_at).limit(100).all()
    return jsonify([{'message': x.message, 'response': x.response, 'created_at': x.created_at.isoformat()} for x in items])


@chatbot_bp.route('/api/clear', methods=['POST'])
@login_required
def api_clear_history():
    session_id = get_or_create_session()
    ChatbotConversation.query.filter_by(session_id=session_id).delete()
    db.session.commit(); session['chatbot_session'] = str(uuid.uuid4())
    return jsonify({'message': 'History cleared successfully'})


@chatbot_bp.route('/widget')
@login_required
def widget():
    return render_template('chatbot/widget.html')


@chatbot_bp.route('/api/quick-replies')
@login_required
def api_quick_replies():
    if role_name() == 'doctor':
        return jsonify(['What are my appointments today?', 'Show my schedule', 'Find a patient', 'Show my patients symptoms'])
    return jsonify(['When is my next appointment?', 'Book an appointment', 'Show available slots', 'Cancel my appointment'])

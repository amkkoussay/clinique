"""Private integration endpoints used by n8n.

These endpoints are protected with N8N_API_KEY and are intentionally small.
n8n handles automation; Flask remains the source of truth for clinic data.
"""
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from functools import wraps
from models import db, Appointment, Patient

integration_bp = Blueprint('integration', __name__)


def n8n_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        expected = current_app.config.get('N8N_API_KEY')
        provided = request.headers.get('X-N8N-API-Key') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not expected or provided != expected:
            return jsonify({'error': 'Unauthorized'}), 401
        return fn(*args, **kwargs)
    return wrapped


def apt_json(a):
    return {
        'id': a.id, 'uuid': a.uuid, 'patient_id': a.patient_id,
        'patient_name': a.patient.get_full_name() if a.patient else None,
        'patient_email': a.patient.email if a.patient else None,
        'doctor_id': a.doctor_id, 'doctor_name': a.doctor.get_full_name() if a.doctor else None,
        'date': a.appointment_date.isoformat(), 'start_time': a.start_time.strftime('%H:%M'),
        'end_time': a.end_time.strftime('%H:%M'), 'status': a.status,
        'reason': a.reason, 'type': a.appointment_type,
    }


@integration_bp.route('/reminders/due')
@n8n_auth
def reminders_due():
    timezone_name = current_app.config.get('CLINIC_TIMEZONE', 'Africa/Tunis')
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo('UTC')
    now = datetime.now(tz).replace(tzinfo=None)
    start = now + timedelta(hours=23, minutes=30)
    end = now + timedelta(hours=24, minutes=30)
    candidates = Appointment.query.filter(
        Appointment.status.in_(['scheduled', 'confirmed']),
        Appointment.appointment_date >= date.today(),
        Appointment.reminder_sent.is_(False),
    ).all()
    due = []
    for a in candidates:
        appointment_dt = datetime.combine(a.appointment_date, a.start_time)
        if start <= appointment_dt <= end:
            due.append(apt_json(a))
    return jsonify({'count': len(due), 'appointments': due})


@integration_bp.route('/reminders/<int:appointment_id>/sent', methods=['POST'])
@n8n_auth
def reminder_sent(appointment_id):
    a = Appointment.query.get_or_404(appointment_id)
    a.reminder_sent = True
    a.reminder_sent_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'ok': True, 'appointment_id': a.id})


@integration_bp.route('/appointments/<int:appointment_id>')
@n8n_auth
def appointment(appointment_id):
    return jsonify(apt_json(Appointment.query.get_or_404(appointment_id)))

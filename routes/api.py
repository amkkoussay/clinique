"""
Clinic Management Platform - API Routes
=======================================
REST API endpoints for AJAX requests and external integrations.
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_

from models import (
    db, User, Patient, Appointment, MedicalRecord, Prescription,
    Invoice, Payment, VitalSigns, LabTest, Service, Medicine, Task
)

api_bp = Blueprint('api', __name__)


@api_bp.route('/stats/dashboard')
@login_required
def dashboard_stats():
    """Get dashboard statistics."""
    today = date.today()
    start_of_month = today.replace(day=1)
    
    stats = {
        'patients': {
            'total': Patient.query.filter_by(is_active=True).count(),
            'new_this_month': Patient.query.filter(
                func.strftime('%Y-%m', Patient.created_at) == today.strftime('%Y-%m')
            ).count()
        },
        'appointments': {
            'today': Appointment.query.filter_by(appointment_date=today).count(),
            'upcoming': Appointment.query.filter(
                Appointment.appointment_date >= today,
                Appointment.status.in_(['scheduled', 'confirmed'])
            ).count()
        },
        'revenue': {
            'today': float(db.session.query(func.sum(Invoice.paid_amount)).filter(
                Invoice.invoice_date == today
            ).scalar() or 0),
            'month': float(db.session.query(func.sum(Invoice.paid_amount)).filter(
                Invoice.invoice_date >= start_of_month
            ).scalar() or 0)
        },
        'pending_tasks': Task.query.filter(
            Task.assigned_to == current_user.id,
            Task.status.in_(['pending', 'in_progress'])
        ).count() if not current_user.is_admin() else Task.query.filter(
            Task.status.in_(['pending', 'in_progress'])
        ).count()
    }
    
    return jsonify(stats)


@api_bp.route('/patients/search')
@login_required
def search_patients():
    """Search patients API."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    patients = Patient.query.filter(
        and_(
            db.or_(
                Patient.first_name.ilike(f'%{query}%'),
                Patient.last_name.ilike(f'%{query}%'),
                Patient.patient_id.ilike(f'%{query}%'),
                Patient.phone.ilike(f'%{query}%')
            ),
            Patient.is_active == True
        )
    ).limit(limit).all()
    
    return jsonify([{
        'id': p.id,
        'patient_id': p.patient_id,
        'name': p.get_full_name(),
        'phone': p.phone,
        'email': p.email,
        'age': p.get_age(),
        'gender': p.gender
    } for p in patients])


@api_bp.route('/patients/<int:patient_id>')
@login_required
def get_patient(patient_id):
    """Get patient details API."""
    patient = Patient.query.get_or_404(patient_id)
    
    return jsonify({
        'id': patient.id,
        'patient_id': patient.patient_id,
        'first_name': patient.first_name,
        'last_name': patient.last_name,
        'full_name': patient.get_full_name(),
        'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        'age': patient.get_age(),
        'gender': patient.gender,
        'blood_type': patient.blood_type,
        'phone': patient.phone,
        'email': patient.email,
        'address': patient.address,
        'allergies': patient.get_allergies_list(),
        'chronic_conditions': patient.get_chronic_conditions_list(),
        'insurance_provider': patient.insurance_provider
    })


@api_bp.route('/patients/<int:patient_id>/vital-signs')
@login_required
def get_patient_vital_signs(patient_id):
    """Get patient vital signs history."""
    vital_signs = VitalSigns.query.filter_by(
        patient_id=patient_id
    ).order_by(VitalSigns.recorded_at.desc()).limit(20).all()
    
    return jsonify([{
        'id': v.id,
        'recorded_at': v.recorded_at.isoformat(),
        'height_cm': v.height_cm,
        'weight_kg': v.weight_kg,
        'bmi': v.bmi,
        'temperature': v.temperature_celsius,
        'blood_pressure': v.get_blood_pressure(),
        'heart_rate': v.heart_rate,
        'oxygen_saturation': v.oxygen_saturation,
        'blood_glucose': v.blood_glucose
    } for v in vital_signs])


@api_bp.route('/appointments/upcoming')
@login_required
def upcoming_appointments():
    """Get upcoming appointments."""
    today = date.today()
    limit = request.args.get('limit', 10, type=int)
    
    query = Appointment.query.filter(
        Appointment.appointment_date >= today,
        Appointment.status.in_(['scheduled', 'confirmed'])
    )
    
    if current_user.is_doctor():
        query = query.filter_by(doctor_id=current_user.id)
    
    appointments = query.order_by(
        Appointment.appointment_date,
        Appointment.start_time
    ).limit(limit).all()
    
    return jsonify([{
        'id': apt.id,
        'uuid': apt.uuid,
        'patient_id': apt.patient_id,
        'patient_name': apt.patient.get_full_name(),
        'doctor_name': apt.doctor.get_full_name(),
        'date': apt.appointment_date.isoformat(),
        'start_time': apt.start_time.strftime('%H:%M'),
        'end_time': apt.end_time.strftime('%H:%M'),
        'status': apt.status,
        'type': apt.appointment_type,
        'reason': apt.reason
    } for apt in appointments])


@api_bp.route('/appointments/today')
@login_required
def today_appointments():
    """Get today's appointments."""
    today = date.today()
    
    query = Appointment.query.filter_by(appointment_date=today)
    
    if current_user.is_doctor():
        query = query.filter_by(doctor_id=current_user.id)
    
    appointments = query.order_by(Appointment.start_time).all()
    
    return jsonify([{
        'id': apt.id,
        'patient_name': apt.patient.get_full_name(),
        'start_time': apt.start_time.strftime('%H:%M'),
        'end_time': apt.end_time.strftime('%H:%M'),
        'status': apt.status,
        'type': apt.appointment_type
    } for apt in appointments])


@api_bp.route('/doctors/available-slots')
@login_required
def get_available_slots():
    """Get available time slots for a doctor."""
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')
    
    if not doctor_id or not date_str:
        return jsonify({'error': 'Doctor ID and date required'}), 400
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get existing appointments
    existing = Appointment.query.filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == selected_date,
            Appointment.status.notin_(['cancelled'])
        )
    ).all()
    
    # Generate time slots
    slots = []
    start_time = datetime.strptime('09:00', '%H:%M')
    end_time = datetime.strptime('17:00', '%H:%M')
    
    current = start_time
    while current < end_time:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=30)).time()
        
        is_available = True
        for apt in existing:
            if apt.start_time < slot_end and apt.end_time > slot_start:
                is_available = False
                break
        
        slots.append({
            'start': slot_start.strftime('%H:%M'),
            'end': slot_end.strftime('%H:%M'),
            'available': is_available
        })
        
        current += timedelta(minutes=30)
    
    return jsonify(slots)


@api_bp.route('/medicines/search')
@login_required
def search_medicines():
    """Search medicines API."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    medicines = Medicine.query.filter(
        and_(
            db.or_(
                Medicine.name.ilike(f'%{query}%'),
                Medicine.generic_name.ilike(f'%{query}%')
            ),
            Medicine.is_active == True
        )
    ).limit(limit).all()
    
    return jsonify([{
        'id': m.id,
        'name': m.name,
        'generic_name': m.generic_name,
        'category': m.category,
        'default_dosage': m.default_dosage,
        'dosage_forms': m.get_dosage_forms_list()
    } for m in medicines])


@api_bp.route('/services/search')
@login_required
def search_services():
    """Search services API."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 10, type=int)
    
    if len(query) < 2:
        return jsonify([])
    
    services = Service.query.filter(
        and_(
            Service.service_name.ilike(f'%{query}%'),
            Service.is_active == True
        )
    ).limit(limit).all()
    
    return jsonify([{
        'id': s.id,
        'service_code': s.service_code,
        'service_name': s.service_name,
        'category': s.category,
        'default_price': s.default_price
    } for s in services])


@api_bp.route('/reports/revenue')
@login_required
def revenue_report():
    """Get revenue report data."""
    period = request.args.get('period', 'month')  # day, week, month, year
    
    today = date.today()
    
    if period == 'day':
        # Last 30 days
        start_date = today - timedelta(days=30)
        date_format = '%Y-%m-%d'
        group_by = func.date(Invoice.invoice_date)
    elif period == 'week':
        # Last 12 weeks
        start_date = today - timedelta(weeks=12)
        date_format = '%Y-W%W'
        group_by = func.strftime('%Y-W%W', Invoice.invoice_date)
    elif period == 'year':
        # Last 5 years
        start_date = today.replace(year=today.year - 5)
        date_format = '%Y'
        group_by = func.strftime('%Y', Invoice.invoice_date)
    else:  # month
        # Last 12 months
        start_date = today.replace(day=1) - timedelta(days=365)
        date_format = '%Y-%m'
        group_by = func.strftime('%Y-%m', Invoice.invoice_date)
    
    revenue_data = db.session.query(
        group_by.label('period'),
        func.sum(Invoice.paid_amount).label('revenue'),
        func.count(Invoice.id).label('count')
    ).filter(
        Invoice.invoice_date >= start_date
    ).group_by(group_by).order_by(group_by).all()
    
    return jsonify([{
        'period': r.period,
        'revenue': float(r.revenue or 0),
        'invoice_count': r.count
    } for r in revenue_data])


@api_bp.route('/reports/patient-visits')
@login_required
def patient_visits_report():
    """Get patient visits report."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    visits = db.session.query(
        func.date(Appointment.appointment_date).label('date'),
        func.count(Appointment.id).label('count')
    ).filter(
        Appointment.appointment_date >= start,
        Appointment.appointment_date <= end
    ).group_by(func.date(Appointment.appointment_date)).order_by('date').all()
    
    return jsonify([{
        'date': v.date.isoformat(),
        'visits': v.count
    } for v in visits])


@api_bp.route('/notifications/unread-count')
@login_required
def unread_notifications_count():
    """Get unread notifications count."""
    from models import Notification
    
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify({'count': count})


@api_bp.route('/tasks/pending')
@login_required
def pending_tasks():
    """Get pending tasks."""
    limit = request.args.get('limit', 5, type=int)
    
    query = Task.query.filter(
        Task.status.in_(['pending', 'in_progress'])
    )
    
    if not current_user.is_admin():
        query = query.filter_by(assigned_to=current_user.id)
    
    tasks = query.order_by(Task.due_date).limit(limit).all()
    
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'priority': t.priority,
        'status': t.status,
        'due_date': t.due_date.isoformat() if t.due_date else None
    } for t in tasks])


@api_bp.route('/system/health')
def system_health():
    """System health check endpoint."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    return jsonify({
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'database': db_status,
        'timestamp': datetime.utcnow().isoformat()
    })

"""
Clinic Management Platform - Appointment Routes
===============================================
Routes for appointment scheduling and management.
"""

from flask import abort, Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import and_

from models import db, Appointment, Patient, User, AuditLog, Notification
from forms import AppointmentForm
from decorators import role_required

appointments_bp = Blueprint('appointments', __name__)


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


def create_notification(user_id, title, message, notification_type='info', link=None):
    """Create notification for user."""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link
    )
    db.session.add(notification)
    db.session.commit()


@appointments_bp.route('/')
@login_required
def index():
    """Appointment list route."""
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', date.today().isoformat())
    status_filter = request.args.get('status', 'all')
    doctor_filter = request.args.get('doctor', 'all')
    
    query = Appointment.query
    # Doctors can only see their own appointments.
    if current_user.is_doctor():
        query = query.filter(Appointment.doctor_id == current_user.id)
    
    # Apply filters
    if date_filter:
        query = query.filter(Appointment.appointment_date == date_filter)
    
    if status_filter != 'all':
        query = query.filter(Appointment.status == status_filter)
    
    if doctor_filter != 'all':
        query = query.filter(Appointment.doctor_id == int(doctor_filter))
    
    appointments = query.order_by(Appointment.start_time).paginate(
        page=page, per_page=15, error_out=False
    )
    
    # Get doctors for filter
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    
    return render_template('appointments/index.html',
                         appointments=appointments,
                         doctors=doctors,
                         date_filter=date_filter,
                         status_filter=status_filter,
                         doctor_filter=doctor_filter,
                         title='Appointments')


@appointments_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def create():
    """Create appointment route."""
    form = AppointmentForm()
    
    # Populate patient choices
    form.patient_id.choices = [(p.id, f"{p.patient_id} - {p.get_full_name()}") 
                               for p in Patient.query.filter_by(is_active=True).all()]
    
    # Populate doctor choices
    form.doctor_id.choices = [(d.id, f"Dr. {d.get_full_name()}") 
                              for d in User.query.filter_by(role='doctor', is_active=True).all()]
    
    if form.validate_on_submit():
        # Check for conflicts
        conflict = Appointment.query.filter(
            and_(
                Appointment.doctor_id == form.doctor_id.data,
                Appointment.appointment_date == form.appointment_date.data,
                Appointment.status.notin_(['cancelled', 'completed']),
                Appointment.start_time < form.end_time.data,
                Appointment.end_time > form.start_time.data
            )
        ).first()
        
        if conflict:
            flash('This time slot conflicts with another appointment.', 'error')
            return render_template('appointments/create.html', form=form, title='New Appointment')
        
        appointment = Appointment(
            patient_id=form.patient_id.data,
            doctor_id=form.doctor_id.data,
            appointment_date=form.appointment_date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            appointment_type=form.appointment_type.data,
            status=form.status.data,
            reason=form.reason.data,
            notes=form.notes.data,
            is_recurring=form.is_recurring.data,
            recurring_pattern=form.recurring_pattern.data if form.is_recurring.data else None,
            created_by=current_user.id
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Create notification for doctor
        create_notification(
            appointment.doctor_id,
            'New Appointment',
            f"New appointment scheduled with {appointment.patient.get_full_name()} on {appointment.appointment_date}",
            link=url_for('appointments.view', appointment_id=appointment.id)
        )
        
        log_action('create', 'Appointment', appointment.id, 
                  f"Created appointment for {appointment.patient.get_full_name()}")
        
        flash('Appointment created successfully.', 'success')
        
        # Handle recurring appointments
        if form.is_recurring.data and form.recurring_pattern.data:
            create_recurring_appointments(appointment, form.recurring_pattern.data)
        
        return redirect(url_for('appointments.index'))
    
    # Pre-fill from query parameters
    if request.args.get('patient_id'):
        form.patient_id.data = int(request.args.get('patient_id'))
    if request.args.get('date'):
        form.appointment_date.data = datetime.strptime(request.args.get('date'), '%Y-%m-%d').date()
    
    return render_template('appointments/create.html', form=form, title='New Appointment')


def create_recurring_appointments(base_appointment, pattern):
    """Create recurring appointments based on pattern."""
    appointments_created = 0
    current_date = base_appointment.appointment_date
    
    # Create 10 recurring appointments
    for _ in range(10):
        if pattern == 'daily':
            current_date += timedelta(days=1)
        elif pattern == 'weekly':
            current_date += timedelta(weeks=1)
        elif pattern == 'biweekly':
            current_date += timedelta(weeks=2)
        elif pattern == 'monthly':
            # Add one month (approximate)
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        else:
            break
        
        # Check for conflicts
        conflict = Appointment.query.filter(
            and_(
                Appointment.doctor_id == base_appointment.doctor_id,
                Appointment.appointment_date == current_date,
                Appointment.status.notin_(['cancelled', 'completed']),
                Appointment.start_time < base_appointment.end_time,
                Appointment.end_time > base_appointment.start_time
            )
        ).first()
        
        if not conflict:
            new_appointment = Appointment(
                patient_id=base_appointment.patient_id,
                doctor_id=base_appointment.doctor_id,
                appointment_date=current_date,
                start_time=base_appointment.start_time,
                end_time=base_appointment.end_time,
                appointment_type=base_appointment.appointment_type,
                status='scheduled',
                reason=base_appointment.reason,
                notes=f"Recurring appointment (from {base_appointment.uuid})",
                is_recurring=True,
                recurring_pattern=pattern,
                created_by=current_user.id
            )
            db.session.add(new_appointment)
            appointments_created += 1
    
    db.session.commit()
    
    if appointments_created > 0:
        flash(f'{appointments_created} recurring appointments created.', 'info')


@appointments_bp.route('/<int:appointment_id>')
@login_required
def view(appointment_id):
    """View appointment details."""
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.is_doctor() and appointment.doctor_id != current_user.id:
        abort(403)
    return render_template('appointments/view.html', 
                         appointment=appointment, 
                         title='Appointment Details')


@appointments_bp.route('/<int:appointment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'receptionist')
def edit(appointment_id):
    """Edit appointment route."""
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.is_doctor() and appointment.doctor_id != current_user.id:
        abort(403)
    form = AppointmentForm(obj=appointment)
    
    # Populate choices
    form.patient_id.choices = [(p.id, f"{p.patient_id} - {p.get_full_name()}") 
                               for p in Patient.query.filter_by(is_active=True).all()]
    form.doctor_id.choices = [(d.id, f"Dr. {d.get_full_name()}") 
                              for d in User.query.filter_by(role='doctor', is_active=True).all()]
    
    if form.validate_on_submit():
        # Check for conflicts (excluding current appointment)
        conflict = Appointment.query.filter(
            and_(
                Appointment.doctor_id == form.doctor_id.data,
                Appointment.appointment_date == form.appointment_date.data,
                Appointment.status.notin_(['cancelled', 'completed']),
                Appointment.start_time < form.end_time.data,
                Appointment.end_time > form.start_time.data,
                Appointment.id != appointment_id
            )
        ).first()
        
        if conflict:
            flash('This time slot conflicts with another appointment.', 'error')
            return render_template('appointments/edit.html', 
                                 form=form, 
                                 appointment=appointment, 
                                 title='Edit Appointment')
        
        appointment.patient_id = form.patient_id.data
        appointment.doctor_id = form.doctor_id.data
        appointment.appointment_date = form.appointment_date.data
        appointment.start_time = form.start_time.data
        appointment.end_time = form.end_time.data
        appointment.appointment_type = form.appointment_type.data
        appointment.status = form.status.data
        appointment.reason = form.reason.data
        appointment.notes = form.notes.data
        appointment.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_action('update', 'Appointment', appointment.id, 
                  f"Updated appointment for {appointment.patient.get_full_name()}")
        
        flash('Appointment updated successfully.', 'success')
        return redirect(url_for('appointments.view', appointment_id=appointment_id))
    
    return render_template('appointments/edit.html', 
                         form=form, 
                         appointment=appointment, 
                         title='Edit Appointment')


@appointments_bp.route('/<int:appointment_id>/cancel', methods=['POST', 'PUT'])
@login_required
@role_required('admin', 'receptionist')
def cancel(appointment_id):
    """Cancel appointment route."""
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.is_doctor() and appointment.doctor_id != current_user.id:
        abort(403)
    
    appointment.status = 'cancelled'
    appointment.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_action('cancel', 'Appointment', appointment.id, 
              f"Cancelled appointment for {appointment.patient.get_full_name()}")
    
    if request.method == 'PUT':
        return jsonify({
            'ok': True,
            'appointment_id': appointment.id,
            'status': appointment.status,
            'message': 'Appointment cancelled successfully.'
        })

    flash('Appointment cancelled successfully.', 'success')
    return redirect(url_for('appointments.index'))


@appointments_bp.route('/<int:appointment_id>/status/<status>', methods=['POST', 'PUT'])
@login_required
def update_status(appointment_id, status):
    """Update appointment status."""
    appointment = Appointment.query.get_or_404(appointment_id)
    if current_user.is_doctor() and appointment.doctor_id != current_user.id:
        abort(403)
    
    valid_statuses = ['scheduled', 'confirmed', 'in_progress', 'completed', 'cancelled', 'no_show']
    
    if status not in valid_statuses:
        flash('Invalid status.', 'error')
        return redirect(url_for('appointments.view', appointment_id=appointment_id))
    
    appointment.status = status
    appointment.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_action('update', 'Appointment', appointment.id, 
              f"Changed status to {status}")
    
    if request.method == 'PUT':
        return jsonify({
            'ok': True,
            'appointment_id': appointment.id,
            'status': appointment.status,
            'message': f"Appointment status updated to {status.replace('_', ' ').title()}."
        })

    flash(f"Appointment status updated to {status.replace('_', ' ').title()}.", 'success')
    return redirect(url_for('appointments.view', appointment_id=appointment_id))


@appointments_bp.route('/waiting-room')
@login_required
@role_required('admin', 'doctor', 'receptionist')
def waiting_room():
    """Waiting room display route."""
    today = date.today()
    
    # Doctors get their own waiting room; clinic staff/admin can view the full clinic queue.
    waiting_query = Appointment.query.filter(Appointment.appointment_date == today)
    if current_user.is_doctor():
        waiting_query = waiting_query.filter(Appointment.doctor_id == current_user.id)
    appointments = waiting_query.order_by(Appointment.start_time).all()
    
    # Group by status
    waiting = [a for a in appointments if a.status == 'confirmed']
    in_progress = [a for a in appointments if a.status == 'in_progress']
    completed = [a for a in appointments if a.status == 'completed']
    
    return render_template('appointments/waiting_room.html',
                         waiting=waiting,
                         in_progress=in_progress,
                         completed=completed,
                         today=today,
                         title='Waiting Room')


@appointments_bp.route('/api/available-slots')
@login_required
def api_available_slots():
    """API endpoint for available time slots."""
    doctor_id = request.args.get('doctor_id', type=int)
    date_str = request.args.get('date')
    
    if not doctor_id or not date_str:
        return jsonify({'error': 'Doctor ID and date required'}), 400
    
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    
    # Get existing appointments for the doctor on that date
    existing = Appointment.query.filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == selected_date,
            Appointment.status.notin_(['cancelled'])
        )
    ).all()
    
    # Generate time slots (9 AM to 5 PM, 30 min intervals)
    slots = []
    start_time = datetime.strptime('09:00', '%H:%M').time()
    end_time = datetime.strptime('17:00', '%H:%M').time()
    
    current = datetime.combine(selected_date, start_time)
    end = datetime.combine(selected_date, end_time)
    
    while current < end:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=30)).time()
        
        # Check if slot is available
        is_available = True
        for apt in existing:
            if (apt.start_time < slot_end and apt.end_time > slot_start):
                is_available = False
                break
        
        slots.append({
            'start': slot_start.strftime('%H:%M'),
            'end': slot_end.strftime('%H:%M'),
            'available': is_available
        })
        
        current += timedelta(minutes=30)
    
    return jsonify(slots)


@appointments_bp.route('/api/doctor-schedule/<int:doctor_id>')
@login_required
def api_doctor_schedule(doctor_id):
    """API endpoint for doctor's schedule."""
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    query = Appointment.query.filter_by(doctor_id=doctor_id)
    
    if start_date:
        query = query.filter(Appointment.appointment_date >= start_date)
    if end_date:
        query = query.filter(Appointment.appointment_date <= end_date)
    
    appointments = query.all()
    
    return jsonify([{
        'id': apt.id,
        'patient_name': apt.patient.get_full_name(),
        'date': apt.appointment_date.isoformat(),
        'start_time': apt.start_time.strftime('%H:%M'),
        'end_time': apt.end_time.strftime('%H:%M'),
        'status': apt.status,
        'type': apt.appointment_type
    } for apt in appointments])

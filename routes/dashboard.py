"""
Clinic Management Platform - Dashboard Routes
=============================================
Routes for the main dashboard and overview pages.
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_

from models import (
    db, User, Patient, Appointment, MedicalRecord, Prescription,
    Invoice, Payment, VitalSigns, Task, Notification, AuditLog
)

dashboard_bp = Blueprint('dashboard', __name__)


def month_bounds(value):
    """Return an inclusive start and exclusive end for a calendar month."""
    start = value.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1)
    return start, end


@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard route."""
    today = date.today()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    current_month_start, current_month_end = month_bounds(today)
    
    # Statistics
    stats = {
        'total_patients': Patient.query.filter_by(is_active=True).count(),
        'today_appointments': (
            Appointment.query.filter(
                Appointment.appointment_date == today,
                Appointment.doctor_id == current_user.id
            ).count() if current_user.is_doctor() else Appointment.query.filter(
                Appointment.appointment_date == today
            ).count()
        ),
        'pending_appointments': Appointment.query.filter(
            Appointment.appointment_date >= today,
            Appointment.status.in_(['scheduled', 'confirmed'])
        ).count(),
        'monthly_revenue': db.session.query(
            func.sum(Invoice.paid_amount)
        ).filter(
            Invoice.invoice_date >= current_month_start,
            Invoice.invoice_date < current_month_end
        ).scalar() or 0,
        'pending_tasks': Task.query.filter(
            Task.assigned_to == current_user.id,
            Task.status.in_(['pending', 'in_progress'])
        ).count() if not current_user.is_admin() else Task.query.filter(
            Task.status.in_(['pending', 'in_progress'])
        ).count()
    }
    
    # Today's appointments: doctors only see their own; admin/reception see the clinic list.
    appointments_query = Appointment.query.filter(Appointment.appointment_date == today)
    if current_user.is_doctor():
        appointments_query = appointments_query.filter(Appointment.doctor_id == current_user.id)
    today_appointments = appointments_query.order_by(Appointment.start_time).limit(10).all()
    
    # Recent patients
    recent_patients = Patient.query.order_by(
        Patient.created_at.desc()
    ).limit(5).all()
    
    # Pending tasks
    pending_tasks = Task.query.filter(
        Task.assigned_to == current_user.id,
        Task.status.in_(['pending', 'in_progress'])
    ).order_by(Task.due_date).limit(5).all() if not current_user.is_admin() else Task.query.filter(
        Task.status.in_(['pending', 'in_progress'])
    ).order_by(Task.due_date).limit(5).all()
    
    # Notifications
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).limit(5).all()
    
    # Recent activity
    recent_activity = AuditLog.query.order_by(
        AuditLog.created_at.desc()
    ).limit(10).all()
    
    # Weekly appointment data: doctors only see their own appointments; clinic staff see all.
    week_start = today - timedelta(days=today.weekday())
    weekly_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        weekly_query = Appointment.query.filter(Appointment.appointment_date == day)
        if current_user.is_doctor():
            weekly_query = weekly_query.filter(Appointment.doctor_id == current_user.id)
        count = weekly_query.count()
        weekly_data.append({
            'day': day.strftime('%a'),
            'count': count
        })
    
    # Revenue data for chart (last 6 months)
    revenue_data = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i*30)
        month_start, month_end = month_bounds(month_date)
        revenue = db.session.query(func.sum(Invoice.paid_amount)).filter(
            Invoice.invoice_date >= month_start,
            Invoice.invoice_date < month_end
        ).scalar() or 0
        revenue_data.append({
            'month': month_date.strftime('%b'),
            'revenue': float(revenue)
        })
    
    return render_template(
        'dashboard/index.html',
        title='Dashboard',
        stats=stats,
        today_appointments=today_appointments,
        recent_patients=recent_patients,
        pending_tasks=pending_tasks,
        notifications=notifications,
        recent_activity=recent_activity,
        weekly_data=weekly_data,
        revenue_data=revenue_data,
        today=today
    )


@dashboard_bp.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for dashboard statistics."""
    today = date.today()
    
    stats = {
        'total_patients': Patient.query.filter_by(is_active=True).count(),
        'today_appointments': (
            Appointment.query.filter(
                Appointment.appointment_date == today,
                Appointment.doctor_id == current_user.id
            ).count() if current_user.is_doctor() else Appointment.query.filter(
                Appointment.appointment_date == today
            ).count()
        ),
        'pending_tasks': Task.query.filter(
            Task.assigned_to == current_user.id,
            Task.status.in_(['pending', 'in_progress'])
        ).count() if not current_user.is_admin() else Task.query.filter(
            Task.status.in_(['pending', 'in_progress'])
        ).count(),
        'monthly_revenue': float(db.session.query(
            func.sum(Invoice.paid_amount)
        ).filter(
            Invoice.invoice_date >= month_bounds(today)[0],
            Invoice.invoice_date < month_bounds(today)[1]
        ).scalar() or 0)
    }
    
    return jsonify(stats)


@dashboard_bp.route('/api/appointments/today')
@login_required
def api_today_appointments():
    """API endpoint for today's appointments."""
    today = date.today()
    
    appointments_query = Appointment.query.filter(Appointment.appointment_date == today)
    if current_user.is_doctor():
        appointments_query = appointments_query.filter(Appointment.doctor_id == current_user.id)
    appointments = appointments_query.order_by(Appointment.start_time).all()
    
    return jsonify([{
        'id': apt.id,
        'uuid': apt.uuid,
        'patient_name': apt.patient.get_full_name(),
        'doctor_name': apt.doctor.get_full_name(),
        'start_time': apt.start_time.strftime('%H:%M'),
        'end_time': apt.end_time.strftime('%H:%M'),
        'status': apt.status,
        'type': apt.appointment_type,
        'reason': apt.reason
    } for apt in appointments])


@dashboard_bp.route('/notifications')
@login_required
def notifications():
    """Notifications page."""
    page = request.args.get('page', 1, type=int)
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('dashboard/notifications.html', 
                         notifications=notifications, 
                         title='Notifications')


@dashboard_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark notification as read."""
    from flask import redirect, url_for, flash
    
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.notifications'))
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    if notification.link:
        return redirect(notification.link)
    
    return redirect(url_for('dashboard.notifications'))


@dashboard_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read."""
    from flask import redirect, url_for, flash
    
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({
        'is_read': True,
        'read_at': datetime.utcnow()
    })
    db.session.commit()
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('dashboard.notifications'))


@dashboard_bp.route('/tasks')
@login_required
def tasks():
    """Tasks page."""
    from flask import request
    
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    
    query = Task.query
    
    if not current_user.is_admin():
        query = query.filter_by(assigned_to=current_user.id)
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    tasks = query.order_by(Task.due_date).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('dashboard/tasks.html', 
                         tasks=tasks, 
                         status_filter=status_filter,
                         title='Tasks')


@dashboard_bp.route('/tasks/<int:task_id>/complete', methods=['POST'])
@login_required
def complete_task(task_id):
    """Mark task as complete."""
    from flask import redirect, url_for, flash
    
    task = Task.query.get_or_404(task_id)
    
    if task.assigned_to != current_user.id and not current_user.is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.tasks'))
    
    task.status = 'completed'
    task.completed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Task completed successfully.', 'success')
    return redirect(url_for('dashboard.tasks'))


@dashboard_bp.route('/calendar')
@login_required
def calendar():
    """Full calendar view."""
    return render_template('dashboard/calendar.html', title='Calendar')


@dashboard_bp.route('/api/calendar/events')
@login_required
def api_calendar_events():
    """API endpoint for calendar events."""
    from flask import request
    
    start = request.args.get('start')
    end = request.args.get('end')
    
    query = Appointment.query
    
    if start:
        query = query.filter(Appointment.appointment_date >= start)
    if end:
        query = query.filter(Appointment.appointment_date <= end)
    
    appointments = query.all()
    
    events = []
    for apt in appointments:
        events.append({
            'id': apt.uuid,
            'title': f"{apt.patient.get_full_name()} - {apt.appointment_type}",
            'start': f"{apt.appointment_date}T{apt.start_time}",
            'end': f"{apt.appointment_date}T{apt.end_time}",
            'status': apt.status,
            'url': f"/appointments/{apt.id}",
            'color': get_appointment_color(apt.status)
        })
    
    return jsonify(events)


def get_appointment_color(status):
    """Get color for appointment status."""
    colors = {
        'scheduled': '#3b82f6',
        'confirmed': '#06b6d4',
        'in_progress': '#f59e0b',
        'completed': '#10b981',
        'cancelled': '#ef4444',
        'no_show': '#6b7280'
    }
    return colors.get(status, '#3b82f6')


# Import request at the end to avoid circular imports
from flask import request

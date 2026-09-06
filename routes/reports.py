"""
Clinic Management Platform - Reports Routes
===========================================
Routes for generating various reports and analytics.
"""

from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import io
import csv

from models import db, Patient, Appointment, MedicalRecord, Invoice, Payment, LabTest, User

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    """Reports dashboard."""
    return render_template('reports/index.html', title='Reports')


@reports_bp.route('/patients')
@login_required
def patient_report():
    """Patient statistics report."""
    # Patient demographics
    gender_stats = db.session.query(
        Patient.gender,
        func.count(Patient.id).label('count')
    ).filter_by(is_active=True).group_by(Patient.gender).all()
    
    blood_type_stats = db.session.query(
        Patient.blood_type,
        func.count(Patient.id).label('count')
    ).filter_by(is_active=True).group_by(Patient.blood_type).all()
    
    # New patients by month
    today = date.today()
    new_patients = db.session.query(
        func.strftime('%Y-%m', Patient.created_at).label('month'),
        func.count(Patient.id).label('count')
    ).filter(
        Patient.created_at >= today - timedelta(days=365)
    ).group_by('month').order_by('month').all()
    
    # Age distribution
    age_groups = {
        '0-18': 0,
        '19-35': 0,
        '36-50': 0,
        '51-65': 0,
        '65+': 0
    }
    
    patients = Patient.query.filter_by(is_active=True).all()
    for patient in patients:
        age = patient.get_age()
        if age <= 18:
            age_groups['0-18'] += 1
        elif age <= 35:
            age_groups['19-35'] += 1
        elif age <= 50:
            age_groups['36-50'] += 1
        elif age <= 65:
            age_groups['51-65'] += 1
        else:
            age_groups['65+'] += 1
    
    return render_template('reports/patients.html',
                         gender_stats=gender_stats,
                         blood_type_stats=blood_type_stats,
                         new_patients=new_patients,
                         age_groups=age_groups,
                         total_patients=len(patients),
                         title='Patient Report')


@reports_bp.route('/appointments')
@login_required
def appointment_report():
    """Appointment statistics report."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Appointments by status
    status_stats = db.session.query(
        Appointment.status,
        func.count(Appointment.id).label('count')
    ).filter(
        Appointment.appointment_date >= start,
        Appointment.appointment_date <= end
    ).group_by(Appointment.status).all()
    
    # Appointments by type
    type_stats = db.session.query(
        Appointment.appointment_type,
        func.count(Appointment.id).label('count')
    ).filter(
        Appointment.appointment_date >= start,
        Appointment.appointment_date <= end
    ).group_by(Appointment.appointment_type).all()
    
    # Appointments by doctor
    doctor_stats = db.session.query(
        func.concat(User.first_name, ' ', User.last_name).label('doctor_name'),
        func.count(Appointment.id).label('count')
    ).join(User, Appointment.doctor_id == User.id).filter(
        Appointment.appointment_date >= start,
        Appointment.appointment_date <= end
    ).group_by('doctor_name').all()
    
    # Daily appointment counts
    daily_counts = db.session.query(
        func.date(Appointment.appointment_date).label('date'),
        func.count(Appointment.id).label('count')
    ).filter(
        Appointment.appointment_date >= start,
        Appointment.appointment_date <= end
    ).group_by(func.date(Appointment.appointment_date)).order_by('date').all()
    
    return render_template('reports/appointments.html',
                         start_date=start_date,
                         end_date=end_date,
                         status_stats=status_stats,
                         type_stats=type_stats,
                         doctor_stats=doctor_stats,
                         daily_counts=daily_counts,
                         title='Appointment Report')


@reports_bp.route('/financial')
@login_required
def financial_report():
    """Financial report."""
    if not current_user.is_admin():
        return render_template('errors/403.html'), 403
    
    period = request.args.get('period', 'month')
    
    today = date.today()
    
    if period == 'day':
        start_date = today - timedelta(days=30)
        group_by = func.date(Invoice.invoice_date)
        date_format = '%Y-%m-%d'
    elif period == 'year':
        start_date = today.replace(year=today.year - 5)
        group_by = func.strftime('%Y', Invoice.invoice_date)
        date_format = '%Y'
    else:  # month
        start_date = today.replace(day=1) - timedelta(days=365)
        group_by = func.strftime('%Y-%m', Invoice.invoice_date)
        date_format = '%Y-%m'
    
    # Revenue by period
    revenue_data = db.session.query(
        group_by.label('period'),
        func.sum(Invoice.total_amount).label('total'),
        func.sum(Invoice.paid_amount).label('paid'),
        func.sum(Invoice.balance_due).label('outstanding'),
        func.count(Invoice.id).label('count')
    ).filter(
        Invoice.invoice_date >= start_date
    ).group_by(group_by).order_by(group_by).all()
    
    # Payment methods
    payment_methods = db.session.query(
        Payment.payment_method,
        func.sum(Payment.amount).label('total')
    ).filter(
        Payment.payment_date >= start_date
    ).group_by(Payment.payment_method).all()
    
    # Summary
    total_revenue = sum(r.paid for r in revenue_data) if revenue_data else 0
    total_outstanding = db.session.query(func.sum(Invoice.balance_due)).filter(
        Invoice.status.in_(['pending', 'partial', 'overdue'])
    ).scalar() or 0
    
    return render_template('reports/financial.html',
                         period=period,
                         revenue_data=revenue_data,
                         payment_methods=payment_methods,
                         total_revenue=total_revenue,
                         total_outstanding=total_outstanding,
                         title='Financial Report')


@reports_bp.route('/medical')
@login_required
def medical_report():
    """Medical statistics report."""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = (date.today() - timedelta(days=90)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Common diagnoses
    diagnoses = db.session.query(
        MedicalRecord.primary_diagnosis,
        func.count(MedicalRecord.id).label('count')
    ).filter(
        MedicalRecord.visit_date >= start,
        MedicalRecord.visit_date <= end,
        MedicalRecord.primary_diagnosis.isnot(None)
    ).group_by(MedicalRecord.primary_diagnosis).order_by(func.count(MedicalRecord.id).desc()).limit(10).all()
    
    # Lab tests by category
    lab_categories = db.session.query(
        LabTest.test_category,
        func.count(LabTest.id).label('count')
    ).filter(
        LabTest.ordered_date >= start,
        LabTest.ordered_date <= end
    ).group_by(LabTest.test_category).all()
    
    # Lab test status
    lab_status = db.session.query(
        LabTest.status,
        func.count(LabTest.id).label('count')
    ).filter(
        LabTest.ordered_date >= start,
        LabTest.ordered_date <= end
    ).group_by(LabTest.status).all()
    
    return render_template('reports/medical.html',
                         start_date=start_date,
                         end_date=end_date,
                         diagnoses=diagnoses,
                         lab_categories=lab_categories,
                         lab_status=lab_status,
                         title='Medical Report')


@reports_bp.route('/export/patients')
@login_required
def export_patients():
    """Export patients to CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Patient ID', 'First Name', 'Last Name', 'Date of Birth', 'Gender',
        'Blood Type', 'Phone', 'Email', 'Address', 'Insurance Provider',
        'Created Date'
    ])
    
    # Data
    patients = Patient.query.filter_by(is_active=True).all()
    for patient in patients:
        writer.writerow([
            patient.patient_id,
            patient.first_name,
            patient.last_name,
            patient.date_of_birth.isoformat() if patient.date_of_birth else '',
            patient.gender,
            patient.blood_type,
            patient.phone,
            patient.email,
            patient.address,
            patient.insurance_provider,
            patient.created_at.isoformat() if patient.created_at else ''
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'patients_export_{date.today().isoformat()}.csv'
    )


@reports_bp.route('/export/appointments')
@login_required
def export_appointments():
    """Export appointments to CSV."""
    start_date = request.args.get('start_date', date.today().isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Date', 'Start Time', 'End Time', 'Patient', 'Doctor',
        'Type', 'Status', 'Reason'
    ])
    
    # Data
    appointments = Appointment.query.filter(
        Appointment.appointment_date >= start_date,
        Appointment.appointment_date <= end_date
    ).all()
    
    for apt in appointments:
        writer.writerow([
            apt.appointment_date.isoformat(),
            apt.start_time.strftime('%H:%M') if apt.start_time else '',
            apt.end_time.strftime('%H:%M') if apt.end_time else '',
            apt.patient.get_full_name(),
            apt.doctor.get_full_name(),
            apt.appointment_type,
            apt.status,
            apt.reason
        ])
    
    output.seek(0)
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'appointments_export_{date.today().isoformat()}.csv'
    )



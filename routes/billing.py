"""
Clinic Management Platform - Billing Routes
===========================================
Routes for billing, invoices, and payments.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from models import db, Patient, Invoice, InvoiceItem, Payment, Service, AuditLog
from forms import InvoiceForm, InvoiceItemForm, PaymentForm, ServiceForm
from decorators import role_required

billing_bp = Blueprint('billing', __name__)


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


def generate_invoice_number():
    """Generate unique invoice number."""
    prefix = 'INV'
    year = datetime.now().strftime('%Y')
    last_inv = Invoice.query.filter(
        Invoice.invoice_number.like(f'{prefix}{year}%')
    ).order_by(Invoice.id.desc()).first()
    
    if last_inv:
        last_num = int(last_inv.invoice_number[-6:])
        new_num = last_num + 1
    else:
        new_num = 1
    
    return f'{prefix}{year}{new_num:06d}'


# ==================== INVOICES ====================

@billing_bp.route('/invoices')
@login_required
def list_invoices():
    """List invoices."""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    patient_id = request.args.get('patient_id', type=int)
    
    query = Invoice.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    
    invoices = query.order_by(Invoice.invoice_date.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('billing/invoices.html',
                         invoices=invoices,
                         status_filter=status_filter,
                         title='Invoices')


@billing_bp.route('/invoices/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'accountant')
def create_invoice():
    """Create invoice route."""
    form = InvoiceForm()
    form.patient_id.choices = [(p.id, f"{p.patient_id} - {p.get_full_name()}") 
                               for p in Patient.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        invoice = Invoice(
            invoice_number=generate_invoice_number(),
            patient_id=form.patient_id.data,
            invoice_date=form.invoice_date.data,
            due_date=form.due_date.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        log_action('create', 'Invoice', invoice.id, 
                  f"Created invoice {invoice.invoice_number}")
        
        flash('Invoice created successfully. Add items below.', 'success')
        return redirect(url_for('billing.edit_invoice', invoice_id=invoice.id))
    
    # Pre-fill patient if provided
    if request.args.get('patient_id'):
        form.patient_id.data = int(request.args.get('patient_id'))
    
    return render_template('billing/create_invoice.html', 
                         form=form, 
                         title='New Invoice')


@billing_bp.route('/invoices/<int:invoice_id>')
@login_required
def view_invoice(invoice_id):
    """View invoice."""
    invoice = Invoice.query.get_or_404(invoice_id)
    return render_template('billing/view_invoice.html',
                         invoice=invoice,
                         title=f'Invoice {invoice.invoice_number}')


@billing_bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'accountant')
def edit_invoice(invoice_id):
    """Edit invoice and add items."""
    invoice = Invoice.query.get_or_404(invoice_id)
    form = InvoiceForm(obj=invoice)
    item_form = InvoiceItemForm()
    
    # Get services for dropdown
    services = Service.query.filter_by(is_active=True).all()
    
    if request.method == 'POST':
        if 'add_item' in request.form:
            # Add new item
            item = InvoiceItem(
                invoice_id=invoice_id,
                service_name=request.form.get('service_name'),
                service_code=request.form.get('service_code'),
                description=request.form.get('description'),
                quantity=float(request.form.get('quantity', 1)),
                unit_price=float(request.form.get('unit_price', 0))
            )
            item.calculate_total()
            db.session.add(item)
            
            # Recalculate invoice totals
            invoice.calculate_totals()
            db.session.commit()
            
            flash('Item added.', 'success')
            return redirect(url_for('billing.edit_invoice', invoice_id=invoice_id))
        
        elif 'update_invoice' in request.form and form.validate():
            invoice.invoice_date = form.invoice_date.data
            invoice.due_date = form.due_date.data
            invoice.notes = form.notes.data
            db.session.commit()
            
            flash('Invoice updated.', 'success')
            return redirect(url_for('billing.view_invoice', invoice_id=invoice_id))
    
    return render_template('billing/edit_invoice.html',
                         invoice=invoice,
                         form=form,
                         item_form=item_form,
                         services=services,
                         title='Edit Invoice')


@billing_bp.route('/invoices/items/<int:item_id>/delete', methods=['POST'])
@login_required
@role_required('admin', 'accountant')
def delete_invoice_item(item_id):
    """Delete invoice item."""
    item = InvoiceItem.query.get_or_404(item_id)
    invoice_id = item.invoice_id
    
    db.session.delete(item)
    
    # Recalculate invoice totals
    invoice = Invoice.query.get(invoice_id)
    invoice.calculate_totals()
    db.session.commit()
    
    flash('Item removed.', 'success')
    return redirect(url_for('billing.edit_invoice', invoice_id=invoice_id))


@billing_bp.route('/invoices/<int:invoice_id>/payment', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'accountant')
def record_payment(invoice_id):
    """Record payment for invoice."""
    invoice = Invoice.query.get_or_404(invoice_id)
    form = PaymentForm()
    
    if form.validate_on_submit():
        payment = Payment(
            invoice_id=invoice_id,
            amount=form.amount.data,
            payment_method=form.payment_method.data,
            transaction_id=form.transaction_id.data,
            reference_number=form.reference_number.data,
            notes=form.notes.data,
            recorded_by=current_user.id
        )
        
        db.session.add(payment)
        
        # Update invoice
        invoice.paid_amount += form.amount.data
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        
        if invoice.balance_due <= 0:
            invoice.status = 'paid'
        elif invoice.paid_amount > 0:
            invoice.status = 'partial'
        
        db.session.commit()
        
        log_action('create', 'Payment', payment.id, 
                  f"Recorded payment of ${form.amount.data} for invoice {invoice.invoice_number}")
        
        flash('Payment recorded successfully.', 'success')
        return redirect(url_for('billing.view_invoice', invoice_id=invoice_id))
    
    # Pre-fill with remaining balance
    if request.method == 'GET':
        form.amount.data = invoice.balance_due
    
    return render_template('billing/record_payment.html',
                         form=form,
                         invoice=invoice,
                         title='Record Payment')


@billing_bp.route('/invoices/<int:invoice_id>/pdf')
@login_required
def invoice_pdf(invoice_id):
    """Generate invoice PDF."""
    from flask import current_app
    
    invoice = Invoice.query.get_or_404(invoice_id)
    
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
    
    # Invoice title
    story.append(Paragraph("<h2>INVOICE</h2>", styles['Heading2']))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice details
    story.append(Paragraph(f"<b>Invoice #:</b> {invoice.invoice_number}", styles['Normal']))
    story.append(Paragraph(f"<b>Date:</b> {invoice.invoice_date.strftime('%B %d, %Y')}", styles['Normal']))
    story.append(Paragraph(f"<b>Due Date:</b> {invoice.due_date.strftime('%B %d, %Y') if invoice.due_date else 'N/A'}", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Patient info
    story.append(Paragraph(f"<b>Bill To:</b>", styles['Heading3']))
    story.append(Paragraph(invoice.patient.get_full_name(), styles['Normal']))
    if invoice.patient.address:
        story.append(Paragraph(invoice.patient.address, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Items table
    data = [['Service', 'Description', 'Qty', 'Unit Price', 'Total']]
    for item in invoice.items:
        data.append([
            item.service_name,
            item.description or '',
            str(item.quantity),
            f"${item.unit_price:.2f}",
            f"${item.total_price:.2f}"
        ])
    
    table = Table(data, colWidths=[1.5*inch, 2*inch, 0.5*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.2*inch))
    
    # Totals
    story.append(Paragraph(f"<b>Subtotal:</b> ${invoice.subtotal:.2f}", styles['Normal']))
    story.append(Paragraph(f"<b>Tax:</b> ${invoice.tax_amount:.2f}", styles['Normal']))
    story.append(Paragraph(f"<b>Discount:</b> ${invoice.discount_amount:.2f}", styles['Normal']))
    story.append(Paragraph(f"<b>Total:</b> ${invoice.total_amount:.2f}", styles['Heading3']))
    story.append(Paragraph(f"<b>Paid:</b> ${invoice.paid_amount:.2f}", styles['Normal']))
    story.append(Paragraph(f"<b>Balance Due:</b> ${invoice.balance_due:.2f}", styles['Heading3']))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{invoice.invoice_number}.pdf",
        mimetype='application/pdf'
    )


# ==================== SERVICES ====================

@billing_bp.route('/services')
@login_required
def list_services():
    """List services catalog."""
    page = request.args.get('page', 1, type=int)
    services = Service.query.order_by(Service.service_name).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('billing/services.html',
                         services=services,
                         title='Services')


@billing_bp.route('/services/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_service():
    """Create service route."""
    form = ServiceForm()
    
    if form.validate_on_submit():
        service = Service(
            service_code=form.service_code.data,
            service_name=form.service_name.data,
            description=form.description.data,
            category=form.category.data,
            default_price=form.default_price.data
        )
        
        db.session.add(service)
        db.session.commit()
        
        log_action('create', 'Service', service.id, f"Added service: {service.service_name}")
        
        flash('Service added successfully.', 'success')
        return redirect(url_for('billing.list_services'))
    
    return render_template('billing/create_service.html',
                         form=form,
                         title='Add Service')


@billing_bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_service(service_id):
    """Edit service route."""
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    
    if form.validate_on_submit():
        service.service_code = form.service_code.data
        service.service_name = form.service_name.data
        service.description = form.description.data
        service.category = form.category.data
        service.default_price = form.default_price.data
        
        db.session.commit()
        
        log_action('update', 'Service', service.id, f"Updated service: {service.service_name}")
        
        flash('Service updated successfully.', 'success')
        return redirect(url_for('billing.list_services'))
    
    return render_template('billing/edit_service.html',
                         form=form,
                         service=service,
                         title='Edit Service')


@billing_bp.route('/api/services/search')
@login_required
def api_search_services():
    """API endpoint for service search."""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    services = Service.query.filter(
        Service.service_name.ilike(f'%{query}%'),
        Service.is_active == True
    ).limit(10).all()
    
    return jsonify([{
        'id': s.id,
        'service_code': s.service_code,
        'service_name': s.service_name,
        'default_price': s.default_price
    } for s in services])


# ==================== REPORTS ====================

@billing_bp.route('/reports')
@login_required
def reports():
    """Financial reports route."""
    report_type = request.args.get('type', 'daily')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date:
        start_date = date.today().replace(day=1).isoformat()
    if not end_date:
        end_date = date.today().isoformat()
    
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get revenue data
    revenue_query = db.session.query(
        func.date(Invoice.invoice_date).label('date'),
        func.sum(Invoice.paid_amount).label('revenue'),
        func.count(Invoice.id).label('count')
    ).filter(
        Invoice.invoice_date >= start,
        Invoice.invoice_date <= end
    ).group_by(func.date(Invoice.invoice_date))
    
    revenue_data = revenue_query.all()
    
    # Summary statistics
    total_revenue = sum(r.revenue for r in revenue_data) if revenue_data else 0
    total_invoices = sum(r.count for r in revenue_data) if revenue_data else 0
    
    # Outstanding balance
    outstanding = db.session.query(func.sum(Invoice.balance_due)).filter(
        Invoice.status.in_(['pending', 'partial', 'overdue'])
    ).scalar() or 0
    
    return render_template('billing/reports.html',
                         report_type=report_type,
                         start_date=start_date,
                         end_date=end_date,
                         revenue_data=revenue_data,
                         total_revenue=total_revenue,
                         total_invoices=total_invoices,
                         outstanding=outstanding,
                         title='Financial Reports')

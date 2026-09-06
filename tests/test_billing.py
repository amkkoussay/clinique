"""
Tests for billing routes: invoice creation and listing.
"""

from models import Invoice


class TestInvoiceList:

    def test_list_requires_login(self, client):
        response = client.get('/billing/invoices', follow_redirects=True)
        assert response.request.path == '/auth/login'

    def test_list_loads_for_accountant(self, client, login_as, accountant_user):
        login_as(client, accountant_user)
        response = client.get('/billing/invoices')
        assert response.status_code == 200


class TestInvoiceCreate:

    def test_create_invoice_success(self, client, login_as, accountant_user, sample_patient, db):
        login_as(client, accountant_user)

        response = client.post('/billing/invoices/create', data={
            'patient_id': sample_patient.id,
            'invoice_date': '2026-07-31',
            'due_date': '2026-08-14',
            'notes': 'Test invoice',
        }, follow_redirects=True)

        assert response.status_code == 200
        invoice = Invoice.query.filter_by(patient_id=sample_patient.id).first()
        assert invoice is not None
        assert invoice.notes == 'Test invoice'
        assert invoice.invoice_number.startswith('INV')

    def test_invoice_number_is_unique_per_invoice(self, client, login_as, accountant_user,
                                                    sample_patient, db):
        login_as(client, accountant_user)

        for _ in range(2):
            client.post('/billing/invoices/create', data={
                'patient_id': sample_patient.id,
                'invoice_date': '2026-07-31',
            }, follow_redirects=True)

        invoices = Invoice.query.filter_by(patient_id=sample_patient.id).all()
        assert len(invoices) == 2
        assert invoices[0].invoice_number != invoices[1].invoice_number

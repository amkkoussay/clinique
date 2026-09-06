"""
Tests for role-based access control (the @role_required decorator)
applied across appointments, patients, medical and billing routes.
"""


class TestAppointmentPermissions:

    def test_receptionist_can_create_appointment_page(self, client, login_as, receptionist_user):
        login_as(client, receptionist_user)
        response = client.get('/appointments/create')
        assert response.status_code == 200

    def test_admin_can_create_appointment_page(self, client, login_as, admin_user):
        login_as(client, admin_user)
        response = client.get('/appointments/create')
        assert response.status_code == 200

    def test_doctor_cannot_create_appointment_page(self, client, login_as, doctor_user):
        login_as(client, doctor_user)
        response = client.get('/appointments/create', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_anonymous_redirected_to_login(self, client):
        response = client.get('/appointments/create', follow_redirects=True)
        assert response.request.path == '/auth/login'


class TestPatientPermissions:

    def test_receptionist_can_create_patient_page(self, client, login_as, receptionist_user):
        login_as(client, receptionist_user)
        response = client.get('/patients/create')
        assert response.status_code == 200

    def test_doctor_cannot_create_patient_page(self, client, login_as, doctor_user):
        login_as(client, doctor_user)
        response = client.get('/patients/create', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_doctor_can_still_view_patient_list(self, client, login_as, doctor_user):
        """Read-only patient list stays open to all logged-in roles."""
        login_as(client, doctor_user)
        response = client.get('/patients/')
        assert response.status_code == 200

    def test_accountant_cannot_edit_patient(self, client, login_as, accountant_user, sample_patient):
        login_as(client, accountant_user)
        response = client.get(f'/patients/{sample_patient.id}/edit', follow_redirects=True)
        assert b'do not have permission' in response.data


class TestMedicalPermissions:

    def test_doctor_can_view_records_list(self, client, login_as, doctor_user):
        login_as(client, doctor_user)
        response = client.get('/medical/records')
        assert response.status_code == 200

    def test_receptionist_cannot_view_medical_records(self, client, login_as, receptionist_user):
        login_as(client, receptionist_user)
        response = client.get('/medical/records', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_accountant_cannot_view_medical_records(self, client, login_as, accountant_user):
        login_as(client, accountant_user)
        response = client.get('/medical/records', follow_redirects=True)
        assert b'do not have permission' in response.data


class TestBillingPermissions:

    def test_accountant_can_create_invoice_page(self, client, login_as, accountant_user):
        login_as(client, accountant_user)
        response = client.get('/billing/invoices/create')
        assert response.status_code == 200

    def test_doctor_cannot_create_invoice_page(self, client, login_as, doctor_user):
        login_as(client, doctor_user)
        response = client.get('/billing/invoices/create', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_receptionist_cannot_create_invoice_page(self, client, login_as, receptionist_user):
        login_as(client, receptionist_user)
        response = client.get('/billing/invoices/create', follow_redirects=True)
        assert b'do not have permission' in response.data

    def test_admin_can_create_invoice_page(self, client, login_as, admin_user):
        login_as(client, admin_user)
        response = client.get('/billing/invoices/create')
        assert response.status_code == 200

    def test_only_admin_can_manage_services(self, client, login_as, accountant_user):
        """Services catalog stays admin-only even for accountants."""
        login_as(client, accountant_user)
        response = client.get('/billing/services/create', follow_redirects=True)
        assert b'do not have permission' in response.data

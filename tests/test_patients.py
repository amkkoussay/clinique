"""
Tests for patient management routes (list, create, view, edit, delete).
"""

from models import Patient


class TestPatientList:

    def test_list_requires_login(self, client):
        response = client.get('/patients/', follow_redirects=True)
        assert response.request.path == '/auth/login'

    def test_list_shows_existing_patient(self, client, login_as, admin_user, sample_patient):
        login_as(client, admin_user)
        response = client.get('/patients/')
        assert response.status_code == 200
        assert sample_patient.first_name.encode() in response.data

    def test_search_filters_results(self, client, login_as, admin_user, sample_patient):
        login_as(client, admin_user)
        response = client.get('/patients/', query_string={'search': 'Doe'})
        assert response.status_code == 200
        assert b'Doe' in response.data

    def test_search_no_match_returns_empty_state(self, client, login_as, admin_user, sample_patient):
        login_as(client, admin_user)
        response = client.get('/patients/', query_string={'search': 'Nonexistent999'})
        assert response.status_code == 200
        assert b'Doe' not in response.data


class TestPatientCreate:

    def test_create_page_loads_for_receptionist(self, client, login_as, receptionist_user):
        login_as(client, receptionist_user)
        response = client.get('/patients/create')
        assert response.status_code == 200

    def test_create_patient_success(self, client, login_as, admin_user, db):
        login_as(client, admin_user)

        response = client.post('/patients/create', data={
            'first_name': 'Alice',
            'last_name': 'Wonder',
            'date_of_birth': '1995-05-20',
            'gender': 'female',
            'phone': '555-7777',
            'email': 'alice@example.com',
        }, follow_redirects=True)

        assert response.status_code == 200
        patient = Patient.query.filter_by(first_name='Alice', last_name='Wonder').first()
        assert patient is not None
        assert patient.phone == '555-7777'

    def test_create_patient_missing_required_field_fails(self, client, login_as, admin_user):
        login_as(client, admin_user)

        response = client.post('/patients/create', data={
            'first_name': '',
            'last_name': 'Wonder',
            'date_of_birth': '1995-05-20',
            'gender': 'female',
            'phone': '555-7777',
        }, follow_redirects=True)

        # Form re-renders (200) rather than redirecting to a created record
        assert response.status_code == 200
        assert Patient.query.filter_by(last_name='Wonder').first() is None


class TestPatientView:

    def test_view_existing_patient(self, client, login_as, admin_user, sample_patient):
        login_as(client, admin_user)
        response = client.get(f'/patients/{sample_patient.id}')
        assert response.status_code == 200
        assert sample_patient.first_name.encode() in response.data

    def test_view_nonexistent_patient_returns_404(self, client, login_as, admin_user):
        login_as(client, admin_user)
        response = client.get('/patients/999999')
        assert response.status_code == 404


class TestPatientEdit:

    def test_edit_updates_patient(self, client, login_as, admin_user, sample_patient, db):
        login_as(client, admin_user)

        response = client.post(f'/patients/{sample_patient.id}/edit', data={
            'first_name': 'Johnny',
            'last_name': sample_patient.last_name,
            'date_of_birth': sample_patient.date_of_birth.isoformat(),
            'gender': sample_patient.gender,
            'phone': sample_patient.phone,
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(sample_patient)
        assert sample_patient.first_name == 'Johnny'


class TestPatientDelete:

    def test_delete_deactivates_patient(self, client, login_as, admin_user, sample_patient, db):
        login_as(client, admin_user)

        response = client.post(f'/patients/{sample_patient.id}/delete', follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(sample_patient)
        assert sample_patient.is_active is False

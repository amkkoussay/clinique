"""
Tests for appointment scheduling routes.
"""

from datetime import date, timedelta

from models import Appointment


class TestAppointmentList:

    def test_list_requires_login(self, client):
        response = client.get('/appointments/', follow_redirects=True)
        assert response.request.path == '/auth/login'

    def test_list_loads_for_doctor(self, client, login_as, doctor_user):
        login_as(client, doctor_user)
        response = client.get('/appointments/')
        assert response.status_code == 200

    def test_list_shows_existing_appointment(self, client, login_as, admin_user, sample_appointment):
        login_as(client, admin_user)
        response = client.get('/appointments/')
        assert response.status_code == 200


class TestAppointmentCreate:

    def test_create_appointment_success(self, client, login_as, receptionist_user,
                                         sample_patient, doctor_user, db):
        login_as(client, receptionist_user)

        tomorrow = (date.today() + timedelta(days=3)).isoformat()

        response = client.post('/appointments/create', data={
            'patient_id': sample_patient.id,
            'doctor_id': doctor_user.id,
            'appointment_date': tomorrow,
            'start_time': '11:00',
            'end_time': '11:30',
            'appointment_type': 'consultation',
            'status': 'scheduled',
            'reason': 'Follow-up visit',
        }, follow_redirects=True)

        assert response.status_code == 200
        appt = Appointment.query.filter_by(reason='Follow-up visit').first()
        assert appt is not None
        assert appt.patient_id == sample_patient.id
        assert appt.doctor_id == doctor_user.id


class TestAppointmentView:

    def test_view_existing_appointment(self, client, login_as, admin_user, sample_appointment):
        login_as(client, admin_user)
        response = client.get(f'/appointments/{sample_appointment.id}')
        assert response.status_code == 200

    def test_view_nonexistent_appointment_404(self, client, login_as, admin_user):
        login_as(client, admin_user)
        response = client.get('/appointments/999999')
        assert response.status_code == 404


class TestAppointmentCancel:

    def test_receptionist_can_cancel(self, client, login_as, receptionist_user, sample_appointment, db):
        login_as(client, receptionist_user)

        response = client.post(
            f'/appointments/{sample_appointment.id}/cancel',
            follow_redirects=True
        )

        assert response.status_code == 200
        db.session.refresh(sample_appointment)
        assert sample_appointment.status == 'cancelled'

    def test_doctor_cannot_cancel(self, client, login_as, doctor_user, sample_appointment, db):
        login_as(client, doctor_user)

        response = client.post(
            f'/appointments/{sample_appointment.id}/cancel',
            follow_redirects=True
        )

        assert b'do not have permission' in response.data
        db.session.refresh(sample_appointment)
        assert sample_appointment.status != 'cancelled'


class TestAppointmentStatusUpdate:

    def test_update_status_to_completed(self, client, login_as, doctor_user, sample_appointment, db):
        login_as(client, doctor_user)

        response = client.post(
            f'/appointments/{sample_appointment.id}/status/completed',
            follow_redirects=True
        )

        assert response.status_code == 200
        db.session.refresh(sample_appointment)
        assert sample_appointment.status == 'completed'

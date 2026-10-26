"""
Tests for FHIR R4 API endpoints: Patient, Appointment, Observation.
"""

import json
from datetime import date, time, datetime
from models import Patient, Appointment, MedicalRecord, User


class TestFHIRAPI:

    def test_fhir_swagger_json(self, client):
        response = client.get('/fhir/swagger.json')
        assert response.status_code == 200
        data = response.get_json()
        assert 'openapi' in data
        assert '/Patient' in data['paths']
        assert '/Appointment' in data['paths']
        assert '/Observation' in data['paths']

    def test_fhir_docs_page(self, client):
        response = client.get('/fhir/docs')
        assert response.status_code == 200
        assert b'FHIR R4 API Documentation' in response.data

    def test_fhir_patient_data_requires_login(self, client, sample_patient):
        """Unauthenticated requests to patient-data routes must not succeed."""
        for method, url in [
            ('get', '/fhir/Patient'),
            ('get', f'/fhir/Patient/{sample_patient.id}'),
            ('post', '/fhir/Patient'),
            ('get', '/fhir/Appointment'),
            ('post', '/fhir/Appointment'),
            ('get', '/fhir/Observation'),
            ('post', '/fhir/Observation'),
        ]:
            response = getattr(client, method)(url, json={} if method == 'post' else None)
            assert response.status_code in (302, 401), (method, url, response.status_code)

    def test_fhir_patient_get(self, client, sample_patient, admin_user, login_as):
        login_as(client, admin_user)
        response = client.get(f'/fhir/Patient/{sample_patient.id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['resourceType'] == 'Patient'
        assert data['id'] == str(sample_patient.id)

    def test_fhir_patient_post_create(self, client, admin_user, login_as):
        login_as(client, admin_user)
        payload = {
            "resourceType": "Patient",
            "name": [{"family": "Smith", "given": ["Alice"]}],
            "telecom": [{"system": "phone", "value": "555-9876"}],
            "gender": "female",
            "birthDate": "1990-05-15",
            "address": [{"text": "123 Medical Way"}]
        }
        response = client.post('/fhir/Patient', json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['resourceType'] == 'Patient'
        assert data['name'][0]['family'] == 'Smith'

    def test_fhir_appointment_get_and_post(self, client, sample_patient, admin_user, login_as):
        login_as(client, admin_user)
        # Create appointment via FHIR
        payload = {
            "resourceType": "Appointment",
            "status": "booked",
            "description": "Routine checkup",
            "start": "2026-09-01T10:00:00Z",
            "end": "2026-09-01T10:30:00Z",
            "participant": [
                {"actor": {"reference": f"Patient/{sample_patient.id}"}},
                {"actor": {"reference": f"Practitioner/{admin_user.id}"}}
            ]
        }
        response = client.post('/fhir/Appointment', json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['resourceType'] == 'Appointment'
        appt_id = data['id']

        # Get appointment via FHIR
        get_resp = client.get(f'/fhir/Appointment/{appt_id}')
        assert get_resp.status_code == 200
        assert get_resp.get_json()['status'] == 'booked'

    def test_fhir_observation_get_and_post(self, client, sample_patient, admin_user, login_as):
        login_as(client, admin_user)
        # Create observation (Medical Record) via FHIR
        payload = {
            "resourceType": "Observation",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "8302-2", "display": "Hypertension Check"}],
                "text": "Hypertension Check"
            },
            "subject": {"reference": f"Patient/{sample_patient.id}"},
            "valueString": "Prescribed lifestyle modifications"
        }
        response = client.post('/fhir/Observation', json=payload)
        assert response.status_code == 201
        data = response.get_json()
        assert data['resourceType'] == 'Observation'
        obs_id = data['id']

        # Get observation via FHIR
        get_resp = client.get(f'/fhir/Observation/{obs_id}')
        assert get_resp.status_code == 200
        assert 'Hypertension Check' in get_resp.get_json()['code']['text']

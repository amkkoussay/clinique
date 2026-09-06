from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_doctor_appointment_list_is_scoped():
    src = (ROOT / "routes" / "appointments.py").read_text(encoding="utf-8")
    assert "Appointment.doctor_id == current_user.id" in src

def test_doctor_appointment_routes_have_ownership_guard():
    src = (ROOT / "routes" / "appointments.py").read_text(encoding="utf-8")
    assert "current_user.is_doctor() and appointment.doctor_id != current_user.id" in src
    assert "abort(403)" in src

def test_doctor_patient_access_is_scoped():
    src = (ROOT / "routes" / "patients.py").read_text(encoding="utf-8")
    assert "Appointment.patient_id == patient.id" in src
    assert "Appointment.doctor_id == current_user.id" in src

#!/usr/bin/env python3
"""Create a complete synthetic clinic demo database.

All people, emails, phone numbers, diagnoses and records are fictional.
Run: python seed_demo_full.py
"""
import os, sqlite3, json, hashlib, base64, datetime as dt, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'clinic.db'
SCHEMA_DB = ROOT / 'clinic_schema.db'
BACKUP = ROOT / 'clinic.db.before-demo.bak'

# Seeded demo password: from CLINIQUE_DEMO_PASSWORD, or a DEMO-ONLY
# default when that variable is unset. Seeded accounts are demo-only and
# must be changed or removed before any real deployment. An environment
# value is never printed; the default is printed, labelled DEMO-ONLY,
# only when it is actually the password in use.
DEMO_PASSWORD = os.environ.get('CLINIQUE_DEMO_PASSWORD')
DEMO_PASSWORD_FROM_ENV = DEMO_PASSWORD is not None
if not DEMO_PASSWORD_FROM_ENV:
    print('NOTE: CLINIQUE_DEMO_PASSWORD is not set — using a DEMO-ONLY default password.')
    DEMO_PASSWORD = 'Demo123!'


def password_hash(password=None):
    if password is None:
        password = DEMO_PASSWORD
    salt = b'clinique-demo-salt-2026'
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000, dklen=32)
    return 'pbkdf2:sha256:600000$clinique-demo-salt-2026$' + key.hex()

# Use a temporary schema copy so the existing empty schema is preserved.
if DB.exists():
    shutil.copy2(DB, BACKUP)
    DB.unlink()
shutil.copy2(SCHEMA_DB, DB) if SCHEMA_DB.exists() else None
# Above would copy the deleted file only if it still existed; restore from backup.
if not DB.exists():
    shutil.copy2(BACKUP, DB)

conn = sqlite3.connect(DB)
conn.execute('PRAGMA foreign_keys=ON')
c = conn.cursor()

# Bring the demo SQLite schema up to the current model version.
cols = {r[1] for r in c.execute('PRAGMA table_info(appointments)')}
if 'booking_key' not in cols:
    c.execute('ALTER TABLE appointments ADD COLUMN booking_key VARCHAR(120)')
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS ix_appointments_booking_key ON appointments(booking_key)')

# Clear in dependency order.
for table in ['payments','invoice_items','invoices','prescription_items','prescriptions','lab_tests','medical_records','vital_signs','appointments','notifications','tasks','chatbot_conversations','patient_documents','audit_logs','medicines','services','patients','users']:
    try: c.execute(f'DELETE FROM {table}')
    except sqlite3.OperationalError: pass

now = dt.datetime(2026,9,3,10,0)
today = now.date()
ph = password_hash()

def ins(table, cols, rows):
    qs = ','.join('?' for _ in cols)
    c.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({qs})", rows)

# Users: admin + 6 doctors + 2 receptionists + 8 patient accounts.
users=[]
users.append(('admin-uuid','admin@clinique-demo.example',ph,'Admin','Manager','+21620000001','admin',None,None,1,None,now.isoformat(),now.isoformat()))
doctors=[
('dr-001','dr.amina.benali@clinique-demo.example','Amina','Ben Ali','General Medicine','MD-TN-1001'),
('dr-002','dr.youssef.trabelsi@clinique-demo.example','Youssef','Trabelsi','Cardiology','MD-TN-1002'),
('dr-003','dr.salma.mansouri@clinique-demo.example','Salma','Mansouri','Pediatrics','MD-TN-1003'),
('dr-004','dr.ahmed.khelifi@clinique-demo.example','Ahmed','Khelifi','Dermatology','MD-TN-1004'),
('dr-005','dr.meriem.gharbi@clinique-demo.example','Meriem','Gharbi','Gynecology','MD-TN-1005'),
('dr-006','dr.wael.jaziri@clinique-demo.example','Wael','Jaziri','Orthopedics','MD-TN-1006'),
]
for u in doctors:
    users.append((u[0],u[1],ph,u[2],u[3],'+2162000'+u[0][-3:] ,'doctor',u[4],u[5],1,None,now.isoformat(),now.isoformat()))
for i,name in enumerate([('Nour','Haddad'),('Karim','Saidi')],1):
    users.append((f'rec-00{i}',f'reception{i}@clinique-demo.example',ph,name[0],name[1],f'+2162000001{i}','receptionist',None,None,1,None,now.isoformat(),now.isoformat()))
ins('users',['uuid','email','password_hash','first_name','last_name','phone','role','specialization','license_number','is_active','last_login','created_at','updated_at'],users)

doctor_ids={r[1]:r[0] for r in c.execute("select id,email from users where role='doctor'")}
admin_id=c.execute("select id from users where role='admin'").fetchone()[0]

# Patients: 40 synthetic records, each linked to a login account for the first 8.
first=['Yasmine','Malek','Ines','Adam','Meriem','Rayen','Sarra','Ahmed','Nour','Omar','Lina','Fares','Amira','Anis','Maya','Seif','Hiba','Wassim','Rim','Elyes']
last=['Ben Salem','Chaabane','Ayari','Jaziri','Gharbi','Trabelsi','Mansouri','Khelifi','Haddad','Saidi','Mrad','Karray','Hamdi','Tlili','Dridi','Bouzid']
conditions=[[],['Hypertension'],['Type 2 diabetes'],['Asthma'],['Migraine'],['Hyperlipidemia'],['Hypothyroidism'],['Seasonal allergy']]
allergies=[[],['Penicillin'],['Dust'],['Peanuts'],['None known']]
patients=[]
for i in range(40):
    fn=first[i%len(first)]; ln=last[(i*3)%len(last)]
    dob=dt.date(1960+(i%38), 1+(i%12), 2+(i%25))
    pid=f'P2026-{i+1:04d}'
    email=f'patient{i+1:02d}@example.com'
    phone=f'+216 20 {100000+i:06d}'
    account_user_id=None
    if i<8:
        # Create patient user account.
        uid=f'patient-{i+1:03d}'
        ins('users',['uuid','email','password_hash','first_name','last_name','phone','role','specialization','license_number','is_active','last_login','created_at','updated_at'],[(uid,email,ph,fn,ln,phone,'patient',None,None,1,None,now.isoformat(),now.isoformat())])
    patients.append((f'patient-uuid-{i+1:04d}',pid,fn,ln,dob.isoformat(),'male' if i%2==0 else 'female',['A+','O+','B+','AB+','O-'][i%5],'single' if i%3 else 'married',['Teacher','Engineer','Student','Designer','Accountant'][i%5],phone,email,f'{10+i} Avenue Demo, Tunis','Emergency Contact',f'+216 71 000 {i+1:04d}','Demo Insurance',f'DEMO-{i+1:05d}','GRP-DEMO',json.dumps(allergies[i%len(allergies)]),json.dumps(conditions[i%len(conditions)]),json.dumps([]),json.dumps({'diabetes':'negative','cardiac':'none'}),json.dumps([]),1,now.isoformat(),now.isoformat()))
ins('patients',['uuid','patient_id','first_name','last_name','date_of_birth','gender','blood_type','marital_status','occupation','phone','email','address','emergency_contact_name','emergency_contact_phone','insurance_provider','insurance_policy_number','insurance_group_number','allergies','chronic_conditions','current_medications','family_history','surgical_history','is_active','created_at','updated_at'],patients)

patient_ids={r[1]:r[0] for r in c.execute('select id,patient_id from patients')}

# Services
services=[
('CONS001','General Consultation','Standard medical consultation','consultation',80.0,1),('CARD001','Cardiology Consultation','Heart and cardiovascular consultation','consultation',120.0,1),('PED001','Pediatric Consultation','Child health consultation','consultation',90.0,1),('DERM001','Dermatology Consultation','Skin consultation','consultation',100.0,1),('GYNE001','Gynecology Consultation','Women health consultation','consultation',110.0,1),('ORTH001','Orthopedic Consultation','Bones and joints consultation','consultation',110.0,1),('CBC001','Complete Blood Count','CBC laboratory test','laboratory',35.0,1),('GLU001','Blood Glucose','Glucose test','laboratory',20.0,1),('ECG001','ECG','Electrocardiogram','procedure',60.0,1),('XRAY001','X-Ray','Basic X-Ray imaging','imaging',90.0,1)]
ins('services',['service_code','service_name','description','category','default_price','is_active'],services)

meds=[
('Paracetamol','Acetaminophen','Analgesic','["tablet","suspension"]','["500mg","650mg"]','500mg as directed','Use as prescribed','Known allergy','Rare nausea',1),
('Amoxicillin','Amoxicillin','Antibiotic','["capsule","suspension"]','["250mg","500mg"]','As prescribed','Complete prescribed course','Penicillin allergy','GI upset',1),
('Metformin','Metformin','Antidiabetic','["tablet"]','["500mg","850mg"]','As prescribed','Take with food','Severe renal impairment','GI upset',1),
('Lisinopril','Lisinopril','Antihypertensive','["tablet"]','["5mg","10mg","20mg"]','As prescribed','Monitor blood pressure','Pregnancy','Dizziness',1),
('Cetirizine','Cetirizine','Antihistamine','["tablet"]','["10mg"]','As prescribed','May cause drowsiness','Known allergy','Drowsiness',1),
('Ibuprofen','Ibuprofen','NSAID','["tablet"]','["200mg","400mg"]','As prescribed','Take with food','Ulcer history','Stomach irritation',1)]
ins('medicines',['name','generic_name','category','dosage_forms','strengths','default_dosage','instructions','contraindications','side_effects','is_active'],meds)

# Appointments: past completed, current confirmed, future scheduled. No overlaps per doctor.
apt_rows=[]
slot_plan=[('09:00','09:30'),('10:00','10:30'),('11:00','11:30'),('14:00','14:30'),('15:00','15:30')]
# 18 past visits
for i in range(18):
    d=today-dt.timedelta(days=2+(i%45)); st,en=slot_plan[i%len(slot_plan)]
    doc_email=doctors[i%len(doctors)][1]; doc=doctor_ids[doc_email]; pat=patient_ids[f'P2026-{i+1:04d}']
    apt_rows.append((f'apt-past-{i+1:03d}',f'{pat}-{doc}-{d.isoformat()}-{st}',pat,doc,d.isoformat(),st,en,'completed','consultation','Follow-up visit','Demo completed appointment',0,None,None,None,now.isoformat(),now.isoformat(),admin_id))
# 20 future/current appointments
for i in range(20):
    d=today+dt.timedelta(days=i%14); st,en=slot_plan[(i+1)%len(slot_plan)]
    doc_email=doctors[(i+2)%len(doctors)][1]; doc=doctor_ids[doc_email]; pat=patient_ids[f'P2026-{((i+5)%40)+1:04d}']
    status='confirmed' if i<8 else 'scheduled'
    apt_rows.append((f'apt-future-{i+1:03d}',f'{pat}-{doc}-{d.isoformat()}-{st}',pat,doc,d.isoformat(),st,en,status,'consultation','Appointment requested','Synthetic demo appointment',0,None,None,None,now.isoformat(),now.isoformat(),admin_id))
ins('appointments',['uuid','booking_key','patient_id','doctor_id','appointment_date','start_time','end_time','status','appointment_type','reason','notes','is_recurring','recurring_pattern','reminder_sent','reminder_sent_at','created_at','updated_at','created_by'],apt_rows)

appointment_ids=[r for r in c.execute('select id,patient_id,doctor_id,appointment_date,status from appointments order by id').fetchall()]

# Medical records for past appointments.
diags=[('Essential hypertension','I10'),('Type 2 diabetes mellitus','E11.9'),('Acute upper respiratory infection','J06.9'),('Migraine without aura','G43.009'),('Atopic dermatitis','L20.9'),('Low back pain','M54.5')]
records=[]
for i,(aid,pid,did,adate,status) in enumerate(appointment_ids[:18]):
    diag,code=diags[i%len(diags)]
    records.append((f'rec-{i+1:04d}',pid,did,aid,'Patient reports symptoms for follow-up.','Stable general examination for demo data.',diag,'Continue monitoring and follow the clinician plan.',diag,None,json.dumps([code]),f'{adate}T10:30:00', (today+dt.timedelta(days=30+i)).isoformat(),'Return if symptoms worsen.',now.isoformat(),now.isoformat()))
ins('medical_records',['uuid','patient_id','doctor_id','appointment_id','subjective','objective','assessment','plan','primary_diagnosis','secondary_diagnosis','icd10_codes','visit_date','follow_up_date','follow_up_notes','created_at','updated_at'],records)

record_ids=[r for r in c.execute('select id,patient_id,doctor_id from medical_records order by id')]
# Vitals
vitals=[]
for i,(rid,pid,did) in enumerate(record_ids):
    height=160+(i%25); weight=55+(i%35); bmi=round(weight/((height/100)**2),2)
    vitals.append((pid,f'{today-dt.timedelta(days=2+(i%45))}T10:20:00',did,height,weight,bmi,36.5+(i%5)*0.1,115+(i%20),70+(i%10),65+(i%15),14+(i%4),97+(i%3),85+(i%25),'Synthetic demo vitals'))
ins('vital_signs',['patient_id','recorded_at','recorded_by','height_cm','weight_kg','bmi','temperature_celsius','blood_pressure_systolic','blood_pressure_diastolic','heart_rate','respiratory_rate','oxygen_saturation','blood_glucose','notes'],vitals)

# Lab tests
labs=[]
for i,(rid,pid,did) in enumerate(record_ids[:12]):
    labs.append((f'lab-{i+1:04d}',pid,rid,did,'Complete Blood Count','blood',f'CBC-{i+1:03d}','completed','Demo result: within expected range.',json.dumps({'hemoglobin':13.5+(i%3)*0.4,'wbc':6.2+(i%2)*0.5}),'See laboratory reference range.','normal',f'{today-dt.timedelta(days=2+i)}T09:00:00',f'{today-dt.timedelta(days=2+i)}T09:30:00',f'{today-dt.timedelta(days=2+i)}T12:00:00','Routine demo lab test','No critical values in synthetic data.'))
ins('lab_tests',['uuid','patient_id','medical_record_id','ordered_by','test_name','test_category','test_code','status','results','result_values','reference_range','abnormal_flags','ordered_date','collected_date','completed_date','clinical_notes','result_notes'],labs)

# Prescriptions and items
prescs=[]
for i,(rid,pid,did) in enumerate(record_ids[:12]):
    prescs.append((f'pres-{i+1:04d}',f'RX-2026-{i+1:04d}',pid,did,rid,(today-dt.timedelta(days=2+i)).isoformat(),'Demo prescription for testing only.','active',now.isoformat(),now.isoformat()))
ins('prescriptions',['uuid','prescription_number','patient_id','doctor_id','medical_record_id','prescription_date','instructions','status','created_at','updated_at'],prescs)
pres_ids=[r for r in c.execute('select id from prescriptions order by id')]
med_names=['Paracetamol','Cetirizine','Metformin','Lisinopril']
items=[]
for i,(presid,) in enumerate(pres_ids):
    name=med_names[i%len(med_names)]
    items.append((presid,name,name,'500mg' if name=='Paracetamol' else '10mg','as directed','7 days','oral','Synthetic demo instruction; follow clinician prescription.'))
ins('prescription_items',['prescription_id','medication_name','generic_name','dosage','frequency','duration','route','instructions'],items)

# Invoices, invoice items and payments
invoice_rows=[]
for i in range(12):
    pid=patient_ids[f'P2026-{i+1:04d}']; amount=80.0+(i%4)*20
    paid=amount if i<8 else round(amount/2,2)
    status='paid' if paid==amount else 'partial'
    invoice_rows.append((f'INV-2026-{i+1:04d}',pid,(today-dt.timedelta(days=i%10)).isoformat(),(today+dt.timedelta(days=20)).isoformat(),amount,0,0,amount,paid,amount-paid,status,'cash',1,paid,'Synthetic demo invoice',now.isoformat(),admin_id))
ins('invoices',['invoice_number','patient_id','invoice_date','due_date','subtotal','tax_amount','discount_amount','total_amount','paid_amount','balance_due','status','payment_method','insurance_claimed','insurance_amount','notes','created_at','created_by'],invoice_rows)
inv_ids=[r for r in c.execute('select id,invoice_number from invoices order by id')]
items=[]
for i,(iid,num) in enumerate(inv_ids):
    items.append((iid,'General Consultation','CONS001','Synthetic demo service',1,80.0+(i%4)*20,80.0+(i%4)*20))
ins('invoice_items',['invoice_id','service_name','service_code','description','quantity','unit_price','total_price'],items)
for i,(iid,num) in enumerate(inv_ids[:8]):
    amount=80.0+(i%4)*20
    ins('payments',['invoice_id','payment_date','amount','payment_method','transaction_id','reference_number','notes','recorded_by'],[(iid,f'{today-dt.timedelta(days=i%8)}T13:00:00',amount,'cash',f'DEMO-TXN-{i+1:04d}',f'DEMO-REF-{i+1:04d}','Synthetic demo payment',admin_id)])

# Notifications for patients/doctors
for i in range(8):
    uid=c.execute("select id from users where role='patient' order by id limit 1 offset ?",(i,)).fetchone()[0]
    ins('notifications',['user_id','title','message','notification_type','entity_type','entity_id','link','is_read','read_at','created_at'],[(uid,'Appointment confirmed','Your synthetic demo appointment is confirmed.','appointment','appointment',appointment_ids[i][0],'/appointments',0,None,now.isoformat())])

conn.commit()

print('Demo database created:', DB)
for table in ['users','patients','appointments','medical_records','prescriptions','lab_tests','vital_signs','invoices','invoice_items','payments','notifications']:
    print(f'{table}:', c.execute(f'select count(*) from {table}').fetchone()[0])
if DEMO_PASSWORD_FROM_ENV:
    print('\nDemo password for all accounts: from CLINIQUE_DEMO_PASSWORD (not printed)')
else:
    print("\nDemo password for all accounts (DEMO-ONLY default): Demo123!")
print('WARNING: seeded accounts are demo-only — change or remove them before any real deployment.')
print('Patient login examples: patient01@example.com')
print('Doctor login: dr.amina.benali@clinique-demo.example')
print('Admin login: admin@clinique-demo.example')
conn.close()

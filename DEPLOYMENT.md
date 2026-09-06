# تشغيل النسخة الكاملة

## 1. قاعدة البيانات الدائمة

هذه النسخة تستخدم PostgreSQL في الإنتاج. شغّل PostgreSQL مع:

```bash
docker compose up -d postgres
```

ثم ثبّت المتطلبات وشغّل ترحيل قاعدة البيانات القديمة:

```bash
pip install -r requirements.txt
python scripts/migrate_sqlite_to_postgres.py
```

بعد الترحيل، شغّل التطبيق:

```bash
python run.py
```

قاعدة البيانات محفوظة في Docker volume باسم `clinic_postgres_data`، لذلك لا تضيع عند إعادة تشغيل الحاوية.

## 2. Qwen

مفتاح Qwen موجود في `.env` لهذا الـdeployment. لا تضعه في JavaScript أو Git.

النموذج الافتراضي هو `qwen3.8-max-0902`.

## 3. n8n

شغّل:

```bash
docker compose up -d n8n
```

ثم افتح n8n واستورد:

- `n8n/01_appointment_events.json`
- `n8n/02_24h_reminders.json`

قبل إرسال البريد الحقيقي، أضف SMTP credential داخل n8n. لا يوجد بريد SMTP في المشروع لأن كلمة مرور البريد لم تُعطَ.

## 4. الترتيب الكامل

```text
Website
  -> Flask
  -> PostgreSQL

Patient/Doctor Chatbot
  -> Flask
  -> Qwen
  -> clinic tools
  -> PostgreSQL

Appointment event
  -> n8n
  -> email confirmation

24h reminder
  -> n8n
  -> email reminder
```

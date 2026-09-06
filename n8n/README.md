# n8n for the clinic

These workflows connect the clinic website to email.

## 1. Appointment Events

File: `01_appointment_events.json`

The Flask app sends an event when an appointment is:

- booked
- cancelled
- moved

n8n receives the event and sends an email to the patient when an email is available.

## 2. 24-hour Reminders

File: `02_24h_reminders.json`

The workflow runs every hour.

It asks Flask for appointments that are about 24 hours away. It sends one email per appointment and then marks the reminder as sent.

## n8n settings

Set these environment values:

```env
CLINIC_BASE_URL=http://127.0.0.1:5000
N8N_API_KEY=the-same-secret-used-by-Flask
MAIL_DEFAULT_SENDER=noreply@example.com
```

If n8n runs in Docker and Flask runs on the host, use a host address that the container can reach, such as:

```env
CLINIC_BASE_URL=http://host.docker.internal:5000
```

Create one SMTP credential in n8n for the email nodes.

## Flask settings

In `.env`:

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/clinic-appointment-events
N8N_API_KEY=the-same-secret-used-by-n8n
CLINIC_TIMEZONE=Africa/Tunis
```

The API key is only used between Flask and n8n.

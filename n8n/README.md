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

Events are sent for appointments created, cancelled or rescheduled from BOTH
the chatbot and the staff web pages, and the event payload always carries the
patient's email (`patient_email`) — without it, workflow 1 can never send.

## n8n Cloud (deployed instance)

The clinic owner's instance: `https://koussay.app.n8n.cloud`

- Workflow 1 (Appointment Events) is imported there in a Cloud-adapted copy:
  the webhook checks the `x-n8n-api-key` header itself (Flask already sends
  it), because n8n Cloud has no per-instance environment variables like a
  self-hosted install. Flask side stays unchanged apart from the URL:
  `N8N_WEBHOOK_URL=https://koussay.app.n8n.cloud/webhook/clinic-appointment-events`
- Workflow 2 (24h Reminders) is imported but left **inactive**: it polls
  Flask, and the clinic app has no public URL yet, so Cloud cannot reach it.
  On the day the clinic is deployed publicly, set the real base URL in the
  two HTTP nodes (currently a placeholder) and activate it.
- Email delivery needs one SMTP credential inside n8n, attached to the
  "Send Email" nodes. Until it exists, executions reach the email step and
  fail there — everything before it (webhook, key check, formatting) works.

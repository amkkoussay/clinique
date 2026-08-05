"""
Clinic Management Platform - Chatbot Routes
===========================================
Routes for the AI-powered medical chatbot assistant.
"""

from flask import Blueprint, render_template, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime
import uuid
import json
import re

from models import db, ChatbotConversation, Patient, Appointment, Service

chatbot_bp = Blueprint('chatbot', __name__)


def get_or_create_session():
    """Get or create chatbot session ID."""
    if 'chatbot_session' not in session:
        session['chatbot_session'] = str(uuid.uuid4())
    return session['chatbot_session']


def detect_intent(message):
    """Detect user intent from message."""
    message_lower = message.lower()
    
    # Symptom checking
    if any(word in message_lower for word in ['symptom', 'pain', 'hurt', 'fever', 'cough', 'headache', 'sick', 'feel']):
        return 'symptom_check'
    
    # Appointment booking
    if any(word in message_lower for word in ['appointment', 'book', 'schedule', 'visit', 'see doctor']):
        return 'appointment_booking'
    
    # Services inquiry
    if any(word in message_lower for word in ['service', 'treatment', 'procedure', 'cost', 'price']):
        return 'services_inquiry'
    
    # Working hours
    if any(word in message_lower for word in ['hour', 'open', 'close', 'time', 'when']):
        return 'working_hours'
    
    # Location
    if any(word in message_lower for word in ['location', 'address', 'where', 'find']):
        return 'location'
    
    # Emergency
    if any(word in message_lower for word in ['emergency', 'urgent', 'critical', '911']):
        return 'emergency'
    
    # Greeting
    if any(word in message_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
        return 'greeting'
    
    # Goodbye
    if any(word in message_lower for word in ['bye', 'goodbye', 'thank', 'thanks']):
        return 'goodbye'
    
    return 'general'


def get_symptom_response(message):
    """Generate response for symptom checking."""
    message_lower = message.lower()
    
    # Simple symptom checker (in production, this would use ML/AI)
    responses = {
        'fever': "Fever can indicate various conditions. If your temperature is above 103°F (39.4°C) or persists for more than 3 days, please schedule an appointment with a doctor immediately.",
        'headache': "Headaches can be caused by stress, dehydration, or other factors. If you experience severe headaches, vision changes, or headaches that don't improve with rest, please consult a doctor.",
        'cough': "A cough can be a sign of a cold, flu, or allergies. If you have difficulty breathing, chest pain, or cough up blood, seek immediate medical attention.",
        'chest pain': "CHEST PAIN can be serious. If you're experiencing severe chest pain, please call emergency services (911) immediately or go to the nearest emergency room.",
        'stomach': "Stomach issues can range from minor to serious. If you have severe pain, vomiting blood, or signs of dehydration, please seek immediate medical care.",
        'rash': "Skin rashes can have many causes. If the rash is spreading rapidly, accompanied by fever, or causing severe discomfort, please schedule an appointment.",
        'dizzy': "Dizziness can be caused by various factors. If you experience fainting, severe vertigo, or dizziness with chest pain, please consult a doctor immediately."
    }
    
    for symptom, response in responses.items():
        if symptom in message_lower:
            return response
    
    return "I understand you're not feeling well. To get proper medical advice, I'd recommend scheduling an appointment with one of our doctors. Would you like me to help you book an appointment?"


def get_appointment_response(message, session_data):
    """Handle appointment booking flow."""
    # Check if we're in the middle of booking
    if session_data.get('booking_step') == 'select_date':
        # Extract date from message
        date_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|tomorrow|today)', message.lower())
        if date_match:
            session_data['preferred_date'] = date_match.group(1)
            session_data['booking_step'] = 'select_time'
            return "Great! What time would you prefer? Our clinic is open from 9 AM to 5 PM."
        return "Please provide a valid date (YYYY-MM-DD format) or say 'today' or 'tomorrow'."
    
    if session_data.get('booking_step') == 'select_time':
        # Extract time
        time_match = re.search(r'(\d{1,2}):?(\d{2})?\s*(am|pm)?', message.lower())
        if time_match:
            session_data['preferred_time'] = time_match.group(0)
            session_data['booking_step'] = 'confirm'
            return f"Perfect! So you'd like an appointment on {session_data.get('preferred_date')} at {session_data.get('preferred_time')}. Would you like me to confirm this booking?"
        return "Please provide a valid time (e.g., '10:00 AM' or '2:30 PM')."
    
    if session_data.get('booking_step') == 'confirm':
        if any(word in message.lower() for word in ['yes', 'confirm', 'book', 'ok']):
            session_data['booking_step'] = None
            return "Your appointment request has been noted. Please visit our appointments page or call us to complete the booking. You can also provide your patient ID if you're an existing patient."
        else:
            session_data['booking_step'] = 'select_date'
            return "No problem. Let's start over. What date would you prefer for your appointment?"
    
    # Start booking flow
    session_data['booking_step'] = 'select_date'
    return "I'd be happy to help you book an appointment! What date would you prefer? (You can say 'today', 'tomorrow', or provide a date like '2024-01-15')"


def get_services_response():
    """Get list of services."""
    services = Service.query.filter_by(is_active=True).limit(10).all()
    
    if services:
        service_list = ", ".join([s.service_name for s in services])
        return f"We offer a variety of services including: {service_list}. Would you like more details about any specific service?"
    
    return "We offer comprehensive medical services including consultations, laboratory tests, vaccinations, and more. Please visit our services page for detailed information."


def generate_response(message, session_id):
    """Generate chatbot response based on message."""
    # Get conversation history for context
    history = ChatbotConversation.query.filter_by(
        session_id=session_id
    ).order_by(ChatbotConversation.created_at.desc()).limit(5).all()
    
    # Get or initialize session data
    session_data = {}
    if history:
        try:
            last_response = json.loads(history[0].response)
            session_data = last_response.get('session_data', {})
        except:
            pass
    
    intent = detect_intent(message)
    
    # Generate response based on intent
    if intent == 'symptom_check':
        response_text = get_symptom_response(message)
    elif intent == 'appointment_booking':
        response_text = get_appointment_response(message, session_data)
    elif intent == 'services_inquiry':
        response_text = get_services_response()
    elif intent == 'working_hours':
        response_text = "Our clinic is open Monday to Friday from 9:00 AM to 5:00 PM, and Saturday from 9:00 AM to 1:00 PM. We are closed on Sundays."
    elif intent == 'location':
        response_text = "We're located at 123 Healthcare Street, Medical City. You can find directions on our contact page."
    elif intent == 'emergency':
        response_text = "If this is a medical emergency, please call 911 immediately or go to the nearest emergency room. For urgent but non-emergency situations, please call our clinic."
    elif intent == 'greeting':
        response_text = "Hello! Welcome to our clinic. I'm your virtual assistant. How can I help you today?"
    elif intent == 'goodbye':
        response_text = "Thank you for chatting with me! If you need any assistance, feel free to ask. Have a great day!"
    else:
        response_text = "I'm here to help! You can ask me about symptoms, book appointments, learn about our services, or get clinic information. What would you like to know?"
    
    # Save conversation
    conversation = ChatbotConversation(
        session_id=session_id,
        message=message,
        response=response_text,
        intent=intent
    )
    db.session.add(conversation)
    db.session.commit()
    
    return {
        'response': response_text,
        'intent': intent,
        'session_data': session_data
    }


@chatbot_bp.route('/')
@login_required
def index():
    """Chatbot interface page."""
    session_id = get_or_create_session()
    
    # Get conversation history
    history = ChatbotConversation.query.filter_by(
        session_id=session_id
    ).order_by(ChatbotConversation.created_at).all()
    
    return render_template('chatbot/index.html',
                         history=history,
                         title='Medical Assistant')


@chatbot_bp.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chatbot interaction."""
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
    
    message = data['message'].strip()
    session_id = get_or_create_session()
    
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Generate response
    result = generate_response(message, session_id)
    
    return jsonify({
        'response': result['response'],
        'intent': result['intent'],
        'timestamp': datetime.utcnow().isoformat()
    })


@chatbot_bp.route('/api/history')
@login_required
def api_history():
    """API endpoint to get chat history."""
    session_id = get_or_create_session()
    
    conversations = ChatbotConversation.query.filter_by(
        session_id=session_id
    ).order_by(ChatbotConversation.created_at).all()
    
    return jsonify([{
        'message': c.message,
        'response': c.response,
        'timestamp': c.created_at.isoformat()
    } for c in conversations])


@chatbot_bp.route('/api/clear', methods=['POST'])
@login_required
def api_clear_history():
    """Clear chat history."""
    session_id = get_or_create_session()
    
    ChatbotConversation.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    
    # Generate new session ID
    session['chatbot_session'] = str(uuid.uuid4())
    
    return jsonify({'message': 'History cleared successfully'})


@chatbot_bp.route('/widget')
def widget():
    """Chatbot widget for embedding."""
    return render_template('chatbot/widget.html')


# Quick replies for common questions
QUICK_REPLIES = {
    'symptom_check': [
        "I have a fever",
        "I have a headache",
        "I have stomach pain",
        "I have a cough"
    ],
    'appointment': [
        "Book an appointment",
        "Check available slots",
        "Reschedule my appointment"
    ],
    'information': [
        "What services do you offer?",
        "What are your working hours?",
        "Where are you located?"
    ]
}


@chatbot_bp.route('/api/quick-replies')
def api_quick_replies():
    """API endpoint for quick reply suggestions."""
    return jsonify(QUICK_REPLIES)

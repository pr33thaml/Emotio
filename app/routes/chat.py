from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime

from app.services.ai import AIService
from app.services.emotion import EmotionService

bp = Blueprint('chat', __name__, url_prefix='/chat')
ai_service = AIService()
emotion_service = EmotionService()

@bp.route('/', methods=['GET', 'POST'])
@login_required
def chat():
    if request.method == 'GET':
        return render_template('chat.html')
    
    try:
        data = request.get_json()
        message = data.get('message')
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Message is required'}), 400

        # Detect mood from message
        mood = emotion_service.detect_mood(message)
        
        # Generate AI response
        ai_response = ai_service.get_chat_response(message, mood)

        # Save the conversation
        db.chat_messages.insert_one({
            'user_id': ObjectId(current_user.id),
            'message': message,
            'response': ai_response,
            'mood': mood,
            'timestamp': datetime.now()
        })

        return jsonify({
            'status': 'success',
            'response': ai_response,
            'mood': mood
        })

    except Exception as e:
        print(f"Error in chat: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/history')
@login_required
def get_chat_history():
    try:
        messages = list(db.chat_messages.find(
            {'user_id': ObjectId(current_user.id)}
        ).sort('timestamp', -1).limit(50))
        
        return jsonify({
            'status': 'success',
            'messages': messages
        })
    except Exception as e:
        print(f"Error getting chat history: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/mood')
@login_required
def get_current_mood():
    try:
        # Get recent messages
        recent_messages = list(db.chat_messages.find(
            {'user_id': ObjectId(current_user.id)}
        ).sort('timestamp', -1).limit(10))
        
        # Calculate emotional score
        emotional_score = emotion_service.calculate_emotional_score(recent_messages)
        
        # Get average mood emoji
        mood_emoji = emotion_service.get_avg_mood_emoji(recent_messages)
        
        return jsonify({
            'status': 'success',
            'emotional_score': emotional_score,
            'mood_emoji': mood_emoji
        })
    except Exception as e:
        print(f"Error getting mood: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 
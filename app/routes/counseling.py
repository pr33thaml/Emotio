from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from bson import ObjectId
from datetime import datetime

from app.models.session import CounselingSession
from app.services.ai import AIService

bp = Blueprint('counseling', __name__, url_prefix='/counseling')
ai_service = AIService()

@bp.route('/', methods=['GET', 'POST'])
@login_required
def counseling():
    if request.method == 'GET':
        return render_template('counseling.html')
    
    try:
        data = request.get_json()
        message = data.get('message')
        session_id = data.get('session_id')
        session_type = data.get('session_type', 'general')
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Message is required'}), 400

        # Get or create counseling session
        if not session_id:
            session_data = CounselingSession.create(current_user.id, session_type)
            session_id = str(session_data['_id'])
            db.counseling_sessions.insert_one(session_data)
        
        # Get session data
        session = db.counseling_sessions.find_one({'_id': ObjectId(session_id)})
        
        # Generate AI response
        ai_response = ai_service.get_counseling_response(
            message, 
            session_type,
            session.get('goals', [])
        )

        # Save the conversation
        db.counseling_sessions.update_one(
            {'_id': ObjectId(session_id)},
            {'$push': {'messages': {
                'user_message': message,
                'ai_response': ai_response,
                'timestamp': datetime.now()
            }}}
        )

        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'response': ai_response,
            'session_type': session_type
        })

    except Exception as e:
        print(f"Error in counseling session: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/sessions')
@login_required
def get_counseling_sessions():
    try:
        sessions = list(db.counseling_sessions.find(
            {'user_id': ObjectId(current_user.id)},
            {'messages': {'$slice': -1}}
        ).sort('created_at', -1))
        
        return jsonify({
            'status': 'success',
            'sessions': sessions
        })
    except Exception as e:
        print(f"Error getting counseling sessions: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/summary/<session_id>')
@login_required
def get_counseling_summary(session_id):
    try:
        session = db.counseling_sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': ObjectId(current_user.id)
        })
        
        if not session:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        # Generate summary
        messages = [msg['user_message'] for msg in session.get('messages', [])]
        summary = ai_service.generate_session_summary(messages)
        
        return jsonify({
            'status': 'success',
            'summary': summary,
            'session_type': session.get('session_type', 'general'),
            'goals': session.get('goals', []),
            'exercises': session.get('exercises', []),
            'messages': session.get('messages', [])
        })
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500 
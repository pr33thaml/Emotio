from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.services.emotion import EmotionService

bp = Blueprint('insights', __name__)
emotion_service = EmotionService()

@bp.route('/mood-analysis')
@login_required
def get_mood_analysis():
    entries = list(db.journal_entries.find({'user_id': current_user.id}))
    analysis = emotion_service.analyze_journal_sentiment(entries)
    return jsonify(analysis) 
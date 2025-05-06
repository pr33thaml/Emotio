from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.journal import JournalEntry
from app.services.insights import InsightsService

bp = Blueprint('insights', __name__)
insights_service = InsightsService()

@bp.route('/insights')
@login_required
def insights():
    entries = JournalEntry.get_user_entries(current_user.id)
    mood_trends = insights_service.analyze_mood_trends(entries)
    common_emotions = insights_service.get_common_emotions(entries)
    recommendations = insights_service.get_recommendations(entries)
    
    return render_template('insights.html',
                         mood_trends=mood_trends,
                         common_emotions=common_emotions,
                         recommendations=recommendations) 
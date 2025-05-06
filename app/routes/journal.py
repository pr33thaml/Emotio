from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models.journal import JournalEntry
from app.services.emotion import EmotionService
from datetime import datetime

bp = Blueprint('journal', __name__)
emotion_service = EmotionService()

@bp.route('/journal')
@login_required
def journal():
    entries = JournalEntry.get_user_entries(current_user.id)
    return render_template('journal.html', entries=entries)

@bp.route('/journal/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    if request.method == 'POST':
        content = request.form.get('content')
        if content:
            # Analyze emotion
            emotion = emotion_service.analyze_emotion(content)
            
            # Create entry
            entry = JournalEntry(
                user_id=current_user.id,
                content=content,
                emotion=emotion,
                timestamp=datetime.utcnow()
            )
            entry.save()
            
            flash('Journal entry saved successfully!', 'success')
            return redirect(url_for('journal.journal'))
    
    return render_template('new_entry.html')

@bp.route('/journal/<entry_id>')
@login_required
def view_entry(entry_id):
    entry = JournalEntry.get_by_id(entry_id)
    if entry and entry.user_id == current_user.id:
        return render_template('view_entry.html', entry=entry)
    flash('Entry not found', 'error')
    return redirect(url_for('journal.journal'))

@bp.route('/entries', methods=['GET'])
@login_required
def get_entries():
    entries = list(db.journal_entries.find({'user_id': current_user.id}))
    return jsonify(entries)

@bp.route('/entries', methods=['POST'])
@login_required
def create_entry():
    data = request.get_json()
    entry = {
        'user_id': current_user.id,
        'content': data.get('content'),
        'timestamp': datetime.utcnow()
    }
    db.journal_entries.insert_one(entry)
    return jsonify({'message': 'Entry created successfully'}) 
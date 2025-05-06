from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from datetime import datetime

bp = Blueprint('journal', __name__)

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
from flask_login import UserMixin
from bson import ObjectId
from datetime import datetime

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data.get('email')
        self.created_at = user_data.get('created_at', datetime.utcnow())
        self.mood_history = user_data.get('mood_history', [])
        self.journal_entries = user_data.get('journal_entries', [])
        self.bmi_history = user_data.get('bmi_history', [])

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at,
            'mood_history': self.mood_history,
            'journal_entries': self.journal_entries,
            'bmi_history': self.bmi_history
        }

    @staticmethod
    def create(username, email, password=None, google_id=None):
        user_data = {
            'username': username,
            'email': email,
            'created_at': datetime.utcnow()
        }
        
        if password:
            from werkzeug.security import generate_password_hash
            user_data['password'] = generate_password_hash(password)
        
        if google_id:
            user_data['google_id'] = google_id
            
        return user_data

    def add_mood_entry(self, mood):
        self.mood_history.append({
            'mood': mood,
            'timestamp': datetime.utcnow()
        })

    def add_journal_entry(self, content, mood):
        self.journal_entries.append({
            'content': content,
            'mood': mood,
            'timestamp': datetime.utcnow()
        })

    def add_bmi_entry(self, bmi):
        self.bmi_history.append({
            'bmi': bmi,
            'timestamp': datetime.utcnow()
        }) 
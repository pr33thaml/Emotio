from datetime import datetime
from app import db
from bson import ObjectId

class JournalEntry:
    def __init__(self, user_id, content, emotion, timestamp=None):
        self.user_id = user_id
        self.content = content
        self.emotion = emotion
        self.timestamp = timestamp or datetime.utcnow()

    def save(self):
        entry_data = {
            'user_id': ObjectId(self.user_id),
            'content': self.content,
            'emotion': self.emotion,
            'timestamp': self.timestamp
        }
        result = db.journal_entries.insert_one(entry_data)
        self.id = str(result.inserted_id)
        return self.id

    @staticmethod
    def get_by_id(entry_id):
        entry_data = db.journal_entries.find_one({'_id': ObjectId(entry_id)})
        if entry_data:
            entry = JournalEntry(
                user_id=str(entry_data['user_id']),
                content=entry_data['content'],
                emotion=entry_data['emotion'],
                timestamp=entry_data['timestamp']
            )
            entry.id = str(entry_data['_id'])
            return entry
        return None

    @staticmethod
    def get_user_entries(user_id):
        entries = []
        cursor = db.journal_entries.find(
            {'user_id': ObjectId(user_id)}
        ).sort('timestamp', -1)
        
        for entry_data in cursor:
            entry = JournalEntry(
                user_id=str(entry_data['user_id']),
                content=entry_data['content'],
                emotion=entry_data['emotion'],
                timestamp=entry_data['timestamp']
            )
            entry.id = str(entry_data['_id'])
            entries.append(entry)
        
        return entries 
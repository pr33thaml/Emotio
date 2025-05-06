from bson import ObjectId
from datetime import datetime

class CounselingSession:
    def __init__(self, session_data):
        self.id = str(session_data['_id'])
        self.user_id = str(session_data['user_id'])
        self.messages = session_data.get('messages', [])
        self.session_type = session_data.get('session_type', 'general')
        self.goals = session_data.get('goals', [])
        self.exercises = session_data.get('exercises', [])
        self.created_at = session_data.get('created_at', datetime.utcnow())
        self.status = session_data.get('status', 'active')

    @staticmethod
    def create(user_id, session_type='general'):
        return {
            '_id': ObjectId(),
            'user_id': ObjectId(user_id),
            'messages': [],
            'session_type': session_type,
            'goals': [],
            'exercises': [],
            'created_at': datetime.utcnow(),
            'status': 'active'
        }

    def add_message(self, user_message, ai_response):
        self.messages.append({
            'user_message': user_message,
            'ai_response': ai_response,
            'timestamp': datetime.utcnow()
        })

    def add_goal(self, goal):
        self.goals.append(goal)

    def add_exercise(self, exercise):
        self.exercises.append(exercise)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'messages': self.messages,
            'session_type': self.session_type,
            'goals': self.goals,
            'exercises': self.exercises,
            'created_at': self.created_at,
            'status': self.status
        } 
from datetime import datetime
from app import db
from bson import ObjectId

class ChatService:
    def __init__(self):
        self.default_responses = {
            'greeting': [
                "Hello! How are you feeling today?",
                "Hi there! I'm here to listen and support you.",
                "Welcome! How can I help you today?"
            ],
            'sad': [
                "I'm sorry to hear you're feeling down. Would you like to talk about what's bothering you?",
                "It's okay to feel sad sometimes. I'm here to listen if you want to share more.",
                "Remember that difficult times are temporary. Would you like to discuss what's on your mind?"
            ],
            'anxious': [
                "I notice you might be feeling anxious. Would you like to try some breathing exercises?",
                "It's natural to feel anxious sometimes. Let's talk about what's causing this feeling.",
                "I'm here to help you work through your anxiety. What's on your mind?"
            ],
            'happy': [
                "I'm glad to hear you're feeling good! What's bringing you joy today?",
                "That's wonderful! Would you like to share what's making you happy?",
                "It's great to see you in a positive mood! What's been going well?"
            ],
            'default': [
                "I'm here to listen and support you. Would you like to tell me more?",
                "Thank you for sharing. How does that make you feel?",
                "I understand. Would you like to explore this further?"
            ]
        }

    def get_response(self, message, user_id):
        # Simple response logic based on keywords
        message = message.lower()
        
        if any(word in message for word in ['hello', 'hi', 'hey']):
            return self._get_random_response('greeting')
        elif any(word in message for word in ['sad', 'unhappy', 'depressed', 'down']):
            return self._get_random_response('sad')
        elif any(word in message for word in ['anxious', 'worried', 'nervous', 'stress']):
            return self._get_random_response('anxious')
        elif any(word in message for word in ['happy', 'joy', 'excited', 'great']):
            return self._get_random_response('happy')
        else:
            return self._get_random_response('default')

    def _get_random_response(self, category):
        import random
        return random.choice(self.default_responses[category])

    def save_conversation(self, user_id, message, response):
        try:
            db.chat_messages.insert_one({
                'user_id': ObjectId(user_id),
                'message': message,
                'response': response,
                'timestamp': datetime.utcnow()
            })
        except Exception as e:
            print(f"Error saving conversation: {str(e)}") 
import os
import json
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from oauthlib.oauth2 import WebApplicationClient
import openai
import requests
from textblob import TextBlob  # Sentiment analysis for mood detection
from transformers import pipeline
import numpy as np
from collections import Counter
import secrets
from urllib.parse import urlencode

# Load environment variables
load_dotenv()

import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Environment safety checks
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OPENROUTER_API_KEY]):
    raise EnvironmentError("Missing one of: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OPENROUTER_API_KEY")

# Initialize app
app = Flask(__name__, 
    template_folder='app/templates',
    static_folder='app/static')
app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

# Configure OpenAI with OpenRouter
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = OPENROUTER_API_KEY
openai.api_version = "v1"
openai.api_type = "openai"

# Define OpenRouter headers
OPENROUTER_HEADERS = {
    "HTTP-Referer": "http://localhost:5000",  # Your app URL
    "X-Title": "Emotio App"
}

# MongoDB
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.emotio_db
users = db.users
conversations = db.conversations

# Ensure the users collection has the required indexes
users.create_index([('email', 1)], unique=True)
users.create_index([('journal_entries.timestamp', -1)])

# OAuth2 setup
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
oauth_client = WebApplicationClient(GOOGLE_CLIENT_ID)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET')
GITHUB_REDIRECT_URI = os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:5000/github-callback')

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data.get('email')

@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# Emotion Detection using TextBlob
def detect_mood(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.5:
        return "happy"
    elif polarity < -0.3:
        return "sad"
    else:
        return "neutral"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_data = users.find_one({'username': username})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            session['username'] = username
            session['show_welcome'] = True  # Set flag to show welcome message
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        if users.find_one({'$or': [{'username': username}, {'email': email}]}):
            return render_template('signup.html', error="Username or email already exists")
        hashed_password = generate_password_hash(password)
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.utcnow()
        }
        users.insert_one(user_data)
        user = User(user_data)
        login_user(user)
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/login/google')
def google_login():
    google_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    auth_uri = oauth_client.prepare_request_uri(
        google_cfg["authorization_endpoint"],
        redirect_uri=url_for('google_callback', _external=True),
        scope=["openid", "email", "profile"]
    )
    return redirect(auth_uri)

@app.route('/login/google/callback')
def google_callback():
    code = request.args.get("code")
    google_cfg = requests.get(GOOGLE_DISCOVERY_URL).json()
    token_endpoint = google_cfg["token_endpoint"]

    token_url, headers, body = oauth_client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=url_for('google_callback', _external=True),
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
    oauth_client.parse_request_body_response(json.dumps(token_response.json()))

    userinfo_endpoint = google_cfg["userinfo_endpoint"]
    uri, headers, body = oauth_client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body).json()

    if userinfo_response.get("email_verified"):
        email = userinfo_response["email"]
        username = email.split('@')[0]
        user_data = users.find_one({'email': email})
        if not user_data:
            user_data = {
                'username': username,
                'email': email,
                'google_id': userinfo_response["sub"],
                'created_at': datetime.utcnow()
            }
            users.insert_one(user_data)
        user = User(user_data)
        login_user(user)
        session['username'] = username
        session['show_welcome'] = True  # Set flag to show welcome message
        return redirect(url_for('home'))
    return "Email not verified", 400

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile/update-name', methods=['POST'])
@login_required
def update_name():
    try:
        data = request.get_json()
        new_name = data.get('name')
        
        if not new_name:
            return jsonify({'status': 'error', 'message': 'Name is required'}), 400
            
        # Update the user's name in MongoDB
        users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': {'name': new_name}}
        )
        
        return jsonify({'status': 'success', 'message': 'Name updated successfully'})
        
    except Exception as e:
        print(f"Error updating name: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            data = request.get_json()
            updates = {}
            
            # Update basic profile info
            if 'name' in data:
                updates['name'] = data['name']
            if 'bio' in data:
                updates['bio'] = data['bio']
            if 'goals' in data:
                updates['goals'] = data['goals']
            
            # Update notification preferences
            if 'notifications' in data:
                updates['notifications'] = {
                    'email': data['notifications'].get('email', False),
                    'reminders': data['notifications'].get('reminders', False),
                    'streak_alerts': data['notifications'].get('streak_alerts', False)
                }
            
            # Update privacy settings
            if 'privacy' in data:
                updates['privacy'] = {
                    'share_mood': data['privacy'].get('share_mood', False),
                    'share_goals': data['privacy'].get('share_goals', False),
                    'share_progress': data['privacy'].get('share_progress', False)
                }
            
            # Update the user's profile
            users.update_one(
                {'_id': ObjectId(current_user.id)},
                {'$set': updates}
            )
            
            return jsonify({'status': 'success', 'message': 'Profile updated successfully'})
            
        except Exception as e:
            print(f"Error updating profile: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    # GET method - return profile data
    try:
        user = users.find_one({'_id': ObjectId(current_user.id)})
        if not user:
            return jsonify({'status': 'error', 'message': 'User not found'}), 404
        
        # Get stored streak from MongoDB
        stored_streak = user.get('streak', 0)
        
        # Get last mood check time
        last_mood_check = None
        if user.get('mood_history'):
            last_mood = max(user['mood_history'], key=lambda x: x['timestamp'])
            last_mood_check = last_mood['timestamp']
        
        # Get user stats
        stats = {
            'total_entries': len(user.get('journal_entries', [])),
            'total_moods': len(user.get('mood_history', [])),
            'streak': stored_streak,
            'average_mood': get_avg_mood_emoji(user),
            'wellness_scores': {
                'physical': calculate_physical_score(user),
                'mental': calculate_mental_score(user),
                'emotional': calculate_emotional_score(user)
            },
            'last_mood_check': last_mood_check
        }
        
        # Format profile data
        profile_data = {
            'name': user.get('name', ''),
            'email': user.get('email', ''),
            'bio': user.get('bio', ''),
            'goals': user.get('goals', []),
            'notifications': user.get('notifications', {
                'email': False,
                'reminders': False,
                'streak_alerts': False
            }),
            'privacy': user.get('privacy', {
                'share_mood': False,
                'share_goals': False,
                'share_progress': False
            }),
            'stats': stats,
            'created_at': user.get('created_at', datetime.utcnow())
        }
        
        return render_template('profile.html', user_data=profile_data)
        
    except Exception as e:
        print(f"Error getting profile: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def calculate_streak(user_data):
    mood_history = user_data.get('mood_history', [])
    if not mood_history:
        return 0
    
    # Sort mood history by timestamp
    mood_history.sort(key=lambda x: x['timestamp'])
    
    streak = 0
    current_date = datetime.utcnow().date()
    last_date = mood_history[-1]['timestamp'].date()
    
    # If last entry was today or yesterday, start counting
    if last_date == current_date or last_date == current_date - timedelta(days=1):
        streak = 1
        # Check previous days
        for i in range(2, len(mood_history) + 1):
            prev_date = mood_history[-i]['timestamp'].date()
            expected_date = last_date - timedelta(days=i-1)
            if prev_date == expected_date:
                streak += 1
            else:
                break
    
    return streak

@app.route('/track-mood', methods=['POST'])
@login_required
def track_mood():
    try:
        data = request.get_json()
        mood = data.get('mood')
        context = data.get('context', '')
        
        if not mood:
            return jsonify({'status': 'error', 'message': 'Mood is required'}), 400
        
        # Create mood entry
        mood_entry = {
            'mood': mood,
            'context': context,
            'timestamp': datetime.utcnow()
        }
        
        # Update user's mood history
        users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$push': {'mood_history': mood_entry}}
        )
        
        # Update streak
        user = users.find_one({'_id': ObjectId(current_user.id)})
        streak = calculate_streak(user)
        
        return jsonify({
            'status': 'success',
            'message': 'Mood tracked successfully',
            'streak': streak
        })
        
    except Exception as e:
        print(f"Error tracking mood: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Load once during app start
emotion_classifier = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=False)

@app.route('/analyze_emotion', methods=['POST'])
def analyze_emotion():
    data = request.get_json()
    message = data.get('message', '')

    if not message:
        return jsonify({'emotion': 'neutral'})

    # Run the classifier
    result = emotion_classifier(message)[0]
    emotion = result['label'].lower()

    return jsonify({'emotion': emotion})

@app.route("/get-response", methods=["POST"])
@login_required
def get_response():
    data = request.get_json()
    user_input = data.get("user_input", "")
    user_mood = detect_mood(user_input)  # Detect mood based on input
    
    try:
        # Enhanced system prompt with focus on emotional support and goal-setting
        system_prompt = """You are an emotionally supportive AI companion focused on mental health, emotional well-being, and personal growth. 
Your primary role is to provide emotional support, guidance, and help with goal-setting.

GUIDELINES:
1. For emotional support and mental health:
   - Provide empathetic responses
   - Offer coping strategies
   - Help process emotions
   - Suggest self-care practices

2. For goal-setting and personal development:
   - Help create SMART (Specific, Measurable, Achievable, Relevant, Time-bound) goals
   - Provide specific, actionable steps
   - Break down larger goals into manageable tasks
   - Offer accountability and progress tracking suggestions

3. For off-topic questions (like cars, technology, sports, etc.):
   - Gently redirect to emotional aspects
   - Focus on how the topic affects their well-being
   - Encourage discussion of feelings and emotions

4. Response Format:
   - For emotional topics: Provide supportive, empathetic responses
   - For goal-setting: Give specific, actionable goals and steps
   - For off-topic questions: Redirect to emotional aspects
   - For crisis situations: Encourage seeking professional help

5. When setting goals:
   - Make them specific and measurable
   - Ensure they are achievable
   - Provide clear steps or actions
   - Include timeframes when appropriate
   - Consider emotional impact and well-being

Remember: Your purpose is to support emotional well-being while helping users achieve their personal goals in a healthy, balanced way."""

        if user_mood == "sad":
            system_prompt += "\nThe user is feeling sad. Respond with extra empathy and warmth, offering specific coping strategies."
        elif user_mood == "happy":
            system_prompt += "\nThe user is feeling happy. Celebrate their positive emotions and encourage them to build on this momentum."
        else:
            system_prompt += "\nThe user feels neutral. Be supportive and help them explore their emotions."
        
        # Make the API call to OpenRouter
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=500,
            headers=OPENROUTER_HEADERS
        )
        
        if response and hasattr(response, 'choices') and response.choices:
            reply = response.choices[0].message.content.strip()
            
            # Ensure the response is complete and appropriate
            if reply.endswith(('.', '!', '?')):
                # Store conversation in database
                conversations.insert_one({
                    'user_id': ObjectId(current_user.id),
                    'user_message': user_input,
                    'ai_response': reply,
                    'timestamp': datetime.utcnow()
                })
                
                return jsonify({"reply": reply})
            else:
                # If response is incomplete, try to get a complete response
                retry_response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt + " Ensure your response is complete and ends with proper punctuation."},
                        {"role": "user", "content": user_input}
                    ],
                    temperature=0.7,
                    max_tokens=500,
                    headers=OPENROUTER_HEADERS
                )
                
                if retry_response and hasattr(retry_response, 'choices') and retry_response.choices:
                    complete_reply = retry_response.choices[0].message.content.strip()
                    
                    # Store conversation in database
                    conversations.insert_one({
                        'user_id': ObjectId(current_user.id),
                        'user_message': user_input,
                        'ai_response': complete_reply,
                        'timestamp': datetime.utcnow()
                    })
                    
                    return jsonify({"reply": complete_reply})
        
        return jsonify({"reply": "I'm here to support your emotional well-being. How are you feeling today?"})
            
    except Exception as e:
        print(f"OpenRouter API error: {str(e)}")
        return jsonify({"reply": "I'm here to support your emotional well-being. How are you feeling today?"})

@app.route('/quick-support', methods=['POST'])
@login_required
def quick_support():
    data = request.get_json()
    support_type = data.get('type')
    
    # Define support responses based on type
    support_responses = {
        'Breathing Exercise': "Let's do a quick breathing exercise. Breathe in for 4 seconds, hold for 4 seconds, and exhale for 4 seconds. Repeat this 5 times. Focus on your breath and let go of any tension.",
        'Positive Affirmations': "You are stronger than you think. Every day is a new opportunity to grow and learn. You are capable of handling whatever comes your way.",
        'Sleep Tips': "Try to maintain a regular sleep schedule. Avoid screens an hour before bed. Create a calming bedtime routine. Your mind and body need rest to function at their best.",
        'Mindfulness': "Take a moment to focus on the present. Notice your surroundings, your breath, and how you feel. There's no need to judge or change anything right now."
    }
    
    return jsonify({'response': support_responses.get(support_type, "I'm here to support you.")})

@app.route('/user-data')
@login_required
def get_user_data():
    user_data = users.find_one({'_id': ObjectId(current_user.id)})
    
    # Calculate statistics
    total_conversations = conversations.count_documents({'user_id': ObjectId(current_user.id)})
    
    # Calculate average mood from last 7 days
    mood_history = user_data.get('mood_history', [])
    recent_moods = [m['mood'] for m in mood_history if m['timestamp'] > datetime.utcnow() - timedelta(days=7)]
    mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
    avg_mood_score = np.mean([mood_scores.get(m, 3) for m in recent_moods]) if recent_moods else 3
    avg_mood_emoji = {5: '😄', 4: '😊', 3: '😐', 2: '😰', 1: '😢'}.get(round(avg_mood_score), '😐')
    
    # Calculate streak
    streak = 0
    if mood_history:
        last_date = mood_history[-1]['timestamp'].date()
        current_date = datetime.utcnow().date()
        if last_date == current_date:
            streak = 1
            for i in range(len(mood_history)-2, -1, -1):
                if mood_history[i]['timestamp'].date() == last_date - timedelta(days=1):
                    streak += 1
                    last_date = mood_history[i]['timestamp'].date()
                else:
                    break
    
    # Get common emotions
    emotion_counter = Counter([m['mood'] for m in mood_history])
    total_emotions = sum(emotion_counter.values())
    common_emotions = [
        {'name': mood, 'percentage': round(count/total_emotions*100) if total_emotions > 0 else 0}
        for mood, count in emotion_counter.most_common(5)
    ]
    
    # Get emotional triggers (simplified version)
    triggers = [
        {'emoji': '😰', 'description': 'Work-related stress'},
        {'emoji': '😊', 'description': 'Positive social interactions'},
        {'emoji': '😢', 'description': 'Loneliness'}
    ]
    
    # Get recent journal entries
    journal_entries = [
        {
            'date': entry['timestamp'].strftime('%Y-%m-%d'),
            'content': entry['content']
        }
        for entry in user_data.get('journal_entries', [])[-5:]  # Last 5 entries
    ]
    
    return jsonify({
        'totalConversations': total_conversations,
        'averageMood': avg_mood_emoji,
        'streak': streak,
        'commonEmotions': common_emotions,
        'triggers': triggers,
        'journalEntries': journal_entries
    })

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

app.json_encoder = JSONEncoder

@app.route('/journal', methods=['GET', 'POST'])
@login_required
def journal():
    if request.method == 'GET':
        return render_template('journal.html')
    
    # POST method handling
    try:
        data = request.get_json()
        content = data.get('content')
        mood = data.get('mood')
        
        if not content or not mood:
            return jsonify({'status': 'error', 'message': 'Content and mood are required'}), 400

        # Create a new journal entry
        new_entry = {
            '_id': ObjectId(),
            'content': content,
            'mood': mood,
            'timestamp': datetime.now()
        }

        # Update the user's document to add the new journal entry
        result = users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$push': {'journal_entries': new_entry}}
        )

        if result.modified_count > 0:
            return jsonify({
                'status': 'success',
                'message': 'Journal entry saved successfully',
                'entry': {
                    '_id': str(new_entry['_id']),
                    'content': new_entry['content'],
                    'mood': new_entry['mood'],
                    'timestamp': new_entry['timestamp'].isoformat()
                }
            })
        else:
            return jsonify({'status': 'error', 'message': 'Failed to save journal entry'}), 500

    except Exception as e:
        print(f"Error saving journal entry: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/journal-entries')
@login_required
def get_journal_entries():
    try:
        user = users.find_one({'_id': ObjectId(current_user.id)})
        if not user or 'journal_entries' not in user:
            return jsonify([])

        # Get the last 10 entries, reverse them to show newest first, and convert ObjectId to string
        entries = user['journal_entries'][-10:][::-1]  # Get last 10 and reverse the order
        for entry in entries:
            entry['_id'] = str(entry['_id'])
            if isinstance(entry['timestamp'], datetime):
                entry['timestamp'] = entry['timestamp'].isoformat()

        return jsonify(entries)
    except Exception as e:
        print(f"Error retrieving journal entries: {str(e)}")
        return jsonify([])

@app.route('/analyze-journal')
@login_required
def analyze_journal():
    user_data = users.find_one({'_id': ObjectId(current_user.id)})
    journal_entries = user_data.get('journal_entries', [])
    
    if len(journal_entries) < 3:
        return jsonify({'error': 'Need at least 3 entries to analyze'}), 400
    
    # Get the last 5 entries for analysis
    recent_entries = journal_entries[-5:]
    entries_text = ' '.join([entry['content'] for entry in recent_entries])
    
    # Use OpenAI to analyze the entries
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a journal analysis assistant. Generate a structured report with clear sections and proper formatting. Use numbered sections and bullet points where appropriate. Do not use markdown symbols like ## or **. Keep each point on a new line."},
                {"role": "user", "content": f"Analyze these journal entries and provide a structured report:\n\n{entries_text}"}
            ],
            max_tokens=800
        )
        
        # Get the AI analysis
        ai_analysis = response.choices[0].message.content.strip()
        
        # Format the emotional analysis section
        emotional_analysis = f"""
1. Emotional Statistics
   • Total Entries Analyzed: {len(recent_entries)}
   • Dominant Mood: {detect_mood(entries_text)}
   • Mood Distribution:
     {chr(10).join(f"  - {mood}: {count} entries" for mood, count in Counter(entry['mood'] for entry in recent_entries).items())}

2. Emotional Overview
   {ai_analysis}

3. Key Themes
   {', '.join(word for word, count in Counter(entries_text.split()).most_common(5) if len(word) > 3)}

4. Insights & Patterns
   {', '.join(word for word, count in Counter(entries_text.split()).most_common(5) if len(word) > 3 and word.isupper())}

5. Recommendations
   {', '.join(word for word, count in Counter(entries_text.split()).most_common(5) if len(word) > 3 and word.endswith('!') or word.endswith('?'))}
"""

        return jsonify({
            'status': 'success',
            'emotional_analysis': emotional_analysis,
            'key_themes': [word for word, count in Counter(entries_text.split()).most_common(5) if len(word) > 3],
            'recommendations': [word for word, count in Counter(entries_text.split()).most_common(5) if len(word) > 3 and (word.endswith('!') or word.endswith('?'))]
        })
        
    except Exception as e:
        print(f"Error analyzing journal: {str(e)}")
        return jsonify({'error': 'Error analyzing journal entries'}), 500

@app.route('/insights')
@login_required
def insights():
    return render_template('insights.html')

@app.route('/insights-data')
@login_required
def insights_data():
    try:
        user = users.find_one({'_id': ObjectId(current_user.id)})
        period = request.args.get('period', 'week')
        
        # Calculate time range based on period
        now = datetime.utcnow()
        if period == 'week':
            start_date = now - timedelta(days=7)
        elif period == 'month':
            start_date = now - timedelta(days=30)
        else:  # year
            start_date = now - timedelta(days=365)
        
        # Get mood history from both mood_history and journal entries
        mood_history = []
        
        # Add mood entries from mood_history
        mood_history.extend([m for m in user.get('mood_history', []) 
                           if m['timestamp'] >= start_date])
        
        # Add mood entries from journal entries
        journal_entries = user.get('journal_entries', [])
        mood_history.extend([{
            'mood': entry.get('mood', 'neutral'),
            'timestamp': entry.get('timestamp', now)
        } for entry in journal_entries if entry.get('timestamp') >= start_date])
        
        # Sort mood history by timestamp
        mood_history.sort(key=lambda x: x['timestamp'])
        
        # Calculate mood data
        mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
        mood_data = []
        mood_labels = []
        
        if period == 'week':
            # Daily mood for the week
            for i in range(7):
                date = now - timedelta(days=i)
                day_moods = [m for m in mood_history 
                            if m['timestamp'].date() == date.date()]
                avg_mood = np.mean([mood_scores.get(m['mood'], 3) for m in day_moods]) if day_moods else 3
                mood_data.insert(0, avg_mood)
                mood_labels.insert(0, date.strftime('%a'))
        else:
            # Weekly averages for month/year
            weeks = []
            current_week = []
            for mood in reversed(mood_history):
                if not current_week or (current_week[0]['timestamp'] - mood['timestamp']).days < 7:
                    current_week.append(mood)
                else:
                    weeks.append(current_week)
                    current_week = [mood]
            if current_week:
                weeks.append(current_week)
            
            for week in weeks:
                avg_mood = np.mean([mood_scores.get(m['mood'], 3) for m in week])
                mood_data.append(avg_mood)
                mood_labels.append(week[0]['timestamp'].strftime('%b %d'))
        
        # Time of day analysis
        time_slots = {
            'Morning': (6, 12),
            'Afternoon': (12, 18),
            'Evening': (18, 22),
            'Night': (22, 6)
        }
        time_data = []
        for slot, (start, end) in time_slots.items():
            if start > end:  # Night slot
                slot_moods = [m for m in mood_history 
                             if m['timestamp'].hour >= start or m['timestamp'].hour < end]
            else:
                slot_moods = [m for m in mood_history 
                             if start <= m['timestamp'].hour < end]
            avg_mood = np.mean([mood_scores.get(m['mood'], 3) for m in slot_moods]) if slot_moods else 3
            time_data.append(avg_mood)
        
        # Calculate best time of day
        best_time_index = np.argmax(time_data)
        best_time = list(time_slots.keys())[best_time_index]
        
        # Calculate mood triggers
        mood_triggers = "Not enough data"
        if len(mood_history) >= 2:  # Reduced threshold to 2 entries
            mood_changes = []
            for i in range(1, len(mood_history)):
                prev_mood = mood_history[i-1]['mood']
                curr_mood = mood_history[i]['mood']
                if prev_mood != curr_mood:
                    mood_changes.append(f"{prev_mood} → {curr_mood}")
            if mood_changes:
                pattern_counter = Counter(mood_changes)
                most_common = pattern_counter.most_common(2)
                triggers = []
                for pattern, count in most_common:
                    if count > 1:
                        triggers.append(f"{pattern} ({count} times)")
                mood_triggers = ", ".join(triggers) if triggers else "No clear patterns"
        
        # Calculate weekly pattern
        weekly_pattern = "Not enough data"
        if len(mood_history) >= 2:  # Reduced threshold to 2 entries
            weekly_moods = {i: [] for i in range(7)}
            for mood in mood_history:
                day_of_week = mood['timestamp'].weekday()
                weekly_moods[day_of_week].append(mood)
            
            day_avg_moods = {}
            for day, moods in weekly_moods.items():
                if moods:
                    avg_mood = np.mean([mood_scores.get(m['mood'], 3) for m in moods])
                    day_avg_moods[day] = avg_mood
            
            if day_avg_moods:
                # Sort days by average mood score
                sorted_days = sorted(day_avg_moods.items(), key=lambda x: x[1])
                worst_day = sorted_days[0]
                best_day = sorted_days[-1]
                
                # Only show different days
                if worst_day[0] != best_day[0]:
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    weekly_pattern = f"Best on {days[best_day[0]]}, Challenging on {days[worst_day[0]]}"
                else:
                    # If all days have the same mood, show a different message
                    weekly_pattern = "Mood remains consistent"
        
        # Generate mood insights
        mood_insights = "Not enough data"
        if len(mood_history) >= 2:  # Reduced threshold to 2 entries
            mood_values = [mood_scores.get(m['mood'], 3) for m in mood_history]
            avg_mood = np.mean(mood_values)
            mood_std = np.std(mood_values)
            stability = "stable" if mood_std < 1 else "variable"
            mood_counter = Counter([m['mood'] for m in mood_history])
            most_common_mood = mood_counter.most_common(1)[0][0]
            
            # Calculate mood distribution
            mood_distribution = []
            total_moods = len(mood_history)
            for mood, count in mood_counter.items():
                percentage = (count / total_moods) * 100
                mood_distribution.append(f"{mood}: {percentage:.1f}%")
            
            if period == 'week':
                mood_insights = f"Your mood has been {stability} this week, with {most_common_mood} being the most common mood. Mood distribution: {', '.join(mood_distribution)}"
            elif period == 'month':
                mood_insights = f"Over the past month, your mood has been {stability}, with {most_common_mood} being the most common mood. Mood distribution: {', '.join(mood_distribution)}"
            else:
                mood_insights = f"Looking at the past year, your mood has been {stability}, with {most_common_mood} being the most common mood. Mood distribution: {', '.join(mood_distribution)}"
        
        # Calculate wellness scores
        physical_score = calculate_physical_score(user)
        mental_score = calculate_mental_score(user)
        emotional_score = calculate_emotional_score(user)
        
        # Calculate trends
        prev_period = 'week' if period == 'week' else 'month'
        prev_start_date = now - timedelta(days=7 if prev_period == 'week' else 30)
        prev_mood_history = [m for m in mood_history 
                            if m['timestamp'] >= prev_start_date and m['timestamp'] < prev_start_date + timedelta(days=7 if prev_period == 'week' else 30)]
        
        prev_physical_score = calculate_physical_score({'mood_history': prev_mood_history}) if prev_mood_history else physical_score
        prev_mental_score = calculate_mental_score({'mood_history': prev_mood_history}) if prev_mood_history else mental_score
        prev_emotional_score = calculate_emotional_score({'mood_history': prev_mood_history}) if prev_mood_history else emotional_score
        
        physical_trend = physical_score - prev_physical_score
        mental_trend = mental_score - prev_mental_score
        emotional_trend = emotional_score - prev_emotional_score
        
        # Get stored streak from MongoDB
        streak = user.get('streak', 0)
        
        # Calculate total entries and average mood
        total_entries = len(mood_history)
        avg_mood = get_avg_mood_emoji(user)
        
        return jsonify({
            'moodData': mood_data,
            'moodLabels': mood_labels,
            'timeData': time_data,
            'bestTime': best_time,
            'moodTriggers': mood_triggers,
            'weeklyPattern': weekly_pattern,
            'moodInsights': mood_insights,
            'physicalScore': physical_score,
            'mentalScore': mental_score,
            'emotionalScore': emotional_score,
            'physicalTrend': physical_trend,
            'mentalTrend': mental_trend,
            'emotionalTrend': emotional_trend,
            'streak': streak,
            'totalEntries': total_entries,
            'averageMood': avg_mood
        })
        
    except Exception as e:
        print(f"Error in insights_data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/track-bmi', methods=['POST'])
@login_required
def track_bmi():
    try:
        data = request.get_json()
        height = float(data.get('height'))
        weight = float(data.get('weight'))
        
        bmi = weight / ((height / 100) ** 2)
        category = get_bmi_category(bmi)
        
        # Generate AI analysis using OpenRouter
        analysis_prompt = f"""
        Based on a BMI of {bmi:.1f} ({category}), provide a brief, friendly, and supportive analysis.
        Include:
        1. What this BMI means for their health
        2. Simple, actionable suggestions for improvement
        3. A positive, encouraging tone
        Keep it under 100 words.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a supportive health assistant providing BMI analysis."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=150
            )
            analysis = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenRouter API error: {str(e)}")
            analysis = f"Your BMI of {bmi:.1f} falls in the {category} category. Consider consulting a healthcare professional for personalized advice."
        
        # Store BMI in user's history
        users.update_one(
            {'_id': ObjectId(current_user.id)},
            {
                '$push': {
                    'bmi_history': {
                        'bmi': bmi,
                        'timestamp': datetime.utcnow()
                    }
                }
            }
        )
        
        return jsonify({
            'bmi': bmi,
            'category': category,
            'analysis': analysis
        })
    except Exception as e:
        print(f"Error in track_bmi: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_bmi_category(bmi):
    if bmi < 18.5:
        return 'Underweight'
    elif bmi < 25:
        return 'Normal weight'
    elif bmi < 30:
        return 'Overweight'
    else:
        return 'Obese'

def calculate_physical_score(user_data):
    bmi_history = user_data.get('bmi_history', [])
    if not bmi_history:
        return 50  # Default score
    
    latest_bmi = bmi_history[-1]['bmi']
    if 18.5 <= latest_bmi <= 24.9:
        return 80
    elif 25 <= latest_bmi <= 29.9:
        return 60
    elif latest_bmi < 18.5:
        return 40
    else:
        return 30

def calculate_mental_score(user_data):
    journal_entries = user_data.get('journal_entries', [])
    mood_history = user_data.get('mood_history', [])
    
    if not journal_entries or not mood_history:
        return 50  # Default score
    
    # Analyze journal sentiment
    sentiment_scores = []
    for entry in journal_entries[-5:]:  # Last 5 entries
        blob = TextBlob(entry['content'])
        sentiment_scores.append(blob.sentiment.polarity)
    
    avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
    mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
    avg_mood = np.mean([mood_scores.get(m['mood'], 3) for m in mood_history[-7:]]) if mood_history else 3
    
    return int((avg_sentiment + 1) * 25 + (avg_mood / 5) * 25)  # Scale to 0-100

def calculate_emotional_score(user_data):
    mood_history = user_data.get('mood_history', [])
    if not mood_history:
        return 50  # Default score
    
    # Calculate mood consistency
    mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
    recent_moods = [mood_scores.get(m['mood'], 3) for m in mood_history[-7:]]
    mood_std = np.std(recent_moods) if len(recent_moods) > 1 else 0
    
    # Lower standard deviation indicates more emotional stability
    stability_score = max(0, 100 - (mood_std * 20))
    
    return int(stability_score)

def get_avg_mood_emoji(user_data):
    mood_history = user_data.get('mood_history', [])
    if not mood_history:
        return '😐'
    
    mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
    recent_moods = [mood_scores.get(m['mood'], 3) for m in mood_history[-7:]]
    avg_mood = np.mean(recent_moods) if recent_moods else 3
    
    emojis = {5: '😄', 4: '😊', 3: '😐', 2: '😰', 1: '😢'}
    return emojis.get(round(avg_mood), '😐')

@app.route('/analyze-journal/<entry_id>')
@login_required
def analyze_journal_entry(entry_id):
    user_data = users.find_one({'_id': ObjectId(current_user.id)})
    entries = user_data.get('journal_entries', [])
    
    # Find the specific entry
    entry = next((e for e in entries if str(e['_id']) == entry_id), None)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    
    # Analyze the entry using TextBlob
    blob = TextBlob(entry['content'])
    
    # Determine emotional tone
    polarity = blob.sentiment.polarity
    if polarity > 0.5:
        emotional_tone = "Very Positive"
    elif polarity > 0:
        emotional_tone = "Positive"
    elif polarity < -0.5:
        emotional_tone = "Very Negative"
    elif polarity < 0:
        emotional_tone = "Negative"
    else:
        emotional_tone = "Neutral"
    
    # Extract key themes (simple implementation)
    words = blob.words
    common_words = Counter(words).most_common(5)
    key_themes = [word for word, count in common_words if len(word) > 3]
    
    # Generate suggestions based on emotional tone
    suggestions = []
    if polarity < 0:
        suggestions.append("Consider practicing gratitude by listing three things you're thankful for.")
        suggestions.append("Try a short mindfulness exercise to center yourself.")
    elif polarity > 0:
        suggestions.append("Build on this positive momentum by setting a small, achievable goal.")
        suggestions.append("Share your positive experience with someone you care about.")
    else:
        suggestions.append("Reflect on what might help you feel more engaged or fulfilled.")
        suggestions.append("Consider trying a new activity or hobby to spark joy.")
    
    return jsonify({
        'emotionalTone': emotional_tone,
        'keyThemes': key_themes,
        'suggestions': suggestions
    })

@app.route('/edit-entry/<entry_id>', methods=['POST'])
@login_required
def edit_entry(entry_id):
    try:
        data = request.get_json()
        content = data.get('content')
        mood = data.get('mood')
        
        if not content or not mood:
            return jsonify({'status': 'error', 'message': 'Content and mood are required'}), 400

        # Update the specific journal entry
        result = users.update_one(
            {
                '_id': ObjectId(current_user.id),
                'journal_entries._id': ObjectId(entry_id)
            },
            {
                '$set': {
                    'journal_entries.$.content': content,
                    'journal_entries.$.mood': mood,
                    'journal_entries.$.timestamp': datetime.now()
                }
            }
        )

        if result.modified_count > 0:
            return jsonify({'status': 'success', 'message': 'Entry updated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to update entry'}), 500

    except Exception as e:
        print(f"Error updating entry: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete-entry/<entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    try:
        result = users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$pull': {'journal_entries': {'_id': ObjectId(entry_id)}}}
        )

        if result.modified_count > 0:
            return jsonify({'status': 'success', 'message': 'Entry deleted successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete entry'}), 500

    except Exception as e:
        print(f"Error deleting entry: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete-entries', methods=['POST'])
@login_required
def delete_entries():
    try:
        data = request.get_json()
        entry_ids = [ObjectId(id) for id in data.get('entry_ids', [])]
        
        result = users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$pull': {'journal_entries': {'_id': {'$in': entry_ids}}}}
        )

        if result.modified_count > 0:
            return jsonify({'status': 'success', 'message': 'Entries deleted successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete entries'}), 500

    except Exception as e:
        print(f"Error deleting entries: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/delete-all-entries', methods=['POST'])
@login_required
def delete_all_entries():
    try:
        result = users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': {'journal_entries': []}}
        )

        if result.modified_count > 0:
            return jsonify({'status': 'success', 'message': 'All entries deleted successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to delete entries'}), 500

    except Exception as e:
        print(f"Error deleting all entries: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/generate-report', methods=['POST'])
@login_required
def generate_report():
    try:
        data = request.get_json()
        entry_ids = [ObjectId(id) for id in data.get('entry_ids', [])]
        
        # Get the selected entries
        user = users.find_one({'_id': ObjectId(current_user.id)})
        if not user or 'journal_entries' not in user:
            return jsonify({'status': 'error', 'message': 'No entries found'}), 404

        # Filter entries by selected IDs
        selected_entries = [entry for entry in user['journal_entries'] if entry['_id'] in entry_ids]
        if not selected_entries:
            return jsonify({'status': 'error', 'message': 'No selected entries found'}), 404

        # Prepare entries text for AI analysis
        entries_text = '\n\n'.join([
            f"Entry from {entry['timestamp'].strftime('%Y-%m-%d')} (Mood: {entry['mood']}):\n{entry['content']}"
            for entry in selected_entries
        ])

        # Calculate mood statistics
        mood_stats = Counter(entry['mood'] for entry in selected_entries)
        dominant_mood = max(mood_stats.items(), key=lambda x: x[1])[0]
        mood_distribution = '\n'.join(f"  • {mood.capitalize()}: {count} entries" for mood, count in mood_stats.items())

        # Use OpenAI to analyze the entries with a more focused prompt
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are a supportive journal analysis assistant. Generate a clear, structured report that helps the user understand their emotional patterns and provides specific, helpful recommendations.

Format the report with these sections:
1. Emotional Overview
   • Key emotional patterns observed
   • Most common emotional states
   • Notable changes in mood

2. Key Themes
   • Main topics discussed
   • Recurring subjects
   • Important events or situations

3. Insights & Patterns
   • Specific triggers identified
   • Time-based patterns
   • Situational patterns

4. Personalized Recommendations

   Specific Recommendations:
   • Practice deep breathing exercises during moments of anxiety, especially before or during heavy traffic drives
   • Journal about confusing emotions to gain clarity and understanding of inner feelings
   • Engage in regular social interactions to maintain a positive emotional balance

   Practical Exercises:
   • Progressive muscle relaxation to reduce anxiety levels
   • Gratitude journaling to focus on positive experiences and emotions

   Daily Practices:
   • Set aside time for meditation to promote a sense of calm and inner peace
   • Reflect on daily activities to acknowledge and process emotions effectively

Keep each section concise and focused. Use bullet points for clarity. Make recommendations highly personalized based on their actual journal entries and emotional patterns."""},
                {"role": "user", "content": f"Analyze these journal entries and provide a helpful, actionable report:\n\n{entries_text}"}
            ],
            max_tokens=1000
        )
        
        # Get the AI analysis
        ai_analysis = response.choices[0].message.content.strip()
        
        # Format the emotional analysis section
        emotional_analysis = f"""
1. Emotional Statistics
   • Total Entries Analyzed: {len(selected_entries)}
   • Dominant Mood: {dominant_mood.capitalize()}
   • Mood Distribution:
{mood_distribution}

{ai_analysis}
"""

        return jsonify({
            'status': 'success',
            'emotional_analysis': emotional_analysis
        })

    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# AI Counseling Session Routes
@app.route('/counseling', methods=['GET', 'POST'])
@login_required
def counseling():
    if request.method == 'GET':
        return render_template('counseling.html')
    
    try:
        data = request.get_json()
        message = data.get('message')
        session_id = data.get('session_id')
        session_type = data.get('session_type', 'general')  # New parameter for session type
        
        if not message:
            return jsonify({'status': 'error', 'message': 'Message is required'}), 400

        # Get or create counseling session
        if not session_id:
            session_id = str(ObjectId())
            counseling_session = {
                '_id': ObjectId(session_id),
                'user_id': ObjectId(current_user.id),
                'messages': [],
                'session_type': session_type,
                'goals': [],
                'exercises': [],
                'created_at': datetime.now(),
                'status': 'active'
            }
            db.counseling_sessions.insert_one(counseling_session)
        
        # Get session data
        session = db.counseling_sessions.find_one({'_id': ObjectId(session_id)})
        
        # Generate AI response with specialized prompts based on session type
        system_prompt = "You are a professional counselor providing supportive and empathetic guidance. "
        
        if session_type == 'cbt':
            system_prompt += """
            Use Cognitive Behavioral Therapy techniques:
            1. Help identify negative thought patterns
            2. Challenge cognitive distortions
            3. Suggest behavioral experiments
            4. Provide worksheets and exercises
            """
        elif session_type == 'mindfulness':
            system_prompt += """
            Focus on mindfulness and meditation:
            1. Guide through breathing exercises
            2. Teach body scan techniques
            3. Provide grounding exercises
            4. Suggest daily mindfulness practices
            """
        elif session_type == 'stress':
            system_prompt += """
            Address stress management:
            1. Identify stress triggers
            2. Teach relaxation techniques
            3. Suggest time management strategies
            4. Provide stress reduction exercises
            """
        else:
            system_prompt += "Focus on active listening, validation, and evidence-based therapeutic techniques."
        
        # Add session context to the prompt
        if session and session.get('goals'):
            system_prompt += f"\nSession Goals: {', '.join(session['goals'])}"
        
        # Generate response
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
        )
        
        ai_response = response.choices[0].message.content

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

@app.route('/counseling-sessions')
@login_required
def get_counseling_sessions():
    try:
        sessions = list(db.counseling_sessions.find(
            {'user_id': ObjectId(current_user.id)},
            {'messages': {'$slice': -1}}  # Get only the last message
        ).sort('created_at', -1))
        
        return jsonify({
            'status': 'success',
            'sessions': sessions
        })
    except Exception as e:
        print(f"Error getting counseling sessions: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/counseling-summary/<session_id>')
@login_required
def get_counseling_summary(session_id):
    try:
        session = db.counseling_sessions.find_one({
            '_id': ObjectId(session_id),
            'user_id': ObjectId(current_user.id)
        })
        
        if not session:
            return jsonify({'status': 'error', 'message': 'Session not found'}), 404
        
        # Generate summary using OpenAI
        messages = [msg['user_message'] for msg in session.get('messages', [])]
        summary_prompt = f"""
        Generate a counseling session summary based on the following conversation:
        {messages}
        
        Include:
        1. Key insights and patterns
        2. Progress made
        3. Recommended next steps
        4. Therapeutic techniques used
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional counselor creating session summaries."},
                {"role": "user", "content": summary_prompt}
            ]
        )
        
        summary = response.choices[0].message.content
        
        return jsonify({
            'status': 'success',
            'summary': summary,
            'session_type': session.get('session_type', 'general'),
            'goals': session.get('goals', []),
            'exercises': session.get('exercises', []),
            'messages': session.get('messages', [])  # Include messages in the response
        })
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Mental Health Professionals Integration
@app.route('/professionals', methods=['GET'])
@login_required
def professionals():
    return render_template('professionals.html')

@app.route('/get-professionals', methods=['GET'])
@login_required
def get_professionals():
    try:
        # In a real application, this would query a database of professionals
        # For now, we'll return sample data
        professionals = [
            {
                'id': '1',
                'name': 'Dr. Sarah Johnson',
                'specialty': 'Anxiety & Depression',
                'credentials': 'PhD, LCSW',
                'availability': 'Mon-Fri, 9am-5pm',
                'contact': 'sarah.johnson@example.com'
            },
            {
                'id': '2',
                'name': 'Dr. Michael Chen',
                'specialty': 'Trauma & PTSD',
                'credentials': 'MD, Psychiatrist',
                'availability': 'Tue-Sat, 10am-6pm',
                'contact': 'michael.chen@example.com'
            },
            {
                'id': '3',
                'name': 'Dr. Emily Rodriguez',
                'specialty': 'Family Therapy',
                'credentials': 'LMFT, PhD',
                'availability': 'Wed-Sun, 11am-7pm',
                'contact': 'emily.rodriguez@example.com'
            }
        ]
        
        return jsonify({
            'status': 'success',
            'professionals': professionals
        })
    except Exception as e:
        print(f"Error getting professionals: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/clear-welcome-flag', methods=['POST'])
@login_required
def clear_welcome_flag():
    session.pop('show_welcome', None)
    return jsonify({'status': 'success'})

@app.route('/delete-session/<session_id>', methods=['DELETE'])
@login_required
def delete_counseling_session(session_id):
    try:
        # Delete the session from the database
        result = db.counseling_sessions.delete_one({
            '_id': ObjectId(session_id),
            'user_id': ObjectId(current_user.id)
        })
        
        if result.deleted_count > 0:
            return jsonify({
                'status': 'success',
                'message': 'Session deleted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Session not found'
            }), 404
            
    except Exception as e:
        print(f"Error deleting counseling session: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/github-login')
def github_login():
    """Redirect to GitHub OAuth login page"""
    params = {
        'client_id': GITHUB_CLIENT_ID,
        'redirect_uri': GITHUB_REDIRECT_URI,
        'scope': 'user:email',
        'state': secrets.token_urlsafe(16)
    }
    return redirect(f'https://github.com/login/oauth/authorize?{urlencode(params)}')

@app.route('/github-callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return redirect(url_for('login', error='GitHub login failed'))
    
    # Exchange code for access token
    token_url = 'https://github.com/login/oauth/access_token'
    token_data = {
        'client_id': GITHUB_CLIENT_ID,
        'client_secret': GITHUB_CLIENT_SECRET,
        'code': code,
        'redirect_uri': GITHUB_REDIRECT_URI
    }
    headers = {'Accept': 'application/json'}
    
    try:
        response = requests.post(token_url, data=token_data, headers=headers)
        response.raise_for_status()
        access_token = response.json().get('access_token')
        
        if not access_token:
            return redirect(url_for('login', error='Failed to get access token'))
        
        # Get user info from GitHub
        user_url = 'https://api.github.com/user'
        headers = {'Authorization': f'token {access_token}'}
        response = requests.get(user_url, headers=headers)
        response.raise_for_status()
        user_data = response.json()
        
        # Get user email
        email_url = 'https://api.github.com/user/emails'
        response = requests.get(email_url, headers=headers)
        response.raise_for_status()
        emails = response.json()
        primary_email = next((email['email'] for email in emails if email['primary']), None)
        
        if not primary_email:
            return redirect(url_for('login', error='No primary email found'))
        
        # Check if user exists
        user = User.query.filter_by(email=primary_email).first()
        
        if not user:
            # Create new user
            username = user_data.get('login')
            # Ensure username is unique
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=primary_email,
                password=generate_password_hash(secrets.token_urlsafe(16)),
                created_at=datetime.utcnow()
            )
            db.session.add(user)
            db.session.commit()
        
        # Log in user
        session['user_id'] = user.id
        session['username'] = user.username
        session['last_activity'] = datetime.utcnow()
        
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"GitHub login error: {str(e)}")
        return redirect(url_for('login', error='GitHub login failed'))

if __name__ == "__main__":
    app.run(debug=True)
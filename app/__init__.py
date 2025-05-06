from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__,
           template_folder='templates',
           static_folder='static')
app.secret_key = os.getenv('SECRET_KEY')
CORS(app)

# MongoDB setup
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client.emotio_db

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Import routes
from app.routes import auth, chat, counseling, journal, insights, professionals, main

# Register blueprints
app.register_blueprint(main.bp)
app.register_blueprint(auth.bp)
app.register_blueprint(chat.bp)
app.register_blueprint(counseling.bp)
app.register_blueprint(journal.bp)
app.register_blueprint(insights.bp)
app.register_blueprint(professionals.bp)

# Import and register models
from app.models.user import User
from app.models.session import CounselingSession

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': user_id})
    return User(user_data) if user_data else None 
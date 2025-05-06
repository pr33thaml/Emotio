# Emotio - AI-Powered Emotional Support App

A Flask-based web application that provides emotional support and mental health assistance through AI-powered interactions.

## Features

- AI-powered chat interface
- Mood tracking and analysis
- Journal system
- BMI tracking
- Emotional insights
- User authentication

## Tech Stack

- Flask
- MongoDB
- OpenAI GPT-3.5
- TextBlob for sentiment analysis
- Gunicorn for production

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables:
   - SECRET_KEY
   - MONGODB_URI
   - GOOGLE_CLIENT_ID
   - GOOGLE_CLIENT_SECRET
   - OPENROUTER_API_KEY
4. Run the application: `python app.py`

## Deployment

The application is configured for deployment on Render. See `render.yaml` for configuration details. 
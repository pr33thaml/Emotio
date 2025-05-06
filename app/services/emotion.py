from textblob import TextBlob
import numpy as np
from collections import Counter
from datetime import datetime, timedelta

class EmotionService:
    def __init__(self):
        pass

    def detect_mood(self, text):
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.5:
            return "happy"
        elif polarity < -0.3:
            return "sad"
        else:
            return "neutral"

    def analyze_emotion(self, message):
        if not message:
            return {'emotion': 'neutral'}
        
        blob = TextBlob(message)
        polarity = blob.sentiment.polarity
        
        if polarity > 0.5:
            emotion = 'happy'
        elif polarity > 0.2:
            emotion = 'calm'
        elif polarity < -0.3:
            emotion = 'sad'
        elif polarity < -0.1:
            emotion = 'anxious'
        else:
            emotion = 'neutral'
            
        return {'emotion': emotion}

    def calculate_emotional_score(self, mood_history):
        if not mood_history:
            return 50  # Default score
        
        mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
        recent_moods = [mood_scores.get(m['mood'], 3) for m in mood_history[-7:]]
        mood_std = np.std(recent_moods) if len(recent_moods) > 1 else 0
        
        # Lower standard deviation indicates more emotional stability
        stability_score = max(0, 100 - (mood_std * 20))
        return int(stability_score)

    def get_avg_mood_emoji(self, mood_history):
        if not mood_history:
            return '😐'
        
        mood_scores = {'happy': 5, 'calm': 4, 'neutral': 3, 'anxious': 2, 'sad': 1}
        recent_moods = [mood_scores.get(m['mood'], 3) for m in mood_history[-7:]]
        avg_mood = np.mean(recent_moods) if recent_moods else 3
        
        emojis = {5: '😄', 4: '😊', 3: '😐', 2: '😰', 1: '😢'}
        return emojis.get(round(avg_mood), '😐')

    def analyze_journal_sentiment(self, journal_entries):
        if not journal_entries:
            return {'sentiment': 0, 'key_themes': [], 'emotional_tone': 'neutral'}
        
        # Calculate overall sentiment
        sentiment_scores = []
        for entry in journal_entries:
            blob = TextBlob(entry['content'])
            sentiment_scores.append(blob.sentiment.polarity)
        
        avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
        
        # Extract key themes
        all_words = []
        for entry in journal_entries:
            words = TextBlob(entry['content']).words
            all_words.extend([word.lower() for word in words if len(word) > 3])
        
        word_counter = Counter(all_words)
        key_themes = [word for word, count in word_counter.most_common(5)]
        
        # Determine emotional tone
        if avg_sentiment > 0.5:
            emotional_tone = "Very Positive"
        elif avg_sentiment > 0:
            emotional_tone = "Positive"
        elif avg_sentiment < -0.5:
            emotional_tone = "Very Negative"
        elif avg_sentiment < 0:
            emotional_tone = "Negative"
        else:
            emotional_tone = "Neutral"
        
        return {
            'sentiment': avg_sentiment,
            'key_themes': key_themes,
            'emotional_tone': emotional_tone
        } 
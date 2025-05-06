from textblob import TextBlob
import numpy as np
from collections import Counter
from datetime import datetime, timedelta

class EmotionService:
    def __init__(self):
        pass

    def analyze_emotion(self, text):
        # Use TextBlob for basic sentiment analysis
        analysis = TextBlob(text)
        
        # Get polarity (-1 to 1) and subjectivity (0 to 1)
        polarity = analysis.sentiment.polarity
        subjectivity = analysis.sentiment.subjectivity
        
        # Determine emotion based on polarity and subjectivity
        if polarity > 0.3:
            return 'happy'
        elif polarity < -0.3:
            return 'sad'
        elif subjectivity > 0.5:
            return 'anxious'
        else:
            return 'neutral'

    def detect_mood(self, text):
        return self.analyze_emotion(text)

    def calculate_emotional_score(self, messages):
        if not messages:
            return 0
        
        total_score = 0
        for message in messages:
            emotion = self.analyze_emotion(message.get('message', ''))
            if emotion == 'happy':
                total_score += 1
            elif emotion == 'sad':
                total_score -= 1
            elif emotion == 'anxious':
                total_score -= 0.5
        
        return total_score / len(messages)

    def get_avg_mood_emoji(self, messages):
        if not messages:
            return '😐'
        
        happy_count = 0
        sad_count = 0
        anxious_count = 0
        
        for message in messages:
            emotion = self.analyze_emotion(message.get('message', ''))
            if emotion == 'happy':
                happy_count += 1
            elif emotion == 'sad':
                sad_count += 1
            elif emotion == 'anxious':
                anxious_count += 1
        
        total = len(messages)
        if happy_count / total > 0.5:
            return '😊'
        elif sad_count / total > 0.5:
            return '😢'
        elif anxious_count / total > 0.5:
            return '😰'
        else:
            return '😐'

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
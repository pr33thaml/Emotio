from datetime import datetime, timedelta
from collections import Counter

class InsightsService:
    def analyze_mood_trends(self, entries):
        # Group entries by date and calculate average mood
        mood_data = {}
        for entry in entries:
            date = entry.timestamp.strftime('%Y-%m-%d')
            if date not in mood_data:
                mood_data[date] = []
            mood_data[date].append(entry.emotion)

        # Calculate average mood score for each day
        dates = []
        scores = []
        for date, moods in sorted(mood_data.items()):
            dates.append(date)
            # Simple scoring: positive = 1, neutral = 0, negative = -1
            score = sum(1 if m in ['happy', 'excited'] else -1 if m in ['sad', 'anxious'] else 0 for m in moods) / len(moods)
            scores.append(score)

        return {
            'labels': dates,
            'data': scores
        }

    def get_common_emotions(self, entries):
        # Count occurrences of each emotion
        emotions = [entry.emotion for entry in entries]
        emotion_counts = Counter(emotions)
        
        # Get top 5 emotions
        top_emotions = emotion_counts.most_common(5)
        
        return {
            'labels': [e[0] for e in top_emotions],
            'data': [e[1] for e in top_emotions]
        }

    def get_recommendations(self, entries):
        recommendations = []
        
        # Analyze recent entries (last 7 days)
        recent_entries = [e for e in entries if e.timestamp > datetime.utcnow() - timedelta(days=7)]
        
        if not recent_entries:
            return ["Start journaling to get personalized recommendations!"]
        
        # Count emotions in recent entries
        recent_emotions = Counter(e.emotion for e in recent_entries)
        
        # Generate recommendations based on emotions
        if recent_emotions.get('sad', 0) > recent_emotions.get('happy', 0):
            recommendations.append("Consider trying some mood-lifting activities like exercise or meditation.")
        
        if recent_emotions.get('anxious', 0) > 2:
            recommendations.append("You might benefit from practicing deep breathing exercises daily.")
        
        if len(recent_entries) < 3:
            recommendations.append("Try to journal more frequently to better track your emotional patterns.")
        
        if not recommendations:
            recommendations.append("Keep up the good work! Continue journaling to maintain awareness of your emotions.")
        
        return recommendations 
import openai
import os
from datetime import datetime

class AIService:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-3.5-turbo"
        
    def get_chat_response(self, message, mood=None):
        """Generate a response for general chat"""
        prompt = f"""
        You are a supportive and empathetic AI assistant. The user is feeling {mood if mood else 'neutral'}.
        Respond to their message in a caring and understanding way.
        
        User message: {message}
        """
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a supportive and empathetic AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()
    
    def get_counseling_response(self, message, session_type, previous_messages=None):
        """Generate a response for counseling sessions"""
        system_prompt = self._get_counseling_system_prompt(session_type)
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        if previous_messages:
            messages.extend(previous_messages)
            
        messages.append({"role": "user", "content": message})
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip()
    
    def generate_session_summary(self, session_messages, session_type):
        """Generate a summary of the counseling session"""
        prompt = f"""
        Generate a summary of this {session_type} counseling session. Include:
        1. Key insights and breakthroughs
        2. Progress made
        3. Goals achieved
        4. Recommended exercises
        5. Next steps
        
        Session messages:
        {session_messages}
        """
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a professional counselor summarizing a therapy session."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    
    def _get_counseling_system_prompt(self, session_type):
        """Get the appropriate system prompt based on session type"""
        prompts = {
            'cbt': """
            You are a Cognitive Behavioral Therapy (CBT) counselor. Focus on:
            - Identifying and challenging negative thought patterns
            - Helping the user reframe their thoughts
            - Providing practical exercises for cognitive restructuring
            - Setting achievable goals
            """,
            'mindfulness': """
            You are a Mindfulness counselor. Focus on:
            - Guiding the user through mindfulness exercises
            - Helping them stay present in the moment
            - Teaching breathing techniques
            - Encouraging self-awareness
            """,
            'stress': """
            You are a Stress Management counselor. Focus on:
            - Identifying stress triggers
            - Teaching relaxation techniques
            - Providing coping strategies
            - Helping develop stress management plans
            """,
            'general': """
            You are a general counselor. Focus on:
            - Active listening
            - Empathetic responses
            - Helping the user explore their feelings
            - Providing supportive guidance
            """
        }
        
        return prompts.get(session_type.lower(), prompts['general'])

    def analyze_journal_entries(self, entries_text):
        analysis_prompt = f"""
        Analyze these journal entries and provide insights:
        {entries_text}
        
        Include:
        1. Emotional patterns and trends
        2. Key themes and topics
        3. Recommendations for improvement
        4. Positive aspects to celebrate
        """
        
        response = openai.ChatCompletion.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an emotional analysis AI providing insights on journal entries."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content.strip() 
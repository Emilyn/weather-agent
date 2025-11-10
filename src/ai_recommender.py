"""
AI-powered clothing recommendation engine.
Uses free AI APIs (Groq/Hugging Face) with fallback to rule-based logic.
"""

import os
from typing import Dict, List, Optional
import json


class AIRecommender:
    """Generate clothing recommendations using AI or rule-based logic."""
    
    def __init__(self, groq_api_key: Optional[str] = None, hf_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key
        self.hf_api_key = hf_api_key
        self.use_ai = bool(groq_api_key or hf_api_key)
    
    def generate_recommendation(self, weather_data: Dict) -> str:
        """Generate clothing recommendation based on weather data."""
        if self.use_ai:
            try:
                if self.groq_api_key:
                    return self._generate_with_groq(weather_data)
                elif self.hf_api_key:
                    return self._generate_with_huggingface(weather_data)
            except Exception as e:
                print(f"AI generation failed: {e}, falling back to rule-based")
        
        # Fallback to rule-based logic
        return self._generate_rule_based(weather_data)
    
    def _generate_with_groq(self, weather_data: Dict) -> str:
        """Generate recommendation using Groq API with Llama."""
        try:
            from groq import Groq
            
            client = Groq(api_key=self.groq_api_key)
            
            # Prepare weather summary
            weather_summary = self._format_weather_for_ai(weather_data)
            
            prompt = f"""Based on the following 10-hour weather forecast, provide a concise clothing recommendation (2-3 sentences max).
Focus on practical advice about what to wear.

Weather forecast:
{weather_summary}

Provide a friendly, practical recommendation about what to wear today."""

            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful weather assistant that provides practical clothing advice. Keep responses brief and actionable."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=200
            )
            
            return chat_completion.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Groq API error: {e}")
            raise
    
    def _generate_with_huggingface(self, weather_data: Dict) -> str:
        """Generate recommendation using Hugging Face Inference API."""
        try:
            import requests
            
            API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
            headers = {"Authorization": f"Bearer {self.hf_api_key}"}
            
            weather_summary = self._format_weather_for_ai(weather_data)
            
            prompt = f"""<s>[INST] Based on this 10-hour weather forecast, provide a brief clothing recommendation (2-3 sentences):

{weather_summary}

What should I wear? [/INST]"""

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 150,
                    "temperature": 0.7,
                    "return_full_text": False
                }
            }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0]['generated_text'].strip()
            
            raise Exception("Unexpected response format from Hugging Face")
        
        except Exception as e:
            print(f"Hugging Face API error: {e}")
            raise
    
    def _format_weather_for_ai(self, weather_data: Dict) -> str:
        """Format weather data for AI prompt."""
        hourly = weather_data['hourly_data']
        
        # Get temperature range
        temps = [h['temperature'] for h in hourly]
        min_temp = min(temps)
        max_temp = max(temps)
        
        # Check for precipitation
        total_precip = sum(h['precipitation'] for h in hourly)
        will_rain = total_precip > 1.0
        
        # Get wind info
        max_wind = max(h['wind_speed'] for h in hourly)
        
        # Get most common condition
        conditions = [h['condition'] for h in hourly]
        main_condition = max(set(conditions), key=conditions.count)
        
        summary = f"""Temperature: {min_temp}°C to {max_temp}°C
Conditions: {main_condition}
Precipitation: {total_precip:.1f}mm total {'(rain expected)' if will_rain else '(dry)'}
Wind: up to {max_wind:.1f} m/s
Humidity: {hourly[0]['humidity']}%"""
        
        return summary
    
    def _generate_rule_based(self, weather_data: Dict) -> str:
        """Generate recommendation using rule-based logic."""
        hourly = weather_data['hourly_data']
        
        # Analyze weather
        temps = [h['temperature'] for h in hourly]
        min_temp = min(temps)
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        total_precip = sum(h['precipitation'] for h in hourly)
        will_rain = total_precip > 1.0
        
        max_wind = max(h['wind_speed'] for h in hourly)
        is_windy = max_wind > 8.0
        
        # Build recommendation
        recommendation = []
        
        # Temperature-based clothing
        if avg_temp < 0:
            recommendation.append("🧥 Heavy winter coat, thermal layers, gloves, and a warm hat")
        elif avg_temp < 10:
            recommendation.append("🧥 Warm jacket or coat, long sleeves, and a scarf")
        elif avg_temp < 15:
            recommendation.append("🧥 Light jacket or sweater")
        elif avg_temp < 20:
            recommendation.append("👕 Long sleeves or a light sweater")
        elif avg_temp < 25:
            recommendation.append("👕 T-shirt or light clothing")
        else:
            recommendation.append("👕 Light, breathable clothing, stay hydrated")
        
        # Precipitation
        if will_rain:
            if total_precip > 5:
                recommendation.append("☔ Umbrella and waterproof jacket essential")
            else:
                recommendation.append("☔ Bring an umbrella or rain jacket")
        
        # Wind
        if is_windy:
            recommendation.append("💨 Windproof outer layer recommended")
        
        # Temperature variation
        if max_temp - min_temp > 8:
            recommendation.append("🌡️ Temperature varies - dress in layers")
        
        # Build final message
        intro = f"Temperature: {min_temp}°C to {max_temp}°C. "
        advice = " • ".join(recommendation)
        
        return intro + advice
    
    def format_notification(self, weather_data: Dict, recommendation: str) -> str:
        """Format the complete notification message."""
        hourly = weather_data['hourly_data']
        sources = weather_data['sources_used']
        reliability = weather_data['reliability_score']
        
        # Header
        message = "🌤️ Good Morning! Weather Report\n"
        message += "=" * 35 + "\n\n"
        
        # Summary
        temps = [h['temperature'] for h in hourly]
        message += f"📊 Next 10 Hours Summary:\n"
        message += f"   Temperature: {min(temps)}°C - {max(temps)}°C\n"
        message += f"   Conditions: {hourly[0]['condition']}\n\n"
        
        # Recommendation
        message += f"👔 What to Wear:\n{recommendation}\n\n"
        
        # Hourly breakdown (condensed)
        message += "⏰ Hourly Forecast:\n"
        for i, hour in enumerate(hourly[:10]):
            time_label = f"+{i}h"
            message += f"{time_label:>4}: {hour['temperature']:>4.1f}°C {hour['condition'][:20]}"
            if hour['precipitation'] > 0.5:
                message += f" 💧{hour['precipitation']:.1f}mm"
            message += "\n"
        
        # Footer
        message += f"\n📡 Data from {len(sources)} sources"
        message += f" (Reliability: {reliability*100:.0f}%)\n"
        message += f"Sources: {', '.join(sources[:3])}"
        if len(sources) > 3:
            message += f" +{len(sources)-3} more"
        
        return message


if __name__ == "__main__":
    # Test the AI recommender
    sample_weather = {
        'hourly_data': [
            {'hour': i, 'temperature': 15 + i*0.5, 'precipitation': 0.1 if i < 3 else 0,
             'wind_speed': 5.0, 'humidity': 70, 'condition': 'Partly cloudy'}
            for i in range(10)
        ],
        'sources_used': ['Open-Meteo', 'WeatherAPI', 'wttr.in'],
        'reliability_score': 0.6
    }
    
    groq_key = os.getenv('GROQ_API_KEY')
    recommender = AIRecommender(groq_api_key=groq_key)
    
    recommendation = recommender.generate_recommendation(sample_weather)
    print("Recommendation:", recommendation)
    print("\n" + "="*50 + "\n")
    
    full_notification = recommender.format_notification(sample_weather, recommendation)
    print(full_notification)


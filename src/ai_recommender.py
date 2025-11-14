"""
AI-powered clothing recommendation engine.
Uses free AI APIs (Groq/Hugging Face) - requires at least one API key.
"""

import os
from typing import Dict, List, Optional
import json
from utils import fetch_api_data
from reflection_engine import ReflectionEngine, ReflectionResult


class AIRecommender:
    """Generate clothing recommendations using AI (requires Groq or Hugging Face API key)."""
    
    def __init__(self, groq_api_key: Optional[str] = None, hf_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key
        self.hf_api_key = hf_api_key
        
        if not groq_api_key and not hf_api_key:
            raise ValueError(
                "At least one API key is required. Please provide either GROQ_API_KEY or HUGGINGFACE_API_KEY."
            )
    
    def generate_recommendation(
        self,
        weather_data: Dict,
        reflection_engine: Optional[ReflectionEngine] = None,
        max_refinements: int = 2
    ) -> str:
        """
        Generate clothing recommendation based on weather data using AI.
        Uses reflection pattern to improve quality iteratively.
        
        Args:
            weather_data: Weather data dictionary
            reflection_engine: Optional reflection engine for quality assessment
            max_refinements: Maximum number of refinement iterations
            
        Returns:
            Generated recommendation string
        """
        try:
            # Initial generation
            if self.groq_api_key:
                recommendation = self._generate_with_groq(weather_data)
            elif self.hf_api_key:
                recommendation = self._generate_with_huggingface(weather_data)
            else:
                raise ValueError("No AI API key available")
            
            # Apply reflection pattern if reflection engine provided
            if reflection_engine:
                for iteration in range(max_refinements + 1):
                    # Reflect on the recommendation
                    reflection = reflection_engine.reflect_on_recommendation(
                        recommendation, weather_data
                    )
                    
                    if reflection.passed:
                        if iteration > 0:
                            print(f"   ✓ Recommendation refined (iteration {iteration + 1})")
                        break
                    
                    # If not passed and not last iteration, refine
                    if iteration < max_refinements:
                        print(f"   🔄 Refining recommendation (iteration {iteration + 2})...")
                        print(f"      Issues: {', '.join(reflection.issues[:2])}")
                        
                        # Generate refined recommendation with feedback
                        refined = self._generate_with_feedback(
                            weather_data,
                            reflection.issues,
                            reflection.suggestions
                        )
                        recommendation = refined
                    else:
                        # Last iteration, accept what we have
                        print(f"   ⚠️  Quality threshold not fully met, but proceeding")
                        break
            
            return recommendation
            
        except Exception as e:
            print(f"AI generation failed: {e}")
            raise RuntimeError(f"Failed to generate recommendation with AI: {e}") from e
    
    def _generate_with_groq(
        self,
        weather_data: Dict,
        feedback_issues: Optional[List[str]] = None,
        feedback_suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Generate recommendation using Groq API with Llama.
        
        Args:
            weather_data: Weather data dictionary
            feedback_issues: Optional list of issues from reflection
            feedback_suggestions: Optional list of suggestions from reflection
        """
        try:
            from groq import Groq
            
            client = Groq(api_key=self.groq_api_key)
            
            # Prepare weather summary
            weather_summary = self._format_weather_for_ai(weather_data)
            
            # Build prompt with optional feedback
            base_prompt = f"""Based on the following 10-hour weather forecast, provide a concise clothing recommendation (2-3 sentences max).
Focus on practical advice about what to wear.

Weather forecast:
{weather_summary}"""
            
            if feedback_issues and feedback_suggestions:
                feedback_text = "\n\nPrevious attempt had these issues: " + ", ".join(feedback_issues[:2])
                feedback_text += "\nPlease address: " + ", ".join(feedback_suggestions[:2])
                prompt = base_prompt + feedback_text + "\n\nProvide an improved, friendly, practical recommendation about what to wear today."
            else:
                prompt = base_prompt + "\n\nProvide a friendly, practical recommendation about what to wear today."

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
    
    def _generate_with_feedback(
        self,
        weather_data: Dict,
        issues: List[str],
        suggestions: List[str]
    ) -> str:
        """Generate refined recommendation based on feedback."""
        if self.groq_api_key:
            return self._generate_with_groq(weather_data, issues, suggestions)
        elif self.hf_api_key:
            return self._generate_with_huggingface(weather_data, issues, suggestions)
        else:
            raise ValueError("No AI API key available")
    
    def _generate_with_huggingface(
        self,
        weather_data: Dict,
        feedback_issues: Optional[List[str]] = None,
        feedback_suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Generate recommendation using Hugging Face Inference API.
        
        Args:
            weather_data: Weather data dictionary
            feedback_issues: Optional list of issues from reflection
            feedback_suggestions: Optional list of suggestions from reflection
        """
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        headers = {"Authorization": f"Bearer {self.hf_api_key}"}
        
        weather_summary = self._format_weather_for_ai(weather_data)
        
        base_prompt = f"""<s>[INST] Based on this 10-hour weather forecast, provide a brief clothing recommendation (2-3 sentences):

{weather_summary}"""
        
        if feedback_issues and feedback_suggestions:
            feedback_text = "\n\nPrevious attempt had issues: " + ", ".join(feedback_issues[:2])
            feedback_text += ". Please address: " + ", ".join(feedback_suggestions[:2])
            prompt = base_prompt + feedback_text + "\n\nWhat should I wear? [/INST]"
        else:
            prompt = base_prompt + "\n\nWhat should I wear? [/INST]"

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "return_full_text": False
            }
        }
        
        result = fetch_api_data(
            url=API_URL,
            headers=headers,
            method='POST',
            json_data=payload,
            timeout=30,
            source_name="Hugging Face"
        )
        
        if not result:
            raise Exception("Failed to get response from Hugging Face API")
        
        if isinstance(result, list) and len(result) > 0:
            return result[0]['generated_text'].strip()
        
        raise Exception("Unexpected response format from Hugging Face")
    
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
    
    def _calculate_feels_like(self, temp: float, humidity: float, wind_speed: float) -> float:
        """Calculate 'feels like' temperature using wind chill and heat index formulas."""
        # Convert wind speed from m/s to km/h for calculations
        wind_kmh = wind_speed * 3.6
        
        # Wind chill for cold temperatures (< 10°C)
        if temp < 10 and wind_kmh > 4.8:
            # Wind chill formula (approximate)
            feels_like = 13.12 + 0.6215 * temp - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp * (wind_kmh ** 0.16)
        # Heat index for warm temperatures (> 27°C)
        elif temp > 27 and humidity > 40:
            # Simplified heat index formula
            hi = -8.78469475556 + 1.61139411 * temp + 2.33854883889 * humidity
            hi += -0.14611605 * temp * humidity - 0.012308094 * (temp ** 2)
            hi += -0.0164248277778 * (humidity ** 2) + 0.002211732 * (temp ** 2) * humidity
            hi += 0.00072546 * temp * (humidity ** 2) - 0.000003582 * (temp ** 2) * (humidity ** 2)
            feels_like = hi
        # For moderate temperatures, wind still affects perception
        elif wind_kmh > 10:
            # Simple wind effect adjustment
            feels_like = temp - (wind_kmh - 10) * 0.3
        else:
            feels_like = temp
        
        return round(feels_like, 1)
    
    def format_notification(self, weather_data: Dict, recommendation: str) -> str:
        """Format the complete notification message with nice formatting."""
        hourly = weather_data['hourly_data']
        
        # Calculate key metrics
        temps = [h['temperature'] for h in hourly]
        min_temp = min(temps)
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        # Calculate feels like temperatures
        feels_like_temps = [
            self._calculate_feels_like(h['temperature'], h['humidity'], h['wind_speed'])
            for h in hourly
        ]
        min_feels_like = min(feels_like_temps)
        max_feels_like = max(feels_like_temps)
        avg_feels_like = sum(feels_like_temps) / len(feels_like_temps)
        
        # Rain analysis
        total_precip = sum(h['precipitation'] for h in hourly)
        max_precip = max(h['precipitation'] for h in hourly)
        will_rain = total_precip > 0.5
        rain_hours = [i for i, h in enumerate(hourly) if h['precipitation'] > 0.5]
        
        # Wind analysis
        wind_speeds = [h['wind_speed'] for h in hourly]
        max_wind = max(wind_speeds)
        avg_wind = sum(wind_speeds) / len(wind_speeds)
        is_windy = max_wind > 7.0  # m/s
        
        # Initialize message
        message = ""
        
        # Temperature section
        message += "🌡️ Temperature\n"
        message += f"• Low: {min_temp:.1f}°C\n"
        message += f"• High: {max_temp:.1f}°C\n"
        message += f"• Feels like: {avg_feels_like:.1f}°C\n"
        message += f"  (Range: {min_feels_like:.1f}°C - {max_feels_like:.1f}°C)\n\n"
        
        # Rain section
        message += "☁️ Rain\n"
        if will_rain:
            if len(rain_hours) > 0:
                hours_str = ", ".join([f"+{h}h" for h in rain_hours[:5]])
                if len(rain_hours) > 5:
                    hours_str += f" (+{len(rain_hours)-5} more)"
                message += "• ⚠️ Rain expected\n"
                message += f"• Total: {total_precip:.1f}mm\n"
                message += f"• Peak: {max_precip:.1f}mm\n"
                message += f"• Hours: {hours_str}\n"
            else:
                message += f"• ⚠️ Light rain possible ({total_precip:.1f}mm total)\n"
        else:
            message += "• ✅ No rain expected\n"
        message += "\n"
        
        # Wind section
        message += "🌬️ Wind\n"
        if is_windy:
            message += "• ⚠️ Windy conditions\n"
        else:
            message += "• ✅ Light winds\n"
        message += f"• Speed: {avg_wind:.1f} m/s (avg)\n"
        message += f"• Peak: {max_wind:.1f} m/s\n"
        message += "\n"
        
        # Recommendation section
        message += "👔 Recommendation\n"
        message += f"{recommendation}\n"
        message += "                \n"
        message += "Have a great day!\n"
        message += "                \n"
        message += "                \n"
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


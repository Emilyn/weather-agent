"""
AI-powered clothing recommendation engine.
Uses free AI APIs: GitHub Models (free with any GitHub account, works with the
GitHub Actions GITHUB_TOKEN), with Groq and Hugging Face as optional fallbacks.
Falls back to rule-based advice if every provider fails.
"""

import os
import requests
from typing import Dict, List, Optional
import json
from utils import fetch_api_data
from reflection_engine import ReflectionEngine, ReflectionResult


# Override with the GITHUB_MODELS_MODEL env var; if the model is retired the
# recommender picks an available one from the GitHub Models catalog.
DEFAULT_GITHUB_MODEL = "openai/gpt-4.1-mini"
GITHUB_MODELS_URL = "https://models.github.ai/inference/chat/completions"
GITHUB_MODELS_CATALOG_URL = "https://models.github.ai/catalog/models"
# Error codes meaning the requested model doesn't exist or was retired. Other errors
# (bad parameters, rate limits) must surface rather than silently switch models.
MODEL_UNAVAILABLE_CODES = ("unknown_model", "model_not_found", "model_decommissioned")

# Override with the GROQ_MODEL env var; Groq retires models regularly, so if this
# one is gone the recommender picks an available model from Groq's model list.
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
# Models that can't do chat completions (speech, moderation, etc.)
NON_CHAT_MODEL_MARKERS = ("whisper", "tts", "guard", "playai", "orpheus", "prompt-guard")


class AIRecommender:
    """Generate clothing recommendations using AI (GitHub Models, Groq or Hugging Face)."""
    
    def __init__(self, groq_api_key: Optional[str] = None, hf_api_key: Optional[str] = None,
                 github_token: Optional[str] = None):
        self.github_token = github_token
        self.groq_api_key = groq_api_key
        self.hf_api_key = hf_api_key
        self.github_model = os.getenv('GITHUB_MODELS_MODEL') or DEFAULT_GITHUB_MODEL
        self.groq_model = os.getenv('GROQ_MODEL') or DEFAULT_GROQ_MODEL
        
        if not github_token and not groq_api_key and not hf_api_key:
            raise ValueError(
                "At least one AI credential is required: GITHUB_TOKEN, GROQ_API_KEY or HUGGINGFACE_API_KEY."
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
            recommendation = self._generate_with_feedback(weather_data, [], [])
        except RuntimeError as e:
            # Never skip the daily notification because the AI providers are down
            print(f"   ⚠️  {e}. Using rule-based recommendation instead.")
            return self._rule_based_recommendation(weather_data)
        
        try:
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
                        
                        # Generate refined recommendation with feedback;
                        # keep the current one if refinement fails
                        try:
                            recommendation = self._generate_with_feedback(
                                weather_data,
                                reflection.issues,
                                reflection.suggestions
                            )
                        except RuntimeError as e:
                            print(f"   ⚠️  Refinement failed ({e}), keeping previous recommendation")
                            break
                    else:
                        # Last iteration, accept what we have
                        print(f"   ⚠️  Quality threshold not fully met, but proceeding")
                        break
            
            return recommendation
            
        except Exception as e:
            # A reflection bug shouldn't discard a recommendation we already have
            print(f"   ⚠️  Reflection failed ({e}), using unrefined recommendation")
            return recommendation
    
    def _build_chat_messages(
        self,
        weather_data: Dict,
        feedback_issues: Optional[List[str]] = None,
        feedback_suggestions: Optional[List[str]] = None
    ) -> List[Dict]:
        """Build the chat prompt shared by the chat-completion providers."""
        weather_summary = self._format_weather_for_ai(weather_data)
        
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
        
        return [
            {
                "role": "system",
                "content": "You are a helpful weather assistant that provides practical clothing advice. Keep responses brief and actionable."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    
    def _generate_with_github_models(
        self,
        weather_data: Dict,
        feedback_issues: Optional[List[str]] = None,
        feedback_suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Generate recommendation using GitHub Models (free, OpenAI-compatible API).
        If the configured model has been retired, switches to an available one and retries once.
        """
        messages = self._build_chat_messages(weather_data, feedback_issues, feedback_suggestions)
        
        response = self._post_github_models(messages)
        if response.status_code in (400, 404) and is_model_unavailable_error(response.text):
            replacement = self._find_available_github_model()
            if replacement:
                print(f"   ⚠️  GitHub model '{self.github_model}' unavailable, switching to '{replacement}'. "
                      f"Set GITHUB_MODELS_MODEL to choose a model explicitly.")
                self.github_model = replacement
                response = self._post_github_models(messages)
        
        if not response.ok:
            raise Exception(f"GitHub Models error {response.status_code}: {response.text[:300]}")
        return response.json()['choices'][0]['message']['content'].strip()
    
    def _post_github_models(self, messages: List[Dict]) -> requests.Response:
        return requests.post(
            GITHUB_MODELS_URL,
            headers={
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
            },
            json={
                "model": self.github_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 200,
            },
            timeout=30
        )
    
    def _find_available_github_model(self) -> Optional[str]:
        """Pick a text chat model from the GitHub Models catalog, preferring small models."""
        catalog = fetch_api_data(
            url=GITHUB_MODELS_CATALOG_URL,
            headers={"Authorization": f"Bearer {self.github_token}", "Accept": "application/vnd.github+json"},
            source_name="GitHub Models catalog"
        )
        if not isinstance(catalog, list):
            return None
        
        model_ids = [
            m['id'] for m in catalog
            if m.get('id') and m['id'] != self.github_model
            and 'text' in m.get('supported_output_modalities', ['text'])
            and 'embedding' not in m['id'].lower()
        ]
        return choose_github_model(model_ids)
    
    def _generate_with_groq(
        self,
        weather_data: Dict,
        feedback_issues: Optional[List[str]] = None,
        feedback_suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Generate recommendation using Groq API.
        If the configured model has been retired, switches to an available one and retries once.
        
        Args:
            weather_data: Weather data dictionary
            feedback_issues: Optional list of issues from reflection
            feedback_suggestions: Optional list of suggestions from reflection
        """
        try:
            from groq import Groq
            
            client = Groq(api_key=self.groq_api_key)
            messages = self._build_chat_messages(weather_data, feedback_issues, feedback_suggestions)
            
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=self.groq_model,
                    temperature=0.7,
                    max_tokens=200
                )
            except Exception as e:
                if not is_model_unavailable_error(str(e)):
                    raise
                replacement = self._find_available_groq_model()
                if not replacement:
                    raise
                print(f"   ⚠️  Groq model '{self.groq_model}' unavailable, switching to '{replacement}'. "
                      f"Set GROQ_MODEL to choose a model explicitly.")
                self.groq_model = replacement
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=self.groq_model,
                    temperature=0.7,
                    max_tokens=200
                )
            
            return chat_completion.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Groq API error: {e}")
            raise
    
    def _find_available_groq_model(self) -> Optional[str]:
        """Pick a chat model from Groq's live model list, preferring small Llama models."""
        data = fetch_api_data(
            url=GROQ_MODELS_URL,
            headers={"Authorization": f"Bearer {self.groq_api_key}"},
            source_name="Groq models"
        )
        if not data:
            return None
        
        model_ids = [
            m['id'] for m in data.get('data', [])
            if m.get('active', True) and m.get('id') != self.groq_model
            and not any(marker in m['id'].lower() for marker in NON_CHAT_MODEL_MARKERS)
        ]
        return choose_groq_model(model_ids)
    
    def _generate_with_feedback(
        self,
        weather_data: Dict,
        issues: List[str],
        suggestions: List[str]
    ) -> str:
        """
        Generate a recommendation (optionally with reflection feedback), trying each
        configured provider in turn: GitHub Models, Groq, then Hugging Face.
        Raises RuntimeError if every provider fails.
        """
        providers = []
        if self.github_token:
            providers.append(("GitHub Models", self._generate_with_github_models))
        if self.groq_api_key:
            providers.append(("Groq", self._generate_with_groq))
        if self.hf_api_key:
            providers.append(("Hugging Face", self._generate_with_huggingface))
        
        errors = []
        for index, (name, generate) in enumerate(providers):
            try:
                recommendation = generate(weather_data, issues or None, suggestions or None)
                if recommendation:
                    return recommendation
                errors.append(f"{name}: empty response")
            except Exception as e:
                errors.append(f"{name}: {e}")
            if index < len(providers) - 1:
                print(f"   ⚠️  {errors[-1]}, trying next provider")
        
        raise RuntimeError("All AI providers failed (" + "; ".join(errors) + ")")
    
    def _rule_based_recommendation(self, weather_data: Dict) -> str:
        """Simple deterministic clothing advice used when no AI provider is reachable."""
        hourly = weather_data['hourly_data']
        min_feels = min(
            self._calculate_feels_like(h['temperature'], h['humidity'], h['wind_speed'])
            for h in hourly
        )
        total_rain = sum(h.get('rain', 0) for h in hourly)
        total_snow = sum(h.get('snow', 0) for h in hourly)
        max_wind = max(h['wind_speed'] for h in hourly)
        
        if min_feels < 0:
            advice = "Wear a warm winter coat, hat and gloves."
        elif min_feels < 10:
            advice = "Wear a warm jacket and layers."
        elif min_feels < 18:
            advice = "A light jacket or sweater should be enough."
        else:
            advice = "Light clothing is fine today."
        
        if total_snow > 0.5:
            advice += " Expect snow, so waterproof boots are a good idea."
        elif total_rain > 0.5:
            advice += " Take an umbrella or rain jacket."
        if max_wind > 7.0:
            advice += " It will be windy."
        
        return advice
    
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
        total_rain = sum(h.get('rain', 0) for h in hourly)
        total_snow = sum(h.get('snow', 0) for h in hourly)
        will_rain = total_rain > 1.0
        will_snow = total_snow > 0.5
        
        # Get wind info
        max_wind = max(h['wind_speed'] for h in hourly)
        
        # Get most common condition
        conditions = [h['condition'] for h in hourly]
        main_condition = max(set(conditions), key=conditions.count)
        
        # Build precipitation description
        precip_desc = []
        if will_snow:
            precip_desc.append(f"snow: {total_snow:.1f}mm")
        if will_rain:
            precip_desc.append(f"rain: {total_rain:.1f}mm")
        if not precip_desc:
            precip_desc.append("dry")
        
        summary = f"""Temperature: {min_temp}°C to {max_temp}°C
Conditions: {main_condition}
Precipitation: {', '.join(precip_desc)}
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

        # Calculate feels like temperatures
        feels_like_temps = [
            self._calculate_feels_like(h['temperature'], h['humidity'], h['wind_speed'])
            for h in hourly
        ]
        min_feels_like = min(feels_like_temps)
        max_feels_like = max(feels_like_temps)

        # Precipitation analysis
        total_rain = sum(h.get('rain', 0) for h in hourly)
        total_snow = sum(h.get('snow', 0) for h in hourly)
        max_rain = max(h.get('rain', 0) for h in hourly)
        max_snow = max(h.get('snow', 0) for h in hourly)

        will_rain = total_rain > 0.5
        will_snow = total_snow > 0.5

        rain_hours = [i for i, h in enumerate(hourly) if h.get('rain', 0) > 0.5]
        snow_hours = [i for i, h in enumerate(hourly) if h.get('snow', 0) > 0.5]

        # Wind analysis
        wind_speeds = [h['wind_speed'] for h in hourly]
        max_wind = max(wind_speeds)
        avg_wind = sum(wind_speeds) / len(wind_speeds)
        is_windy = max_wind > 7.0  # m/s

        # Header — quick at-a-glance summary
        message = f"🌤️ Today: {min_temp:.0f}°C – {max_temp:.0f}°C\n\n"

        # Temperature section
        message += "🌡️ Temperature\n"
        message += f"• {min_temp:.1f}°C → {max_temp:.1f}°C\n"
        message += f"• Feels like: {min_feels_like:.1f}°C → {max_feels_like:.1f}°C\n\n"

        # Rain section
        message += "🌧️ Rain\n"
        if will_rain:
            hours_str = ", ".join([f"+{h}h" for h in rain_hours[:5]])
            if len(rain_hours) > 5:
                hours_str += f" (+{len(rain_hours)-5} more)"
            if rain_hours:
                message += f"• ⚠️ Expected · {total_rain:.1f}mm total · Peak: {max_rain:.1f}mm/h\n"
                message += f"• At: {hours_str}\n"
            else:
                message += f"• ⚠️ Light rain possible ({total_rain:.1f}mm total)\n"
        else:
            message += "• ✅ None expected\n"
        message += "\n"

        # Snow section — only shown when relevant
        if will_snow:
            message += "❄️ Snow\n"
            hours_str = ", ".join([f"+{h}h" for h in snow_hours[:5]])
            if len(snow_hours) > 5:
                hours_str += f" (+{len(snow_hours)-5} more)"
            if snow_hours:
                message += f"• ⚠️ Expected · {total_snow:.1f}mm total · Peak: {max_snow:.1f}mm/h\n"
                message += f"• At: {hours_str}\n"
            else:
                message += f"• ⚠️ Light snow possible ({total_snow:.1f}mm total)\n"
            message += "\n"

        # Wind section
        message += "🌬️ Wind\n"
        if is_windy:
            message += f"• ⚠️ Windy · {avg_wind:.1f} m/s avg · {max_wind:.1f} m/s peak\n\n"
        else:
            message += f"• ✅ Light · {avg_wind:.1f} m/s avg · {max_wind:.1f} m/s peak\n\n"

        # Recommendation section
        message += "─────────────────\n"
        message += "👔 Recommendation\n"
        message += f"{recommendation}\n\n"
        message += "Have a great day!\n"
        return message


def choose_groq_model(model_ids: List[str]) -> Optional[str]:
    """Choose the best replacement model: fast Llama, then any Llama, then anything else."""
    preferences = [
        lambda m: 'llama' in m and 'instant' in m,
        lambda m: 'llama' in m,
        lambda m: True,
    ]
    for matches in preferences:
        candidates = sorted(m for m in model_ids if matches(m.lower()))
        if candidates:
            return candidates[0]
    return None


def is_model_unavailable_error(error_text: str) -> bool:
    """True if an API error says the requested model doesn't exist or was retired."""
    return any(code in error_text for code in MODEL_UNAVAILABLE_CODES)


def choose_github_model(model_ids: List[str]) -> Optional[str]:
    """Choose the best replacement model: small OpenAI model, then any small model, then anything."""
    preferences = [
        lambda m: m.startswith('openai/') and 'mini' in m,
        lambda m: 'mini' in m or 'small' in m,
        lambda m: True,
    ]
    for matches in preferences:
        candidates = sorted(m for m in model_ids if matches(m.lower()))
        if candidates:
            return candidates[0]
    return None


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


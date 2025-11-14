#!/usr/bin/env python3
"""
Weather AI Agent - Main orchestrator script.
Fetches weather data, generates AI recommendations, and sends notifications.
"""

import os
import sys
import requests
from weather_sources import WeatherSources
from ai_recommender import AIRecommender
from reflection_engine import ReflectionEngine
from utils import (
    load_env_file, validate_coordinates, validate_required_env_vars,
    print_success, print_error, print_warning
)


def send_ntfy_notification(topic: str, message: str, title: str = "Weather Alert") -> bool:
    """Send notification via Ntfy.sh."""
    try:
        url = f"https://ntfy.sh/{topic}"
        
        response = requests.post(
            url,
            data=message.encode('utf-8'),
            headers={
                "Title": title,
                "Priority": "default",
                "Tags": "sunny,clothing"
            },
            timeout=10
        )
        
        response.raise_for_status()
        print_success(f"Notification sent successfully to topic: {topic}")
        return True
    
    except Exception as e:
        print_error(f"Failed to send notification: {e}")
        return False


def main():
    """Main execution function."""
    print("🌤️  Weather AI Agent Starting...")
    print("=" * 50)
    
    # Load .env file
    load_env_file()
    
    # Validate required environment variables
    required_vars = ['LOCATION_LAT', 'LOCATION_LON', 'NTFY_TOPIC']
    env_vars = validate_required_env_vars(required_vars)
    
    lat_str = env_vars['LOCATION_LAT']
    lon_str = env_vars['LOCATION_LON']
    ntfy_topic = env_vars['NTFY_TOPIC']
    
    # Validate coordinates
    try:
        lat, lon = validate_coordinates(lat_str, lon_str)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)
    
    # Optional API keys
    weatherapi_key = os.getenv('WEATHERAPI_KEY')
    openweather_key = os.getenv('OPENWEATHER_KEY')
    groq_api_key = os.getenv('GROQ_API_KEY')
    hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
    
    # Validate at least one AI API key is present
    if not groq_api_key and not hf_api_key:
        print_error("At least one AI API key is required (GROQ_API_KEY or HUGGINGFACE_API_KEY)")
        sys.exit(1)
    
    print(f"📍 Location: {lat}, {lon}")
    print(f"📱 Notification topic: {ntfy_topic}")
    
    # Initialize reflection engine
    reflection_engine = ReflectionEngine(quality_threshold=0.7)
    
    # Step 1: Fetch weather data from multiple sources
    print("\n🌐 Step 1: Fetching weather data...")
    try:
        weather_sources = WeatherSources(
            lat=lat,
            lon=lon,
            weatherapi_key=weatherapi_key,
            openweather_key=openweather_key
        )
        
        weather_data = weather_sources.aggregate_weather_data()
        
        print_success("Weather data aggregated successfully")
        print(f"   Sources used: {len(weather_data.sources_used)}")
        print(f"   Reliability: {weather_data.reliability_score * 100:.0f}%")
        print(f"   Hours available: {len(weather_data.hourly_data)}")
        
        # Reflection: Evaluate weather data quality
        print("\n   🔍 Reflecting on weather data quality...")
        weather_reflection = reflection_engine.reflect_on_weather_data(weather_data.to_dict())
        print(f"   Quality: {weather_reflection.quality.value} (score: {weather_reflection.score:.2f})")
        if weather_reflection.issues:
            print_warning(f"   Issues found: {len(weather_reflection.issues)}")
            for issue in weather_reflection.issues[:2]:
                print(f"      - {issue}")
        if not weather_reflection.passed:
            print_warning("   Weather data quality below threshold, but proceeding...")
        
    except Exception as e:
        print_error(f"Failed to fetch weather data: {e}")
        sys.exit(1)
    
    # Step 2: Generate AI recommendation with reflection
    print("\n🤖 Step 2: Generating clothing recommendation...")
    try:
        ai_recommender = AIRecommender(
            groq_api_key=groq_api_key,
            hf_api_key=hf_api_key
        )
        
        if groq_api_key:
            print("   Using Groq AI (Llama 3.1)")
        elif hf_api_key:
            print("   Using Hugging Face AI (Mistral-7B)")
        
        # Generate with reflection pattern (iterative refinement)
        recommendation = ai_recommender.generate_recommendation(
            weather_data.to_dict(),
            reflection_engine=reflection_engine,
            max_refinements=2
        )
        
        # Final reflection on recommendation
        print("\n   🔍 Reflecting on recommendation quality...")
        rec_reflection = reflection_engine.reflect_on_recommendation(
            recommendation, weather_data.to_dict()
        )
        print(f"   Quality: {rec_reflection.quality.value} (score: {rec_reflection.score:.2f})")
        if rec_reflection.issues:
            print_warning(f"   Issues found: {len(rec_reflection.issues)}")
        
        print_success("Recommendation generated")
        print(f"   Preview: {recommendation[:100]}...")
        
    except Exception as e:
        print_error(f"Failed to generate recommendation: {e}")
        sys.exit(1)
    
    # Step 3: Format notification message
    print("\n📝 Step 3: Formatting notification...")
    try:
        full_message = ai_recommender.format_notification(
            weather_data.to_dict(),
            recommendation
        )
        
        # Reflection: Evaluate notification completeness
        print("\n   🔍 Reflecting on notification quality...")
        notif_reflection = reflection_engine.reflect_on_notification(
            full_message,
            weather_data.to_dict(),
            recommendation
        )
        print(f"   Quality: {notif_reflection.quality.value} (score: {notif_reflection.score:.2f})")
        if notif_reflection.issues:
            print_warning(f"   Issues found: {len(notif_reflection.issues)}")
            for issue in notif_reflection.issues[:2]:
                print(f"      - {issue}")
        
        print_success("Notification formatted")
        print(f"   Message length: {len(full_message)} characters")
        
    except Exception as e:
        print_error(f"Failed to format notification: {e}")
        sys.exit(1)
    
    # Step 4: Send notification
    print("\n📤 Step 4: Sending notification...")
    try:
        success = send_ntfy_notification(
            topic=ntfy_topic,
            message=full_message,
            title="Today's Weather"
        )
        
        if not success:
            sys.exit(1)
        
    except Exception as e:
        print_error(f"Failed to send notification: {e}")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("✅ Weather AI Agent completed successfully!")
    print(f"📊 Summary:")
    print(f"   - Weather sources: {', '.join(weather_data.sources_used)}")
    print(f"   - Reliability: {weather_data.reliability_score * 100:.0f}%")
    print(f"   - Temperature range: {min(h['temperature'] for h in weather_data.hourly_data):.1f}°C - "
          f"{max(h['temperature'] for h in weather_data.hourly_data):.1f}°C")
    print(f"   - Notification sent to: {ntfy_topic}")
    
    # Optional: Print full message for debugging
    if os.getenv('DEBUG'):
        print("\n📄 Full notification message:")
        print("-" * 50)
        print(full_message)
        print("-" * 50)


if __name__ == "__main__":
    main()


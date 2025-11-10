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
        print(f"✅ Notification sent successfully to topic: {topic}")
        return True
    
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")
        return False


def main():
    """Main execution function."""
    print("🌤️  Weather AI Agent Starting...")
    print("=" * 50)
    
    # Load configuration from environment variables
    lat = os.getenv('LOCATION_LAT')
    lon = os.getenv('LOCATION_LON')
    ntfy_topic = os.getenv('NTFY_TOPIC')
    
    # Optional API keys
    weatherapi_key = os.getenv('WEATHERAPI_KEY')
    openweather_key = os.getenv('OPENWEATHER_KEY')
    groq_api_key = os.getenv('GROQ_API_KEY')
    hf_api_key = os.getenv('HUGGINGFACE_API_KEY')
    
    # Validate required configuration
    if not lat or not lon:
        print("❌ ERROR: LOCATION_LAT and LOCATION_LON must be set")
        sys.exit(1)
    
    if not ntfy_topic:
        print("❌ ERROR: NTFY_TOPIC must be set")
        sys.exit(1)
    
    try:
        lat = float(lat)
        lon = float(lon)
    except ValueError:
        print("❌ ERROR: LOCATION_LAT and LOCATION_LON must be valid numbers")
        sys.exit(1)
    
    print(f"📍 Location: {lat}, {lon}")
    print(f"📱 Notification topic: {ntfy_topic}")
    
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
        
        print(f"✅ Weather data aggregated successfully")
        print(f"   Sources used: {len(weather_data.sources_used)}")
        print(f"   Reliability: {weather_data.reliability_score * 100:.0f}%")
        print(f"   Hours available: {len(weather_data.hourly_data)}")
        
    except Exception as e:
        print(f"❌ Failed to fetch weather data: {e}")
        sys.exit(1)
    
    # Step 2: Generate AI recommendation
    print("\n🤖 Step 2: Generating clothing recommendation...")
    try:
        ai_recommender = AIRecommender(
            groq_api_key=groq_api_key,
            hf_api_key=hf_api_key
        )
        
        if ai_recommender.use_ai:
            print("   Using AI-powered recommendations")
        else:
            print("   Using rule-based recommendations (no AI API key provided)")
        
        recommendation = ai_recommender.generate_recommendation(weather_data.to_dict())
        
        print(f"✅ Recommendation generated")
        print(f"   Preview: {recommendation[:100]}...")
        
    except Exception as e:
        print(f"❌ Failed to generate recommendation: {e}")
        sys.exit(1)
    
    # Step 3: Format notification message
    print("\n📝 Step 3: Formatting notification...")
    try:
        full_message = ai_recommender.format_notification(
            weather_data.to_dict(),
            recommendation
        )
        
        print("✅ Notification formatted")
        print(f"   Message length: {len(full_message)} characters")
        
    except Exception as e:
        print(f"❌ Failed to format notification: {e}")
        sys.exit(1)
    
    # Step 4: Send notification
    print("\n📤 Step 4: Sending notification...")
    try:
        success = send_ntfy_notification(
            topic=ntfy_topic,
            message=full_message,
            title="Morning Weather Report"
        )
        
        if not success:
            sys.exit(1)
        
    except Exception as e:
        print(f"❌ Failed to send notification: {e}")
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


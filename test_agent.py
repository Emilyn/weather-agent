#!/usr/bin/env python3
"""
Test script for Weather AI Agent
Run this to verify your setup before deploying to GitHub Actions
"""

import os
import sys

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    try:
        import requests
        import statistics
        print("   ✅ Standard libraries OK")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    try:
        sys.path.insert(0, 'src')
        from weather_sources import WeatherSources
        from ai_recommender import AIRecommender
        import weather_agent
        print("   ✅ Project modules OK")
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    
    return True


def test_environment():
    """Test if required environment variables are set."""
    print("\n🔧 Testing environment variables...")
    required = ['LOCATION_LAT', 'LOCATION_LON', 'NTFY_TOPIC']
    optional = ['WEATHERAPI_KEY', 'OPENWEATHER_KEY']
    
    all_ok = True
    for var in required:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
        else:
            print(f"   ❌ {var} is NOT set (required)")
            all_ok = False
    
    has_ai_key = False
    for var in ['GROQ_API_KEY', 'HUGGINGFACE_API_KEY']:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
            has_ai_key = True
    
    if not has_ai_key:
        print(f"   ❌ No AI API key set (GROQ_API_KEY or HUGGINGFACE_API_KEY is required)")
        all_ok = False
    
    for var in ['WEATHERAPI_KEY', 'OPENWEATHER_KEY']:
        if os.getenv(var):
            print(f"   ✅ {var} is set")
        else:
            print(f"   ⚠️  {var} is NOT set (optional, but recommended)")
    
    return all_ok


def test_coordinates():
    """Test if coordinates are valid."""
    print("\n📍 Testing coordinates...")
    try:
        lat = float(os.getenv('LOCATION_LAT', '0'))
        lon = float(os.getenv('LOCATION_LON', '0'))
        
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            print(f"   ✅ Coordinates valid: {lat}, {lon}")
            return True
        else:
            print(f"   ❌ Coordinates out of range: {lat}, {lon}")
            return False
    except (ValueError, TypeError):
        print(f"   ❌ Coordinates are not valid numbers")
        return False


def test_weather_sources():
    """Test if weather sources can be fetched."""
    print("\n🌐 Testing weather sources...")
    try:
        sys.path.insert(0, 'src')
        from weather_sources import WeatherSources
        
        lat = float(os.getenv('LOCATION_LAT', '48.8566'))
        lon = float(os.getenv('LOCATION_LON', '2.3522'))
        
        weather = WeatherSources(
            lat=lat,
            lon=lon,
            weatherapi_key=os.getenv('WEATHERAPI_KEY'),
            openweather_key=os.getenv('OPENWEATHER_KEY')
        )
        
        # Test individual sources
        sources_tested = 0
        sources_working = 0
        
        print("   Testing Open-Meteo...")
        if weather.fetch_open_meteo():
            print("      ✅ Open-Meteo working")
            sources_working += 1
        else:
            print("      ❌ Open-Meteo failed")
        sources_tested += 1
        
        if os.getenv('WEATHERAPI_KEY'):
            print("   Testing WeatherAPI...")
            if weather.fetch_weatherapi():
                print("      ✅ WeatherAPI working")
                sources_working += 1
            else:
                print("      ❌ WeatherAPI failed")
            sources_tested += 1
        
        if os.getenv('OPENWEATHER_KEY'):
            print("   Testing OpenWeatherMap...")
            if weather.fetch_openweathermap():
                print("      ✅ OpenWeatherMap working")
                sources_working += 1
            else:
                print("      ❌ OpenWeatherMap failed")
            sources_tested += 1
        
        print("   Testing 7Timer...")
        if weather.fetch_7timer():
            print("      ✅ 7Timer working")
            sources_working += 1
        else:
            print("      ❌ 7Timer failed")
        sources_tested += 1
        
        print("   Testing wttr.in...")
        if weather.fetch_wttr():
            print("      ✅ wttr.in working")
            sources_working += 1
        else:
            print("      ❌ wttr.in failed")
        sources_tested += 1
        
        print(f"\n   📊 {sources_working}/{sources_tested} sources working")
        
        if sources_working >= 2:
            print("   ✅ Sufficient sources available")
            return True
        else:
            print("   ❌ Need at least 2 working sources")
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing weather sources: {e}")
        return False


def test_ntfy():
    """Test if Ntfy.sh is accessible."""
    print("\n📱 Testing Ntfy.sh connectivity...")
    try:
        import requests
        topic = os.getenv('NTFY_TOPIC', 'test')
        
        # Just test if we can reach ntfy.sh
        response = requests.get("https://ntfy.sh", timeout=5)
        if response.status_code == 200:
            print(f"   ✅ Ntfy.sh is accessible")
            print(f"   📡 Your topic: {topic}")
            print(f"   💡 Subscribe in the Ntfy app to receive notifications")
            return True
        else:
            print(f"   ⚠️  Ntfy.sh returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot reach Ntfy.sh: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("🌤️  Weather AI Agent - Test Suite")
    print("=" * 60)
    
    results = {
        'imports': test_imports(),
        'environment': test_environment(),
        'coordinates': test_coordinates(),
        'weather': test_weather_sources(),
        'ntfy': test_ntfy()
    }
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:>10} - {test_name.capitalize()}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! You're ready to deploy.")
        print("\nNext steps:")
        print("1. Push your code to GitHub")
        print("2. Add secrets to GitHub repository settings")
        print("3. Enable GitHub Actions")
        print("4. Test with 'Run workflow' button")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("- Set missing environment variables in .env file")
        print("- Check your API keys are valid")
        print("- Verify your internet connection")
        sys.exit(1)
    
    print("=" * 60)


if __name__ == "__main__":
    main()


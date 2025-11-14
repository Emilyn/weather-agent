#!/usr/bin/env python3
"""
Test script for Weather AI Agent
Run this to verify your setup before deploying to GitHub Actions
"""

import os
import sys
sys.path.insert(0, 'src')
from utils import validate_coordinates, print_success, print_error, print_warning

def test_imports():
    """Test if all required modules can be imported."""
    print("🧪 Testing imports...")
    try:
        import requests
        import statistics
        print_success("Standard libraries OK", indent=3)
    except ImportError as e:
        print_error(f"Import error: {e}", indent=3)
        return False
    
    try:
        from weather_sources import WeatherSources
        from ai_recommender import AIRecommender
        import weather_agent
        print_success("Project modules OK", indent=3)
    except ImportError as e:
        print_error(f"Import error: {e}", indent=3)
        return False
    
    return True


def test_environment():
    """Test if required environment variables are set."""
    print("\n🔧 Testing environment variables...")
    required = ['LOCATION_LAT', 'LOCATION_LON', 'NTFY_TOPIC']
    optional = ['WEATHERAPI_KEY', 'OPENWEATHER_KEY']
    ai_keys = ['GROQ_API_KEY', 'HUGGINGFACE_API_KEY']
    
    all_ok = True
    for var in required:
        if os.getenv(var):
            print_success(f"{var} is set", indent=3)
        else:
            print_error(f"{var} is NOT set (required)", indent=3)
            all_ok = False
    
    has_ai_key = False
    for var in ai_keys:
        if os.getenv(var):
            print_success(f"{var} is set", indent=3)
            has_ai_key = True
    
    if not has_ai_key:
        print_error("No AI API key set (GROQ_API_KEY or HUGGINGFACE_API_KEY is required)", indent=3)
        all_ok = False
    
    for var in optional:
        if os.getenv(var):
            print_success(f"{var} is set", indent=3)
        else:
            print_warning(f"{var} is NOT set (optional, but recommended)", indent=3)
    
    return all_ok


def test_coordinates():
    """Test if coordinates are valid."""
    print("\n📍 Testing coordinates...")
    try:
        lat_str = os.getenv('LOCATION_LAT', '0')
        lon_str = os.getenv('LOCATION_LON', '0')
        lat, lon = validate_coordinates(lat_str, lon_str)
        print_success(f"Coordinates valid: {lat}, {lon}", indent=3)
        return True
    except ValueError as e:
        print_error(str(e), indent=3)
        return False


def _test_single_source(weather: 'WeatherSources', source_name: str, fetch_func) -> bool:
    """Helper function to test a single weather source."""
    print(f"   Testing {source_name}...", end="")
    result = fetch_func()
    if result:
        print_success(f"{source_name} working", indent=0)
        return True
    else:
        print_error(f"{source_name} failed", indent=0)
        return False

def test_weather_sources():
    """Test if weather sources can be fetched."""
    print("\n🌐 Testing weather sources...")
    try:
        from weather_sources import WeatherSources
        
        lat_str = os.getenv('LOCATION_LAT', '48.8566')
        lon_str = os.getenv('LOCATION_LON', '2.3522')
        lat, lon = validate_coordinates(lat_str, lon_str)
        
        weather = WeatherSources(
            lat=lat,
            lon=lon,
            weatherapi_key=os.getenv('WEATHERAPI_KEY'),
            openweather_key=os.getenv('OPENWEATHER_KEY')
        )
        
        # Test individual sources
        sources_to_test = [
            ('Open-Meteo', weather.fetch_open_meteo),
            ('7Timer', weather.fetch_7timer),
            ('wttr.in', weather.fetch_wttr),
        ]
        
        if os.getenv('WEATHERAPI_KEY'):
            sources_to_test.append(('WeatherAPI', weather.fetch_weatherapi))
        
        if os.getenv('OPENWEATHER_KEY'):
            sources_to_test.append(('OpenWeatherMap', weather.fetch_openweathermap))
        
        sources_working = sum(1 for name, func in sources_to_test if _test_single_source(weather, name, func))
        sources_tested = len(sources_to_test)
        
        print(f"\n   📊 {sources_working}/{sources_tested} sources working")
        
        if sources_working >= 2:
            print_success("Sufficient sources available", indent=3)
            return True
        else:
            print_error("Need at least 2 working sources", indent=3)
            return False
            
    except Exception as e:
        print_error(f"Error testing weather sources: {e}", indent=3)
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
            print_success("Ntfy.sh is accessible", indent=3)
            print(f"   📡 Your topic: {topic}")
            print(f"   💡 Subscribe in the Ntfy app to receive notifications")
            return True
        else:
            print_warning(f"Ntfy.sh returned status {response.status_code}", indent=3)
            return False
    except Exception as e:
        print_error(f"Cannot reach Ntfy.sh: {e}", indent=3)
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
        if result:
            print_success(f"{test_name.capitalize()}", indent=0)
        else:
            print_error(f"{test_name.capitalize()}", indent=0)
    
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


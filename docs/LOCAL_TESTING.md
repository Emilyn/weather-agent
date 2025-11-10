# 🧪 Local Testing Guide

This guide will help you test the Weather AI Agent on your local machine before deploying to GitHub Actions.

## Prerequisites

- Python 3.8 or higher
- Internet connection
- API keys (see below)

## Quick Start

### Option 1: Using the Setup Script (Recommended)

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh

# Edit .env file with your values
nano .env  # or use your preferred editor

# Activate virtual environment
source venv/bin/activate

# Run the agent
cd src && python weather_agent.py
```

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp env .env

# 5. Edit .env with your values
nano .env  # or use your preferred editor

# 6. Run the agent
cd src && python weather_agent.py
```

## Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Required: Your location coordinates
LOCATION_LAT=48.8566
LOCATION_LON=2.3522

# Required: Your Ntfy.sh topic name (make it unique!)
NTFY_TOPIC=weather-test-123

# Required: AI API Key (choose one)
GROQ_API_KEY=gsk_your_key_here
# OR
# HUGGINGFACE_API_KEY=hf_your_key_here

# Optional: Additional weather sources (improves accuracy)
WEATHERAPI_KEY=your_weatherapi_key
OPENWEATHER_KEY=your_openweather_key

# Optional: Enable debug output
DEBUG=1
```

### Getting Your Values

**Location Coordinates:**
- Visit [latlong.net](https://www.latlong.net/) and search for your city
- Or use Google Maps: Right-click your location → Click coordinates

**NTFY Topic:**
- Install Ntfy.sh app on your phone
- Create a unique topic name (e.g., `weather-test-123`)
- Subscribe to it in the app

**API Keys:**
- **Groq**: [console.groq.com](https://console.groq.com) (free, recommended)
- **Hugging Face**: [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (free)
- **WeatherAPI**: [weatherapi.com](https://www.weatherapi.com/) (free, optional)
- **OpenWeatherMap**: [openweathermap.org/api](https://openweathermap.org/api) (free, optional)

## Running Tests

### Test 1: Run the Test Suite

```bash
# Make sure you're in the project root
# Activate virtual environment first
source venv/bin/activate

# Set environment variables (or use .env file)
export LOCATION_LAT="48.8566"
export LOCATION_LON="2.3522"
export NTFY_TOPIC="weather-test-123"
export GROQ_API_KEY="your_key_here"

# Run test suite
python test_agent.py
```

The test suite will check:
- ✅ All required modules can be imported
- ✅ Environment variables are set correctly
- ✅ Coordinates are valid
- ✅ Weather sources are accessible
- ✅ Ntfy.sh is reachable

### Test 2: Run the Full Agent

```bash
# Activate virtual environment
source venv/bin/activate

# Navigate to src directory
cd src

# Run the agent
python weather_agent.py
```

Expected output:
```
🌤️  Weather AI Agent Starting...
==================================================
📍 Location: 48.8566, 2.3522
📱 Notification topic: weather-test-123

🌐 Step 1: Fetching weather data...
Fetching weather data from multiple sources...
Successfully fetched from 5 sources: ['Open-Meteo', 'WeatherAPI', ...]
✅ Weather data aggregated successfully
   Sources used: 5
   Reliability: 100%
   Hours available: 10

🤖 Step 2: Generating clothing recommendation...
   Using AI-powered recommendations
✅ Recommendation generated
   Preview: Based on the forecast, I recommend wearing...

📝 Step 3: Formatting notification...
✅ Notification formatted
   Message length: 450 characters

📤 Step 4: Sending notification...
✅ Notification sent successfully to topic: weather-test-123

==================================================
✅ Weather AI Agent completed successfully!
```

### Test 3: Debug Mode

To see the full notification message:

```bash
export DEBUG=1
cd src && python weather_agent.py
```

This will print the complete notification message at the end.

## Testing Individual Components

### Test Weather Sources Only

```bash
cd src
python -c "
from weather_sources import WeatherSources
weather = WeatherSources(48.8566, 2.3522)
data = weather.aggregate_weather_data()
print(f'Sources: {data.sources_used}')
print(f'Reliability: {data.reliability_score}')
for hour in data.hourly_data[:3]:
    print(f\"Hour {hour['hour']}: {hour['temperature']}°C\")
"
```

### Test AI Recommender Only

```bash
cd src
python -c "
from ai_recommender import AIRecommender
import os
recommender = AIRecommender(groq_api_key=os.getenv('GROQ_API_KEY'))
sample_data = {
    'hourly_data': [
        {'temperature': 15, 'precipitation': 0, 'wind_speed': 5, 
         'humidity': 70, 'condition': 'Partly cloudy'}
        for _ in range(10)
    ],
    'sources_used': ['test'],
    'reliability_score': 1.0
}
rec = recommender.generate_recommendation(sample_data)
print(rec)
"
```

## Troubleshooting

### "Module not found" errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "LOCATION_LAT and LOCATION_LON must be set"

- Make sure you've created a `.env` file
- Check that variables are set correctly (no quotes needed)
- Or export them manually: `export LOCATION_LAT="48.8566"`

### "Failed to fetch from at least 2 weather sources"

- Check your internet connection
- Some APIs may be temporarily down
- Add optional API keys (WEATHERAPI_KEY, OPENWEATHER_KEY) for more sources

### "Failed to send notification"

- Verify your NTFY_TOPIC is correct
- Make sure you're subscribed to the topic in the Ntfy.sh app
- Check that the topic name doesn't have spaces or special characters

### Type comparison errors

If you see `'<' not supported between instances of 'str' and 'int'`:
- This should be fixed in the latest version
- Make sure you're using the updated `weather_sources.py`
- Try running `pip install --upgrade -r requirements.txt`

## Environment Variables vs .env File

You can set environment variables in two ways:

**Method 1: .env file (Recommended for local testing)**
```bash
# Create .env file
LOCATION_LAT=48.8566
LOCATION_LON=2.3522
# ... etc
```

**Method 2: Export in shell**
```bash
export LOCATION_LAT="48.8566"
export LOCATION_LON="2.3522"
export NTFY_TOPIC="weather-test-123"
export GROQ_API_KEY="your_key_here"
```

The code will automatically load from `.env` if `python-dotenv` is installed (it's in requirements.txt).

## Next Steps

Once local testing works:

1. ✅ Push your code to GitHub
2. ✅ Add secrets to GitHub repository (Settings → Secrets → Actions)
3. ✅ Enable GitHub Actions
4. ✅ Test with "Run workflow" button
5. ✅ Wait for scheduled runs at 6 AM GMT+1

## Tips

- **Test without sending notifications**: Comment out the notification step in `weather_agent.py` temporarily
- **Test individual sources**: Modify `aggregate_weather_data()` to test one source at a time
- **Use debug mode**: Set `DEBUG=1` to see full output
- **Check logs**: All errors are printed to console with clear messages

---

**Happy Testing! 🧪**


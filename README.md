# 🌤️ Weather AI Agent

A completely free, automated weather notification system that runs daily via GitHub Actions. Get personalized weather forecasts and AI-powered clothing recommendations delivered to your phone every morning at 6 AM (GMT+1).

## ✨ Features

- **Multiple Weather Sources**: Aggregates data from 5 free weather APIs for maximum reliability
  - Open-Meteo (no API key needed)
  - WeatherAPI.com (free tier)
  - OpenWeatherMap (free tier)
  - 7Timer (no API key needed)
  - wttr.in (no API key needed)

- **AI-Powered Recommendations**: Uses free AI APIs (Groq/Hugging Face) to generate personalized clothing advice
- **Smart Aggregation**: Calculates consensus weather data using median values from multiple sources
- **Push Notifications**: Sends formatted notifications to your phone via Ntfy.sh
- **Completely Free**: All services used are free (within their generous limits)
- **Automated**: Runs daily via GitHub Actions at your specified time

## 📋 Prerequisites

Before setting up, you'll need:

1. A GitHub account (free)
2. Your location coordinates (latitude and longitude)
3. A smartphone with Ntfy.sh app installed
4. API keys (all free):
   - Groq API key (recommended) OR Hugging Face API key
   - Optional: WeatherAPI.com and OpenWeatherMap keys for more data sources

## 🚀 Quick Start

### 1. Fork/Clone This Repository

```bash
git clone https://github.com/yourusername/weather-agent.git
cd weather-agent
```

Or click the "Fork" button on GitHub to create your own copy.

### 2. Get Your Location Coordinates

Find your latitude and longitude:
- Use [LatLong.net](https://www.latlong.net/)
- Or Google Maps: Right-click your location → Click the coordinates

Example: Paris, France = `48.8566, 2.3522`

### 3. Get API Keys (All Free)

#### Required: AI API Key (Choose One)

**Option A: Groq (Recommended - Faster)**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free account
3. Navigate to API Keys
4. Create a new API key
5. Free tier: 14,400 requests/day

**Option B: Hugging Face**
1. Go to [huggingface.co](https://huggingface.co)
2. Sign up for free account
3. Go to Settings → Access Tokens
4. Create a new token with "Read" permission
5. Free tier: Generous limits

#### Optional: Additional Weather APIs

**WeatherAPI.com** (Recommended for better accuracy)
1. Go to [weatherapi.com](https://www.weatherapi.com/)
2. Sign up for free account
3. Get your API key from dashboard
4. Free tier: 1,000,000 calls/month

**OpenWeatherMap**
1. Go to [openweathermap.org](https://openweathermap.org/api)
2. Sign up for free account
3. Get your API key
4. Free tier: 1,000 calls/day

### 4. Set Up Ntfy.sh

1. Install Ntfy.sh app on your phone:
   - [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - [iOS](https://apps.apple.com/app/ntfy/id1625396347)

2. Open the app and create a unique topic name (e.g., `myweather_abc123`)
   - Make it unique to avoid getting others' notifications!
   - Example: `weather_john_xyz789`

3. Subscribe to your topic in the app

### 5. Configure GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Description | Example | Required |
|------------|-------------|---------|----------|
| `LOCATION_LAT` | Your latitude | `48.8566` | ✅ Yes |
| `LOCATION_LON` | Your longitude | `2.3522` | ✅ Yes |
| `NTFY_TOPIC` | Your unique Ntfy.sh topic | `weather_john_xyz789` | ✅ Yes |
| `GROQ_API_KEY` | Groq API key | `gsk_...` | ✅ Yes (or HF) |
| `HUGGINGFACE_API_KEY` | Hugging Face token | `hf_...` | ⚠️ Alternative to Groq |
| `WEATHERAPI_KEY` | WeatherAPI.com key | `abc123...` | ⭐ Recommended |
| `OPENWEATHER_KEY` | OpenWeatherMap key | `xyz789...` | ⭐ Recommended |

**Note**: You need either `GROQ_API_KEY` or `HUGGINGFACE_API_KEY`. The optional weather API keys improve accuracy but the agent will work without them.

### 6. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. Click "I understand my workflows, go ahead and enable them"
3. The workflow will now run automatically every day at 6 AM GMT+1

### 7. Test It!

Don't wait until tomorrow! Test it now:

1. Go to **Actions** tab
2. Click on **Daily Weather Notification** workflow
3. Click **Run workflow** → **Run workflow**
4. Wait ~30 seconds
5. Check your phone for the notification!

## 📱 What You'll Receive

Every morning at 6 AM, you'll get a notification like this:

```
🌤️ Good Morning! Weather Report
===================================

📊 Next 10 Hours Summary:
   Temperature: 12°C - 18°C
   Conditions: Partly cloudy

👔 What to Wear:
Based on the forecast, I recommend wearing a light 
jacket or sweater. The temperature will be mild but 
may feel cool in the morning. No rain expected, so 
you can leave the umbrella at home!

⏰ Hourly Forecast:
  +0h: 12.0°C Partly cloudy
  +1h: 13.5°C Partly cloudy
  +2h: 15.0°C Mostly sunny
  +3h: 16.5°C Sunny
  +4h: 17.5°C Sunny
  +5h: 18.0°C Sunny
  +6h: 17.5°C Partly cloudy
  +7h: 16.0°C Partly cloudy
  +8h: 15.0°C Cloudy
  +9h: 14.0°C Cloudy

📡 Data from 5 sources (Reliability: 100%)
Sources: Open-Meteo, WeatherAPI, wttr.in
```

## ⚙️ Customization

### Change Notification Time

Edit `.github/workflows/weather-notification.yml`:

```yaml
schedule:
  # Change '0 5' to your desired UTC time
  # Current: 5 AM UTC = 6 AM GMT+1
  - cron: '0 5 * * *'
```

**Time Zone Conversion Examples**:
- 6 AM GMT+1 (Paris) = `0 5` (5 AM UTC)
- 7 AM EST (New York) = `0 12` (12 PM UTC)
- 8 AM PST (Los Angeles) = `0 16` (4 PM UTC)
- 6 AM JST (Tokyo) = `0 21` (9 PM UTC previous day)

Use [crontab.guru](https://crontab.guru/) to help with cron syntax.

### Adjust Forecast Hours

Edit `src/weather_sources.py` to change from 10 hours to your preference.

### Customize Notification Format

Edit `src/ai_recommender.py` in the `format_notification()` method.

## 🔧 Local Testing

Test the agent locally before deploying:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LOCATION_LAT="48.8566"
export LOCATION_LON="2.3522"
export NTFY_TOPIC="your_topic_name"
export GROQ_API_KEY="your_groq_key"
export WEATHERAPI_KEY="your_weatherapi_key"  # optional
export OPENWEATHER_KEY="your_openweather_key"  # optional

# Run the agent
cd src
python weather_agent.py
```

Enable debug mode to see the full notification:

```bash
export DEBUG=1
python weather_agent.py
```

## 📊 How It Works

1. **GitHub Actions** triggers the workflow daily at 6 AM GMT+1
2. **Weather Sources** fetches data from 5 different APIs simultaneously
3. **Aggregation** calculates median values for temperature, precipitation, wind, etc.
4. **AI Recommender** analyzes the weather and generates clothing advice
5. **Ntfy.sh** delivers the formatted notification to your phone

## 🆓 Cost Breakdown

| Service | Free Tier | Usage | Cost |
|---------|-----------|-------|------|
| GitHub Actions | 2,000 min/month | ~1 min/day | $0 |
| Open-Meteo | Unlimited | 1 call/day | $0 |
| WeatherAPI.com | 1M calls/month | 1 call/day | $0 |
| OpenWeatherMap | 1,000 calls/day | 1 call/day | $0 |
| 7Timer | Unlimited | 1 call/day | $0 |
| wttr.in | Unlimited | 1 call/day | $0 |
| Groq | 14,400 req/day | 1 req/day | $0 |
| Ntfy.sh | Unlimited | 1 msg/day | $0 |
| **TOTAL** | | | **$0/month** |

## 🛠️ Troubleshooting

### Notification Not Received

1. Check your phone's Ntfy.sh app is running
2. Verify you're subscribed to the correct topic
3. Check GitHub Actions logs for errors
4. Ensure all required secrets are set correctly

### "Failed to fetch from at least 2 weather sources"

- At least 2 weather APIs must work for the agent to run
- Add optional API keys (WeatherAPI, OpenWeatherMap) for redundancy
- Check if any APIs are temporarily down

### AI Recommendation Failed

- Verify your Groq or Hugging Face API key is correct
- Check API rate limits haven't been exceeded
- The agent will fall back to rule-based recommendations

### GitHub Actions Not Running

1. Ensure Actions are enabled in repository settings
2. Check the workflow file syntax is correct
3. Verify the cron schedule is in UTC time

## 🔒 Privacy & Security

- All API keys are stored as GitHub Secrets (encrypted)
- Weather data is fetched but not stored
- Notifications are sent directly to your phone
- No data is collected or shared with third parties
- Open source - audit the code yourself!

## 📝 Project Structure

```
weather-agent/
├── .github/
│   └── workflows/
│       └── weather-notification.yml  # GitHub Actions workflow
├── src/
│   ├── weather_agent.py             # Main orchestrator
│   ├── weather_sources.py           # Multi-source weather fetching
│   └── ai_recommender.py            # AI clothing recommendations
├── requirements.txt                  # Python dependencies
└── README.md                        # This file
```

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest new features
- Add more weather sources
- Improve AI recommendations
- Enhance notification formatting

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Weather data from Open-Meteo, WeatherAPI.com, OpenWeatherMap, 7Timer, and wttr.in
- AI powered by Groq and Hugging Face
- Notifications via Ntfy.sh
- Automated by GitHub Actions

## 💡 Tips

- **Add more weather sources** for even better reliability
- **Customize the AI prompt** in `ai_recommender.py` for personalized advice
- **Set up multiple topics** for different locations (family members)
- **Use workflow_dispatch** to test changes without waiting for the scheduled run
- **Check GitHub Actions logs** if something goes wrong

---

**Enjoy your daily weather notifications! ☀️🌧️⛈️❄️**

If you find this useful, please star ⭐ the repository!


# ⚡ Quick Start Guide

Get your weather notifications running in 5 minutes!

## Step 1: Get API Keys (5 minutes)

### Required: Groq API Key (FREE)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (use Google/GitHub login)
3. Click "API Keys" → "Create API Key"
4. Copy your key (starts with `gsk_`)

### Optional but Recommended: WeatherAPI Key (FREE)
1. Go to [weatherapi.com](https://www.weatherapi.com/)
2. Sign up
3. Copy your API key from the dashboard

## Step 2: Get Your Coordinates (1 minute)

1. Go to [latlong.net](https://www.latlong.net/)
2. Type your city name
3. Copy the latitude and longitude

Example: Paris = `48.8566, 2.3522`

## Step 3: Setup Ntfy.sh (2 minutes)

1. Install the app on your phone:
   - [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - [iOS](https://apps.apple.com/app/ntfy/id1625396347)

2. Open app → Click "+" → Create a topic
   - Use a unique name: `weather_yourname_123`
   - Remember this topic name!

3. Subscribe to your topic in the app

## Step 4: Configure GitHub (3 minutes)

1. **Fork this repository** (click "Fork" button on GitHub)

2. **Add Secrets** to your forked repo:
   - Go to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Add these secrets:

| Secret Name | Your Value |
|------------|------------|
| `LOCATION_LAT` | Your latitude (e.g., `48.8566`) |
| `LOCATION_LON` | Your longitude (e.g., `2.3522`) |
| `NTFY_TOPIC` | Your topic name (e.g., `weather_john_123`) |
| `GROQ_API_KEY` | Your Groq API key (e.g., `gsk_...`) |
| `WEATHERAPI_KEY` | Your WeatherAPI key (optional) |

3. **Enable GitHub Actions**:
   - Go to "Actions" tab
   - Click "I understand my workflows, go ahead and enable them"

## Step 5: Test It! (1 minute)

1. Go to "Actions" tab in your GitHub repo
2. Click "Daily Weather Notification"
3. Click "Run workflow" → "Run workflow"
4. Wait 30 seconds
5. Check your phone! 📱

## ✅ Done!

You'll now get weather notifications every morning at 6 AM GMT+1!

## 🔧 Troubleshooting

**No notification?**
- Check your phone's Ntfy.sh app is running
- Verify you're subscribed to the correct topic
- Check GitHub Actions logs for errors

**Want to change the time?**
- Edit `.github/workflows/weather-notification.yml`
- Change the cron schedule (currently `0 5` = 5 AM UTC)

**Need help?**
- See the full [README.md](README.md) for detailed instructions
- Open an issue on GitHub

## 💡 Pro Tips

- Add `OPENWEATHER_KEY` secret for even more accurate weather
- Use `workflow_dispatch` to test anytime without waiting
- Star ⭐ the repo if you find it useful!

---

**Total setup time: ~10 minutes**  
**Cost: $0/month (completely free!)**


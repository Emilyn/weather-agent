# 🌤️ Weather AI Agent

A completely free, automated weather notification system that runs daily via GitHub Actions. Get personalized weather forecasts and AI-powered clothing recommendations delivered to your phone every morning. 

## ✨ Features

- **Multiple Weather Sources**: Aggregates data from 4 free weather APIs for maximum reliability
- **Comprehensive Weather Data**: Tracks temperature, rain, snow, wind speed, and humidity
- **AI-Powered Recommendations**: Uses free GitHub Models (no key needed in Actions), with an optional Groq fallback and self-reflection for quality
- **Smart Aggregation**: Calculates consensus weather data using weighted medians from multiple sources
- **Self-Reflection Pattern**: Agent evaluates and improves its own outputs iteratively
- **Push Notifications**: Sends formatted notifications to your phone via Ntfy.sh
- **Completely Free**: All services used are free (within their generous limits)
- **Automated**: Runs daily via GitHub Actions at your specified time

## 📋 Prerequisites

Before setting up, you'll need:

1. A GitHub account (free)
2. Your location coordinates (latitude and longitude)
3. A smartphone with Ntfy.sh app installed
4. Optional API keys (all free):
   - WeatherAPI.com and OpenWeatherMap keys for more data sources
   - Groq key as a backup AI provider (AI uses GitHub Models by default, no key needed)

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

#### AI: GitHub Models (Default, No Setup)

The workflow uses [GitHub Models](https://github.com/marketplace/models) through the built-in `GITHUB_TOKEN`, so there's nothing to sign up for. The Groq key below is an optional backup.

**Optional backup: Groq**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free account
3. Navigate to API Keys
4. Create a new API key
5. Free tier: 14,400 requests/day

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

Follow these steps to add your API keys and configuration as GitHub Secrets:

1. **Navigate to your repository** on GitHub
2. Click the **Settings** tab (at the top of the repository page)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click the **New repository secret** button (green button, top right)
5. For each secret below:
   - Enter the **Name** exactly as shown (case-sensitive)
   - Paste your **Value** in the secret field
   - Click **Add secret**
   - Repeat for each secret you need to add

**Required Secrets** (add these first):

6. Add the following secrets one by one:

| Secret Name | Description | Example | Required |
|------------|-------------|---------|----------|
| `LOCATION_LAT` | Your latitude | `48.8566` | ✅ Yes |
| `LOCATION_LON` | Your longitude | `2.3522` | ✅ Yes |
| `NTFY_TOPIC` | Your unique Ntfy.sh topic | `weather_john_xyz789` | ✅ Yes |
| `GROQ_API_KEY` | Groq API key | `gsk_...` | Optional fallback |
| `WEATHERAPI_KEY` | WeatherAPI.com key | `abc123...` | ⭐ Recommended |
| `OPENWEATHER_KEY` | OpenWeatherMap key | `xyz789...` | ⭐ Recommended |

**Note**: No AI key is needed when running in GitHub Actions: the workflow uses **GitHub Models** (free) through the built-in `GITHUB_TOKEN`. A Groq key is an optional fallback, and if every AI provider fails the agent still sends rule-based clothing advice. The optional weather API keys improve accuracy but the agent will work without them.

**Running locally**: set `GITHUB_TOKEN` to a GitHub personal access token with the `models:read` permission (or run `export GITHUB_TOKEN=$(gh auth token)`).

**Optional — GitHub model**: the default is `openai/gpt-4.1-mini`. To choose another, add a repository **variable** (Settings → Secrets and variables → Actions → Variables tab) named `GITHUB_MODELS_MODEL` (see [github.com/marketplace/models](https://github.com/marketplace/models)). If the model is retired, the agent picks an available one automatically.

**Optional — Groq model**: Groq retires models from time to time. To pick one yourself, add a repository **variable** (Settings → Secrets and variables → Actions → Variables tab) named `GROQ_MODEL`, e.g. `llama-3.3-70b-versatile` (see [console.groq.com/docs/models](https://console.groq.com/docs/models)). If it's unset or the model is retired, the agent picks an available model automatically.

### 6. Enable GitHub Actions

1. Go to the **Actions** tab in your repository (top navigation bar)
2. If you see a message about enabling workflows, click **"I understand my workflows, go ahead and enable them"**
3. The workflow will now run automatically every morning (see [Reliable 06:00 delivery](#reliable-0600-delivery) below)

### 7. Run GitHub Actions (Manual Testing)

**Don't wait until tomorrow! Test it right now:**

#### Option A: Run from Actions Tab (Recommended)

1. Go to the **Actions** tab in your repository
2. In the left sidebar, click on **Daily Weather Notification** workflow
3. Click the **Run workflow** dropdown button (top right)
4. Select the branch (usually `main` or `master`)
5. Click the green **Run workflow** button
6. Wait ~30 seconds for it to complete
7. Check your phone for the notification! 📱

#### Option B: Check Workflow Status

After triggering a run:

1. You'll see a new workflow run appear in the list
2. Click on the run to see detailed logs
3. Watch it progress through:
   - ✅ Set up Python
   - ✅ Install dependencies
   - ✅ Run weather agent
   - ✅ Send notification
4. If it shows a green checkmark ✅, it succeeded!
5. If it shows a red X ❌, click it to see error details

#### Option C: Automatic Scheduled Runs

Once enabled, the workflow runs automatically:
- **Schedule**: 06:00 Stockholm time by default, adjusted automatically for summer/winter time
- **Once per day**: extra triggers on the same day are skipped
- **Check history**: Go to Actions tab to see all past runs

#### Reliable 06:00 Delivery

GitHub's built-in scheduler often starts runs late, from a few minutes up to several hours, and it pauses schedules after 60 days without repository activity. The workflow keeps GitHub's schedule as a backup, but for an on-time notification use a free external scheduler to start the run:

1. Create a fine-grained personal access token: GitHub → Settings → Developer settings → Fine-grained tokens. Give it access to this repository only, with the **Actions: Read and write** permission.
2. Sign up at [cron-job.org](https://cron-job.org) (free) and create a cron job:
   - **URL**: `https://api.github.com/repos/<your-user>/weather-agent/actions/workflows/weather-notification.yml/dispatches`
   - **Schedule**: every day at 06:00, time zone **Europe/Stockholm**
   - **Advanced → Request method**: `POST`
   - **Headers**: `Authorization: Bearer <your token>`, `Accept: application/vnd.github+json`
   - **Request body**: `{"ref": "main", "inputs": {"trigger": "scheduler"}}`
3. Use **Test run** in cron-job.org and check that a run appears in the Actions tab.

Runs started this way, and GitHub's backup schedule, send at most one notification per day. Manual runs from the Actions tab always send.

## 📱 What You'll Receive

Every morning at 6 AM, you'll get a notification like this:

```
🌤️ Today: 9°C – 17°C

🌡️ Temperature
• 8.6°C at 06:00 → 16.6°C at 16:00
• Feels like: 8.0°C → 16.6°C

🌧️ Rain
• ⚠️ Expected · 2.4mm total · Peak: 0.9mm/h
• At: 14:00, 15:00, 16:00

🌬️ Wind
• ✅ Light · 1.5 m/s avg · 1.7 m/s peak

─────────────────
👔 Recommendation
Cool morning, mild afternoon: wear a light jacket
over a sweater and bring an umbrella for the
afternoon showers.

Have a great day!
```

## ⚙️ Customization

### Change Notification Time

1. Set the time in your external scheduler (see [Reliable 06:00 delivery](#reliable-0600-delivery)).
2. Add repository **variables** (Settings → Secrets and variables → Actions → Variables tab):
   - `NOTIFY_TIME`: local send time, e.g. `07:30` (default `06:00`)
   - `NOTIFY_TIMEZONE`: e.g. `Europe/Paris` (default `Europe/Stockholm`)
3. Update the backup `cron` lines in `.github/workflows/weather-notification.yml` so they fire at your local time in both summer and winter (cron uses UTC). Use [crontab.guru](https://crontab.guru/) to help with cron syntax.

### Forecast Period

The forecast covers every hour from when the agent runs until midnight, so a 06:00 notification covers the whole day.

### Customize Notification Format

Edit `src/ai_recommender.py` in the `format_notification()` method.

## 🔧 Local Testing

Test the agent locally before deploying. See [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for detailed setup instructions.

Quick test:
```bash
pip install -r requirements.txt
# Create .env file with your API keys
cd src && python weather_agent.py
```

## 📊 How It Works

1. **GitHub Actions** triggers the workflow daily at your scheduled time
2. **Weather Sources** fetches data from 4 different APIs and aligns them to the same local hours
3. **Aggregation** calculates weighted median values for temperature, precipitation, wind, etc.
4. **Reflection Engine** evaluates data quality and identifies issues
5. **AI Recommender** generates clothing advice with iterative refinement
6. **Reflection Engine** evaluates recommendation quality and refines if needed
7. **Ntfy.sh** delivers the formatted notification to your phone

See [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for architecture details.


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

- Check the Actions log for the GitHub Models or Groq error message
- Check API rate limits haven't been exceeded
- The agent will fall back to rule-based recommendations

### GitHub Actions Not Running

**Workflow won't start:**
1. Ensure Actions are enabled: Go to **Settings** → **Actions** → **General** → Make sure "Allow all actions" is selected
2. Check the workflow file exists: `.github/workflows/weather-notification.yml`
3. Verify the workflow file syntax is correct (YAML format)
4. Check if you've added all required secrets (see step 5)

**Can't find "Run workflow" button:**
1. Make sure you're on the **Actions** tab
2. Click on the workflow name in the left sidebar first
3. The button should appear at the top right
4. If it's still missing, the workflow file might not exist yet

**Workflow runs but fails:**
1. Click on the failed run to see error logs
2. Check if all required secrets are set correctly
3. Verify your API keys are valid (not expired)
4. Check the logs for specific error messages
5. Common issues:
   - Missing secrets → Add them in Settings → Secrets
   - Invalid API keys → Regenerate and update secrets
   - Network errors → Usually temporary, try again

**Scheduled runs not happening:**
1. Verify the cron schedule is in UTC time (not your local time)
2. Check Actions tab for past runs (might have failed silently)
3. Ensure the repository is active (GitHub pauses workflows on inactive repos)
4. First scheduled run may take up to 24 hours to start

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
│       ├── weather-notification.yml  # Daily notification workflow
│       └── tests.yml                 # Unit tests on push / pull request
├── src/
│   ├── weather_agent.py             # Main orchestrator
│   ├── weather_sources.py           # Multi-source weather fetching
│   ├── ai_recommender.py            # AI clothing recommendations
│   ├── reflection_engine.py         # Self-evaluation and refinement
│   └── utils.py                     # Shared utilities (DRY principles)
├── tests/                           # Unit tests (python -m unittest discover tests)
├── docs/
│   └── DEV_GUIDE.md                 # Development guide & coding patterns
├── requirements.txt                  # Python dependencies
└── README.md                        # This file
```

## 🤝 Contributing

Contributions are welcome! Please see [docs/DEV_GUIDE.md](docs/DEV_GUIDE.md) for:
- Development setup instructions
- Coding patterns and principles (DRY, Reflection, etc.)
- Architecture overview
- Contribution guidelines

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Weather data from Open-Meteo, WeatherAPI.com, OpenWeatherMap, and wttr.in
- AI powered by GitHub Models and Groq
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


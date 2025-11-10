#!/bin/bash
# Quick script to run the weather agent locally with proper environment setup

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from template..."
    if [ -f "env" ]; then
        cp env .env
        echo "✅ Created .env file. Please edit it with your values before running."
        echo "   Required: LOCATION_LAT, LOCATION_LON, NTFY_TOPIC, GROQ_API_KEY"
        exit 1
    else
        echo "❌ No 'env' template file found. Please create a .env file manually."
        exit 1
    fi
fi

# Run the agent
echo "🌤️  Running Weather AI Agent..."
echo ""
cd src
python3 weather_agent.py


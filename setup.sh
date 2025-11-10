#!/bin/bash

# Weather AI Agent Setup Script
# This script helps you set up the project for local testing

echo "🌤️  Weather AI Agent Setup"
echo "=========================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Failed to create virtual environment"
    exit 1
fi

echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Edit the .env file with your actual values:"
    echo "   - LOCATION_LAT and LOCATION_LON (your coordinates)"
    echo "   - NTFY_TOPIC (your unique topic name)"
    echo "   - GROQ_API_KEY (your Groq API key)"
    echo "   - Optional: WEATHERAPI_KEY and OPENWEATHER_KEY"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

echo ""
echo "=========================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Test the agent: cd src && python weather_agent.py"
echo ""
echo "For GitHub Actions setup, see README.md"
echo ""


#!/bin/bash

# Script to set up and run the Telegram Bot

# Make the script executable
chmod +x run_simplified_telegram_bot.py

# Print banner
echo "====================================="
echo "SonicKid Telegram Bot Setup"
echo "====================================="

# Check for environment variables
if [ ! -f .env.telegram ]; then
    echo "❌ .env.telegram file not found. Creating template..."
    
    cat > .env.telegram << EOL
# Telegram Bot Configuration

# Telegram Bot Token (Required)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Database URL (Optional, for data retrieval)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres

# OpenRouter API Key (Optional, for AI responses)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Telegram Chat IDs
# Comma-separated list of all chat IDs where the bot is active
TELEGRAM_CHAT_IDS=

# Specialized chat groups
TELEGRAM_BANDIT_KIDZ_CHAT_ID=  # BanditKidz Media group for advanced features
TELEGRAM_SONIC_LIDZ_CHAT_ID=   # SonicLidz 2.0 main community chat
EOL
    
    echo "✅ Created .env.telegram template"
    echo "🔧 Please edit .env.telegram with your bot token and API keys"
    exit 1
fi

# Check for bot token
BOT_TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env.telegram | cut -d "=" -f 2)
if [ "$BOT_TOKEN" = "your_telegram_bot_token_here" ] || [ -z "$BOT_TOKEN" ]; then
    echo "❌ TELEGRAM_BOT_TOKEN not set in .env.telegram"
    echo "🔧 Please edit .env.telegram with your Telegram bot token"
    exit 1
fi

# Check for OpenRouter API key
OR_KEY=$(grep "OPENROUTER_API_KEY" .env.telegram | cut -d "=" -f 2)
if [ "$OR_KEY" = "your_openrouter_api_key_here" ] || [ -z "$OR_KEY" ]; then
    echo "⚠️ OPENROUTER_API_KEY not set in .env.telegram"
    echo "🔧 Some AI response features may not work without this key"
fi

# Install required packages
echo "📦 Installing required packages..."
pip install python-telegram-bot==20.7 python-dotenv asyncpg aiohttp

# Run the bot
echo "🚀 Starting Telegram Bot..."
python run_simplified_telegram_bot.py
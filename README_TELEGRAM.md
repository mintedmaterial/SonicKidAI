# SonicKid Telegram Bot

This is a simplified Telegram bot implementation for the SonicKid AI platform that provides crypto market insights and AI-powered analysis.

## Features

- Real-time token price data from the database
- Market analysis and insights using AI
- Contract address analysis
- NFT collection insights
- Trading signals for crypto pairs
- General crypto Q&A with AI-powered responses

## Setup Instructions

### Prerequisites

1. A Telegram bot token (create one using [@BotFather](https://t.me/BotFather) on Telegram)
2. An OpenRouter API key (optional, for AI responses)
3. PostgreSQL database connection (already set up in the project)

### Quick Setup

1. Run the setup script:
   ```bash
   ./run_telegram_bot_setup.sh
   ```

2. Edit the `.env.telegram` file with your own values:
   ```
   TELEGRAM_BOT_TOKEN=your_token_from_botfather
   OPENROUTER_API_KEY=your_openrouter_key
   TELEGRAM_CHAT_IDS=id1,id2,id3
   TELEGRAM_BANDIT_KIDZ_CHAT_ID=bandit_group_id
   TELEGRAM_SONIC_LIDZ_CHAT_ID=sonic_group_id
   ```

3. Run the bot:
   ```bash
   python run_simplified_telegram_bot.py
   ```

### Manual Setup

1. Create a `.env.telegram` file with the following content:
   ```
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   
   # Telegram Chat IDs
   TELEGRAM_CHAT_IDS=
   
   # Specialized chat groups
   TELEGRAM_BANDIT_KIDZ_CHAT_ID=
   TELEGRAM_SONIC_LIDZ_CHAT_ID=
   ```

2. Install required packages:
   ```bash
   pip install python-telegram-bot==20.7 python-dotenv asyncpg aiohttp
   ```

3. Run the bot:
   ```bash
   python run_simplified_telegram_bot.py
   ```

## Bot Commands

- `/start` - Start the bot and get welcome message
- `/help` - Display help information
- `/price <symbol>` - Get token price data (e.g., `/price SONIC`)
- `/market` - Get recent market data
- `/sonic` - Get Sonic chain insights
- `/token <address>` - Analyze any token contract
- `/nft <collection>` - Get NFT collection insights
- `/trade <pair>` - Get trading signals
- `/query <question>` - Ask a specific question

## Group Functionalities

- **BanditKidz Media Group**: Advanced features like trading analysis and AI training
- **SonicLidz 2.0**: Main community chat for member interactions

## Development

The bot is implemented in `simplified_telegram_bot.py` with a modular design:

- `DatabaseConnector`: Handles PostgreSQL database queries
- `InstructorAgent`: Provides AI-powered responses using OpenRouter
- `SimplifiedTelegramBot`: Main bot class that handles commands and messages

## Testing

Run the test script to ensure everything is working properly:

```bash
python test_simplified_telegram_bot.py
```

This will check the database connection, instructor agent, and bot initialization.

## Troubleshooting

- If you see a "TELEGRAM_BOT_TOKEN environment variable not set" error, make sure to set it in `.env.telegram`
- For AI functionality, ensure your OpenRouter API key is valid
- Check PostgreSQL database connection if price data isn't loading
- Make sure your bot has the necessary permissions in group chats
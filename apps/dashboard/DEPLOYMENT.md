# SonicKid Dashboard Deployment Guide

This guide explains how to deploy the SonicKid dashboard, which serves as both a web application and a Telegram Mini App.

## Prerequisites

- Node.js 16+
- pnpm
- Telegram Bot Token (from BotFather)
- ThirdWeb API credentials
- Subgraph endpoint URL

## Environment Setup

1. Copy the environment example file:
   ```bash
   cp .env.example .env
   ```

2. Fill in the required environment variables:
   ```env
   # ThirdWeb Configuration
   VITE_THIRDWEB_CLIENT_ID=your_client_id
   VITE_THIRDWEB_SECRET_KEY=your_secret_key

   # Subgraph Configuration
   VITE_SUBGRAPH_ENDPOINT=https://api.studio.thegraph.com/query/your-id/sonic-blockchain/version
   VITE_SUBGRAPH_WS_ENDPOINT=wss://api.studio.thegraph.com/query/your-id/sonic-blockchain/version

   # Telegram Configuration
   VITE_TELEGRAM_BOT_USERNAME=your_bot_username
   VITE_TELEGRAM_BOT_TOKEN=your_bot_token
   ```

## Building the Application

1. Install dependencies:
   ```bash
   pnpm install
   ```

2. Build the application:
   ```bash
   pnpm build
   ```

The build output will be in the `dist` directory.

## Deployment Options

### 1. Vercel (Recommended)

1. Install Vercel CLI:
   ```bash
   npm i -g vercel
   ```

2. Deploy:
   ```bash
   vercel
   ```

3. For production:
   ```bash
   vercel --prod
   ```

### 2. Netlify

1. Install Netlify CLI:
   ```bash
   npm i -g netlify-cli
   ```

2. Deploy:
   ```bash
   netlify deploy
   ```

3. For production:
   ```bash
   netlify deploy --prod
   ```

### 3. Static Hosting

The `dist` directory can be deployed to any static hosting service:
- AWS S3 + CloudFront
- GitHub Pages
- Firebase Hosting

## Telegram Mini App Setup

1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Use the `/newapp` command
3. Choose your bot
4. Enter app title and description
5. Enter your deployed URL (e.g., https://your-app.vercel.app)

## Post-Deployment Verification

1. Check web access:
   - Visit your deployed URL
   - Verify all features work
   - Test authentication flow

2. Check Telegram Mini App:
   - Open your bot in Telegram
   - Start the Mini App
   - Verify Telegram-specific features

3. Test GraphQL Integration:
   - Check real-time data updates
   - Verify subgraph queries
   - Monitor WebSocket connections

## Monitoring

- Set up error tracking (e.g., Sentry)
- Monitor API endpoints
- Watch GraphQL query performance
- Track Telegram Bot API usage

## Troubleshooting

1. Telegram Web App not loading:
   - Verify the script is loaded: `https://telegram.org/js/telegram-web-app.js`
   - Check bot token and username in environment variables
   - Ensure HTTPS is enabled

2. Subgraph issues:
   - Verify endpoint URLs
   - Check WebSocket connection
   - Monitor query performance

3. ThirdWeb connection:
   - Verify client ID and secret
   - Check chain configuration
   - Test wallet connections

## Security Considerations

1. Environment Variables:
   - Never commit .env files
   - Use secret management in production
   - Rotate keys regularly

2. API Access:
   - Implement rate limiting
   - Use CORS appropriately
   - Validate all inputs

3. Telegram Security:
   - Validate Telegram Web App data
   - Check user authentication
   - Monitor bot activity

## Updates and Maintenance

1. Regular updates:
   ```bash
   pnpm update
   ```

2. Deploy changes:
   ```bash
   pnpm build
   # Use your chosen deployment method
   ```

3. Monitor logs and performance after updates

## Support

For issues and support:
- Check the GitHub repository
- Review Telegram Bot API documentation
- Contact the development team

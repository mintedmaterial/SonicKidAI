# Social Providers

This package provides social media platform integrations for the SonicKid AI framework. It implements the core `SocialPlatform` interface for various social media platforms.

## Supported Platforms

### Twitter
The Twitter provider uses a combination of the official Twitter API v2 and our custom Twitter client for enhanced functionality.

```typescript
import { createTwitterProvider } from '@sonickid/social-providers'

const twitter = createTwitterProvider({
  apiKey: process.env.TWITTER_API_KEY!,
  apiSecret: process.env.TWITTER_API_SECRET!,
  accessToken: process.env.TWITTER_ACCESS_TOKEN!,
  accessTokenSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET!,
  bearerToken: process.env.TWITTER_BEARER_TOKEN!,
  authToken: process.env.TWITTER_AUTH_TOKEN!
})

// Basic operations
await twitter.post('Hello from SonicKid AI!')
await twitter.delete('tweet_id')
await twitter.getEngagement('tweet_id')

// Extended functionality
await twitter.getTimeline(20)
await twitter.replyToTweet('tweet_id', 'Reply content')
await twitter.retweet('tweet_id')
```

## Environment Variables

The following environment variables are required for the Twitter provider:

```env
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
TWITTER_BEARER_TOKEN=your_bearer_token
TWITTER_AUTH_TOKEN=your_auth_token
```

## Error Handling

All provider methods throw errors with descriptive messages when operations fail. It's recommended to wrap calls in try-catch blocks:

```typescript
try {
  await twitter.post('Hello!')
} catch (error) {
  console.error('Failed to post tweet:', error)
}
```

## Rate Limiting

The providers implement rate limiting according to each platform's guidelines:

- Twitter: 
  - Tweet posting: 300 per 3 hours
  - Timeline fetching: 100,000 per day
  - Engagement metrics: 500,000 per day

## Future Platforms

The following platforms are planned for future implementation:

- Discord
- Telegram
- LinkedIn
- Instagram

## Contributing

To add a new social platform provider:

1. Create a new directory under `src/` for your platform
2. Implement the `SocialPlatform` interface
3. Add configuration types and factory function
4. Update the package exports
5. Add documentation

## License

MIT

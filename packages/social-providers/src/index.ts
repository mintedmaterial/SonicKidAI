// Twitter Provider
export { TwitterProvider, type TwitterProviderConfig } from './twitter/provider'
export { createTwitterProvider } from './twitter/factory'

// Telegram Provider
export { TelegramProvider, type TelegramProviderConfig } from './telegram/provider'

// Discord Provider
export { DiscordProvider, type DiscordProviderConfig } from './discord/provider'

// Factory functions
export const createTelegramProvider = (config: TelegramProviderConfig) => new TelegramProvider(config)
export const createDiscordProvider = (config: DiscordProviderConfig) => new DiscordProvider(config)

// Provider type union
export type SocialProviderType = 'TWITTER' | 'TELEGRAM' | 'DISCORD'

// Provider factory map
export const providerFactories = {
  TWITTER: createTwitterProvider,
  TELEGRAM: createTelegramProvider,
  DISCORD: createDiscordProvider
} as const

// Helper function to create any provider type
export function createSocialProvider(type: SocialProviderType, config: any) {
  const factory = providerFactories[type]
  if (!factory) {
    throw new Error(`Unknown provider type: ${type}`)
  }
  return factory(config)
}

import { TwitterProvider, type TwitterProviderConfig } from './provider'

export function createTwitterProvider(config: TwitterProviderConfig): TwitterProvider {
  return new TwitterProvider(config)
}

import { SocialPlatform } from '@sonickid/core'

export interface DiscordProviderConfig {
  botToken: string
  channelId: string
  webhookUrl?: string
}

export class DiscordProvider implements SocialPlatform {
  name = 'DISCORD' as const
  private baseUrl = 'https://discord.com/api/v10'
  private config: DiscordProviderConfig

  constructor(config: DiscordProviderConfig) {
    this.config = config
  }

  async post(content: string): Promise<string> {
    try {
      // If webhook URL is provided, use it for posting
      if (this.config.webhookUrl) {
        const response = await fetch(this.config.webhookUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ content })
        })

        if (!response.ok) {
          throw new Error(`Discord API error: ${response.statusText}`)
        }

        const data = await response.json()
        return data.id
      }

      // Otherwise use the bot token and channel ID
      const response = await fetch(`${this.baseUrl}/channels/${this.config.channelId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bot ${this.config.botToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      })

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.id
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to send message: ${error.message}`)
    }
  }

  async delete(messageId: string): Promise<boolean> {
    try {
      const response = await fetch(
        `${this.baseUrl}/channels/${this.config.channelId}/messages/${messageId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bot ${this.config.botToken}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to delete message: ${error.message}`)
    }
  }

  async getEngagement(messageId: string): Promise<{
    reactions?: number
    replies?: number
  }> {
    try {
      const response = await fetch(
        `${this.baseUrl}/channels/${this.config.channelId}/messages/${messageId}`,
        {
          headers: {
            'Authorization': `Bot ${this.config.botToken}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        reactions: data.reactions?.reduce((total: number, reaction: any) => total + reaction.count, 0) || 0,
        replies: data.thread?.message_count || 0
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get message engagement: ${error.message}`)
    }
  }

  async replyToMessage(messageId: string, content: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/channels/${this.config.channelId}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bot ${this.config.botToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content,
          message_reference: {
            message_id: messageId,
            channel_id: this.config.channelId
          }
        })
      })

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.id
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to reply to message: ${error.message}`)
    }
  }

  async createThread(messageId: string, name: string): Promise<string> {
    try {
      const response = await fetch(
        `${this.baseUrl}/channels/${this.config.channelId}/messages/${messageId}/threads`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bot ${this.config.botToken}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name,
            auto_archive_duration: 1440 // 24 hours
          })
        }
      )

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.id
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to create thread: ${error.message}`)
    }
  }

  async addReaction(messageId: string, emoji: string): Promise<boolean> {
    try {
      const encodedEmoji = encodeURIComponent(emoji)
      const response = await fetch(
        `${this.baseUrl}/channels/${this.config.channelId}/messages/${messageId}/reactions/${encodedEmoji}/@me`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bot ${this.config.botToken}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to add reaction: ${error.message}`)
    }
  }

  async pinMessage(messageId: string): Promise<boolean> {
    try {
      const response = await fetch(
        `${this.baseUrl}/channels/${this.config.channelId}/pins/${messageId}`,
        {
          method: 'PUT',
          headers: {
            'Authorization': `Bot ${this.config.botToken}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Discord API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to pin message: ${error.message}`)
    }
  }
}

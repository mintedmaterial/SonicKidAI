import { SocialPlatform } from '@sonickid/core'

export interface TelegramProviderConfig {
  botToken: string
  chatId: string
}

export class TelegramProvider implements SocialPlatform {
  name = 'TELEGRAM' as const
  private baseUrl: string
  private config: TelegramProviderConfig

  constructor(config: TelegramProviderConfig) {
    this.config = config
    this.baseUrl = `https://api.telegram.org/bot${config.botToken}`
  }

  async post(content: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: this.config.chatId,
          text: content,
          parse_mode: 'HTML'
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.result.message_id.toString()
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to send message: ${error.message}`)
    }
  }

  async delete(messageId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/deleteMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: this.config.chatId,
          message_id: parseInt(messageId)
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to delete message: ${error.message}`)
    }
  }

  async getEngagement(messageId: string): Promise<{
    views?: number
    forwards?: number
    replies?: number
  }> {
    try {
      const response = await fetch(`${this.baseUrl}/getMessageInfo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: this.config.chatId,
          message_id: parseInt(messageId)
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      const data = await response.json()
      return {
        views: data.result.views,
        forwards: data.result.forwards,
        replies: data.result.reply_count
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get message engagement: ${error.message}`)
    }
  }

  async replyToMessage(messageId: string, content: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/sendMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: this.config.chatId,
          text: content,
          reply_to_message_id: parseInt(messageId),
          parse_mode: 'HTML'
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.result.message_id.toString()
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to reply to message: ${error.message}`)
    }
  }

  async forwardMessage(messageId: string, targetChatId: string): Promise<string> {
    try {
      const response = await fetch(`${this.baseUrl}/forwardMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: targetChatId,
          from_chat_id: this.config.chatId,
          message_id: parseInt(messageId)
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.result.message_id.toString()
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to forward message: ${error.message}`)
    }
  }

  async pinMessage(messageId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/pinChatMessage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          chat_id: this.config.chatId,
          message_id: parseInt(messageId)
        })
      })

      if (!response.ok) {
        throw new Error(`Telegram API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to pin message: ${error.message}`)
    }
  }
}

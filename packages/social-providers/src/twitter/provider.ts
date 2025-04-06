import { SocialPlatform } from '@sonickid/core'
import { TwitterClientImpl } from '@sonickid/twitter-client'

export interface TwitterProviderConfig {
  apiKey: string
  apiSecret: string
  accessToken: string
  accessTokenSecret: string
  bearerToken: string
  authToken: string
}

export class TwitterProvider implements SocialPlatform {
  name = 'TWITTER' as const
  private client: TwitterClientImpl

  constructor(config: TwitterProviderConfig) {
    this.client = new TwitterClientImpl({
      auth: {
        authToken: config.authToken
      }
    })
  }

  async post(content: string): Promise<string> {
    try {
      const response = await fetch('https://api.twitter.com/2/tweets', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.client['authToken']}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: content })
      })

      if (!response.ok) {
        throw new Error(`Twitter API error: ${response.statusText}`)
      }

      const data = await response.json()
      return data.data.id
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to post tweet: ${error.message}`)
    }
  }

  async delete(postId: string): Promise<boolean> {
    try {
      await this.client.deleteTweet(postId)
      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to delete tweet: ${error.message}`)
    }
  }

  async getEngagement(postId: string): Promise<{
    likes?: number
    retweets?: number
    replies?: number
  }> {
    try {
      const response = await fetch(`https://api.twitter.com/2/tweets/${postId}?tweet.fields=public_metrics`, {
        headers: {
          'Authorization': `Bearer ${this.client.getAuthToken()}`
        }
      })

      if (!response.ok) {
        throw new Error(`Twitter API error: ${response.statusText}`)
      }

      const { data } = await response.json()
      return {
        likes: data.public_metrics.like_count,
        retweets: data.public_metrics.retweet_count,
        replies: data.public_metrics.reply_count
      }
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get tweet engagement: ${error.message}`)
    }
  }

  async getTimeline(count: number = 20): Promise<Array<{
    id: string
    text: string
    created_at: string
    metrics?: {
      likes: number
      retweets: number
      replies: number
    }
  }>> {
    try {
      const response = await fetch(
        `https://api.twitter.com/2/tweets/search/recent?max_results=${count}&tweet.fields=public_metrics,created_at`,
        {
          headers: {
            'Authorization': `Bearer ${this.client['authToken']}`
          }
        }
      )

      if (!response.ok) {
        throw new Error(`Twitter API error: ${response.statusText}`)
      }

      const { data } = await response.json()
      return data.map((tweet: any) => ({
        id: tweet.id,
        text: tweet.text,
        created_at: tweet.created_at,
        metrics: {
          likes: tweet.public_metrics.like_count,
          retweets: tweet.public_metrics.retweet_count,
          replies: tweet.public_metrics.reply_count
        }
      }))
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to get timeline: ${error.message}`)
    }
  }

  async replyToTweet(tweetId: string, content: string): Promise<string> {
    try {
      const response = await fetch('https://api.twitter.com/2/tweets', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.client['authToken']}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: content,
          reply: {
            in_reply_to_tweet_id: tweetId
          }
        })
      })

      if (!response.ok) {
        throw new Error(`Twitter API error: ${response.statusText}`)
      }

      const { data } = await response.json()
      return data.id
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to reply to tweet: ${error.message}`)
    }
  }

  async retweet(tweetId: string): Promise<boolean> {
    try {
      const { data } = await this.getCurrentUserId()
      const response = await fetch(`https://api.twitter.com/2/users/${data.id}/retweets/${tweetId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.client['authToken']}`
        }
      })

      if (!response.ok) {
        throw new Error(`Twitter API error: ${response.statusText}`)
      }

      return true
    } catch (err) {
      const error = err as Error
      throw new Error(`Failed to retweet: ${error.message}`)
    }
  }

  private async getCurrentUserId(): Promise<any> {
    const response = await fetch('https://api.twitter.com/2/users/me', {
      headers: {
        'Authorization': `Bearer ${this.client['authToken']}`
      }
    })

    if (!response.ok) {
      throw new Error(`Twitter API error: ${response.statusText}`)
    }

    return response.json()
  }
}

"""
This file contains the prompt templates used for generating content in various tasks.
These templates are formatted strings that will be populated with dynamic data at runtime.
"""

#Twitter prompts
POST_TWEET_PROMPT =  ("Generate an engaging tweet for {agent_name}. Don't include any hashtags, links or emojis. Keep it under 280 characters. "
                      "The tweets should be pure commentary, do not shill any coins or projects apart from {Sonic Kid, BanditKid45}. Do not repeat any of the "
                      "tweets that were given as the examples. Avoid the words AI and crypto.")

REPLY_TWEET_PROMPT = ("Generate a friendly, engaging reply to this tweet: {tweet_text}. Keep it under 280 characters. Don't include any usernames, hashtags, links or emojis. ")

TWEET_ANALYSIS_PROMPT = """
Analyze the following tweets from @{username} for crypto market relevance and insights:

TWEETS:
{tweets}

Provide a brief analysis covering:
1. Overall sentiment (bullish, bearish, neutral)
2. Key themes or topics mentioned
3. Any notable price predictions or market analyses
4. Credibility assessment of the information

Focus on extracting actionable market intelligence that would be valuable for traders and investors.
"""

TRENDING_TOPICS_PROMPT = """
Analyze the following Twitter trending topics for cryptocurrency and blockchain relevance:

TRENDS:
{trends}

Identify and analyze:
1. Crypto-specific trends (tokens, projects, technologies)
2. Market-related trends (bull/bear sentiment, price movements)
3. Regulatory or news trends that might impact the crypto market
4. Emerging narratives or themes in the space

Provide a concise summary of the most relevant trends for crypto market intelligence purposes.
"""



"""
Twitter Client Actions

This module provides actions for interacting with Twitter using the ElizaOS agent-twitter-client.
"""

import time
import threading
import logging
from datetime import datetime
from src.action_handler import register_action
from src.helpers import print_h_bar
import prompts

logger = logging.getLogger(__name__)

@register_action("post-twitter-update")
async def post_twitter_update(agent, **kwargs):
    """
    Generate and post a Twitter update about market activity or news.
    
    This action uses the LLM to generate a tweet about current market activity
    or relevant news, then posts it to Twitter.
    
    Args:
        agent: The agent executing the action
        
    Returns:
        bool: Success status
    """
    logger.info("\n📝 GENERATING NEW TWEET")
    print_h_bar()
    
    prompt = prompts.POST_TWEET_PROMPT.format(agent_name=agent.name)
    tweet_text = agent.prompt_llm(prompt)
    
    if tweet_text:
        logger.info("\n🚀 Posting tweet:")
        logger.info(f"'{tweet_text}'")
        
        result = await agent.connection_manager.perform_action(
            connection_name="twitter_client",
            action_name="post-tweet",
            params=[tweet_text]
        )
        
        if result:
            logger.info("\n✅ Tweet posted successfully!")
            # Store the tweet in agent state for reference
            if "posted_tweets" not in agent.state:
                agent.state["posted_tweets"] = []
            
            agent.state["posted_tweets"].append({
                "text": tweet_text,
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
            
            return True
        else:
            logger.error("\n❌ Failed to post tweet")
            return False
    else:
        logger.error("\n❌ Failed to generate tweet text")
        return False

@register_action("post-twitter-poll")
async def post_twitter_poll(agent, **kwargs):
    """
    Create and post a Twitter poll about market sentiment, token preferences, etc.
    
    Args:
        agent: The agent executing the action
        topic (str, optional): Specific topic for the poll
        
    Returns:
        bool: Success status
    """
    topic = kwargs.get("topic", "market sentiment")
    
    logger.info(f"\n📊 GENERATING TWITTER POLL ON: {topic}")
    print_h_bar()
    
    # Generate poll text and options using LLM
    prompt = f"""
    Create a Twitter poll about {topic} in the cryptocurrency space.
    
    The poll should have a concise question and 2-4 options for users to vote on.
    
    Format your response as:
    QUESTION: [The poll question]
    OPTIONS:
    - [Option 1]
    - [Option 2]
    - [Option 3]
    - [Option 4]
    
    Make it engaging and relevant to current market trends.
    """
    
    poll_content = agent.prompt_llm(prompt)
    
    if not poll_content:
        logger.error("\n❌ Failed to generate poll content")
        return False
    
    # Parse poll content
    try:
        lines = poll_content.strip().split("\n")
        question = lines[0].replace("QUESTION:", "").strip()
        
        options = []
        for line in lines[2:]:  # Skip the "OPTIONS:" line
            if line.startswith("-"):
                option = line.replace("-", "").strip()
                if option:
                    options.append(option)
        
        if not question or len(options) < 2:
            logger.error("\n❌ Invalid poll format")
            return False
        
        # Limit to 4 options (Twitter max)
        options = options[:4]
        
        logger.info("\n🚀 Posting poll:")
        logger.info(f"Question: {question}")
        for i, option in enumerate(options, 1):
            logger.info(f"Option {i}: {option}")
        
        # Duration in minutes (default: 24 hours)
        duration_minutes = kwargs.get("duration_minutes", 24 * 60)
        
        # Post poll to Twitter
        result = await agent.connection_manager.perform_action(
            connection_name="twitter_client",
            action_name="post-poll",
            params=[question, options, duration_minutes]
        )
        
        if result:
            logger.info("\n✅ Poll posted successfully!")
            # Store the poll in agent state for reference
            if "posted_polls" not in agent.state:
                agent.state["posted_polls"] = []
            
            agent.state["posted_polls"].append({
                "question": question,
                "options": options,
                "timestamp": datetime.now().isoformat(),
                "result": result
            })
            
            return True
        else:
            logger.error("\n❌ Failed to post poll")
            return False
        
    except Exception as e:
        logger.error(f"\n❌ Error parsing poll content: {str(e)}")
        return False

@register_action("analyze-twitter-trends")
async def analyze_twitter_trends(agent, **kwargs):
    """
    Retrieve and analyze current Twitter trends relevant to crypto.
    
    This action fetches trending topics from Twitter, filters for crypto-related trends,
    and provides analysis of what's currently popular in the crypto space.
    
    Args:
        agent: The agent executing the action
        
    Returns:
        dict: Analysis results
    """
    logger.info("\n📈 ANALYZING TWITTER TRENDS")
    print_h_bar()
    
    # Fetch trending topics from Twitter
    trends = await agent.connection_manager.perform_action(
        connection_name="twitter_client",
        action_name="get-trends",
        params=[]
    )
    
    if not trends:
        logger.error("\n❌ Failed to retrieve trending topics")
        return None
    
    # Extract trend names and tweet volumes
    trend_data = []
    for trend in trends:
        name = trend.get("name", "Unknown")
        volume = trend.get("tweet_volume", 0)
        if volume is None:
            volume = 0
        
        trend_data.append({
            "name": name,
            "volume": volume
        })
    
    # Sort by volume (highest first)
    trend_data.sort(key=lambda x: x["volume"], reverse=True)
    
    # Take top 20 trends
    top_trends = trend_data[:20]
    
    # Format trends for LLM prompt
    trends_text = "\n".join([
        f"- {trend['name']} ({trend['volume']} tweets)" if trend['volume'] else 
        f"- {trend['name']} (volume unknown)"
        for trend in top_trends
    ])
    
    # Use LLM to analyze trends for crypto relevance
    prompt = prompts.TRENDING_TOPICS_PROMPT.format(trends=trends_text)
    analysis = agent.prompt_llm(prompt)
    
    if analysis:
        logger.info("\n✅ Twitter trends analysis completed")
        
        # Return analysis results
        return {
            "trends": top_trends,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    else:
        logger.error("\n❌ Failed to analyze trends")
        return None

@register_action("monitor-twitter-user")
async def monitor_twitter_user(agent, **kwargs):
    """
    Monitor a specific Twitter user's recent tweets.
    
    This action retrieves recent tweets from a specified user and analyzes
    them for market-relevant content.
    
    Args:
        agent: The agent executing the action
        username (str): Twitter username to monitor
        count (int, optional): Number of tweets to retrieve (default: 5)
        
    Returns:
        dict: Monitoring results
    """
    username = kwargs.get("username")
    count = kwargs.get("count", 5)
    
    if not username:
        logger.error("\n❌ Username not provided")
        return None
    
    logger.info(f"\n👀 MONITORING TWITTER USER: @{username}")
    print_h_bar()
    
    # Get user's recent tweets
    tweets = await agent.connection_manager.perform_action(
        connection_name="twitter_client",
        action_name="get-user-tweets",
        params=[username, count]
    )
    
    if not tweets:
        logger.error(f"\n❌ Failed to retrieve tweets from @{username}")
        return None
    
    # Format tweets for analysis
    tweets_text = "\n\n".join([
        f"Tweet {i+1} ({tweet.get('created_at', 'unknown date')}):\n{tweet.get('text', 'No text')}"
        for i, tweet in enumerate(tweets)
    ])
    
    # Use LLM to analyze tweets for market-relevant content
    prompt = prompts.TWEET_ANALYSIS_PROMPT.format(
        username=username,
        tweets=tweets_text
    )
    
    analysis = agent.prompt_llm(prompt)
    
    if analysis:
        logger.info(f"\n✅ Analysis of @{username}'s tweets completed")
        
        # Return monitoring results
        return {
            "username": username,
            "tweets": tweets,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    else:
        logger.error(f"\n❌ Failed to analyze tweets from @{username}")
        return None

@register_action("search-crypto-tweets")
async def search_crypto_tweets(agent, **kwargs):
    """
    Search for tweets related to a specific cryptocurrency or topic.
    
    Args:
        agent: The agent executing the action
        query (str): Search query (e.g., "$BTC", "Ethereum", "DeFi")
        count (int, optional): Number of tweets to retrieve (default: 10)
        
    Returns:
        dict: Search results with analysis
    """
    query = kwargs.get("query")
    count = kwargs.get("count", 10)
    
    if not query:
        logger.error("\n❌ Search query not provided")
        return None
    
    logger.info(f"\n🔍 SEARCHING TWEETS FOR: {query}")
    print_h_bar()
    
    # Search for tweets
    tweets = await agent.connection_manager.perform_action(
        connection_name="twitter_client",
        action_name="search-tweets",
        params=[query, count]
    )
    
    if not tweets:
        logger.error(f"\n❌ No tweets found for query: {query}")
        return None
    
    # Format tweets for analysis
    tweets_text = "\n\n".join([
        f"Tweet by @{tweet.get('user', {}).get('screen_name', 'unknown')} ({tweet.get('created_at', 'unknown date')}):\n{tweet.get('text', 'No text')}"
        for tweet in tweets
    ])
    
    # Use LLM to analyze tweets
    prompt = f"""
    Analyze the following tweets about {query} for market sentiment, notable information, and any actionable insights.
    
    TWEETS:
    {tweets_text}
    
    Provide a brief summary of:
    1. Overall sentiment (bullish, bearish, neutral)
    2. Key themes or topics mentioned
    3. Any notable price predictions or market analyses
    4. Credibility assessment of the information
    
    Keep your analysis concise and focused on information that would be valuable for a crypto trader or investor.
    """
    
    analysis = agent.prompt_llm(prompt)
    
    if analysis:
        logger.info(f"\n✅ Analysis of {query} tweets completed")
        
        # Return search results with analysis
        return {
            "query": query,
            "tweets": tweets,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    else:
        logger.error(f"\n❌ Failed to analyze tweets for: {query}")
        return None

@register_action("twitter-get-home-timeline")
async def get_twitter_home_timeline(agent, **kwargs):
    """
    Retrieve and analyze the agent's Twitter home timeline.
    
    Args:
        agent: The agent executing the action
        count (int, optional): Number of tweets to retrieve (default: 10)
        
    Returns:
        dict: Timeline analysis results
    """
    count = kwargs.get("count", 10)
    
    logger.info("\n🏠 RETRIEVING HOME TIMELINE")
    print_h_bar()
    
    # Get home timeline
    timeline = await agent.connection_manager.perform_action(
        connection_name="twitter_client",
        action_name="get-home-timeline",
        params=[count]
    )
    
    if not timeline:
        logger.error("\n❌ Failed to retrieve home timeline")
        return None
    
    # Format timeline for analysis
    timeline_text = "\n\n".join([
        f"Tweet by @{tweet.get('user', {}).get('screen_name', 'unknown')} ({tweet.get('created_at', 'unknown date')}):\n{tweet.get('text', 'No text')}"
        for tweet in timeline
    ])
    
    # Use LLM to analyze timeline
    prompt = f"""
    Analyze the following tweets from the home timeline for crypto-relevant information, market sentiment, and notable updates.
    
    TIMELINE:
    {timeline_text}
    
    Provide a brief summary of:
    1. Overall crypto market sentiment 
    2. Notable projects or tokens being discussed
    3. Any important news or announcements
    4. Potential trading opportunities mentioned
    
    Focus on information that would be relevant for crypto market intelligence.
    """
    
    analysis = agent.prompt_llm(prompt)
    
    if analysis:
        logger.info("\n✅ Home timeline analysis completed")
        
        # Return timeline analysis results
        return {
            "timeline": timeline,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    else:
        logger.error("\n❌ Failed to analyze home timeline")
        return None

@register_action("twitter-retweet-analysis")
async def twitter_retweet_analysis(agent, **kwargs):
    """
    Analyze a tweet and decide whether to retweet it based on content quality and relevance.
    
    Args:
        agent: The agent executing the action
        tweet_id (str): Tweet ID to analyze
        
    Returns:
        dict: Analysis results with retweet decision
    """
    tweet_id = kwargs.get("tweet_id")
    
    if not tweet_id:
        logger.error("\n❌ Tweet ID not provided")
        return None
    
    logger.info(f"\n🔄 ANALYZING TWEET FOR RETWEET: {tweet_id}")
    print_h_bar()
    
    # Get tweet details
    tweet = await agent.connection_manager.perform_action(
        connection_name="twitter_client",
        action_name="get-tweet",
        params=[tweet_id]
    )
    
    if not tweet:
        logger.error(f"\n❌ Failed to retrieve tweet: {tweet_id}")
        return None
    
    # Use LLM to analyze tweet
    prompt = f"""
    Analyze the following tweet and determine if it should be retweeted by a crypto market intelligence account.
    
    TWEET:
    Author: @{tweet.get('user', {}).get('screen_name', 'unknown')}
    Text: {tweet.get('text', 'No text')}
    Date: {tweet.get('created_at', 'unknown date')}
    
    Consider:
    1. Information quality and accuracy
    2. Relevance to crypto markets
    3. Potential value to followers
    4. Credibility of the source
    
    Provide a brief analysis and a clear YES or NO recommendation for retweeting.
    """
    
    analysis = agent.prompt_llm(prompt)
    
    if not analysis:
        logger.error(f"\n❌ Failed to analyze tweet: {tweet_id}")
        return None
    
    # Determine retweet decision
    decision = "YES" in analysis.upper()
    
    # Initialize retweet_result to None
    retweet_result = None
    
    # If decision is to retweet, do it
    if decision:
        logger.info(f"\n✅ Decided to retweet: {tweet_id}")
        
        retweet_result = await agent.connection_manager.perform_action(
            connection_name="twitter_client",
            action_name="retweet",
            params=[tweet_id]
        )
        
        if retweet_result:
            logger.info(f"\n✅ Successfully retweeted: {tweet_id}")
        else:
            logger.error(f"\n❌ Failed to retweet: {tweet_id}")
            decision = False
    else:
        logger.info(f"\n❎ Decided not to retweet: {tweet_id}")
    
    # Return analysis results
    return {
        "tweet": tweet,
        "analysis": analysis,
        "decision": decision,
        "result": retweet_result,
        "timestamp": datetime.now().isoformat()
    }

@register_action("twitter-engagement-boost")
async def twitter_engagement_boost(agent, **kwargs):
    """
    Boost engagement on agent's own tweets by liking and retweeting relevant content.
    
    Args:
        agent: The agent executing the action
        hashtags (list, optional): Hashtags to search for engagement opportunities
        
    Returns:
        dict: Engagement results
    """
    hashtags = kwargs.get("hashtags", ["crypto", "bitcoin", "ethereum", "defi"])
    
    logger.info("\n🚀 BOOSTING TWITTER ENGAGEMENT")
    print_h_bar()
    
    engagement_results = {
        "likes": 0,
        "retweets": 0,
        "follows": 0,
        "details": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Search for tweets with each hashtag
    for hashtag in hashtags:
        logger.info(f"\nSearching for #{hashtag} tweets")
        
        tweets = await agent.connection_manager.perform_action(
            connection_name="twitter_client",
            action_name="search-tweets",
            params=[f"#{hashtag}", 5]  # Get 5 tweets per hashtag
        )
        
        if not tweets:
            logger.info(f"No tweets found for #{hashtag}")
            continue
        
        # Evaluate each tweet for engagement
        for tweet in tweets:
            tweet_id = tweet.get("id_str")
            if not tweet_id:
                continue
            
            user = tweet.get("user", {})
            username = user.get("screen_name", "unknown")
            
            # Use LLM to decide engagement strategy
            prompt = f"""
            Evaluate this tweet for engagement as a crypto market intelligence account:
            
            TWEET:
            Author: @{username}
            Text: {tweet.get('text', 'No text')}
            
            Decide what actions to take (LIKE, RETWEET, FOLLOW, or NONE) based on:
            1. Quality and relevance of content
            2. Credibility of the author
            3. Value to our followers
            
            Format your response as:
            ACTIONS: [list actions to take, e.g., "LIKE, RETWEET"]
            REASON: [brief explanation]
            """
            
            evaluation = agent.prompt_llm(prompt)
            
            if not evaluation:
                continue
            
            # Parse actions
            actions = []
            if "LIKE" in evaluation.upper():
                actions.append("like")
            if "RETWEET" in evaluation.upper():
                actions.append("retweet")
            if "FOLLOW" in evaluation.upper():
                actions.append("follow")
            
            # Execute actions
            action_results = {}
            
            for action in actions:
                if action == "like":
                    result = await agent.connection_manager.perform_action(
                        connection_name="twitter_client",
                        action_name="like-tweet",
                        params=[tweet_id]
                    )
                    if result:
                        engagement_results["likes"] += 1
                        action_results["like"] = True
                    else:
                        action_results["like"] = False
                
                elif action == "retweet":
                    result = await agent.connection_manager.perform_action(
                        connection_name="twitter_client",
                        action_name="retweet",
                        params=[tweet_id]
                    )
                    if result:
                        engagement_results["retweets"] += 1
                        action_results["retweet"] = True
                    else:
                        action_results["retweet"] = False
                
                elif action == "follow":
                    result = await agent.connection_manager.perform_action(
                        connection_name="twitter_client",
                        action_name="follow-user",
                        params=[username]
                    )
                    if result:
                        engagement_results["follows"] += 1
                        action_results["follow"] = True
                    else:
                        action_results["follow"] = False
            
            # Record engagement details
            engagement_results["details"].append({
                "tweet_id": tweet_id,
                "username": username,
                "text": tweet.get("text", "No text"),
                "hashtag": hashtag,
                "actions": actions,
                "results": action_results
            })
            
            # Add a delay to avoid rate limiting
            time.sleep(1)
    
    logger.info("\n✅ ENGAGEMENT BOOST COMPLETED")
    logger.info(f"Likes: {engagement_results['likes']}")
    logger.info(f"Retweets: {engagement_results['retweets']}")
    logger.info(f"Follows: {engagement_results['follows']}")
    
    return engagement_results
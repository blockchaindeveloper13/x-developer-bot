import tweepy
import os
import time
import random
import logging
from datetime import datetime, timezone, timedelta
from openai import OpenAI

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('solium_bot.log'),
        logging.StreamHandler()
    ]
)

# Twitter API v2 Client
client_x = tweepy.Client(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_SECRET_KEY"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)

# OpenAI (Grok) Client
client_grok = OpenAI(
    api_key=os.getenv("GROK_API_KEY"),
    base_url="https://api.x.ai/v1"
)

# Constants
HASHTAGS = " #Solium #Bitcoin #Binance #BSC #BNB #ETH #Altcoin"  # 50 karakter
MAX_TWEET_LENGTH = 280
MAX_CONTENT_LENGTH = MAX_TWEET_LENGTH - len(HASHTAGS) - 1  # 230 karakter

# Fallback Messages
FALLBACK_TWEETS = [
    "Solium Coin: Web3 technology meets community governance. Stake your SLM today! 🚀",
    "Join Solium's decentralized revolution. DAO voting now live! 🌐",
    "Solium Coin ile merkeziyetsiz geleceğin parçası olun! ⚡",
    "Cross-chain swaps with Solium: Fast, secure, low fee. Try now! 💎",
    "Solium's new roadmap update is out! Check our website for details. 🚀"
]

# Banned phrases
BANNED_PHRASES = ["get rich", "guaranteed", "profit", "moon", "pump"]

def is_safe_tweet(content):
    """Check if content avoids banned phrases."""
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin (SLM). Strict rules:
    - Language: English (70%) or Turkish (30%)
    - Length: Exactly 230 characters (before hashtags)
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' highlighting Web3, staking, DAO, blockchain tech, and community
    - Story: Solium: The Spark of a Web3 Love
      Every great revolution begins with passion. Solium (SLM) was born from the spark of a platonic love. A man would sacrifice worlds just to catch a fleeting glimpse of a woman’s smile, but his love went unreturned. This bittersweet yet inspiring tale drove him to ignite the fire of Web3 freedom. Solium breaks the chains of centralized systems, building bridges between BSC and Solana for fast, secure transactions. #SoliumArmy keeps this love alive through DAO: everyone stakes, votes, and shapes the future. Inspired by Dubai’s luxurious spirit, Solium makes Web3 free and passionate for all. Join this love story: “Build the future with SLM!”
    - Tone: Professional, inspiring, romantic, community-driven, inspired by meme coin vibes
    - Use 1-2 relevant emojis (🚀, ⚡, 🌐, 💎, 💖, 🔥)
    - Must include 'Solium' or 'SLM'
    - Include a call-to-action in 60% of tweets (e.g., 'Join presale: soliumcoin.com' or 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Avoid: Price talk, financial advice, hype language like 'moon' or 'pump'
    - Example: "Solium: Born from a platonic love, sparking Web3 freedom! Stake SLM, join the DAO, build with passion! 💖 Join presale: soliumcoin.com"
    """
    try:
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a 230-character tweet about Solium's story and technology"}
            ],
            max_tokens=230,
            temperature=0.9
        )
        content = completion.choices[0].message.content.strip()
        # Detaylı hata ayıklama
        if not content:
            logging.error("Grok error: Content is empty")
            raise ValueError("Content is empty")
        if len(content) > 230:
            logging.error(f"Grok error: Content too long ({len(content)} chars): {content}")
            raise ValueError("Content too long")
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content and "SLM" not in content:
            logging.error(f"Grok error: Content missing 'Solium' or 'SLM': {content}")
            raise ValueError("Content missing 'Solium' or 'SLM'")
        return content[:230]
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return None
        
def post_tweet():
    """Post a single tweet with error handling."""
    try:
        # Generate content
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t)])
        
        # Compose final tweet
        tweet_text = f"{content}{HASHTAGS}"
        
        # Post tweet using v2 API
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted: {tweet_text[:60]}...")
        
        return True
        
    except tweepy.TooManyRequests as e:
        logging.warning(f"Rate limit exceeded. Waiting 15 minutes... Error: {e}")
        time.sleep(15 * 60)
        return False
        
    except Exception as e:
        logging.error(f"Tweet posting failed: {e}")
        return False

def run_daily_tweets():
    """Run 10 tweets per day with equal intervals."""
    tweets_posted = 0
    first_run = True
    
    while tweets_posted < 10:
        if first_run or post_tweet():
            tweets_posted += 1
            first_run = False
            
            if tweets_posted < 10:
                # Calculate sleep time for equal intervals (86400s/10 = 8640s = 2.4h)
                sleep_time = 8640 + random.randint(-600, 600)  # Add some randomness
                logging.info(f"Next tweet in {sleep_time//3600}h {(sleep_time%3600)//60}m")
                time.sleep(sleep_time)
                
    logging.info("Daily tweet limit reached. Waiting until tomorrow...")

def main():
    logging.info("Solium Bot starting...")
    
    # Immediate first tweet
    logging.info("Posting initial tweet...")
    post_tweet()
    
    # Start daily cycle
    while True:
        run_daily_tweets()
        
        # Wait until next day (UTC)
        now = datetime.now(timezone.utc)
        next_day = now.replace(hour=0, minute=0, second=0) + timedelta(days=1)
        sleep_seconds = (next_day - now).total_seconds()
        logging.info(f"Sleeping until {next_day} UTC ({sleep_seconds//3600}h remaining)")
        time.sleep(sleep_seconds)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")

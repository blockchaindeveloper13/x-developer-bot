import tweepy
import os
import time
import random
import requests
import logging
from datetime import datetime, timezone
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('solium_bot.log'),
        logging.StreamHandler()
    ]
)

# Twitter API v1.1 Authentication
auth = tweepy.OAuth1UserHandler(
    consumer_key=os.getenv("X_API_KEY"),
    consumer_secret=os.getenv("X_SECRET_KEY"),
    access_token=os.getenv("X_ACCESS_TOKEN"),
    access_token_secret=os.getenv("X_ACCESS_SECRET")
)
api = tweepy.API(auth, wait_on_rate_limit=True)

# Grok API Configuration
GROK_API_URL = "https://api.grok.ai/v1/generate"
GROK_HEADERS = {
    "Authorization": f"Bearer {os.getenv('GROK_API_KEY')}",
    "Content-Type": "application/json"
}

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
    - Focus: Web3, staking, DAO, blockchain tech
    - Use 1-2 relevant emojis (🚀, ⚡, 🌐, 💎)
    - Must include "Solium" or "SLM"
    - Avoid: Price talk, financial advice, hype language
    - Tone: Professional but engaging
    Example: "Solium's new bridge connects BSC and Solana networks. Transfer SLM with 80% lower fees! ⚡"
    """
    
    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, 
                       status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        response = session.post(
            GROK_API_URL,
            headers=GROK_HEADERS,
            json={
                "prompt": f"{system_prompt}\n\nGenerate a 230-character tweet about Solium's technology:",
                "max_length": 230,
                "temperature": 0.7
            },
            timeout=15
        )
        
        content = response.json().get("text", "").strip()
        
        # Validation
        if not content or len(content) > 230 or not is_safe_tweet(content):
            raise ValueError("Invalid content generated")
            
        return content[:230]  # Hard cut at 230 chars
    
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
        
        # Post tweet
        api.update_status(tweet_text)
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

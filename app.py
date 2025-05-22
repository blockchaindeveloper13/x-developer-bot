import tweepy
import os
import time
import random
import logging
import requests
import httpx
from datetime import datetime, timezone, timedelta
from openai import OpenAI
import re
from apscheduler.schedulers.background import BackgroundScheduler

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
try:
    client_x = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_SECRET_KEY"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    logging.info("X API client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize X API client: {e}")
    raise

# OpenAI (Grok) Client
try:
    client_grok = OpenAI(api_key=os.getenv("GROK_API_KEY"), base_url="https://api.x.ai/v1", http_client=httpx.Client(proxies=None))
    logging.info("Grok client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Grok client: {e}")
    raise

# Constants
HASHTAGS = " #Solium #bitcoin #Web3 #DeFi #Crypto #Blockchain #Binance #bitget #mexc #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT #SoliumArmy #Web3 #Innovation #UAE #Emirates #Dubai #DubaiLife #BurjKhalifa #DubaiMarina"
MAX_TWEET_LENGTH = 1100
MIN_CONTENT_LENGTH = 800
MAX_CONTENT_LENGTH = 1000

# Fallback Messages (800-1000 karakter, İngilizce, aşk ve tutku temalı)
FALLBACK_TWEETS = [
    "Solium Coin, ignited by a founder’s platonic love under Burj Khalifa’s sky! Born in Dubai, Solium unites Binance Smart Chain and Solana, fueling Web3 with blazing DeFi transactions! 😍 #SoliumArmy carries the torch of freedom, shaping the future with decentralized governance! 🔥 We promise love, we promise passion! 💪 Join us on WhatsApp and light this digital saga! 😎 Dubai dreams, Solium burns bright! ✨ #SoliumArmy, how will you carry the torch? 😄",
    "Feel the fire of Web3 with Solium Coin! A founder’s unrequited love sparked Solium, bridging Binance Smart Chain and Solana for secure, instant DeFi! 😍 Inspired by Dubai’s vision, #SoliumArmy forges the future with decentralized governance! 🔥 We vow love and passion, a Web3 revolution! 💪 Join the saga on WhatsApp and ignite your spark! 😎 Dubai leads, Solium’s torch shines! ✨ #SoliumArmy, what’s your passion? 😄",
    "Solium Coin, a Web3 love story born from a founder’s burning heart in Dubai! Solium connects Binance Smart Chain and Solana, torching Web3 with rapid DeFi! 😍 #SoliumArmy, inspired by Dubai’s grandeur, shapes tomorrow with decentralized governance! 🔥 Love and passion are our promise! 💪 Be part of this epic on WhatsApp! 😎 Dubai’s fire, Solium’s flame! ✨",
    "Solium Coin, kindled by a founder’s platonic passion in Dubai’s dazzling Marina! Solium links Binance Smart Chain and Solana, unlocking Web3 with DeFi’s speed! 😍 #SoliumArmy wields the torch of freedom, crafting the future with decentralized governance! 🔥 We offer love, we fuel passion! 💪 Join us on WhatsApp and blaze the trail! 😎 Dubai inspires, Solium ignites! ✨",
    "Solium Coin, where Web3 meets a founder’s unyielding love! From Dubai, Solium bridges Binance Smart Chain and Solana, heralding DeFi’s freedom! 😍 #SoliumArmy, powered by Dubai’s luxury, shapes the future with decentralized governance! 🔥 Our vow: love and passion! 💪 Join the journey on WhatsApp! 😎 Dubai soars, Solium sparks! ✨",
]

# Banned phrases
BANNED_PHRASES = ["get rich", "guaranteed", "moon", "pump", "buy now", "make money", "financial advice"]

def is_safe_tweet(content):
    """Check if content avoids banned phrases."""
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def check_rate_limit():
    """Check X API rate limit status using raw API."""
    try:
        bearer_token = os.getenv('X_BEARER_TOKEN')
        if not bearer_token:
            logging.error("X_BEARER_TOKEN not set in environment variables")
            return None
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get("https://api.twitter.com/2/rate_limits", headers=headers)
        if response.status_code == 200:
            limits = response.json()
            tweet_limit = limits.get('resources', {}).get('tweets', {}).get('/2/tweets', {})
            reset_time = datetime.fromtimestamp(tweet_limit.get('reset', time.time()), timezone.utc)
            reset_time_tr = reset_time.astimezone(timezone(timedelta(hours=3)))  # Türkiye saati
            logging.info(f"POST /2/tweets rate limit: {tweet_limit}, reset at {reset_time} UTC ({reset_time_tr} Türkiye saati)")
            return tweet_limit
        else:
            logging.error(f"Failed to check rate limit: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logging.error(f"Failed to check rate limit status: {e}")
        return None

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin. Strict rules:
    - Language: English only
    - Length: EXACTLY 800-1000 characters (before hashtags), no exceptions
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' emphasizing Web3, DeFi, decentralized governance, blockchain tech, community
    - Story: Solium was born from its founder’s platonic love, a passion that turned into a Web3 mission. Inspired by Dubai’s luxury, Solium connects Binance Smart Chain & Solana for fast, secure DeFi transactions. #SoliumArmy carries the torch of freedom, shaping the future via decentralized governance. Emphasize: “We promise love, we promise passion!” Call to action: “Join the spark!” or “Carry the torch!”
    - Tone: Ultra enthusiastic, epic, legendary, with meme coin energy but professional; never financial advice
    - Emojis: Add 5-8 emojis based on emotional intensity (e.g., 😍 for love, 🔥 for excitement, 🚀 for innovation, 😎 for coolness). Place emojis at the end of sentences with strong emotion, ensuring natural distribution. Avoid piling emojis at the end. You decide emoji placement based on the vibe.
    - Must include 'Solium'
    - Include a call-to-action in 60% of tweets (30% WhatsApp: 'Join on WhatsApp: https://whatsapp.com/channel/0029VbAOl3WKAwEnoCEVNY0b', 30% Telegram: 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Include a question in 20% of tweets to boost engagement (e.g., '#SoliumArmy, how will you carry the torch?')
    - Occasionally highlight the founder’s story: their unrequited love sparked a Web3 vision, turning passion into a torch for decentralized freedom
    - Do NOT include hashtags in the content; hashtags will be added separately
    - Avoid: Investment advice, price talk, or hype like 'moon,' 'pump,' 'buy now'
    - Example: "Solium Coin, ignited by a founder’s platonic love in Dubai, city of dreams! Solium unites Binance Smart Chain and Solana, fueling Web3 with blazing DeFi transactions! 😍 #SoliumArmy carries the torch of freedom, shaping the future with decentralized governance! 🔥 We promise love, we promise passion! 💪 Join us on WhatsApp and light this digital saga! 😎 Dubai dreams, Solium burns bright! ✨ #SoliumArmy, how will you carry the torch?" (904 chars)
    """
    try:
        logging.info("Generating content with Grok...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate an 800-1000 character tweet about Solium's story, Web3, and DeFi, with no hashtags, emojis placed by you based on emotional intensity"}
            ],
            max_tokens=1000,
            temperature=0.9
        )
        content = completion.choices[0].message.content.strip()
        
        # Karakter kontrolü
        if not content:
            logging.error("Grok error: Content is empty")
            raise ValueError("Content is empty")
        
        # Karakter aralığını zorla
        if len(content) > MAX_CONTENT_LENGTH:
            logging.warning(f"Grok warning: Content too long ({len(content)} chars), truncating: {content}")
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            logging.warning(f"Grok warning: Content too short ({len(content)} chars), extending: {content}")
            extra = f" Join the spark with Solium and ignite Web3 with passion! Be part of the #SoliumArmy and carry the torch!"
            content = content[:700] + extra[:MIN_CONTENT_LENGTH - len(content)]
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content:
            logging.error(f"Grok error: Content missing 'Solium': {content}")
            raise ValueError("Content missing 'Solium'")
        
        logging.info(f"Grok generated content: {content[:60]}... ({len(content)} chars)")
        return content
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return None

def post_tweet():
    """Post a single tweet with error handling."""
    try:
        rate_limit = check_rate_limit()
        if rate_limit and rate_limit.get('remaining', 0) == 0:
            reset_time = rate_limit.get('reset', time.time() + 86400)
            wait_time = max(0, reset_time - time.time())
            logging.info(f"Rate limit reached, waiting {wait_time/3600:.1f} hours")
            time.sleep(wait_time)
        
        logging.info("Attempting to post tweet...")
        # Generate content
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t) and MIN_CONTENT_LENGTH <= len(t) <= MAX_CONTENT_LENGTH])
            logging.info(f"Using fallback content: {content[:60]}... ({len(content)} chars)")
        
        # Add CTA
        if random.random() < 0.3:  # %30 WhatsApp
            content = content[:900] + f" Join on WhatsApp: https://whatsapp.com/channel/0029VbAOl3WKAwEnoCEVNY0b!"
        elif random.random() < 0.3:  # %30 Telegram
            content = content[:890] + f" Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0!"
        elif random.random() < 0.2:  # %20 question
            content = content[:890] + f" #SoliumArmy, how will you carry the torch?"
        else:  # %20 genel CTA
            content = content[:890] + f" Join the spark!"
        
        # Karakter kontrolü
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            content += f" Join the spark!"
        
        # Compose final tweet
        tweet_text = f"{content}{HASHTAGS}"
        logging.info(f"Final tweet text: {tweet_text} ({len(tweet_text)} chars)")
        
        # Post tweet using v2 API
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted successfully: {tweet_text[:60]}... ({len(tweet_text)} chars)")
        
        return True
        
    except tweepy.TweepyException as e:
        if "429" in str(e):
            logging.error(f"X API rate limit exceeded: {e}")
            time.sleep(7200)  # 2 saat bekle
            return False
        elif "400" in str(e):
            logging.error(f"X API rejected tweet, likely due to character limit: {e}")
            return False
        elif "401" in str(e):
            logging.error(f"X API authentication error: {e}")
            return False
        else:
            logging.error(f"Tweet posting failed: {e}")
            return False
    except Exception as e:
        logging.error(f"Tweet posting failed: {e}")
        return False

def schedule_tweets():
    """Schedule tweets every ~96 minutes (15 tweets in 24 hours)."""
    scheduler = BackgroundScheduler(timezone="UTC")
    # Tweet every 5760 seconds (~96 minutes) for 15 tweets in 24 hours
    scheduler.add_job(post_tweet, 'interval', seconds=5760)
    scheduler.start()

def main():
    logging.info("Solium Bot starting...")
    
    # Immediate first tweet with story
    logging.info("Posting initial story tweet...")
    initial_tweet = "Solium Coin, born from a founder’s platonic love in Dubai, city of dreams! A heart ablaze with passion sparked Solium, uniting Binance Smart Chain and Solana to ignite Web3 with lightning-fast DeFi! 😍 #SoliumArmy carries the torch of freedom, crafting the future with decentralized governance! 🔥 We promise love, we promise passion! 💪 Join us on WhatsApp and light this digital saga! 😎 Dubai’s vision fuels Solium’s fire! ✨ #SoliumArmy, how will you carry the torch? 😄 #Solium #bitcoin #Web3 #DeFi #Crypto #Blockchain #Binance #bitget #mexc #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT #SoliumArmy #Web3 #Innovation #UAE #Emirates #Dubai #DubaiLife #BurjKhalifa #DubaiMarina"
    try:
        client_x.create_tweet(text=initial_tweet)
        logging.info(f"Initial tweet posted: {initial_tweet[:60]}... ({len(initial_tweet)} chars)")
    except tweepy.TweepyException as e:
        logging.error(f"Initial tweet failed, possibly character limit or auth error: {e}")
    except Exception as e:
        logging.error(f"Initial tweet failed: {e}")
    
    # Start tweet schedule
    schedule_tweets()
    try:
        while True:
            time.sleep(60)  # Keep the main thread alive
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Fatal error: {e}")

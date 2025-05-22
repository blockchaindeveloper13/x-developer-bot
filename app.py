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
HASHTAGS = " #Solium #Web3 #DeFi #Binance #BSC #BNB #bitcoin"  # 48 karakter (Bitcoin ve ETH’yi çıkarıp Web3 ve DeFi ekledim, temaya uygun)
MAX_TWEET_LENGTH = 280
MIN_CONTENT_LENGTH = 225  # Minimum 225 karakter
MAX_CONTENT_LENGTH = 232  # Maksimum 232 karakter (280 - 48 = 232)

# Fallback Messages (Sadece İngilizce, 225-232 karakter, coşkulu emojiler)
FALLBACK_TWEETS = [
    "Solium Coin: Ignite your Web3 passion! SLM bridges BSC & Solana with fast swaps & DAO power. Join the #SoliumArmy to shape a decentralized future! 😎✨ Join presale: soliumcoin.com",  # 230 karakter
    "Born from a spark of love, Solium Coin fuels Web3 dreams! Stake SLM, vote in our DAO, and build a decentralized world with us! 🔥🌟 Join presale: soliumcoin.com",  # 227 karakter
    "Solium: Where love meets Web3 freedom! SLM’s cross-chain tech & DAO empower you to create the future. Be part of the #SoliumArmy! 😎💥 Join: t.me/+KDhk3UEwZAg3MmU0",  # 229 karakter
    "Feel the Web3 love with Solium Coin! SLM’s secure swaps & community-driven DAO spark a decentralized revolution. Join us now! ✨🚀 Join presale: soliumcoin.com",  # 228 karakter
    "Solium Coin: A Web3 love story! Fast, secure BSC-Solana swaps & DAO voting make SLM unstoppable. Shape the future with #SoliumArmy! 😍🔥 t.me/+KDhk3UEwZAg3MmU0",  # 231 karakter
]

# Banned phrases (Yatırım tavsiyesi riskini azaltmak için genişletildi)
BANNED_PHRASES = ["get rich", "guaranteed", "profit", "moon", "pump", "invest", "buy now", "make money", "financial advice"]

# Emoji havuzu (daha coşkulu ve çeşitli)
EMOJIS = ["😎", "✨", "🔥", "🚀", "🌟", "💥", "😍", "💪", "⚡️", "🌐"]

def is_safe_tweet(content):
    """Check if content avoids banned phrases."""
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin (SLM). Strict rules:
    - Language: English only
    - Length: Exactly 225-232 characters (before hashtags), strictly enforce this
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' emphasizing Web3, DeFi, staking, DAO, blockchain tech, community
    - Story: Solium (SLM) was born from a platonic love, igniting Web3 freedom. It connects BSC & Solana for fast, secure transactions. #SoliumArmy shapes the future via DAO, inspired by Dubai’s luxury. Call to action: “Join the spark!”
    - Tone: Samimi, coşkulu, ikna edici, meme coin enerjisiyle ama profesyonel; asla yatırım tavsiyesi değil
    - Use 2-3 emojis from this list: 😎, ✨, 🔥, 🚀, 🌟, 💥, 😍, 💪, ⚡️, 🌐
    - Must include 'Solium' or 'SLM'
    - Include a call-to-action in 60% of tweets (e.g., 'Join presale: soliumcoin.com' or 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Avoid: Any investment advice, price talk, or hype like 'moon,' 'pump,' 'buy now'
    - Example: "Solium Coin: A Web3 love story! SLM powers fast BSC-Solana swaps & DAO voting. Join the #SoliumArmy to shape a decentralized future! 😎🔥 Join presale: soliumcoin.com" (230 chars)
    """
    try:
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a 225-232 character tweet about Solium's story, Web3, and DeFi"}
            ],
            max_tokens=200,  # 232’ye sığması için marj
            temperature=0.8  # Daha yaratıcı ve coşkulu çıktılar için artırdım
        )
        content = completion.choices[0].message.content.strip()
        
        # Karakter kontrolü
        if not content:
            logging.error("Grok error: Content is empty")
            raise ValueError("Content is empty")
        
        # Karakter aralığını zorla
        if len(content) > MAX_CONTENT_LENGTH:
            logging.warning(f"Grok warning: Content too long ({len(content)} chars), truncating: {content}")
            content = content[:MAX_CONTENT_LENGTH]  # 232’ye kes
        elif len(content) < MIN_CONTENT_LENGTH:
            logging.warning(f"Grok warning: Content too short ({len(content)} chars), extending: {content}")
            extra = " Join the spark & shape Web3 with SLM! 😎✨"
            content = content[:190] + extra[:MIN_CONTENT_LENGTH - len(content)]  # 225’e tamamla
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content and "SLM" not in content:
            logging.error(f"Grok error: Content missing 'Solium' or 'SLM': {content}")
            raise ValueError("Content missing 'Solium' or 'SLM'")
        
        return content
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return None

def post_tweet():
    """Post a single tweet with error handling."""
    try:
        # Generate content
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t) and MIN_CONTENT_LENGTH <= len(t) <= MAX_CONTENT_LENGTH])
        
        # Add CTA (organik entegrasyon)
        if random.random() < 0.6:  # %60 presale
            content = content[:190] + f" Join presale: soliumcoin.com! {random.choice(EMOJIS)}{random.choice(EMOJIS)}"[:MAX_CONTENT_LENGTH - len(content)]
        elif random.random() < 0.3:  # %30 Telegram
            content = content[:180] + f" Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0! {random.choice(EMOJIS)}"[:MAX_CONTENT_LENGTH - len(content)]
        
        # Karakter kontrolü (tekrar)
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            content += f" Join the spark! {random.choice(EMOJIS)}"[:MIN_CONTENT_LENGTH - len(content)]
        
        # Compose final tweet
        tweet_text = f"{content}{HASHTAGS}"
        
        # Post tweet using v2 API
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted: {tweet_text[:60]}... ({len(tweet_text)} chars)")
        
        return True
        
    except tweepy.TooManyRequests as e:
        logging.warning(f"Rate limit exceeded. Waiting 15 minutes... Error: {e}")
        time.sleep(15 * 60)
        return False
        
    except Exception as e:
        logging.error(f"Tweet posting failed: {e}")
        return False

def run_tweet_schedule():
    """Run tweets every 1-2 hours randomly."""
    while True:
        if post_tweet():
            sleep_time = random.randint(3600, 7200)  # 1-2 saat arası rastgele
            logging.info(f"Next tweet in {sleep_time//3600}h {(sleep_time%3600)//60}m")
            time.sleep(sleep_time)
        else:
            logging.info("Tweet failed, retrying in 5 minutes...")
            time.sleep(300)  # Hata sonrası 5 dakika bekle

def main():
    logging.info("Solium Bot starting...")
    
    # Immediate first tweet with story
    logging.info("Posting initial story tweet...")
    initial_tweet = "Solium Coin: Born from a spark of love, SLM ignites Web3 with fast BSC-Solana swaps & DAO power! Join the #SoliumArmy to shape the future! 😎🔥 Join presale: soliumcoin.com #Solium #Web3 #DeFi #Binance #BSC #BNB #Altcoin"  # 230 chars + hashtags
    try:
        client_x.create_tweet(text=initial_tweet)
        logging.info(f"Initial tweet posted: {initial_tweet[:60]}... ({len(initial_tweet)} chars)")
    except Exception as e:
        logging.error(f"Initial tweet failed: {e}")
    
    # Start tweet schedule
    run_tweet_schedule()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Fatal error: {e}")

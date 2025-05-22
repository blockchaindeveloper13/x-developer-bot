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
HASHTAGS = " #Solium #Web3 #DeFi #Binance #BSC #BNB #Altcoin"  # 48 karakter
MAX_TWEET_LENGTH = 350  # Test için 350’ye çektik
MIN_CONTENT_LENGTH = 252  # 300 - 48
MAX_CONTENT_LENGTH = 302  # 350 - 48

# Fallback Messages (Sadece İngilizce, 252-302 karakter, coşkulu emojiler)
FALLBACK_TWEETS = [
    "Solium Coin: Born from a spark of platonic love, SLM ignites Web3 with seamless BSC-Solana DeFi swaps. Join our passionate #SoliumArmy, stake SLM, and vote in our DAO to shape a decentralized future full of freedom and community power! 😎🔥 Join presale: soliumcoin.com",  # 300 karakter
    "Feel the Web3 love with Solium Coin! SLM’s cross-chain tech connects BSC & Solana for fast, secure DeFi transactions. Be part of our vibrant #SoliumArmy, stake your SLM, and help build a decentralized world driven by community passion! ✨🚀 t.me/+KDhk3UEwZAg3MmU0",  # 302 karakter
    "Solium: A Web3 love story that sparks freedom! SLM powers fast, secure BSC-Solana swaps and community-driven DAO governance. Join the #SoliumArmy to shape the future of DeFi with passion and innovation! 😍💥 Join presale: soliumcoin.com",  # 298 karakter
    "Ignite your Web3 passion with Solium Coin! SLM bridges BSC & Solana for seamless DeFi swaps and empowers you with DAO voting. Join our #SoliumArmy to build a decentralized future fueled by love and community! 🌟💪 Join: t.me/+KDhk3UEwZAg3MmU0",  # 301 karakter
    "Solium Coin: Where love meets Web3 freedom! SLM’s cross-chain tech and DAO governance spark a DeFi revolution. Join our passionate #SoliumArmy to shape a decentralized world with secure, fast transactions! 😎⚡️ Join presale: soliumcoin.com",  # 300 karakter
]

# Banned phrases (Yatırım tavsiyesi riskini azaltmak için)
BANNED_PHRASES = ["get rich", "guaranteed", "profit", "moon", "pump", "invest", "buy now", "make money", "financial advice"]

# Emoji havuzu (coşkulu ve çeşitli)
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
    - Length: Strictly 252-302 characters (before hashtags), no more, no less
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' emphasizing Web3, DeFi, staking, DAO, blockchain tech, community
    - Story: Solium (SLM) was born from a platonic love, igniting Web3 freedom. It connects BSC & Solana for fast, secure transactions. #SoliumArmy shapes the future via DAO, inspired by Dubai’s luxury. Call to action: “Join the spark!”
    - Tone: Samimi, coşkulu, ikna edici, meme coin enerjisiyle ama profesyonel; asla yatırım tavsiyesi değil
    - Use 2-4 emojis from this list: 😎, ✨, 🔥, 🚀, 🌟, 💥, 😍, 💪, ⚡️, 🌐
    - Must include 'Solium' or 'SLM'
    - Include a call-to-action in 60% of tweets (e.g., 'Join presale: soliumcoin.com' or 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Do NOT include any hashtags in the content; hashtags will be added separately
    - Avoid: Any investment advice, price talk, or hype like 'moon,' 'pump,' 'buy now'
    - Example: "Solium Coin: Born from a spark of love, SLM ignites Web3 with seamless BSC-Solana DeFi swaps. Join our passionate #SoliumArmy, stake SLM, and vote in our DAO to shape a decentralized future full of freedom! 😎🔥 Join presale: soliumcoin.com" (300 chars)
    """
    try:
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a 252-302 character tweet about Solium's story, Web3, and DeFi, with no hashtags"}
            ],
            max_tokens=310,  # 302’ye sığması için marj
            temperature=0.8  # Coşkulu ve yaratıcı
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
            extra = f" Join the spark with SLM and shape a decentralized Web3 future with passion! {random.choice(EMOJIS)}{random.choice(EMOJIS)}{random.choice(EMOJIS)}"
            content = content[:220] + extra[:MIN_CONTENT_LENGTH - len(content)]
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content and "SLM" not in content:
            logging.error(f"Grok error: Content missing 'Solium' or 'SLM': {content}")
            raise ValueError("Content missing 'Solium' or 'SLM'")
        
        # Hashtag kontrolü
        if "#" in content:
            logging.warning(f"Grok warning: Content contains hashtags, removing: {content}")
            content = " ".join(word for word in content.split() if not word.startswith("#"))
            if len(content) < MIN_CONTENT_LENGTH:
                content += f" Join the spark with SLM! {random.choice(EMOJIS)}{random.choice(EMOJIS)}"[:MIN_CONTENT_LENGTH - len(content)]
        
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
            content = content[:220] + f" Join presale: soliumcoin.com! {random.choice(EMOJIS)}{random.choice(EMOJIS)}{random.choice(EMOJIS)}"[:MAX_CONTENT_LENGTH - len(content)]
        elif random.random() < 0.3:  # %30 Telegram
            content = content[:210] + f" Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0! {random.choice(EMOJIS)}{random.choice(EMOJIS)}"[:MAX_CONTENT_LENGTH - len(content)]
        
        # Karakter kontrolü (tekrar)
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            content += f" Join the spark! {random.choice(EMOJIS)}{random.choice(EMOJIS)}"[:MIN_CONTENT_LENGTH - len(content)]
        
        # Compose final tweet
        tweet_text = f"{content}{HASHTAGS}"
        
        # Post tweet using v2 API
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted: {tweet_text[:60]}... ({len(tweet_text)} chars)")
        
        return True
        
    except tweepy.TweepyException as e:
        if "400" in str(e):
            logging.error(f"X API rejected tweet, likely due to 280-char limit: {e}")
        else:
            logging.error(f"Tweet posting failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Tweet posting failed: {e}")
        return False

def run_tweet_schedule():
    """Run tweets every 45min-2.5h randomly to avoid moderation."""
    while True:
        if post_tweet():
            sleep_time = random.randint(2700, 9000)  # 45dk-2.5sa arası
            logging.info(f"Next tweet in {sleep_time//3600}h {(sleep_time%3600)//60}m")
            time.sleep(sleep_time)
        else:
            logging.info("Tweet failed, retrying in 5 minutes...")
            time.sleep(300)  # Hata sonrası 5 dakika bekle

def main():
    logging.info("Solium Bot starting...")
    
    # Immediate first tweet with story
    logging.info("Posting initial story tweet...")
    initial_tweet = "Solium Coin: Born from a spark of love, SLM ignites Web3 with seamless BSC-Solana DeFi swaps. Join our passionate #SoliumArmy, stake SLM, and vote in our DAO to shape a decentralized future! 😎🔥 Join presale: soliumcoin.com #Solium #Web3 #DeFi #Binance #BSC #BNB #Altcoin"  # 300 chars + hashtags
    try:
        client_x.create_tweet(text=initial_tweet)
        logging.info(f"Initial tweet posted: {initial_tweet[:60]}... ({len(initial_tweet)} chars)")
    except tweepy.TweepyException as e:
        logging.error(f"Initial tweet failed, possibly 280-char limit: {e}")
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

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
    client_grok = OpenAI(
        api_key=os.getenv("GROK_API_KEY"),
        base_url="https://api.x.ai/v1"
    )
    logging.info("Grok client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Grok client: {e}")
    raise

# Constants
HASHTAGS = " #Solium #SoliumArmy #Web3 #DeFi #Crypto #Blockchain #Binance #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT"  # 104 karakter
MAX_TWEET_LENGTH = 600  # Premium için 400-450 + hashtag’ler
MIN_CONTENT_LENGTH = 400  # İçerik için minimum
MAX_CONTENT_LENGTH = 450  # İçerik için maksimum

# Fallback Messages (Sadece İngilizce, 400-450 karakter, emojiler cümle içinde, Grok tarzı)
FALLBACK_TWEETS = [
    "Solium Coin sparks a Web3 love story! 😍 SLM powers BSC-Solana DeFi swaps with epic speed! 🔥 Join our #SoliumArmy, stake SLM, and vote in our DAO to shape a free future. 💪 Feel the passion, ignite the revolution! 😎 Join presale: soliumcoin.com",  # 442 karakter
    "Feel the Web3 vibe with Solium Coin! 🚀 SLM’s cross-chain tech links BSC & Solana for secure swaps! 😄 Our #SoliumArmy stakes SLM and rules the DAO, building a world of love! 💖 Join the revolution, spark the future! ✨ t.me/+KDhk3UEwZAg3MmU0",  # 445 karakter
    "Solium: A Web3 love saga! 🌍 SLM fuels BSC-Solana swaps with blazing speed! ⚡ Join our #SoliumArmy to stake SLM and shape DeFi’s future via DAO. 😍 Ignite freedom with community passion! 🔥 Join presale: soliumcoin.com",  # 440 karakter
    "Ignite your Web3 soul with Solium Coin! 💪 SLM’s BSC-Solana DeFi swaps are unstoppable! 😎 Our #SoliumArmy votes in the DAO to build a free dream. 🌟 Feel the love, spark the revolution! 🎉 Join: t.me/+KDhk3UEwZAg3MmU0",  # 444 karakter
    "Solium Coin: Where love meets Web3! 😘 SLM’s cross-chain tech sparks DeFi with BSC-Solana swaps! 🔥 Join our #SoliumArmy, stake SLM, and shape a future of freedom! 💥 Feel the vibe, ignite the spark! 😎 Join presale: soliumcoin.com",  # 443 karakter
]

# Banned phrases
BANNED_PHRASES = ["get rich", "guaranteed", "profit", "moon", "pump", "invest", "buy now", "make money", "financial advice"]

def is_safe_tweet(content):
    """Check if content avoids banned phrases."""
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def grok_generate_content():
    """Generate Solium-focused tweet content using Grok API."""
    system_prompt = """
    You are a content generator for Solium Coin (SLM). Strict rules:
    - Language: English only
    - Length: Strictly 400-450 characters (before hashtags), no more, no less
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' emphasizing Web3, DeFi, staking, DAO, blockchain tech, community
    - Story: Solium (SLM) was born from a platonic love, igniting Web3 freedom. It connects BSC & Solana for fast, secure transactions. #SoliumArmy shapes the future via DAO, inspired by Dubai’s luxury. Call to action: “Join the spark!” or “Feel the vibe!”
    - Tone: Ultra coşkulu, epik, destansı, meme coin çılgınlığıyla ama profesyonel; asla yatırım tavsiyesi değil
    - Emojis: Use 3-5 emojis of your choice, selecting the most fitting ones for the emotion of each sentence (e.g., 😍 for love, 🔥 for excitement, 🚀 for innovation, 😎 for coolness). Place emojis INSIDE the text, at the end of emotional sentences or within phrases (e.g., “SLM sparks Web3! 🔥”, “Join our #SoliumArmy! 😍”). Do NOT pile all emojis at the end of the tweet. Distribute them naturally to amplify the vibe.
    - Must include 'Solium' or 'SLM'
    - Include a call-to-action in 60% of tweets (e.g., 'Join presale: soliumcoin.com' or 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Do NOT include any hashtags in the content; hashtags will be added separately
    - Avoid: Any investment advice, price talk, or hype like 'moon,' 'pump,' 'buy now'
    - Example: "Solium Coin sparks a Web3 love story! 😍 SLM powers BSC-Solana DeFi swaps with epic speed! 🔥 Join our #SoliumArmy, stake SLM, and vote in our DAO to shape a free future. 💪 Feel the passion, ignite the revolution! 😎 Join presale: soliumcoin.com" (442 chars)
    """
    try:
        logging.info("Generating content with Grok...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a 400-450 character tweet about Solium's story, Web3, and DeFi, with no hashtags, emojis inside emotional sentences"}
            ],
            max_tokens=460,
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
            extra = f" Join the spark with SLM and ignite Web3 with passion! 😍🔥💪"
            content = content[:350] + extra[:MIN_CONTENT_LENGTH - len(content)]
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content and "SLM" not in content:
            logging.error(f"Grok error: Content missing 'Solium' or 'SLM': {content}")
            raise ValueError("Content missing 'Solium' or 'SLM'")
        
        # Emoji dağılım kontrolü
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]'
        import re
        emojis = re.findall(emoji_pattern, content)
        emoji_count = len(emojis)
        last_50_chars = content[-50:]
        last_50_emojis = re.findall(emoji_pattern, last_50_chars)
        last_50_emoji_count = len(last_50_emojis)
        if emoji_count < 3 or last_50_emoji_count >= emoji_count:
            logging.warning(f"Grok warning: Emojis not distributed well ({emoji_count} emojis, {last_50_emoji_count} in last 50 chars): {content}")
            # Emojileri cümle içlerine dağıt
            sentences = content.split('. ')
            if len(sentences) > 2:
                content = '. '.join(
                    s + (f" 😍" if i < len(sentences)-1 and not re.search(emoji_pattern, s) else "")
                    for i, s in enumerate(sentences)
                )
        
        logging.info(f"Grok generated content: {content[:60]}... ({len(content)} chars, {emoji_count} emojis: {emojis})")
        return content
    except Exception as e:
        logging.error(f"Grok error: {e}")
        return None

def post_tweet():
    """Post a single tweet with error handling."""
    try:
        logging.info("Attempting to post tweet...")
        # Generate content
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t) and MIN_CONTENT_LENGTH <= len(t) <= MAX_CONTENT_LENGTH])
            logging.info(f"Using fallback content: {content[:60]}... ({len(content)} chars)")
        
        # Add CTA
        if random.random() < 0.6:  # %60 presale
            content = content[:350] + f" Join presale: soliumcoin.com! 😍🔥"
        elif random.random() < 0.3:  # %30 Telegram
            content = content[:340] + f" Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0! 😎"
        
        # Karakter kontrolü
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            content += f" Join the spark! 😍"
        
        # Compose final tweet
        tweet_text = f"{content}{HASHTAGS}"
        logging.info(f"Final tweet text: {tweet_text} ({len(tweet_text)} chars)")
        
        # Post tweet using v2 API
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet posted successfully: {tweet_text[:60]}... ({len(tweet_text)} chars)")
        
        return True
        
    except tweepy.TweepyException as e:
        if "400" in str(e):
            logging.error(f"X API rejected tweet, likely due to character limit: {e}")
        elif "401" in str(e):
            logging.error(f"X API authentication error: {e}")
        else:
            logging.error(f"Tweet posting failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Tweet posting failed: {e}")
        return False

def run_tweet_schedule():
    """Run tweets every 45min-2.5h randomly to avoid moderation."""
    logging.info("Starting tweet schedule...")
    while True:
        if post_tweet():
            sleep_time = random.randint(2700, 9000)  # 45dk-2.5sa
            logging.info(f"Next tweet in {sleep_time//3600}h {(sleep_time%3600)//60}m")
            time.sleep(sleep_time)
        else:
            logging.info("Tweet failed, retrying in 5 minutes...")
            time.sleep(300)

def main():
    logging.info("Solium Bot starting...")
    
    # Immediate first tweet with story
    logging.info("Posting initial story tweet...")
    initial_tweet = "Solium Coin sparks a Web3 love story! 😍 SLM powers BSC-Solana DeFi swaps with epic speed! 🔥 Join our #SoliumArmy, stake SLM, and vote in our DAO to shape a free future. 💪 Feel the passion, ignite the revolution! 😎 Join presale: soliumcoin.com #Solium #SoliumArmy #Web3 #DeFi #Crypto #Blockchain #Binance #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT"  # 442 chars + hashtags
    try:
        client_x.create_tweet(text=initial_tweet)
        logging.info(f"Initial tweet posted: {initial_tweet[:60]}... ({len(initial_tweet)} chars)")
    except tweepy.TweepyException as e:
        logging.error(f"Initial tweet failed, possibly character limit or auth error: {e}")
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

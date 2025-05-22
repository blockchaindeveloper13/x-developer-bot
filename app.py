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
    client_grok = OpenAI(api_key=os.getenv("GROK_API_KEY"), http_client=httpx.Client(proxies=None))
    logging.info("Grok client initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Grok client: {e}")
    raise

# Constants
HASHTAGS = " #Solium #SoliumArmy #Web3 #DeFi #Crypto #Blockchain #Binance #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT"  # 104 karakter
MAX_TWEET_LENGTH = 1100
MIN_CONTENT_LENGTH = 800
MAX_CONTENT_LENGTH = 1000

# Fallback Messages (800-1000 karakter, emojiler cümle içinde)
FALLBACK_TWEETS = [
    "Solium Coin, bir platonik aşkın kıvılcımıyla doğdu! 😍 SLM, BSC ve Solana’yı birleştiren bir Web3 destanı yazıyor, ışık hızında ve güvenli DeFi işlemleri sunuyor! 🚀 #SoliumArmy, staking ve DAO ile geleceği şekillendiriyor, Dubai’nin lüksünden ilham alarak özgürlüğün ateşini yakıyor! 🔥 Topluluğumuzun tutkusuyla Web3’ü yeniden tanımlıyoruz, her bir SLM stake’i bir özgürlük adımı! 💪 Bu epik yolculuğa katıl, merkeziyetsiz bir dünyanın hayalini bizimle kur! 😎 Neden Solium? Çünkü aşk, teknolojiyle buluştuğunda sınırlar kalkar! 🌟 Presale’e katıl, Web3’ün geleceğine dokun: soliumcoin.com! ✨ #SoliumArmy, sen bu hikayede nasıl bir iz bırakacaksın? 😄",
    "Solium Coin ile Web3’ün ruhunu hisset! 😍 SLM, BSC ve Solana’yı birleştiren cross-chain teknolojisiyle DeFi’yi yeniden tanımlıyor, hızlı ve güvenli işlemler sunuyor! 🚀 #SoliumArmy, DAO’da oy kullanarak ve SLM stake ederek geleceği inşa ediyor, Dubai’nin ihtişamından ilham alıyor! 🔥 Tutkulu topluluğumuz, Web3’ün özgürlük ateşini körüklüyor, her adımda merkeziyetsiz bir dünya yaratıyor! 💪 Solium’un aşk hikayesine katıl, bu destansı yolculukta yerini al! 😎 Presale’e şimdi katıl: soliumcoin.com! ✨ #SoliumArmy, Web3’ü nasıl ateşleyeceksin? 😄",
    "Solium: Web3’ün aşk destanı! 😍 SLM, BSC-Solana köprüsüyle ışık hızında DeFi işlemleri sunuyor, güvenli ve merkeziyetsiz bir gelecek inşa ediyor! 🚀 #SoliumArmy, staking ve DAO ile Web3’ün yönünü belirliyor, Dubai’nin lüksünden esinlenerek özgürlüğün kıvılcımını yakıyor! 🔥 Topluluğumuzun ateşi, merkeziyetsiz dünyanın hayalini gerçeğe dönüştürüyor! 💪 Bu epik hikayede sen de yer al, Solium’un aşkını tüm dünyaya duyur! 😎 Hemen presale’e katıl: soliumcoin.com! ✨",
    "Solium Coin ile Web3’ün ruhunu ateşle! 😍 SLM, BSC ve Solana’yı birleştiren teknolojisiyle DeFi’yi uçuruyor, güvenli işlemlerle özgürlüğün kapılarını aralıyor! 🚀 #SoliumArmy, DAO’da liderlik ederek ve SLM stake ederek geleceği yazıyor, Dubai’nin lüksünden ilham alıyor! 🔥 Tutkumuz, Web3’ün sınırlarını zorluyor, her stake bir özgürlük şarkısı! 💪 Solium’un destanına katıl, aşkın kıvılcımını hisset! 😎 Telegram’a gel: t.me/+KDhk3UEwZAg3MmU0! ✨",
    "Solium Coin: Aşkın Web3’le buluştuğu yer! 😍 SLM, BSC-Solana köprüsüyle DeFi’yi yeniden şekillendiriyor, hızlı ve güvenli işlemlerle özgürlüğü müjdeliyor! 🚀 #SoliumArmy, DAO’da oy kullanarak ve stake ederek geleceği inşa ediyor, Dubai’nin ihtişamından güç alıyor! 🔥 Topluluğumuzun ateşi, Web3’ün özgürlük hayalini gerçeğe dönüştürüyor! 💪 Bu destansı yolculuğa katıl, Solium’un kıvılcımını tüm dünyaya yay! 😎 Presale: soliumcoin.com! ✨",
]

# Banned phrases
BANNED_PHRASES = ["get rich", "guaranteed", "profit", "moon", "pump", "invest", "buy now", "make money", "financial advice"]

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
    You are a content generator for Solium Coin (SLM). Strict rules:
    - Language: English only
    - Length: EXACTLY 800-1000 characters (before hashtags), no exceptions
    - Focus: Solium’s story as 'The Spark of a Web3 Love,' emphasizing Web3, DeFi, staking, DAO, blockchain tech, community
    - Story: Solium (SLM) was born from a platonic love, igniting Web3 freedom. It connects BSC & Solana for fast, secure transactions. #SoliumArmy shapes the future via DAO, inspired by Dubai’s luxury. Call to action: “Join the spark!” or “Feel the vibe!”
    - Tone: Ultra coşkulu, epik, destansı, meme coin çılgınlığıyla ama profesyonel; asla yatırım tavsiyesi değil
    - Emojis: Use 5-8 emojis, selecting the most fitting ones for the emotion of each sentence (e.g., 😍 for love, 🔥 for excitement, 🚀 for innovation, 😎 for coolness). Place emojis INSIDE the text, at the end of emotional sentences or within phrases (e.g., “SLM sparks Web3! 🔥”). Do NOT pile all emojis at the end. Distribute them naturally to amplify the vibe.
    - Must include 'Solium' or 'SLM'
    - Include a call-to-action in 60% of tweets (e.g., 'Join presale: soliumcoin.com' or 'Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0')
    - Include a question in 20% of tweets to boost engagement (e.g., '#SoliumArmy, how will you spark Web3? 😍')
    - Do NOT include any hashtags in the content; hashtags will be added separately
    - Avoid: Any investment advice, price talk, or hype like 'moon,' 'pump,' 'buy now'
    - Example: "Solium Coin, bir platonik aşkın kıvılcımıyla doğdu! 😍 SLM, BSC ve Solana’yı birleştiren bir Web3 destanı yazıyor, ışık hızında ve güvenli DeFi işlemleri sunuyor! 🚀 #SoliumArmy, staking ve DAO ile geleceği şekillendiriyor, Dubai’nin lüksünden ilham alarak özgürlüğün ateşini yakıyor! 🔥 Topluluğumuzun tutkusuyla Web3’ü yeniden tanımlıyoruz, her bir SLM stake’i bir özgürlük adımı! 💪 Bu epik yolculuğa katıl, merkeziyetsiz bir dünyanın hayalini bizimle kur! 😎 Neden Solium? Çünkü aşk, teknolojiyle buluştuğunda sınırlar kalkar! 🌟 Presale’e katıl, Web3’ün geleceğine dokun: soliumcoin.com! ✨ #SoliumArmy, sen bu hikayede nasıl bir iz bırakacaksın? 😄" (904 chars)
    """
    try:
        logging.info("Generating content with Grok...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate an 800-1000 character tweet about Solium's story, Web3, and DeFi, with no hashtags, emojis inside emotional sentences"}
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
            extra = f" Join the spark with SLM and ignite Web3 with passion! 😍🔥💪 Be part of the #SoliumArmy and shape a decentralized future! 😎"
            content = content[:700] + extra[:MIN_CONTENT_LENGTH - len(content)]
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok error: Content contains banned phrases: {content}")
            raise ValueError("Content contains banned phrases")
        if "Solium" not in content and "SLM" not in content:
            logging.error(f"Grok error: Content missing 'Solium' or 'SLM': {content}")
            raise ValueError("Content missing 'Solium' or 'SLM'")
        
        # Emoji dağılım kontrolü
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF]'
        emojis = re.findall(emoji_pattern, content)
        emoji_count = len(emojis)
        last_100_chars = content[-100:]
        last_100_emojis = re.findall(emoji_pattern, last_100_chars)
        last_100_emoji_count = len(last_100_emojis)
        if emoji_count < 5 or last_100_emoji_count >= emoji_count:
            logging.warning(f"Grok warning: Emojis not distributed well ({emoji_count} emojis, {last_100_emoji_count} in last 100 chars): {content}")
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
        if random.random() < 0.6:  # %60 presale
            content = content[:900] + f" Join presale: soliumcoin.com! 😍🔥"
        elif random.random() < 0.3:  # %30 Telegram
            content = content[:890] + f" Join #SoliumArmy: t.me/+KDhk3UEwZAg3MmU0! 😎"
        elif random.random() < 0.2:  # %20 question
            content = content[:890] + f" #SoliumArmy, how will you spark Web3? 😍"
        
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
    initial_tweet = "Solium Coin, bir platonik aşkın kıvılcımıyla doğdu! 😍 SLM, BSC ve Solana’yı birleştiren bir Web3 destanı yazıyor, ışık hızında ve güvenli DeFi işlemleri sunuyor! 🚀 #SoliumArmy, staking ve DAO ile geleceği şekillendiriyor, Dubai’nin lüksünden ilham alarak özgürlüğün ateşini yakıyor! 🔥 Topluluğumuzun tutkusuyla Web3’ü yeniden tanımlıyoruz, her bir SLM stake’i bir özgürlük adımı! 💪 Bu epik yolculuğa katıl, merkeziyetsiz bir dünyanın hayalini bizimle kur! 😎 Neden Solium? Çünkü aşk, teknolojiyle buluştuğunda sınırlar kalkar! 🌟 Presale’e katıl, Web3’ün geleceğine dokun: soliumcoin.com! ✨ #SoliumArmy, sen bu hikayede nasıl bir iz bırakacaksın? 😄 #Solium #SoliumArmy #Web3 #DeFi #Crypto #Blockchain #Binance #BSC #BNB #Solana #Cardano #Polkadot #Altcoin #Ethereum #NFT"
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

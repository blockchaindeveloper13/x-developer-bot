import tweepy
import os
import time
import random
import logging
import httpx
from datetime import datetime, timezone, timedelta
from openai import OpenAI
import re
from apscheduler.schedulers.background import BackgroundScheduler

# Günlük kaydı ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('solium_bot.log'),
        logging.StreamHandler()
    ]
)

# Çevre değişkenlerini kontrol et
required_env_vars = ["X_API_KEY", "X_SECRET_KEY", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "GROK_API_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        logging.error(f"Çevre değişkeni eksik: {var}")
        raise EnvironmentError(f"Çevre değişkeni eksik: {var}")

# Twitter API v2 İstemcisi
try:
    client_x = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_SECRET_KEY"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    logging.info("X API istemcisi başarıyla başlatıldı")
except Exception as e:
    logging.error(f"X API istemcisi başlatılamadı: {e}")
    raise

# OpenAI (Grok) İstemcisi
try:
    client_grok = OpenAI(api_key=os.getenv("GROK_API_KEY"), base_url="https://api.x.ai/v1", http_client=httpx.Client(proxies=None))
    logging.info("Grok istemcisi başarıyla başlatıldı")
except Exception as e:
    logging.error(f"Grok istemcisi başlatılamadı: {e}")
    raise

# Sabitler
WEBSITE_URL = " https://soliumcoin.com"
HASHTAG_POOL = [
    "#Solium", "#Web3", "#DeFi", "#Crypto", "#Blockchain", "#Binance", "#BSC",
    "#Solana", "#SoliumArmy", "#Dubai", "#Innovation", "#Decentralized"
]
MAX_TWEET_LENGTH = 1100  # Twitter karakter sınırı
MIN_CONTENT_LENGTH = 650
MAX_CONTENT_LENGTH = 850  # URL ve hashtag’ler için yer bırakıldı
SALE_MESSAGE = f" Join Solium with BNB only, ignite the Web3 revolution! Explore: {WEBSITE_URL}"

# Yedek Tweet’ler (650-850 karakter, İngilizce, satış odaklı, sadece website linki)
FALLBACK_TWEETS = [
    f"Solium Coin, born from a founder’s passionate heart under Dubai’s dazzling skyline! Bridging Binance Smart Chain & Solana, Solium powers Web3 with lightning-fast DeFi! 😍 Compatible with multiple exchanges, soon on more platforms! #SoliumArmy shapes a decentralized future! 🔥{SALE_MESSAGE}! 💪 Dubai’s vision, Solium’s fire! ✨",
    f"Feel the pulse of Web3 with Solium Coin! Sparked by a founder’s love in Dubai, Solium unites Binance Smart Chain & Solana for seamless DeFi! 😍 Aligned with many exchanges, more to come! #SoliumArmy forges the future! 🔥{SALE_MESSAGE}! 💪 Dubai shines, Solium burns bright! ✨",
    f"Solium Coin, a Web3 love story ignited in Dubai’s luxurious heart! Connecting Binance Smart Chain & Solana, Solium delivers blazing DeFi! 😍 Ready for multiple exchanges soon! #SoliumArmy builds a decentralized tomorrow! 🔥{SALE_MESSAGE}! 💪 Dubai’s fire, Solium’s flame! ✨",
    f"Solium Coin, sparked by a founder’s dream in Dubai Marina! Linking Binance Smart Chain & Solana, Solium drives Web3 with secure DeFi! 😍 Poised for more exchange integrations! #SoliumArmy carries the torch of innovation! 🔥{SALE_MESSAGE}! 💪 Dubai inspires, Solium ignites! ✨",
    f"Solium Coin, a passionate Web3 vision born in Dubai! Uniting Binance Smart Chain & Solana, Solium fuels DeFi with speed and security! 😍 Set for multiple exchange platforms soon! #SoliumArmy shapes decentralized freedom! 🔥{SALE_MESSAGE}! 💪 Dubai’s luxury, Solium’s spark! ✨",
]

# Yasaklı ifadeler (Howey Testi ve kırmızı bayrak radarından kaçınmak için)
BANNED_PHRASES = [
    "get rich", "guaranteed", "to the moon", "skyrocket", "buy now", "make money",
    "financial advice", "profit", "guaranteed returns", "investment opportunity",
    "returns", "pump", "zengin ol", "garanti", "ay’a gider", "yükselir", "hemen al",
    "para kazan", "kâr garantisi", "yatırım getirisi", "fiyat artışı"
]

def is_safe_tweet(content):
    """İçeriğin yasak ifadeler içerip içermediğini kontrol et."""
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def select_random_hashtags():
    """Rastgele 5-7 hashtag seç."""
    return " " + " ".join(random.sample(HASHTAG_POOL, random.randint(5, 7)))

def grok_generate_content():
    """Solium odaklı tweet içeriği üret."""
    system_prompt = f"""
    You are a content generator for Solium Coin. Strict rules:
    - Language: English only
    - Length: 650-850 characters (excluding hashtags and URL)
    - Focus: Solium’s 'Spark of a Web3 Love' story, emphasizing Web3, DeFi, decentralized governance, blockchain tech, and community
    - Story: Solium was born from a founder’s platonic love in Dubai, turning passion into a Web3 mission. Inspired by Dubai’s luxury, Solium bridges Binance Smart Chain & Solana for fast, secure DeFi. #SoliumArmy carries the torch of decentralized freedom. Every tweet must include: “Join Solium with BNB only, ignite the Web3 revolution! Explore: {WEBSITE_URL}”
    - Tone: Enthusiastic, epic, marketing-driven, professional; never financial advice
    - Emojis: 5-8 emojis based on emotional intensity (😍 for love, 🔥 for excitement, 🚀 for innovation, 😎 for coolness). Place naturally at sentence ends, avoid piling at the end.
    - Exchanges: Imply compatibility with phrases like “aligned with multiple exchanges” or “soon on more platforms,” without guaranteeing listings or profits.
    - CTA: Every tweet includes “Join Solium with BNB only, ignite the Web3 revolution! Explore: {WEBSITE_URL}”
    - 30% of tweets include an engagement question (e.g., “#SoliumArmy, how will you ignite Web3?”)
    - Occasionally highlight the founder’s story: their unrequited love sparked a Web3 vision
    - Do NOT include hashtags or website URL in content; added separately
    - Avoid: Investment advice, price talk, 'moon,' 'skyrocket,' 'buy now'
    - Example: "Solium Coin, born from a founder’s love in Dubai! Uniting Binance Smart Chain & Solana, Solium fuels Web3 with fast DeFi! 😍 Aligned with multiple exchanges! #SoliumArmy shapes the future! 🔥 Join Solium with BNB only, ignite the Web3 revolution! Explore: {WEBSITE_URL}! 💪 Dubai’s fire, Solium’s flame! ✨" (700 chars)
    """
    try:
        logging.info("Grok ile içerik üretiliyor...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a 650-850 character tweet about Solium’s story, Web3, and DeFi, no hashtags or website URL, with emojis placed based on emotional intensity"}
            ],
            max_tokens=1000,
            temperature=0.9
        )
        content = completion.choices[0].message.content.strip()
        
        # İçerik kontrolü
        if not content:
            logging.error("Grok hatası: İçerik boş")
            raise ValueError("İçerik boş")
        
        # Karakter aralığı kontrolü
        if len(content) > MAX_CONTENT_LENGTH:
            logging.warning(f"Grok uyarısı: İçerik çok uzun ({len(content)} karakter), kesiliyor: {content}")
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            logging.warning(f"Grok uyarısı: İçerik çok kısa ({len(content)} karakter), uzatılıyor: {content}")
            extra = f" Join Solium’s Web3 vision, spark the future! #SoliumArmy drives decentralized freedom!"
            content = content[:600] + extra[:MIN_CONTENT_LENGTH - len(content)]
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok hatası: İçerik yasak ifadeler içeriyor: {content}")
            raise ValueError("İçerik yasak ifadeler içeriyor")
        if "Solium" not in content:
            logging.error(f"Grok hatası: İçerikte 'Solium' eksik: {content}")
            raise ValueError("İçerikte 'Solium' eksik")
        
        logging.info(f"Grok içeriği üretildi: {content[:60]}... ({len(content)} karakter)")
        return content
    except Exception as e:
        logging.error(f"Grok hatası: {e}")
        return None

def post_tweet():
    """Tek bir tweet gönder, hata yönetimi ile."""
    try:
        logging.info("Tweet gönderiliyor...")
        # İçerik üret
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t) and MIN_CONTENT_LENGTH <= len(t) <= MAX_CONTENT_LENGTH])
            logging.info(f"Yedek içerik kullanılıyor: {content[:60]}... ({len(content)} karakter)")
        
        # CTA ekle
        content = content[:800] + SALE_MESSAGE
        
        # Etkileşim sorusu (%30)
        if random.random() < 0.3:
            content = content[:750] + f" #SoliumArmy, how will you ignite Web3? 😄"
        
        # Karakter kontrolü
        if len(content) > MAX_CONTENT_LENGTH:
            content = content[:MAX_CONTENT_LENGTH]
        elif len(content) < MIN_CONTENT_LENGTH:
            content += SALE_MESSAGE
        
        # Dinamik hashtag’ler
        hashtags = select_random_hashtags()
        
        # Nihai tweet
        tweet_text = f"{content}{hashtags}"
        if len(tweet_text) > MAX_TWEET_LENGTH:
            logging.warning(f"Tweet çok uzun ({len(tweet_text)} karakter), kesiliyor")
            tweet_text = tweet_text[:MAX_TWEET_LENGTH]
        
        logging.info(f"Nihai tweet metni: {tweet_text[:60]}... ({len(tweet_text)} karakter)")
        
        # Tweet gönder
        client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet başarıyla gönderildi: {tweet_text[:60]}... ({len(tweet_text)} karakter)")
        
        return True
        
    except tweepy.TweepyException as e:
        if "429" in str(e):
            logging.error(f"X API oran sınırı aşıldı: {e}")
            time.sleep(7200)  # 2 saat bekle
            return False
        elif "400" in str(e):
            logging.error(f"X API tweeti reddetti, karakter sınırı veya içerik sorunu: {e}")
            return False
        elif "401" in str(e):
            logging.error(f"X API kimlik doğrulama hatası: {e}")
            return False
        else:
            logging.error(f"Tweet gönderimi başarısız: {e}")
            return False
    except Exception as e:
        logging.error(f"Tweet gönderimi başarısız: {e}")
        return False

def schedule_tweets():
    """Tweet’leri ~96 dakikada bir (günde 15 tweet) planla."""
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(post_tweet, 'interval', seconds=5760)
    scheduler.start()

def main():
    logging.info("Solium Bot başlatılıyor...")
    
    # İlk tweet (İngilizce)
    logging.info("İlk hikaye tweeti gönderiliyor...")
    initial_tweet = f"Solium Coin, born from a founder’s platonic love in Dubai’s dazzling skyline! Uniting Binance Smart Chain & Solana, Solium fuels Web3 with lightning-fast DeFi! 😍 Aligned with multiple exchanges, ready for more platforms soon! #SoliumArmy shapes a decentralized future! 🔥 Join Solium with BNB only, ignite the Web3 revolution! Explore: {WEBSITE_URL}! 💪 Dubai’s vision, Solium’s flame! ✨ #SoliumArmy, how will you spark Web3? 😎 #Solium #Web3 #DeFi #Crypto #Blockchain #Binance #Solana"
    try:
        client_x.create_tweet(text=initial_tweet)
        logging.info(f"İlk tweet gönderildi: {initial_tweet[:60]}... ({len(initial_tweet)} karakter)")
    except tweepy.TweepyException as e:
        logging.error(f"İlk tweet başarısız, karakter sınırı veya kimlik doğrulama hatası: {e}")
    except Exception as e:
        logging.error(f"İlk tweet başarısız: {e}")
    
    # Tweet planlamasını başlat
    schedule_tweets()
    try:
        while True:
            time.sleep(60)  # Ana iş parçacığını canlı tut
    except KeyboardInterrupt:
        logging.info("Bot kullanıcı tarafından durduruldu")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Ölümcül hata: {e}")

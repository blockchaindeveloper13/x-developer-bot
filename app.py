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

# Günlük kaydı ayarları (Türkiye saati ile)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('solium_bot.log'),
        logging.StreamHandler()
    ],
    datefmt='%Y-%m-%d %H:%M:%S %Z'
)
logging.Formatter.converter = lambda *args: datetime.now(timezone(timedelta(hours=3))).timetuple()

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
WEBSITE_URL = "https://soliumcoin.com"
HASHTAG_POOL = [
    "#Solium", "#SoliumArmy", "#Web3", "#DeFi", "#Crypto", "#Cryptocurrency",
    "#Cryptocurrencies", "#Blockchain", "#BlockchainTechnology", "#CryptoNews",
    "#CryptocurrencyNews", "#CryptoMarket", "#Cryptotrading", "#CryptoInvestor",
    "#Cryptoworld", "#Cryptolife", "#CryptoCommunity", "#Cryptomemes", "#Bitcoin",
    "#BTC", "#Ethereum", "#ETH", "#Binance", "#BNB", "#Solana", "#SOL", "#Ripple",
    "#XRP", "#Litecoin", "#LTC", "#Dogecoin", "#DOGE", "#Cardano", "#ADA",
    "#Polkadot", "#DOT", "#Chainlink", "#LINK", "#DAO", "#Decentralized",
    "#DecentralizedFinance", "#YieldFarming", "#Staking", "#NFT", "#NFTs",
    "#NFTArt", "#Metaverse", "#CryptoArt", "#NFTCommunity", "#Trading",
    "#CryptocurrencyTrading", "#Altcoin", "#Altcoins", "#HODL", "#CryptoExchange",
    "#BinanceFutures", "#Coinbase", "#KuCoin", "#Kraken", "#CryptoTwitter",
    "#BitcoinCommunity", "#EthereumCommunity", "#SolanaCommunity", "#BSC",
    "#MemeCoin", "#CryptoEvents", "#Invest", "#Investing", "#Investment",
    "#FinancialFreedom", "#PassiveIncome", "#CryptoInvesting", "#BullRun",
    "#BearMarket", "#Dubai", "#Innovation"
]
MAX_TWEET_LENGTH = 4000  # X Premium için maksimum karakter sınırı
PREVIEW_LENGTH = 280  # İlk görünen kısım
SALE_MESSAGE = f" Join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Explore: {WEBSITE_URL}"

# Yedek Tweet’ler (280+ karakter, İngilizce, satış odaklı)
FALLBACK_TWEETS = [
    f"{WEBSITE_URL} Solium Coin presale extended! 🚨 Join with BNB now via MetaMask, Binance, or KuCoin Web3 Wallet! Aligned with top exchanges, launching by Sep, maybe Jul! #SoliumArmy sparks Web3! 😍 Why Choose Solium? Our BSC-Solana bridge delivers unmatched DeFi speed! 🚀 #SoliumArmy shapes the future via DAO! 🔥 BNB joining is seamless with Web3 Wallets! 😎 Exchange protocols signed, Sep or Jul launch! Join with BNB now! Explore: {WEBSITE_URL} 💪 #Solium #Web3 #DeFi",
    f"{WEBSITE_URL} Don’t miss Solium Coin’s presale! 🚨 BNB via Binance, KuCoin Web3 Wallet, or MetaMask! Set for exchanges, launching Sep or Jul! #SoliumArmy ignites DeFi! 😍 Why Choose Solium? BSC-Solana bridge for secure DeFi! 🚀 DAO empowers #SoliumArmy! 🔥 Easy BNB process! 😎 Exchange deals in place! Join with BNB now! Explore: {WEBSITE_URL} 💪 #Solium #Web3 #Crypto",
    f"{WEBSITE_URL} Solium Coin presale is live! 🚨 Join with BNB using MetaMask or Web3 Wallets! Exchange-ready, launching by Sep, maybe Jul! #SoliumArmy builds freedom! 😍 Why Choose Solium? Fastest DeFi with BSC-Solana! 🚀 Community-driven DAO! 🔥 Simple BNB joining! 😎 Exchange protocols ready! Join with BNB now! Explore: {WEBSITE_URL} 💪 #Solium #DeFi #Binance",
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

def check_rate_limit():
    """Twitter API oran sınırını kontrol et."""
    try:
        response = client_x.get_me()
        rate_limit = response.meta.get('x-rate-limit-remaining', None)
        reset_time = response.meta.get('x-rate-limit-reset', time.time() + 3600)
        if rate_limit is not None:
            logging.info(f"Rate limit kalan: {rate_limit}, sıfırlanma: {datetime.fromtimestamp(reset_time, timezone.utc)}")
        return rate_limit, reset_time
    except Exception as e:
        logging.error(f"Rate limit kontrolü başarısız: {e}")
        return None, None

def select_random_hashtags():
    """Rastgele 9-10 hashtag seç."""
    return " " + " ".join(random.sample(HASHTAG_POOL, random.randint(9, 10)))

def grok_generate_content():
    """Solium odaklı tweet içeriği üret."""
    system_prompt = f"""
    You are a content generator for Solium Coin, a Web3 project born from passion. Strict rules:
    - Language: English only
    - Length: Up to 4000 characters, optimized for X Premium. First 280 characters must be highly engaging to drive 'See More' clicks, followed by detailed content.
    - Structure: Start with “{WEBSITE_URL} Solium Coin presale extended! 🚨 Don’t miss out, join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Aligned with top exchanges, launching by September, possibly July if sales soar! Any moment, we could hit major exchanges!” Then, under “Why Choose Solium?”, answer these questions in depth:
      - What is Solium’s technical edge over other DeFi projects? (Highlight BSC-Solana bridge, speed, low fees)
      - How does the community engage, and how does governance work? (Emphasize #SoliumArmy’s DAO, voting power)
      - How does joining with BNB work, is it user-friendly? (Detail MetaMask, Binance/KuCoin Web3 Wallet ease)
      - When will Solium hit exchanges, what’s the progress? (Mention protocols signed, Sep/Jul timeline)
    - Focus: Solium’s 'Spark of a Web3 Love' story, born from a founder’s platonic love in Dubai, turning passion into a Web3 mission. Inspired by Dubai’s luxury, Solium bridges Binance Smart Chain & Solana for ultra-fast, secure DeFi. #SoliumArmy drives decentralized freedom.
    - Tone: Professional, enthusiastic, highly persuasive, inviting, community-focused; never financial advice
    - Emojis: 5-10 emojis per tweet (😍 for love, 🔥 for excitement, 🚀 for innovation, 😎 for coolness). Place naturally at sentence ends.
    - Exchanges: Every tweet must include “Protocols signed with top exchanges, launch set for September, possibly July if sales surge!” without profit guarantees.
    - CTA: Reinforce “Join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Explore: {WEBSITE_URL}” at start and end.
    - Engagement: 30% of tweets end with a question like “#SoliumArmy, ready to ignite Web3?” or “How will you shape Web3 with Solium?”
    - Details: Highlight presale extension, urgency (“any moment, we could hit exchanges”), and user-friendly BNB process. Emphasize Solium’s unique BSC-Solana bridge and DAO governance.
    - Do NOT include hashtags or website URL in content; added separately
    - Avoid: Investment advice, price talk, 'moon,' 'skyrocket,' or any profit guarantees
    - Example: “{WEBSITE_URL} Solium Coin presale extended! 🚨 Don’t miss out, join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Aligned with top exchanges, launching by September, possibly July if sales soar! Any moment, we could hit major exchanges! Why Choose Solium? Solium’s BSC-Solana bridge offers unmatched DeFi speed and low fees, outpacing rivals! 😍 #SoliumArmy shapes every decision via our DAO, giving you voting power! 🔥 Joining with BNB is seamless—connect MetaMask or Web3 Wallet in seconds! 🚀 Protocols signed with top exchanges, launch set for Sep, maybe Jul! 😎 Join with BNB now! Explore: {WEBSITE_URL} #SoliumArmy, ready to ignite Web3? 💪”
    """
    try:
        logging.info("Grok ile içerik üretiliyor...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a tweet about Solium’s story, Web3, and DeFi, up to 4000 characters, starting with the presale message, answering the four questions under 'Why Choose Solium?', with emojis placed based on emotional intensity"}
            ],
            max_tokens=4000,
            temperature=0.9
        )
        content = completion.choices[0].message.content.strip()
        
        # İçerik kontrolü
        if not content:
            logging.error("Grok hatası: İçerik boş")
            raise ValueError("İçerik boş")
        
        # Güvenlik ve Solium kontrolü
        if not is_safe_tweet(content):
            logging.error(f"Grok hatası: İçerik yasak ifadeler içeriyor: {content[:100]}...")
            raise ValueError("İçerik yasak ifadeler içeriyor")
        if "Solium" not in content:
            logging.error(f"Grok hatası: İçerikte 'Solium' eksik: {content[:100]}...")
            raise ValueError("İçerikte 'Solium' eksik")
        
        # İlk 280 karakteri optimize et
        preview = content[:PREVIEW_LENGTH]
        if len(preview) < 100:
            preview += f" Why Choose Solium? Join the Web3 revolution! 😍"
        
        # Tam içeriği logla
        logging.info(f"Grok tam içeriği: {content[:100]}... ({len(content)} karakter)")
        logging.info(f"İlk 280 karakter: {preview} ({len(preview)} karakter)")
        
        return content
    except Exception as e:
        logging.error(f"Grok hatası: {e}")
        return None

def post_tweet():
    """Tek bir tweet gönder, hata yönetimi ile."""
    try:
        rate_limit, reset_time = check_rate_limit()
        if rate_limit == 0:
            wait_time = max(0, reset_time - time.time())
            logging.info(f"Rate limit aşıldı, {wait_time/3600:.1f} saat bekleniyor")
            time.sleep(wait_time)
        
        logging.info("Tweet gönderiliyor...")
        content = grok_generate_content()
        if not content:
            content = random.choice([t for t in FALLBACK_TWEETS if is_safe_tweet(t)])
            logging.info(f"Yedek içerik kullanılıyor: {content[:60]}... ({len(content)} karakter)")
        
        content = f"{WEBSITE_URL} Solium Coin presale extended! 🚨 Don’t miss out, join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Aligned with top exchanges, launching by September, possibly July if sales soar! Any moment, we could hit major exchanges! {content} {SALE_MESSAGE}"
        
        if random.random() < 0.3:
            content += f" #SoliumArmy, ready to ignite Web3? 😎"
        
        hashtags = select_random_hashtags()
        
        tweet_text = f"{content}{hashtags}"
        if len(tweet_text) > MAX_TWEET_LENGTH:
            logging.warning(f"Tweet çok uzun ({len(tweet_text)} karakter), kesiliyor")
            tweet_text = tweet_text[:MAX_TWEET_LENGTH]
        
        logging.info(f"Nihai tweet metni: {tweet_text[:60]}... ({len(tweet_text)} karakter)")
        
        response = client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet başarıyla gönderildi: {tweet_text[:60]}... ({len(tweet_text)} karakter), Tweet ID: {response.data['id']}")
        
        return True
        
    except tweepy.TweepyException as e:
        error_details = getattr(e, 'api_errors', str(e))
        if "429" in str(e):
            logging.error(f"X API oran sınırı aşıldı: {e}, Hata Detayı: {error_details}")
            time.sleep(3600)
            return False
        elif "400" in str(e):
            logging.error(f"X API tweeti reddetti, karakter sınırı veya içerik sorunu: {e}, Hata Detayı: {error_details}")
            return False
        elif "401" in str(e):
            logging.error(f"X API kimlik doğrulama hatası: {e}, Hata Detayı: {error_details}")
            return False
        else:
            logging.error(f"Tweet gönderimi başarısız: {e}, Hata Detayı: {error_details}")
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
    
    initial_tweet = f"{WEBSITE_URL} Solium Coin presale extended! 🚨 Don’t miss out, join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Aligned with top exchanges, launching by Sep, possibly Jul if sales soar! Any moment, we could hit major exchanges! Solium, sparked by love in Dubai! 😍 Merging BSC & Solana for fast DeFi! 🚀 Why Choose Solium? BSC-Solana bridge for unmatched speed! 🔥 #SoliumArmy’s DAO gives you power! 😎 Easy BNB via Web3 Wallets! 💪 Exchange protocols signed! Join with BNB now! Explore: {WEBSITE_URL} #Solium #Web3 #DeFi #Crypto #Binance"
    try:
        response = client_x.create_tweet(text=initial_tweet)
        logging.info(f"İlk tweet gönderildi: {initial_tweet[:60]}... ({len(initial_tweet)} karakter), Tweet ID: {response.data['id']}")
    except tweepy.TweepyException as e:
        logging.error(f"İlk tweet başarısız, hata: {e}, Hata Detayı: {getattr(e, 'api_errors', str(e))}")
    except Exception as e:
        logging.error(f"İlk tweet başarısız: {e}")
    
    schedule_tweets()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Bot kullanıcı tarafından durduruldu")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Ölümcül hata: {e}")

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

# Günlük kaydı (Türkiye saati)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('solium_bot.log'), logging.StreamHandler()],
    datefmt='%Y-%m-%d %H:%M:%S %Z'
)
logging.Formatter.converter = lambda *args: datetime.now(timezone(timedelta(hours=3))).timetuple()

# Çevre değişkenleri kontrol
required_env_vars = ["X_API_KEY", "X_SECRET_KEY", "X_ACCESS_TOKEN", "X_ACCESS_SECRET", "GROK_API_KEY"]
for var in required_env_vars:
    if not os.getenv(var):
        logging.error(f"Çevre değişkeni eksik: {var}")
        raise EnvironmentError(f"Çevre değişkeni eksik: {var}")

# Twitter API v2 istemcisi
try:
    client_x = tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_SECRET_KEY"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_SECRET")
    )
    api_x = tweepy.API(tweepy.OAuthHandler(os.getenv("X_API_KEY"), os.getenv("X_SECRET_KEY")))
    api_x.set_access_token(os.getenv("X_ACCESS_TOKEN"), os.getenv("X_ACCESS_SECRET"))
    logging.info("X API istemcisi başarıyla başlatıldı")
except Exception as e:
    logging.error(f"X API istemcisi başlatılamadı: {e}")
    raise

# Grok istemcisi
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
MAX_TWEET_LENGTH = 4000
PREVIEW_LENGTH = 280
SALE_MESSAGE = f" Join with BNB now via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask! Explore: {WEBSITE_URL}"

# Yedek Tweet’ler
FALLBACK_TWEETS = [
    f"{WEBSITE_URL} Born in Dubai, Solium Coin’s presale is live! 🚨 Join with BNB via MetaMask or Web3 Wallets! Aligned with top exchanges, launching by Sep, maybe Jul! #SoliumArmy sparks Web3! 😍 Why Choose Solium? BSC-Solana bridge for unmatched DeFi speed! 🚀 DAO empowers #SoliumArmy! 🔥 Easy BNB process! 😎 Exchange protocols signed! {SALE_MESSAGE} 💪 #Solium #Web3",
    f"{WEBSITE_URL} Ready for Web3’s future? Solium Coin’s presale awaits! 😍 BNB via Binance, KuCoin Web3 Wallet, or MetaMask! Set for exchanges, launching Sep or Jul! #SoliumArmy ignites DeFi! 🚀 Why Choose Solium? Secure BSC-Solana bridge! 🔥 DAO voting power! 😎 Simple BNB joining! 💪 Exchange deals ready! {SALE_MESSAGE} #Solium #Crypto",
    f"{WEBSITE_URL} Solium Coin’s presale is hot! 🚀 Join with BNB now via MetaMask or Web3 Wallets! Exchange-ready, launching by Sep, maybe Jul! #SoliumArmy builds freedom! 😍 Why Choose Solium? Fastest DeFi with BSC-Solana! 🚀 Community-driven DAO! 🔥 Easy BNB process! 😎 Exchange protocols signed! {SALE_MESSAGE} 💪 #Solium #DeFi",
    f"{WEBSITE_URL} From Dubai’s heart, Solium Coin fuels Web3! 🔥 BNB presale live via Binance or MetaMask! Aligned with exchanges, launching Sep or Jul! #SoliumArmy shines! 😍 Why Choose Solium? BSC-Solana bridge speed! 🚀 DAO empowers you! 😎 Seamless BNB joining! 💪 Exchange deals in place! {SALE_MESSAGE} #Solium #Web3",
    f"{WEBSITE_URL} Solium Coin: Web3’s Dubai dream! 😍 Join presale with BNB via KuCoin Web3 Wallet or MetaMask! Set for exchanges, launching Sep or Jul! #SoliumArmy rises! 🚀 Why Choose Solium? Ultra-fast BSC-Solana bridge! 🔥 DAO governance! 😎 Easy BNB process! 💪 Exchange protocols ready! {SALE_MESSAGE} #Solium #Crypto",
    f"{WEBSITE_URL} Don’t miss Solium Coin’s presale spark! 🚨 BNB via Binance Web3 Wallet or MetaMask! Launching Sep, maybe Jul, with exchange deals! #SoliumArmy roars! 😍 Why Choose Solium? BSC-Solana bridge for DeFi! 🚀 #SoliumArmy’s DAO! 🔥 Simple BNB joining! 😎 Exchange protocols signed! {SALE_MESSAGE} 💪 #Solium #DeFi",
    f"{WEBSITE_URL} Solium Coin, born from Dubai’s passion! 🔥 Presale live with BNB via MetaMask or Web3 Wallets! Exchange-ready, launching Sep or Jul! #SoliumArmy unites! 😍 Why Choose Solium? BSC-Solana speed! 🚀 DAO voting! 😎 Easy BNB process! 💪 Exchange deals set! {SALE_MESSAGE} #Solium #Web3",
    f"{WEBSITE_URL} Join Solium Coin’s Web3 revolution! 🚀 BNB presale via Binance or KuCoin Web3 Wallet! Aligned with exchanges, launching Sep or Jul! #SoliumArmy leads! 😍 Why Choose Solium? Secure BSC-Solana bridge! 🔥 DAO power! 😎 Seamless BNB joining! 💪 Exchange protocols ready! {SALE_MESSAGE} #Solium #Crypto"
]

# Yasaklı ifadeler
BANNED_PHRASES = [
    "get rich", "guaranteed", "to the moon", "skyrocket", "buy now", "make money",
    "financial advice", "profit", "guaranteed returns", "investment opportunity",
    "returns", "pump", "zengin ol", "garanti", "ay’a gider", "yükselir", "hemen al",
    "para kazan", "kâr garantisi", "yatırım getirisi", "fiyat artışı"
]

def is_safe_tweet(content):
    content_lower = content.lower()
    return not any(phrase in content_lower for phrase in BANNED_PHRASES)

def check_rate_limit():
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
    return " " + " ".join(random.sample(HASHTAG_POOL, random.randint(9, 10)))

# TT çekme (TT botuyla sinerji)
def get_trending_topics(woeid):
    try:
        trends = api_x.get_place_trends(woeid)
        return [trend["name"] for trend in trends[0]["trends"][:5]]
    except Exception as e:
        logging.error(f"TT çekme hatası (WOEID: {woeid}): {e}")
        return ["#Crypto", "#Web3", "#DeFi"]

def grok_generate_content():
    system_prompt = f"""
    You are a content generator for Solium Coin, a Web3 project born from passion. Strict rules:
    - Language: English only
    - Length: Up to 4000 chars, optimized for X Premium. First 280 chars must be unique, engaging, and optimized to drive 'See More' clicks, generated creatively by you. Followed by detailed content.
    - First 280 chars: Always start with “{WEBSITE_URL}”. Create a varied, catchy intro (50-100 chars) that MUST include:
      - Presale emphasis (e.g., “presale live!” or “presale extended!”)
      - BNB joining via Binance Web3 Wallet, KuCoin Web3 Wallet, or MetaMask
      - Exchange alignment, launching Sep, possibly Jul (e.g., “any moment, we could hit exchanges!”)
      Vary tone (urgent, story-driven, community-focused) but keep these elements. Examples:
      - “{WEBSITE_URL} Solium Coin presale live! 🚨 Join with BNB via MetaMask! Launching Sep, maybe Jul, exchanges soon!”
      - “{WEBSITE_URL} Presale extended! 😍 BNB via Binance Web3 Wallet, hit exchanges any moment, Sep/Jul launch!”
      - “{WEBSITE_URL} Dubai’s Solium presale is hot! 🚀 Join BNB via KuCoin Wallet, exchanges aligned for Sep/Jul!”
    - Structure: After the intro, under “Why Choose Solium?”, answer:
      - What is Solium’s technical edge? (BSC-Solana bridge, speed, low fees)
      - How does community engage, governance work? (#SoliumArmy’s DAO, voting)
      - How does BNB joining work, is it user-friendly? (MetaMask, Web3 Wallet ease)
      - When will Solium hit exchanges, progress? (Protocols signed, Sep/Jul)
    - Focus: Solium’s 'Spark of a Web3 Love' story, born from a founder’s platonic love in Dubai, turning passion into a Web3 mission. Inspired by Dubai’s luxury, Solium bridges Binance Smart Chain & Solana for ultra-fast, secure DeFi. #SoliumArmy drives freedom.
    - Tone: Professional, enthusiastic, persuasive, community-focused; no financial advice
    - Emojis: 5-10 per tweet (😍, 🔥, 🚀, 😎, 💪), placed naturally
    - Exchanges: Include “Protocols signed with top exchanges, launch set for Sep, possibly Jul if sales surge!” without profit guarantees
    - CTA: End with “{SALE_MESSAGE}”
    - Engagement: 50% of tweets end with a question like “#SoliumArmy, ready to ignite Web3?” or “How will you shape Web3 with Solium?”
    - Details: Highlight presale extension, urgency, BSC-Solana bridge, DAO governance
    - Do NOT include hashtags or website URL in content; added separately
    - Avoid: Investment advice, price talk, 'moon,' 'skyrocket,' profit guarantees
    - Example: “{WEBSITE_URL} Solium Coin presale live! 🚨 Join with BNB via MetaMask! Launching Sep, maybe Jul, exchanges soon! Why Choose Solium? BSC-Solana bridge for unmatched speed! 😍 #SoliumArmy’s DAO empowers you! 🔥 BNB joining is seamless! 🚀 Protocols signed, Sep/Jul launch! 😎 {SALE_MESSAGE} #SoliumArmy, ready to ignite Web3? 💪”
    """
    try:
        logging.info("Grok ile içerik üretiliyor...")
        completion = client_grok.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate a tweet about Solium’s story, Web3, and DeFi, up to 4000 chars, with a unique, optimized first 280 chars, answering the four questions under 'Why Choose Solium?', with emojis based on emotional intensity"}
            ],
            max_tokens=4000,
            temperature=0.9
        )
        content = completion.choices[0].message.content.strip()
        
        # İlk 280 karakterde zorunlu unsurları kontrol et
        preview = content[:PREVIEW_LENGTH]
        if not content or not is_safe_tweet(content) or "Solium" not in content:
            logging.error(f"Grok hatası: İçerik boş veya geçersiz: {content[:100]}...")
            raise ValueError("Geçersiz içerik")
        if not preview.startswith(WEBSITE_URL) or "presale" not in preview.lower() or "BNB" not in preview or "exchange" not in preview.lower():
            logging.error(f"Grok hatası: İlk 280 char eksik: {preview[:100]}...")
            raise ValueError("İlk 280 char zorunlu unsurları içermiyor")
        
        if len(preview) < 100:
            preview += f" Why Choose Solium? Join the Web3 revolution! 😍"
        
        logging.info(f"Grok tam içeriği: {content[:100]}... ({len(content)} chars)")
        logging.info(f"İlk 280 char: {preview} ({len(preview)} chars)")
        
        return content
    except Exception as e:
        logging.error(f"Grok hatası: {e}")
        return None

def post_tweet():
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
            logging.info(f"Yedek içerik: {content[:60]}... ({len(content)} chars)")
        
        if random.random() < 0.5:
            content += f" #SoliumArmy, ready to ignite Web3? 😎"
        
        regions = [
            {"name": "Dubai", "woeid": 1940345}, {"name": "Suudi Arabistan", "woeid": 23424938},
            {"name": "Türkiye", "woeid": 23424969}, {"name": "Singapur", "woeid": 23424948},
            {"name": "Vietnam", "woeid": 23424984}, {"name": "Brezilya", "woeid": 23424768}
        ]
        region = random.choice(regions)
        tt_hashtags = " ".join(get_trending_topics(region["woeid"])[:2])
        hashtags = select_random_hashtags() + f" {tt_hashtags}"
        
        tweet_text = f"{content} {SALE_MESSAGE}{hashtags}"
        if len(tweet_text) > MAX_TWEET_LENGTH:
            logging.warning(f"Tweet çok uzun ({len(tweet_text)} chars), kesiliyor")
            tweet_text = tweet_text[:MAX_TWEET_LENGTH]
        
        logging.info(f"Nihai tweet: {tweet_text[:60]}... ({len(tweet_text)} chars)")
        
        response = client_x.create_tweet(text=tweet_text)
        logging.info(f"Tweet gönderildi: {tweet_text[:60]}... ({len(tweet_text)} chars), ID: {response.data['id']}")
        return True
    except tweepy.TweepyException as e:
        error_details = getattr(e, 'api_errors', str(e))
        if "429" in str(e):
            logging.error(f"X API oran sınırı aşıldı: {e}, Detay: {error_details}")
            time.sleep(3600)
            return False
        elif "400" in str(e):
            logging.error(f"X API tweet reddetti: {e}, Detay: {error_details}")
            return False
        elif "401" in str(e):
            logging.error(f"X API kimlik doğrulama hatası: {e}, Detay: {error_details}")
            return False
        else:
            logging.error(f"Tweet başarısız: {e}, Detay: {error_details}")
            return False
    except Exception as e:
        logging.error(f"Tweet başarısız: {e}")
        return False

def schedule_tweets():
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(post_tweet, 'interval', seconds=5760)  # 96 dk, 15 tweet/gün
    scheduler.start()

def main():
    logging.info("Solium Bot başlatılıyor...")
    # İlk tweet için direkt Grok içeriği
    if not post_tweet():
        logging.error("İlk tweet gönderimi başarısız, bot devam ediyor")
    
    schedule_tweets()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Bot durduruldu")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Ölümcül hata: {e}")

import tweepy
import os
import time
from datetime import datetime

# Heroku Config Vars'tan anahtarları al
api_key = os.getenv("X_API_KEY")
api_secret = os.getenv("X_SECRET_KEY")
access_token = os.getenv("X_ACCESS_TOKEN")
access_secret = os.getenv("X_ACCESS_SECRET")

# Tweepy Client (v2 için)
client = tweepy.Client(
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_secret
)

def post_deneme_tweet():
    try:
        print(f"{datetime.now()}: Kullanıcı bilgilerini çekiyor...")
        user = client.get_me()
        print(f"{datetime.now()}: Kullanıcı: {user.data.username}")

        tweet_text = f"Deneme tweet'i! #BAETrends"
        print(f"{datetime.now()}: Tweet atılıyor: {tweet_text}")
        client.create_tweet(text=tweet_text)
        print(f"{datetime.now()}: Tweet atıldı: {tweet_text}")
    except Exception as e:
        print(f"{datetime.now()}: Hata oluştu: {str(e)}")

if __name__ == "__main__":
    post_deneme_tweet()
    # Test sonrası döngüyü aktif etmek için:
    # while True:
    #     post_deneme_tweet()
    #     time.sleep(8 * 3600)  # 8 saat

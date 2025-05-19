import tweepy
import os
import time
from datetime import datetime

# Heroku Config Vars'tan anahtarları al
api_key = os.getenv("X_API_KEY")
api_secret = os.getenv("X_SECRET_KEY")
access_token = os.getenv("X_ACCESS_TOKEN")
access_secret = os.getenv("X_ACCESS_SECRET")

# Tweepy OAuth 1.0a ile kimlik doğrulama
auth = tweepy.OAuthHandler(api_key, api_secret)
auth.set_access_token(access_token, access_secret)
api = tweepy.API(auth, wait_on_rate_limit=True)

def post_deneme_tweet():
    try:
        print(f"{datetime.now()}: Kullanıcı bilgilerini çekiyor...")
        user = api.verify_credentials()
        print(f"{datetime.now()}: Kullanıcı: {user.screen_name}")

        tweet_text = f"Deneme tweet'i! #BAETrends"
        print(f"{datetime.now()}: Tweet atılıyor: {tweet_text}")
        api.update_status(status=tweet_text)
        print(f"{datetime.now()}: Tweet atıldı: {tweet_text}")
    except Exception as e:
        print(f"{datetime.now()}: Hata oluştu: {str(e)}")

if __name__ == "__main__":
    post_deneme_tweet()
    # Test sonrası döngüyü aktif etmek için:
    # while True:
    #     post_deneme_tweet()
    #     time.sleep(8 * 3600)  # 8 saat

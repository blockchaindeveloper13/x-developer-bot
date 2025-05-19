import tweepy
import os
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

# BAE'nin WOEID'si (Where On Earth ID)
BAE_WOEID = 1940345  # BAE için WOEID

def post_trends_tweet():
    try:
        # Trend topic'leri çek (cache olmadan, taze veri)
        trends = api.get_place_trends(BAE_WOEID)
        top_trends = [trend["name"] for trend in trends[0]["trends"][:5]]  # İlk 5 TT

        # Botun kendi hesabının sabitlenmiş tweet'ini al
        user = api.verify_credentials()
        pinned_tweet = None
        for tweet in api.user_timeline(user_id=user.id, count=10):
            if tweet.pinned:
                pinned_tweet = tweet
                break

        # Alıntı tweet oluştur
        if pinned_tweet:
            trends_text = " ".join(top_trends)  # TT'leri birleştir
            quote_url = f"https://x.com/{user.screen_name}/status/{pinned_tweet.id}"
            tweet_text = f"Güncel BAE Trend Topic'leri: {trends_text} #BAETrends"

            # Alıntı tweet at
            api.update_status(
                status=tweet_text,
                attachment_url=quote_url
            )
            print(f"{datetime.now()}: Alıntı tweet atıldı: {tweet_text}")
        else:
            print(f"{datetime.now()}: Sabitlenmiş tweet bulunamadı.")
    except Exception as e:
        print(f"{datetime.now()}: Hata oluştu: {str(e)}")

if __name__ == "__main__":
    post_trends_tweet()

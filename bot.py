import os
import requests
import feedparser
import json
import time
from google import genai

# Configuration Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Configuration Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def get_news():
    articles = []
    
    # 1. L'API Crypto (Timeout de 10s max)
    try:
        url = "https://cryptocurrency.cv/api/news?limit=5"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            for art in response.json().get("articles", []):
                articles.append({"title": art.get("title"), "link": art.get("link")})
    except Exception as e:
        print(f"API Crypto HS : {e}")

    # 2. Google News (On ne prend que 2 news par catégorie pour aller vite)
    urls = [
        "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
    ]
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]: # On ne prend que les 2 premières
                articles.append({"title": entry.title, "link": entry.link})
        except Exception as e:
            print(f"Erreur RSS : {e}")

    # FILTRE : On supprime les news de trading
    bad_keywords = ["price", "analysis", "forecast", "trading", "technical", "chart", "ether", "bitcoin", "xrp", "solana"]
    clean_articles = []
    for art in articles:
        title_lower = art["title"].lower()
        if not any(bad_word in title_lower for bad_word in bad_keywords):
            clean_articles.append(art)
            
    # On ne garde que les 5 premières news max pour la vitesse
    return clean_articles[:5]

def analyze_and_generate(title):
    prompt = f"""Tu es un trader de memecoins expert. Analyse ce titre : "{title}"
RÈGLES : Si c'est de la finance ou politique lourde, renvoie : {{"tokens": []}}
Si c'est People, Sport US, Tech ou absurde, génère 3 memecoins en JSON strict :
{{"tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, {{"name": "Nom", "ticker": "$TICKER"}}, {{"name": "Nom", "ticker": "$TICKER"}}]}}
"""
    try:
        # Utilisation de gemini-2.0-flash (le modèle stable actuel)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        result = json.loads(response.text)
        return result.get("tokens", [])
    except Exception as e:
        print(f"Erreur IA : {e}")
        return []

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def main():
    articles = get_news()
    print(f"🔎 Analyse des {len(articles)} meilleures news (max 5 pour la vitesse)...")

    for article in articles:
        title = article["title"]
        link = article["link"]
        print(f"Traitement : {title}")

        tokens = analyze_and_generate(title)
        
        # Petite pause de 2 secondes pour ne pas surcharger l'API gratuite
        time.sleep(2) 
        
        if not tokens:
            continue

        message = f"🚨 *SIGNAL HYPE DÉTECTÉ* 🚨\n\n"
        message += f"*{title}*\n"
        message += f"[Lien de la news]({link})\n\n"
        message += f"💡 *Tokens à sniper :*\n"
        
        for t in tokens:
            message += f"• *{t['name']}* (`{t['ticker']}`)\n"

        send_to_telegram(message)
        print(f"✅ Message envoyé !")

if __name__ == "__main__":
    main()

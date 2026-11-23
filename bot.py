import os
import requests
import feedparser
import json
from google import genai

# Configuration Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Configuration Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

def get_news():
    articles = []
    
    # 1. L'API Crypto
    try:
        url = "https://cryptocurrency.cv/api/news?limit=5"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            for art in response.json().get("articles", []):
                articles.append({"title": art.get("title"), "link": art.get("link")})
    except Exception as e:
        print(f"API Crypto HS (on continue) : {e}")

    # 2. Google News (People, Sport, Tech)
    urls = [
        "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
    ]
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]: 
                articles.append({"title": entry.title, "link": entry.link})
        except Exception as e:
            print(f"Erreur RSS {url} : {e}")

    # PRÉ-FILTRE "BÉTON"
    bad_keywords = ["price", "analysis", "forecast", "trading", "technical", "chart", "ether", "bitcoin", "xrp", "solana"]
    clean_articles = []
    for art in articles:
        title_lower = art["title"].lower()
        if not any(bad_word in title_lower for bad_word in bad_keywords):
            clean_articles.append(art)
    return clean_articles

def analyze_and_generate(title):
    prompt = f"""Tu es un trader de memecoins de génie sur Twitter. 
Analyse ce titre de news US : "{title}"

RÈGLES :
1. Si la news parle de célébrité (Miley, Drake, Taylor), de sport US (NFL, NBA), de tech (Elon, Apple), ou d'un fait divers absurde, c'est un EXCELLENT candidat pour un memecoin.
2. Si c'est de la politique lourde (élections), de la guerre, ou de la finance, c'est NUL.

Si c'est NUL, renvoie un JSON vide : {{"tokens": []}}
Si c'est EXCELLENT, génère 3 memecoins. Format JSON strict :
{{"tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, {{"name": "Nom", "ticker": "$TICKER"}}, {{"name": "Nom", "ticker": "$TICKER"}}]}}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "object",
                    "properties": {
                        "tokens": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "ticker": {"type": "string"}
                                },
                                "required": ["name", "ticker"]
                            }
                        }
                    },
                    "required": ["tokens"]
                }
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
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def main():
    articles = get_news()
    print(f"🔎 Analyse de {len(articles)} news ultra-filtrées...")

    for article in articles:
        title = article["title"]
        link = article["link"]
        tokens = analyze_and_generate(title)
        
        if not tokens:
            continue

        message = f"🚨 *SIGNAL HYPE DÉTECTÉ* 🚨\n\n"
        message += f"*{title}*\n"
        message += f"[Lien de la news]({link})\n\n"
        message += f"💡 *Tokens à sniper :*\n"
        for t in tokens:
            message += f"• *{t['name']}* (`{t['ticker']}`)\n"

        send_to_telegram(message)
        print(f"✅ Message envoyé pour : {title}")

if __name__ == "__main__":
    main()

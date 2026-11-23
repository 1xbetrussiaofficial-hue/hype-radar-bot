import os
import requests
import feedparser
from openai import OpenAI

# Configuration Telegram
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Configuration GitHub Models (IA Puissante et Gratuite)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=GITHUB_TOKEN,
)

def get_news():
    articles = []
    
    # 1. L'API Crypto (avec gestion d'erreur stricte)
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
            for entry in feed.entries[:4]: # On prend les 4 premières de chaque
                articles.append({"title": entry.title, "link": entry.link})
        except Exception as e:
            print(f"Erreur RSS {url} : {e}")

    # PRÉ-FILTRE "BÉTON" : On rejette les news de trading/finance inutiles avant l'IA
    bad_keywords = ["price", "analysis", "forecast", "trading", "technical", "chart", "ether", "bitcoin", "xrp", "solana"]
    clean_articles = []
    
    for art in articles:
        title_lower = art["title"].lower()
        if not any(bad_word in title_lower for bad_word in bad_keywords):
            clean_articles.append(art)
            
    return clean_articles

def analyze_and_generate(title):
    """Utilise GPT-4o-mini via GitHub Models pour une analyse parfaite."""
    
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
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Le modèle ultra-puissant de GitHub
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={ "type": "json_object" } # Force l'IA à répondre en JSON
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
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
        
        # Si l'IA a jugé que c'était nul, elle renvoie une liste vide, on passe.
        if not tokens:
            continue

        # Si on a des tokens, on envoie le message
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

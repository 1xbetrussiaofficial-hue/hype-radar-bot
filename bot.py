import os
import requests
import feedparser
import json
import sys

# Force l'affichage des logs
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_news():
    """Récupère les news et extrait l'image originale."""
    articles = []
    rss_urls = [
        "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
        "https://tmz.com/rss.xml"
    ]
    
    # On ignore juste les promos
    bad_keywords = ["black friday", "deal", "sale", "discount", "price", "stock", "market"]
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = entry.title
                
                if any(keyword in title.lower() for keyword in bad_keywords):
                    continue
                
                image_url = None
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url')
                elif hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                    if 'image' in entry.enclosures[0].get('type', ''):
                        image_url = entry.enclosures[0].get('href')
                elif hasattr(entry, 'links'):
                    for link in entry.links:
                        if 'image' in link.get('type', ''):
                            image_url = link.get('href')
                            break
                            
                articles.append({"title": title, "link": entry.link, "image_url": image_url})
        except Exception as e:
            print(f"Erreur lecture RSS {url} : {e}")
            
    return articles

def is_viral_news(title):
    """L'IA accepte le People par défaut, rejette la politique/finance."""
    prompt = f"""Tu es un expert en tendances sur Twitter. Analyse ce titre : "{title}"
    
RÈGLE : Si la news parle de célébrités (People), de clash, de scandale, de films, ou de tech, c'est un OUI (score 9).
Si c'est de la politique lourde, de la finance, de la météo ou des matchs de sport basiques, c'est un NON (score 1).

Réponds UNIQUEMENT en JSON : {{"score": 9}} ou {{"score": 1}}
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, # On baisse la température pour qu'il soit plus déterministe
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return False
        data = response.json()
        result = json.loads(data["choices"][0]["message"]["content"])
        return result.get("score", 0) >= 8
    except Exception as e:
        return False

def send_to_telegram(title, link, image_url):
    """Envoie la news avec l'image originale."""
    caption = f"🚨 *BUZZ VIRAL DÉTECTÉ* 🚨\n\n*{title}*\n\n[Lire l'article]({link})"
    
    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                print("✅ News avec image envoyée !")
                return
        except Exception:
            pass 

    # Si l'image échoue ou n'existe pas
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
        print("✅ News texte envoyée !")
    except Exception as e:
        print(f"Erreur envoi texte : {e}")

def main():
    articles = get_news()
    if not articles: return

    print(f"🔎 Analyse de {len(articles)} news...")
    signaux_envoyes = 0

    for article in articles:
        if signaux_envoyes >= 5: # On envoie max 5 news par heure pour ne pas spammer
            break

        title = article["title"]
        print(f"🧐 Analyse : {title}")
        
        if is_viral_news(title):
            send_to_telegram(title, article["link"], article["image_url"])
            signaux_envoyes += 1
        else:
            print("❌ Ignoré.")

if __name__ == "__main__":
    main()

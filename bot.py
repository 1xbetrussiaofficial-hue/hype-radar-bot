import os
import requests
import feedparser
import json
import sys
import re

# Force l'affichage des logs
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_og_image(url):
    """Extrait l'image originale de l'article (Règle 3)."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        # Regex pour trouver l'image principale de l'article
        match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', res.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def get_news():
    """Récupère les news Crypto, Tech, Business et US (Règle 1)."""
    articles = []
    rss_urls = [
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://www.coindesk.com/arc/outboundfeeds/rss/" # Source Crypto pure
    ]
    
    # BLACKLIST STRICTE (Règle 1)
    banned_words = [
        "taylor swift", "kardashian", "britney", "spears", "movie", "cinema", 
        "album", "music", "reality tv", "concert", "actor", "actress", "hollywood",
        "celebrity", "entertainment"
    ]
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]: # On regarde 10 news par flux
                title = entry.title
                
                # Si un mot interdit est dans le titre, on passe
                if any(word in title.lower() for word in banned_words):
                    continue
                
                # On cherche l'image dans le flux RSS
                image_url = None
                if hasattr(entry, 'media_content') and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url')
                elif hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                    if 'image' in entry.enclosures[0].get('type', ''):
                        image_url = entry.enclosures[0].get('href')
                            
                articles.append({"title": title, "link": entry.link, "image_url": image_url})
        except Exception as e:
            print(f"Erreur lecture RSS {url} : {e}")
            
    return articles

def analyze_news(title):
    """L'IA filtre et génère le nom/ticker (Règles 1 et 2)."""
    prompt = f"""Tu es un expert en memecoins sur Solana. Analyse ce titre : "{title}"

RÈGLE 1 : Si c'est du people, de la musique ou du cinéma, réponds : {{"is_good": false}}
RÈGLE 2 : Si c'est Crypto, Tech, Politique US, ou Scandale financier, c'est OUI. Explique en 1 phrase courte "pourquoi ça marche" (ex: "Panique boursière", "Trump", "Hack").
RÈGLE 3 : Génère 1 seul nom de token (max 3 mots) très accrocheur, et 1 Ticker (4 à 5 lettres max avec un $). Exemple : {{"name": "Save Jensen", "ticker": "$SAVE"}}

Format JSON STRICT :
Si c'est mauvais : {{"is_good": false}}
Si c'est bon : {{"is_good": true, "why": "Explication", "name": "Nom", "ticker": "$TICK"}}
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return None
            
        data = response.json()
        result = json.loads(data["choices"][0]["message"]["content"])
        
        if result.get("is_good") == True:
            return result
        return None
    except Exception as e:
        print(f"Erreur IA : {e}")
        return None

def send_to_telegram(title, link, image_url, ai_data):
    """Envoie le message formaté (Règle 4)."""
    
    # Formatage exact demandé
    caption = f"🚨 *ALERTE MEMECOIN* 🚨\n"
    caption += f"*La News :* {title}\n"
    caption += f"*Pourquoi ça marche :* {ai_data['why']}\n\n"
    caption += f"💡 *Création du Token :*\n"
    caption += f"*Nom :* {ai_data['name']}\n"
    caption += f"*Ticker :* {ai_data['ticker']}\n\n"
    caption += f"🔗 [Lien de l'article]({link})"
    
    # Si l'image n'est pas dans le flux, on va la chercher (Règle 3)
    if not image_url:
        image_url = get_og_image(link)

    if image_url:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=15)
            if res.status_code == 200:
                print("✅ Alerte envoyée avec image !")
                return
        except Exception:
            pass 

    # Fallback texte si pas d'image
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=15)
        print("✅ Alerte envoyée (texte seul).")
    except Exception as e:
        print(f"Erreur envoi texte : {e}")

def main():
    articles = get_news()
    if not articles: return

    print(f"🔎 Analyse de {len(articles)} news...")
    alertes_envoyees = 0

    for article in articles:
        if alertes_envoyees >= 5: # Max 5 alertes par run
            break

        title = article["title"]
        
        # L'IA filtre et génère
        ai_data = analyze_news(title)
        
        if ai_data:
            send_to_telegram(title, article["link"], article["image_url"], ai_data)
            alertes_envoyees += 1
        else:
            print(f"❌ Ignoré (pas de potentiel memecoin) : {title}")

if __name__ == "__main__":
    main()

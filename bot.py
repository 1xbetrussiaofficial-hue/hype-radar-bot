import os
import requests
import feedparser
import json
import urllib.parse

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_news():
    """Récupère les news les plus virales via des flux RSS ciblés."""
    articles = []
    rss_urls = [
        "https://tmz.com/rss.xml",
        "https://nypost.com/entertainment/feed/",
        "http://www.espn.com/espn/rss/news"
    ]
    
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                articles.append({"title": entry.title, "link": entry.link})
        except Exception as e:
            print(f"Erreur lecture RSS {url} : {e}")
            
    return articles

def analyze_and_generate(title):
    """Filtre la news et génère des noms de tokens pertinents avec Groq."""
    prompt = f"""Tu es un trader de memecoins expert. Analyse cette news US : "{title}"

RÈGLES STRICTES :
1. Si la news est ennuyeuse (finance, trading, politique lourde, match de sport de saison régulière), réponds UNIQUEMENT : {{"score": 1, "tokens": []}}
2. Si la news est un vrai buzz (people, clash, célébrité, tech, fait divers absurde), note son potentiel sur 10 et génère 3 noms de tokens en lien DIRECT avec la news.

Format JSON STRICT :
Si buzz : {{"score": 9, "tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, ...]}}
Si ennuyeux : {{"score": 1, "tokens": []}}
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erreur API Groq : {response.text}")
            return None
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        
        if result.get("score", 0) >= 8:
            return result.get("tokens", [])
        return None
    except Exception as e:
        print(f"Erreur IA : {e}")
        return None

def generate_meme_image(trend_title, token_name):
    """Génère une image de mème via memegen.link (gratuit, sans clé, sans limite)."""
    try:
        # On utilise le template "drake" pour un rendu classique et drôle
        template = "drake"
        # Nettoyage des textes pour qu'ils soient valides dans l'URL
        top_text = urllib.parse.quote("Ignorer le buzz")
        bottom_text = urllib.parse.quote(f"Lancer {token_name} sur '{trend_title[:30]}...'")
        
        image_url = f"https://api.memegen.link/images/{template}/{top_text}/{bottom_text}.png"
        
        print(f"🎨 Génération du mème : {image_url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Erreur génération mème : {e}")
        return None

def send_photo_to_telegram(photo_bytes, caption):
    """Envoie l'image et le texte sur Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    files = {'photo': ('meme.png', photo_bytes, 'image/png')}
    data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}
    
    try:
        response = requests.post(url, files=files, data=data, timeout=30)
        if response.status_code == 200:
            print("✅ Image et message envoyés avec succès !")
        else:
            print(f"Erreur envoi Telegram : {response.text}")
    except Exception as e:
        print(f"Erreur envoi photo : {e}")

def main():
    articles = get_news()
    if not articles:
        print("Aucune news récupérée.")
        return

    print(f"🔎 Analyse de {len(articles)} news...")

    for article in articles:
        title = article["title"]
        link = article["link"]
        
        tokens = analyze_and_generate(title)
        
        if not tokens:
            print(f"❌ News ignorée : {title}")
            continue

        # Construction du message texte
        caption = f"🚨 *SIGNAL HYPE* 🚨\n\n"
        caption += f"*{title}*\n"
        caption += f"[Lire l'article]({link})\n\n"
        caption += f"💡 *Tokens suggérés :*\n"
        for t in tokens:
            caption += f"• *{t['name']}* (`{t['ticker']}`)\n"
        
        # On utilise le premier token pour le mème
        first_token_name = tokens[0]['name']
        image_bytes = generate_meme_image(title, first_token_name)
        
        if image_bytes:
            send_photo_to_telegram(image_bytes, caption)
        else:
            print("Envoi du texte seul (image échouée).")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()

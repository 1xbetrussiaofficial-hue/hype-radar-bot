import os
import requests
import feedparser
import json
import urllib.parse
import time

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

def generate_meme_image(prompt):
    """Génère une image via l'endpoint public de Pollinations (gratuit)."""
    encoded_prompt = urllib.parse.quote(prompt)
    # Utilisation de l'URL publique qui fonctionne sans clé
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true"
    
    print(f"🎨 Génération de l'image pour : {prompt}")
    try:
        # User-Agent pour éviter d'être bloqué par le serveur
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(image_url, headers=headers, timeout=60)
        response.raise_for_status()
        return response.content 
    except Exception as e:
        print(f"Erreur génération image : {e}")
        return None

def send_photo_to_telegram(photo_bytes, caption):
    """Envoie l'image et le texte sur Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    files = {'photo': ('meme.jpg', photo_bytes, 'image/jpeg')}
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
        
        # Génération du prompt pour l'image
        image_prompt = f"A funny crypto meme coin illustration about {title}, featuring {tokens[0]['name']}, vibrant colors, internet culture style"
        image_bytes = generate_meme_image(image_prompt)
        
        if image_bytes:
            send_photo_to_telegram(image_bytes, caption)
            # Pause de 15 secondes obligatoire pour respecter la limite de l'API gratuite
            time.sleep(15)
        else:
            print("Envoi du texte seul (image échouée).")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()

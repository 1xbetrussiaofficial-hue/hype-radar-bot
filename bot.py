import os
import requests
import json
import urllib.parse
import urllib.request
from io import BytesIO

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_news():
    """Récupère les news les plus virales via des flux RSS ciblés."""
    articles = []
    rss_urls = [
        "https://tmz.com/rss.xml", # People / Scandales
        "https://nypost.com/entertainment/feed/", # Divertissement
        "http://www.espn.com/espn/rss/news" # Sport US (filtré ensuite)
    ]
    
    for url in rss_urls:
        try:
            response = requests.get(url, timeout=10)
            # On parse le flux RSS manuellement (simple et sans dépendance)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:5]: # 5 par flux
                title = item.find('title').text
                link = item.find('link').text
                articles.append({"title": title, "link": link})
        except Exception as e:
            print(f"Erreur lecture RSS {url} : {e}")
            
    return articles

def analyze_and_generate(title):
    """Filtre la news et génère des noms de tokens pertinents avec Groq."""
    prompt = f"""Tu es un trader de memecoins expert. Analyse cette news US : "{title}"

RÈGLES STRICTES :
1. Si la news est ennuyeuse (finance, trading, match de sport de saison régulière, politique lourde), réponds UNIQUEMENT : {{"score": 1, "tokens": []}}
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
        "model": "openai/gpt-oss-120b", # Modèle puissant pour la pertinence
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            print(f"Erreur API Groq : {response.text}")
            return None
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        
        # On ne garde que si le score est élevé
        if result.get("score", 0) >= 8:
            return result.get("tokens", [])
        return None
    except Exception as e:
        print(f"Erreur IA : {e}")
        return None

def generate_meme_image(prompt):
    """Génère une image de meme via Pollinations.ai (gratuit, sans clé)."""
    encoded_prompt = urllib.parse.quote(prompt)
    # Format carré 1:1 pour Pump.fun
    image_url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width=1024&height=1024&model=flux"
    
    print(f"🎨 Génération de l'image : {image_url}")
    try:
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        return response.content # Renvoie les bytes de l'image
    except Exception as e:
        print(f"Erreur génération image : {e}")
        return None

def send_photo_to_telegram(photo_bytes, caption):
    """Envoie une image via l'API sendPhoto de Telegram (multipart/form-data)."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    # Construction du corps multipart/form-data manuellement
    boundary = "----HypeRadarBoundary"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{CHAT_ID}\r\n'.encode()
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode()
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="photo"; filename="meme.jpg"\r\n'.encode()
    body += b'Content-Type: image/jpeg\r\n\r\n'
    body += photo_bytes
    body += f"\r\n--{boundary}--\r\n".encode()
    
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        urllib.request.urlopen(req, timeout=30)
        print("✅ Image envoyée avec succès !")
    except Exception as e:
        print(f"Erreur envoi photo Telegram : {e}")

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
        
        # Génération du prompt pour l'image (basé sur le premier token)
        image_prompt = f"A funny meme coin illustration about {title}, featuring {tokens[0]['name']}, crypto style, 1:1 square"
        image_bytes = generate_meme_image(image_prompt)
        
        if image_bytes:
            send_photo_to_telegram(image_bytes, caption)
        else:
            # Fallback : envoi du texte seul si l'image échoue
            print("Envoi du texte seul (image échouée).")
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"})

if __name__ == "__main__":
    main()

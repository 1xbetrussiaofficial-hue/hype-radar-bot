import os
import requests
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
    """Extrait l'image originale de l'article."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', res.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def get_news():
    """Récupère UNIQUEMENT des news Crypto via l'API dédiée."""
    articles = []
    try:
        # L'API crypto fiable
        url = "https://cryptocurrency.cv/api/news?limit=15"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for art in data.get("articles", []):
                title = art.get("title", "")
                
                # Mots-clés OBLIGATOIRES pour que ce soit du memecoin (Hack, SEC, Elon, etc.)
                # Si la news ne contient pas au moins un de ces mots, on la jette.
                must_have = ["hack", "scam", "sec", "elon", "musk", "trump", "lawsuit", "ban", "solana", "rug", "crash", "surge", "etf", "binance", "coinbase", "exploit", "whale"]
                
                if not any(word in title.lower() for word in must_have):
                    continue # On ignore les news tech basiques
                    
                # On ignore les prix/analyses classiques
                if any(word in title.lower() for word in ["price prediction", "technical analysis", "how to buy"]):
                    continue

                articles.append({
                    "title": title, 
                    "link": art.get("link"), 
                    "image_url": None # On la cherchera après
                })
    except Exception as e:
        print(f"Erreur API Crypto : {e}")
        
    return articles

def analyze_news(title):
    """L'IA génère le nom de memecoin degen."""
    prompt = f"""Tu es un trader de memecoins "degen" sur Solana.
Analyse ce titre : "{title}"

RÈGLE 1 (FILTRE) : Si la news n'est pas liée à la crypto (finance, hack, politique US, tech), réponds : {{"is_good": false}}
RÈGLE 2 (BUZZ) : Si c'est un Hack, une Faillite, un Scandale, une déclaration d'Elon Musk ou de Trump, ou une action de la SEC : c'est OUI. Explique "pourquoi ça marche" en 1 phrase courte (ex: "Hack de protocole", "Elon drama", "SEC attaque").
RÈGLE 3 (NOM) : Génère un nom de memecoin ULTRA DEGEN (max 3 mots) et un Ticker (4-5 lettres). Utilise le vocabulaire Crypto (Rekt, Fud, Dump, Moon, Inu, Chad).
Exemple : Si "Binance hacked" -> Nom: "BinanceRekt" | Ticker: "$REKT"

Format JSON STRICT :
Si mauvais : {{"is_good": false}}
Si bon : {{"is_good": true, "why": "Explication", "name": "Nom", "ticker": "$TICK"}}
"""
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6,
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
        return None

def send_to_telegram(title, link, ai_data):
    """Formatage parfait avec image."""
    caption = f"🚨 *ALERTE MEMECOIN* 🚨\n"
    caption += f"*La News :* {title}\n"
    caption += f"*Pourquoi ça marche :* {ai_data['why']}\n\n"
    caption += f"💡 *Création du Token :*\n"
    caption += f"*Nom :* {ai_data['name']}\n"
    caption += f"*Ticker :* {ai_data['ticker']}\n\n"
    caption += f"🔗 [Lien de l'article]({link})"
    
    # On va chercher l'image de l'article
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
    except Exception:
        pass

def main():
    articles = get_news()
    if not articles: 
        print("Aucune news crypto pertinente trouvée pour le moment.")
        return

    print(f"🔎 Analyse de {len(articles)} news crypto...")
    alertes_envoyees = 0

    for article in articles:
        if alertes_envoyees >= 5: # Max 5 alertes
            break

        title = article["title"]
        ai_data = analyze_news(title)
        
        if ai_data:
            send_to_telegram(title, article["link"], ai_data)
            alertes_envoyees += 1
        else:
            print(f"❌ Ignoré : {title}")

if __name__ == "__main__":
    main()

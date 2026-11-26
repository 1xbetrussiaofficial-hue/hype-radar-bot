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
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        res = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        match = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\'](.*?)["\']', res.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def check_dexscreener(ticker):
    clean_ticker = ticker.replace("$", "").upper()
    url = f"https://api.dexscreener.com/latest/dex/search?q={clean_ticker}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        pairs = data.get("pairs", [])
        
        if not pairs:
            return "🆕 *Token introuvable sur DexScreener.* (Tu es le premier !)"
            
        best_pair = max(pairs, key=lambda x: float(x.get("volume", {}).get("h24", 0) or 0))
        volume = float(best_pair.get("volume", {}).get("h24", 0) or 0)
        chain = best_pair.get("chainId", "Inconnue").capitalize()
        name = best_pair.get("baseToken", {}).get("name", "Inconnu")
        
        if volume > 10000:
            return f"🔥 *Déjà tendance !* {name} sur {chain} | Vol 24h: ${volume:,.0f}"
        else:
            return f"⚠️ *Token existant mais faible volume.* {name} sur {chain} | Vol 24h: ${volume:,.0f}"
            
    except Exception:
        return "❓ *Impossible de vérifier DexScreener.*"

def get_news():
    articles = []
    try:
        url = "https://cryptocurrency.cv/api/news?limit=15"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for art in data.get("articles", []):
                title = art.get("title", "")
                # On vire juste les analyses techniques pourries
                if any(word in title.lower() for word in ["price prediction", "technical analysis", "how to buy"]):
                    continue
                articles.append({"title": title, "link": art.get("link")})
    except Exception as e:
        print(f"Erreur API Crypto : {e}")
        
    return articles

def analyze_news(title):
    # L'IA fait le tri toute seule maintenant
    prompt = f"""Tu es un trader de memecoins "degen" sur Solana.
Analyse ce titre : "{title}"

RÈGLE 1 (FILTRE) : Si la news n'est pas liée à la crypto ou si c'est une news de finance classique, réponds : {{"is_good": false}}
RÈGLE 2 (BUZZ) : Si c'est un Hack, une Faillite, un Scandale, une action de la SEC, une annonce majeure, ou un drama Elon Musk/Trump : Explique "pourquoi ça marche" en 1 phrase courte.
RÈGLE 3 (NOM) : Génère un nom de memecoin ULTRA DEGEN (max 3 mots) et un Ticker (4-5 lettres). Utilise le vocabulaire Crypto (Rekt, Fud, Dump, Moon, Inu, Chad).
Exemple : "Binance hacked" -> Nom: "BinanceRekt" | Ticker: "$REKT"

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
    except Exception:
        return None

def send_to_telegram(title, link, ai_data):
    print(f"🔎 Vérification DexScreener pour {ai_data['ticker']}...")
    dex_data = check_dexscreener(ai_data['ticker'])

    caption = f"🚨 *ALERTE MEMECOIN* 🚨\n"
    caption += f"*La News :* {title}\n"
    caption += f"*Pourquoi ça marche :* {ai_data['why']}\n\n"
    caption += f"💡 *Création du Token :*\n"
    caption += f"*Nom :* {ai_data['name']}\n"
    caption += f"*Ticker :* {ai_data['ticker']}\n\n"
    caption += f"📊 *On-Chain Check :*\n{dex_data}\n\n"
    caption += f"🔗 [Lien de l'article]({link})"
    
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
        print("Aucune news trouvée par l'API.")
        return

    print(f"🔎 Analyse de {len(articles)} news...")
    alertes_envoyees = 0

    for article in articles:
        if alertes_envoyees >= 3: # Max 3 alertes
            break

        title = article["title"]
        print(f"🧐 Analyse : {title}")
        ai_data = analyze_news(title)
        
        if ai_data:
            send_to_telegram(title, article["link"], ai_data)
            alertes_envoyees += 1
        else:
            print(f"❌ Ignoré par l'IA.")

if __name__ == "__main__":
    main()

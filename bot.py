import os
import requests
import json
from trendspyg import download_google_trends_rss

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_real_trends():
    print("📡 Récupération des tendances Google US...")
    trends_list = []
    try:
        trends = download_google_trends_rss(geo='US')
        trends_list = [trend['trend'] for trend in trends]
        print(f"✅ {len(trends_list)} tendances trouvées.")
    except Exception as e:
        print(f"❌ Erreur Google Trends : {e}")
    
    return trends_list[:15] # On regarde 15 tendances pour trouver les 2 meilleures

def analyze_trend_with_ai(trend_title):
    # Le prompt "Sniper" : strict mais créatif
    prompt = f"""Tu es un trader de memecoins expert qui cherche le BUZZ absolu aux USA.
Voici une tendance de recherche : "{trend_title}"

Ta mission : Filtrer cette tendance.
- Si c'est un sujet majeur (People comme Taylor Swift, Sport US majeur comme la NFL/NBA, Tech comme Elon Musk, Politique absurde, Fait divers choquant), c'est un OUI. Génère 3 memecoins (Nom + Ticker).
- Si c'est un sujet de niche (match obscur, journaliste inconnu, finance ennuyeuse), c'est un NON. 

Format JSON STRICT :
Si OUI : {{"score": 9, "tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, ...]}}
Si NON : {{"score": 1, "tokens": []}}
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-oss-120b", 
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.6, # Un peu moins créatif, plus analytique
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        
        # On ne garde que si le score est élevé (8, 9 ou 10)
        if result.get("score", 0) >= 8:
            return result.get("tokens", [])
        return None
        
    except Exception as e:
        print(f"❌ Erreur IA : {e}")
        return None

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

def main():
    trends = get_real_trends()
    if not trends:
        return

    print(f"🔎 Scan de {len(trends)} tendances pour trouver le vrai buzz...")
    
    signals_envoyes = 0
    MAX_SIGNAUX = 2 # On s'arrête après 2 vrais signaux pour ne pas te spammer

    for trend in trends:
        if signals_envoyes >= MAX_SIGNAUX:
            print("✋ Limite de 2 signaux atteinte. Fin du scan.")
            break

        print(f"🧐 Analyse : {trend}")
        tokens = analyze_trend_with_ai(trend)
        
        if not tokens:
            print("   ⏭️ Ignoré (pas assez fort).")
            continue

        message = f"🚨 *SIGNAL HYPE MAXIMALE* 🚨\n\n"
        message += f"🔥 *Tendance US :* {trend}\n\n"
        message += f"💡 *Tokens à sniper :*\n"
        for t in tokens:
            message += f"• *{t['name']}* (`{t['ticker']}`)\n"

        send_to_telegram(message)
        signals_envoyes += 1
        print(f"   ✅ Signal envoyé !")

if __name__ == "__main__":
    main()

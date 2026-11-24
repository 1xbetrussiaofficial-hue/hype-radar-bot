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
    # Le prompt "Sniper" V2 : On cherche le drame et l'absurde, pas le sport normal
    prompt = f"""Tu es un trader de memecoins expert sur Crypto Twitter. Tu cherches le BUZZ ABSOLU.
Voici une tendance de recherche : "{trend_title}"

Ta mission : Filtrer cette tendance de manière EXTRÊMEMENT STRICTE.
- C'est un OUI (Score 9 ou 10) UNIQUEMENT si c'est : un clash entre célébrités, une déclaration folle d'Elon Musk ou Trump, un fait divers absurde, un scandale people, ou une tragédie qui fait tellement parler qu'elle en devient virale.
- C'est un NON (Score 1) si c'est : un match de sport normal (ex: NBA, NFL de saison régulière), une blessure de sportif, une news de journaliste inconnu, de la finance, ou de la politique lourde.

Si OUI, génère 3 memecoins (Nom + Ticker). 
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
        "temperature": 0.5, # Très analytique, pas de fantaisie inutile
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        
        # On ne garde que si le score est de 9 ou 10
        if result.get("score", 0) >= 9:
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
    MAX_SIGNAUX = 2

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

import os
import requests
import json
from trendspyg import download_google_trends_rss

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Endpoint de Groq
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def get_real_trends():
    """Récupère les vraies tendances de recherche aux US via Google Trends."""
    print("📡 Récupération des tendances Google US...")
    trends_list = []
    try:
        trends = download_google_trends_rss(geo='US')
        trends_list = [trend['trend'] for trend in trends]
        print(f"✅ {len(trends_list)} tendances trouvées.")
    except Exception as e:
        print(f"❌ Erreur Google Trends : {e}")
    
    return trends_list[:10]

def analyze_trend_with_ai(trend_title):
    """Demande à GPT-OSS 20B (via Groq) de noter le potentiel memecoin."""
    
    prompt = f"""Tu es un expert en memecoins qui chasse le buzz sur Twitter.
Voici une tendance de recherche actuelle aux USA : "{trend_title}"

Ta mission :
1. Note de 1 à 10 le potentiel de cette tendance pour créer un memecoin qui va exploser (buzz, émotion, actualité chaude).
2. Si la note est STRICTEMENT INFÉRIEURE à 8, réponds UNIQUEMENT : {{"tokens": []}}
3. Si la note est de 8, 9 ou 10, génère 3 memecoins. Donne un nom (max 2 mots) et un Ticker (3-5 lettres avec $).
Format JSON strict : {{"tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, ...]}}
"""
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-oss-20b", # Modèle gratuit et ultra-rapide
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Erreur API (code {response.status_code}) : {response.text}")
            return []
            
        data = response.json()
        
        if "choices" not in data:
            print(f"❌ Réponse inattendue : {data}")
            return []
            
        content = data["choices"][0]["message"]["content"]
        result = json.loads(content)
        return result.get("tokens", [])
        
    except Exception as e:
        print(f"❌ Erreur lors de l'appel IA : {e}")
        return []

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
        print("Aucune tendance récupérée. Fin du script.")
        return

    print(f"🔎 Analyse de {len(trends)} tendances avec l'IA...")

    for trend in trends:
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
        print(f"   ✅ Signal envoyé pour : {trend}")

if __name__ == "__main__":
    main()

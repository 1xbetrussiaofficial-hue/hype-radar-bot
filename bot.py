import os
import requests
from openai import OpenAI
from trendspyg import TrendReq
import json

# --- Configuration ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Client GitHub Models (utilise le GITHUB_TOKEN fourni automatiquement)
client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=os.environ.get("GITHUB_TOKEN"),
)

def get_real_trends():
    """Récupère les vraies tendances de recherche aux US via Google Trends."""
    print("📡 Récupération des tendances Google US...")
    trends_list = []
    try:
        # Initialisation de TrendReq (US)
        pytrends = TrendReq(hl='en-US', tz=360)
        # Récupère les tendances du jour aux USA
        trending_searches = pytrends.trending_searches(pn='united_states')
        trends_list = trending_searches[0].tolist()
        print(f"✅ {len(trends_list)} tendances trouvées.")
    except Exception as e:
        print(f"❌ Erreur Google Trends : {e}")
    
    # On ne garde que les 10 premières pour ne pas surcharger l'IA
    return trends_list[:10]

def analyze_trend_with_ai(trend_title):
    """Demande à GPT-4o-mini de noter le potentiel memecoin de la tendance."""
    
    prompt = f"""Tu es un expert en memecoins qui chasse le buzz sur Twitter.
Voici une tendance de recherche actuelle aux USA : "{trend_title}"

Ta mission :
1. Note de 1 à 10 le potentiel de cette tendance pour créer un memecoin qui va exploser (buzz, émotion, actualité chaude).
2. Si la note est STRICTEMENT INFÉRIEURE à 8, réponds UNIQUEMENT : {{"tokens": []}}
3. Si la note est de 8, 9 ou 10, génère 3 memecoins. Donne un nom (max 2 mots) et un Ticker (3-5 lettres avec $).
Format JSON strict : {{"tokens": [{{"name": "Nom", "ticker": "$TICKER"}}, ...]}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Modèle ultra-stable de GitHub Models
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        return result.get("tokens", [])
    except Exception as e:
        print(f"❌ Erreur IA : {e}")
        return []

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

def main():
    # 1. On récupère les vraies tendances
    trends = get_real_trends()
    
    if not trends:
        print("Aucune tendance récupérée. Fin du script.")
        return

    print(f"🔎 Analyse de {len(trends)} tendances avec l'IA...")

    # 2. On analyse chaque tendance
    for trend in trends:
        print(f"🧐 Analyse : {trend}")
        tokens = analyze_trend_with_ai(trend)
        
        # Si l'IA a jugé que c'était nul (note < 8), on passe
        if not tokens:
            print("   ⏭️ Ignoré (pas assez fort).")
            continue

        # 3. Si c'est bon, on envoie l'alerte
        message = f"🚨 *SIGNAL HYPE MAXIMALE* 🚨\n\n"
        message += f"🔥 *Tendance US :* {trend}\n\n"
        message += f"💡 *Tokens à sniper :*\n"
        for t in tokens:
            message += f"• *{t['name']}* (`{t['ticker']}`)\n"

        send_to_telegram(message)
        print(f"   ✅ Signal envoyé pour : {trend}")

if __name__ == "__main__":
    main()

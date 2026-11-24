import os
import requests
import freeaipi

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_news():
    """Récupère les news crypto (ton API d'origine)."""
    url = "https://cryptocurrency.cv/api/news?limit=5"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"Erreur récupération news : {e}")
        return []

def analyze_and_filter(title):
    """L'IA filtre la news. Si c'est nul, elle renvoie None."""
    prompt = f"""Tu es un trader de memecoins expert sur Crypto Twitter.
Analyse ce titre d'actualité : "{title}"

RÈGLES STRICTES :
1. Si c'est de la finance ennuyeuse, de l'analyse de trading (ex: Bitcoin price, XRP analysis), ou de la politique lourde : Réponds UNIQUEMENT par le mot : IGNORE
2. Si c'est un vrai buzz (People, Célébrité, Clash, Tech comme Elon Musk, Fait divers absurde) : Génère 3 concepts de memecoins.

Format si c'est un buzz (sans explication) :
Nom du Token ($TICKER)
Nom du Token ($TICKER)
Nom du Token ($TICKER)
"""
    try:
        response = freeaipi.chat(prompt)
        text_response = response.content if hasattr(response, 'content') else str(response)
        
        if "IGNORE" in text_response:
            print(f"❌ News ignorée : {title}")
            return None
            
        # On récupère les noms générés
        return [name.strip() for name in text_response.split("\n") if name.strip() and "$" in name][:3]
    except Exception as e:
        print(f"Erreur génération IA : {e}")
        return None

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
        print("✅ Message envoyé avec succès !")
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def main():
    articles = get_news()
    if not articles:
        print("Aucune news récupérée.")
        return

    print(f"🔎 Analyse de {len(articles)} news...")

    for article in articles:
        title = article.get("title", "Titre inconnu")
        link = article.get("link", "")
        
        # L'IA filtre ici
        names = analyze_and_filter(title)
        
        # Si l'IA a dit "IGNORE", on passe à la suite sans rien envoyer
        if not names:
            continue

        # Si c'est validé, on envoie le message
        message = f"🚨 *SIGNAL HYPE* 🚨\n\n"
        message += f"*{title}*\n"
        message += f"[Lire l'article]({link})\n\n"
        message += f"💡 *Tokens suggérés :*\n"
        for name in names:
            message += f"• `{name}`\n"

        send_to_telegram(message)

if __name__ == "__main__":
    main()

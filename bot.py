import os
import requests
import freeaipi
from telegram import Bot

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_news():
    url = "https://cryptocurrency.cv/api/news?limit=3"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"Erreur récupération news : {e}")
        return []

def generate_token_names(title):
    prompt = f"""Tu es un expert en memecoins. Basé sur ce titre d'actualité : "{title}"
Génère exactement 3 noms de tokens courts, mémorables et accrocheurs (max 3 mots chacun).
Format de réponse attendu : une liste simple, un nom par ligne, sans numérotation ni explication."""
    try:
        # On utilise freeaipi qui ne nécessite pas de clé API
        response = freeaipi.get_response(prompt)
        return [name.strip() for name in response.split("\n") if name.strip()][:3]
    except Exception as e:
        print(f"Erreur génération IA : {e}")
        return []

def send_to_telegram(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
        print("Message envoyé avec succès !")
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def main():
    articles = get_news()
    if not articles:
        print("Aucune news récupérée.")
        return

    for article in articles:
        title = article.get("title", "Titre inconnu")
        link = article.get("link", "")
        print(f"Traitement : {title}")

        names = generate_token_names(title)
        if not names:
            continue

        message = f"🚨 *News virale potentielle*\n\n"
        message += f"*{title}*\n"
        message += f"[Lire l'article]({link})\n\n"
        message += f"💡 *Noms de tokens suggérés :*\n"
        for name in names:
            message += f"• `{name}`\n"

        send_to_telegram(message)

if __name__ == "__main__":
    main()

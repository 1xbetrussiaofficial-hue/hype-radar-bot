import os
import requests
import freeaipi
import json

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_news():
    """Récupère un maximum de news (on va en prendre 10 pour laisser l'IA filtrer)."""
    # On demande 10 news au lieu de 3 pour avoir plus de choix
    url = "https://cryptocurrency.cv/api/news?limit=10"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
    except Exception as e:
        print(f"Erreur récupération news : {e}")
        return []

def analyze_and_generate(title):
    """L'IA note la news. Si elle est nulle, elle renvoie None. Si elle est top, elle génère les noms."""
    prompt = f"""Tu es un trader de memecoins expert qui chasse les tendances virales aux USA.
Analyse ce titre d'actualité : "{title}"

ÉTAPE 1 : Note de 1 à 10 le potentiel de cette news pour créer un memecoin qui va exploser (buzz actuel, émotion forte, tendance US).
ÉTAPE 2 : 
- Si la note est STRICTEMENT INFÉRIEURE à 8, réponds UNIQUEMENT par le mot : IGNORE
- Si la note est de 8, 9 ou 10, génère 3 concepts de memecoins. Pour chaque concept, donne un nom (max 2 mots) suivi d'un Ticker (3 à 5 lettres en majuscules avec un $).

Format attendu si la note est >= 8 (sans explication, juste ce format) :
Nom du Token ($TICKER)"""
    
    try:
        response = freeaipi.chat(prompt)
        text_response = response.content if hasattr(response, 'content') else str(response)
        
        # Si l'IA a jugé que c'était nul, on s'arrête là
        if "IGNORE" in text_response:
            print(f"❌ News ignorée (pas assez virale) : {title}")
            return None
            
        # Sinon, on récupère les noms
        return [name.strip() for name in text_response.split("\n") if name.strip() and "$" in name][:3]
    except Exception as e:
        print(f"Erreur génération IA : {e}")
        return None

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("✅ Message envoyé avec succès !")
        else:
            print(f"Erreur envoi Telegram : {response.text}")
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def main():
    # On récupère 10 news
    articles = get_news()
    if not articles:
        print("Aucune news récupérée.")
        return

    print(f"🔎 Analyse de {len(articles)} news en cours...")

    for article in articles:
        title = article.get("title", "Titre inconnu")
        link = article.get("link", "")

        # L'IA analyse et filtre
        names = analyze_and_generate(title)
        
        # Si l'IA a dit "IGNORE", on passe à la news suivante sans rien envoyer
        if not names:
            continue

        # Si on arrive ici, c'est que la news a eu au moins 8/10 !
        message = f"🔥 *ALERTE HYPE MAXIMALE* 🔥\n\n"
        message += f"*{title}*\n"
        message += f"[Lire l'article]({link})\n\n"
        message += f"💡 *Noms de tokens suggérés :*\n"
        for name in names:
            message += f"• `{name}`\n"

        send_to_telegram(message)

if __name__ == "__main__":
    main()

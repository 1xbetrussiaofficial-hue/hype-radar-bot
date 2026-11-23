import os
import requests
import freeaipi
import feedparser

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_news():
    """Récupère les news de plusieurs sources (Crypto + Buzz US)."""
    articles = []
    
    # 1. L'API Crypto
    try:
        url = "https://cryptocurrency.cv/api/news?limit=3"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            articles.extend(data.get("articles", []))
    except Exception as e:
        print(f"Erreur API Crypto (ignorée) : {e}")

    # 2. Google News US : Divertissement
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Divertissement : {e}")

    # 3. Google News US : Sports
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Sport : {e}")
        
    # 4. Google News US : Technologie
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]:
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Tech : {e}")

    return articles

def analyze_and_generate(title):
    """L'IA décide si la news est un bon meme ou pas."""
    prompt = f"""Tu es un expert en memecoins sur Twitter. Je vais te donner un titre de news US.
Ton but est de générer des noms de memecoins pour les news qui peuvent faire le buzz.

Les BONNES news pour un memecoin (Génère des noms) : Célébrités (Taylor Swift, Drake), Clashs, Sports US (NFL, NBA), Tech (Elon Musk, Apple, IA), Politique absurde, ou Faits divers bizarres. Sois généreux, on cherche du buzz !

Les MAUVAISES news (À IGNORER) : La finance ennuyeuse, les analyses de trading, la météo, les tragédies, les prix du pétrole.

Si la news est mauvaise, réponds UNIQUEMENT par le mot : IGNORE
Si la news est bonne, génère 3 concepts de memecoins. Donne un nom (max 2 mots) suivi d'un Ticker (3 à 5 lettres en majuscules avec un $).
Sois créatif et un peu absurde, comme sur Crypto Twitter !

Format attendu si la news est bonne (sans explication, juste ce format) :
Nom du Token ($TICKER)
Titre : "{title}"
"""
    
    try:
        response = freeaipi.chat(prompt)
        text_response = response.content if hasattr(response, 'content') else str(response)
        
        if "IGNORE" in text_response:
            print(f"❌ Ignorée : {title}")
            return None
            
        return [name.strip() for name in text_response.split("\n") if name.strip() and "$" in name][:3]
    except Exception as e:
        print(f"Erreur IA : {e}")
        return None

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def main():
    articles = get_news()
    if not articles:
        print("Aucune news récupérée.")
        return

    print(f"🔎 Analyse de {len(articles)} news en cours (Crypto + People + Sport + Tech)...")

    for article in articles:
        title = article.get("title", "Titre inconnu")
        link = article.get("link", "")

        names = analyze_and_generate(title)
        
        if not names:
            continue

        message = f"🔥 *ALERTE HYPE MAXIMALE* 🔥\n\n"
        message += f"*{title}*\n"
        message += f"[Lire l'article]({link})\n\n"
        message += f"💡 *Noms de tokens suggérés :*\n"
        for name in names:
            message += f"• `{name}`\n"

        send_to_telegram(message)

if __name__ == "__main__":
    main()

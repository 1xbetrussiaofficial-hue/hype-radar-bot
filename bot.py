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

    # 2. Google News US : Divertissement (People, Célébrités)
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]: # On prend les 3 premières
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Divertissement : {e}")

    # 3. Google News US : Sports
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]: # On prend les 3 premières
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Sport : {e}")
        
    # 4. Google News US : Technologie (Elon Musk, IA, Apple...)
    try:
        rss_url = "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:3]: # On prend les 3 premières
            articles.append({"title": entry.title, "link": entry.link})
    except Exception as e:
        print(f"Erreur Google Tech : {e}")

    return articles

def analyze_and_generate(title):
    """L'IA note la news. Si elle est nulle, elle renvoie None."""
    prompt = f"""Tu es un trader de memecoins expert qui chasse les tendances virales aux USA.
Analyse ce titre d'actualité : "{title}"

ÉTAPE 1 : Note de 1 à 10 le potentiel de cette news pour créer un memecoin qui va faire le buzz (People, Sport, Tech, Clash, Absurdité).
ÉTAPE 2 : 
- Si la note est STRICTEMENT INFÉRIEURE à 8, réponds UNIQUEMENT par le mot : IGNORE
- Si la note est de 8, 9 ou 10, génère 3 concepts de memecoins. Pour chaque concept, donne un nom (max 2 mots) suivi d'un Ticker (3 à 5 lettres en majuscules avec un $).

Format attendu si la note est >= 8 (sans explication, juste ce format) :
Nom du Token ($TICKER)"""
    
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

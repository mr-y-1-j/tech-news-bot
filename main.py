import os
import requests
import google.generativeai as genai
import time

# 設定
WEBHOOK_TECH = os.environ.get("DISCORD_WEBHOOK_URL_TECH", "")
WEBHOOK_STOCK = os.environ.get("DISCORD_WEBHOOK_URL_STOCK", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 設定: 確実に存在するモデル名を使用
MODEL_NAME = "gemini-flash-latest"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)

def get_hacker_news(min_score=100, limit=3):
    print("Fetching Hacker News...")
    try:
        top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
        stories = []
        for story_id in top_ids[:50]:
            if len(stories) >= limit: break
            s = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            if s.get("score", 0) >= min_score and "url" in s:
                stories.append({"title": s["title"], "url": s["url"], "score": s["score"], "type": "Tech"})
        return stories
    except Exception as e:
        print(f"Error fetching HN: {e}")
        return []

def get_reddit_investing(min_score=100, limit=3):
    print("Fetching Reddit Investing...")
    url = "https://www.reddit.com/r/stocks/hot.json?limit=15"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers).json()
        posts = []
        for post in res['data']['children']:
            data = post['data']
            if data.get('score', 0) >= min_score and not data.get('is_self'):
                posts.append({"title": data['title'], "url": data['url'], "score": data['score'], "type": "Stock"})
            if len(posts) >= limit: break
        return posts
    except Exception as e:
        print(f"Error fetching Reddit: {e}")
        return []

def summarize(item):
    category = "株式投資家" if item['type'] == "Stock" else "テックリサーチャー"
    prompt = f"以下の記事を{category}の視点で要約して。\nタイトル: {item['title']}\nURL: {item['url']}\n1行目:核心、2行目:影響・示唆"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return f"⚠️ 要約エラー: {e}"

def send_embed(item, summary):
    color = 3066993 if item['type'] == "Stock" else 3447003
    webhook_url = WEBHOOK_STOCK if item['type'] == "Stock" else WEBHOOK_TECH
    
    if not webhook_url:
        print(f"Skipping {item['type']} notification: No Webhook URL.")
        return

    payload = {
        "embeds": [{
            "title": f"{item['title']}",
            "url": item['url'],
            "description": summary,
            "color": color,
            "fields": [
                {"name": "注目度", "value": f"🔥 {item['score']} pts", "inline": True},
                {"name": "カテゴリ", "value": f"📁 {item['type']}", "inline": True}
            ],
            "footer": {"text": f"Powered by {MODEL_NAME}"}
        }]
    }
    requests.post(webhook_url, json=payload)

def main():
    print(f"Starting News Bot with {MODEL_NAME}...")
    
    # ニュース取得
    news_list = get_hacker_news(limit=3) + get_reddit_investing(limit=3)
    
    if not news_list:
        print("No news found meeting the criteria.")
        # デバッグ用にDiscordに「ニュースなし」と通知しても良いが、一旦コンソールのみ
        return

    for item in news_list:
        summary = summarize(item)
        send_embed(item, summary)
        print(f"Sent: {item['title']}")
        time.sleep(5)

if __name__ == "__main__":
    main()

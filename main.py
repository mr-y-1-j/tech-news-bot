import os
import requests
import google.generativeai as genai
import time

# 設定
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 初期設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_hacker_news(min_score=100, limit=3):
    """テック系: Hacker Newsから取得"""
    print("Fetching Hacker News...")
    top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
    stories = []
    for story_id in top_ids[:50]: # 上位50件から探す
        if len(stories) >= limit: break
        s = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
        if s.get("score", 0) >= min_score and "url" in s:
            stories.append({"title": s["title"], "url": s["url"], "score": s["score"], "type": "Tech"})
    return stories

def get_reddit_investing(min_score=100, limit=3):
    """投資系: Reddit r/stocks から取得"""
    print("Fetching Reddit Investing...")
    # Reddit APIを簡易的に叩く（.jsonを付けると取得可能）
    url = "https://www.reddit.com/r/stocks/hot.json?limit=10"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers).json()
        posts = []
        for post in res['data']['children']:
            data = post['data']
            if data.get('score', 0) >= min_score and not data.get('is_self'): # URLありの記事
                posts.append({"title": data['title'], "url": data['url'], "score": data['score'], "type": "Stock"})
            if len(posts) >= limit: break
        return posts
    except:
        return []

def summarize(item):
    """Geminiで要約。投資用とテック用でプロンプトを分ける"""
    category = "株式投資家" if item['type'] == "Stock" else "テックリサーチャー"
    prompt = f"""
    あなたは優秀な{category}です。以下の記事を日本語で要約してください。
    
    タイトル: {item['title']}
    URL: {item['url']}
    タイプ: {item['type']}

    【出力形式】
    1行目: [ {item['type']} ] 日本語見出し (注目度:{item['score']})
    2行目: 核心（何が起きたか）を1行で
    3行目: 市場や技術への「影響・示唆」を投資家/技術者の視点で1行で
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"要約エラー (429回避中...): {e}"

def main():
    print("Starting Multi-Source Bot...")
    # テック3件、投資3件を目標に取得
    news_list = get_hacker_news(limit=3) + get_reddit_investing(limit=3)
    
    if not news_list:
        print("No viral news found.")
        return

    for item in news_list:
        summary = summarize(item)
        icon = "📈" if item['type'] == "Stock" else "💻"
        message = f"**{icon} {item['type']} News Update**\n{summary}\nOriginal: {item['url']}\n"
        
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print(f"Sent: {item['title']}. Waiting 30 seconds...")
        time.sleep(30) # 429エラーを徹底回避

if __name__ == "__main__":
    main()

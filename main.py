import os
import requests
import google.generativeai as genai
import time

# 設定の読み込み
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 起動チェック
if not DISCORD_WEBHOOK_URL.startswith("http"):
    raise ValueError("DISCORD_WEBHOOK_URL が未設定です。")

# Geminiの初期化 (旧SDK形式)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def get_viral_stories(min_score=100, max_count=5):
    print(f"Searching for stories with score > {min_score}...")
    top_ids = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
    viral_stories = []
    
    for story_id in top_ids:
        if len(viral_stories) >= max_count: break
        story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
        if story.get("score", 0) >= min_score and "url" in story:
            print(f"Found: [{story.get('score')}pts] {story.get('title')}")
            viral_stories.append(story)
    return viral_stories

def summarize_article(title, url, score):
    prompt = f"以下のテックニュースを日本語で要約して。1行目:見出し(スコア:{score}点)、2行目:核心、3行目:影響。\nタイトル: {title}\nURL: {url}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"要約エラー: {e}"

def main():
    print("Starting Tech News Bot (Stable Mode)...")
    stories = get_viral_stories(min_score=100, max_count=5)
    
    if not stories:
        print("No viral stories found.")
        return

    for story in stories:
        summary = summarize_article(story.get('title'), story.get('url'), story.get('score'))
        message = f"**🔥 Tech News Pickup**\n{summary}\nOriginal: {story.get('url')}\n------------------------"
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        print("Waiting 15 seconds...")
        time.sleep(30) # 429エラー回避

if __name__ == "__main__":
    main()

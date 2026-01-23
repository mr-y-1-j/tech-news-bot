import os
import requests
import google.generativeai as genai
import time

# 設定
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def get_top_stories(limit=5):
    """Hacker Newsのトップ記事IDを取得"""
    try:
        response = requests.get(HN_TOP_STORIES_URL)
        return response.json()[:limit]
    except Exception as e:
        print(f"Error fetching top stories: {e}")
        return []

def get_story_details(story_id):
    """記事の詳細データを取得"""
    try:
        response = requests.get(HN_ITEM_URL.format(story_id))
        return response.json()
    except Exception as e:
        print(f"Error fetching details for {story_id}: {e}")
        return None

def summarize_article(title, url):
    """Geminiで要約を作成"""
    prompt = f"""
    あなたは優秀なテックリサーチャーです。以下のHacker Newsの記事タイトルから、内容を推測し、
    日本の多忙なエンジニア向けに要約してください。

    タイトル: {title}
    URL: {url}

    【出力形式】
    1行目: 日本語のキャッチーな見出し (バズり度予測: S/A/B)
    2行目: どんな技術/ニュースなのか（簡潔に）
    3行目: 私たちにどんな影響があるか（推測でOK）
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"要約エラー: {e}"

def send_discord(content):
    """Discordに送信"""
    data = {"content": content}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

def main():
    print("Starting Tech News Bot...")
    story_ids = get_top_stories(limit=5) # トップ5件を取得
    
    for story_id in story_ids:
        story = get_story_details(story_id)
        if not story or "url" not in story:
            continue
            
        # 記事情報をコンソール出力（ログ用）
        print(f"Processing: {story.get('title')}")
        
        # 要約生成
        summary = summarize_article(story.get('title'), story.get('url'))
        
        # Discordへのメッセージ作成
        message = f"**Hacker News Pickup** 🚀\n{summary}\nOriginal: {story.get('url')}\n------------------------"
        
        # 送信
        send_discord(message)
        time.sleep(2) # 連投制限回避

if __name__ == "__main__":
    main()

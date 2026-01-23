import os
import requests
from google import genai
import time

# 設定の読み込み
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 起動チェック
if not DISCORD_WEBHOOK_URL.startswith("http"):
    raise ValueError("Error: DISCORD_WEBHOOK_URL が正しく設定されていません。GitHubのSecretsを確認してください。")

# Geminiの初期化
client = genai.Client(api_key=GEMINI_API_KEY)

def get_viral_stories(min_score=100, max_count=5):
    """
    Hacker Newsのトップ記事から、指定スコア以上のものを最大max_count件取得
    """
    print(f"Searching for stories with score > {min_score}...")
    top_ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    item_url = "https://hacker-news.firebaseio.com/v0/item/{}.json"
    
    top_ids = requests.get(top_ids_url).json()
    viral_stories = []
    
    # 上位から順にチェックし、条件に合うものを探す
    for story_id in top_ids:
        if len(viral_stories) >= max_count:
            break
            
        story = requests.get(item_url.format(story_id)).json()
        score = story.get("score", 0)
        
        if score >= min_score and "url" in story:
            print(f"Found: [{score}pts] {story.get('title')}")
            viral_stories.append(story)
            
    return viral_stories

def summarize_article(title, url, score):
    """Geminiで要約を作成"""
    prompt = f"""
    以下のテックニュースを日本語で要約してください。
    
    タイトル: {title}
    URL: {url}
    HackerNewsスコア: {score}

    【出力形式】
    1行目: 日本語の見出し (スコア:{score}点)
    2行目: ニュースの核心を1行で
    3行目: 技術的背景や将来的な影響を1行で
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"要約エラー (429回避中...): {e}"

def main():
    print("Starting Tech News Bot (Viral Filter Mode)...")
    
    # 100ポイント以上の記事を最大5件取得
    stories = get_viral_stories(min_score=100, max_count=5)
    
    if not stories:
        print("No viral stories found at this time.")
        return

    for story in stories:
        title = story.get('title')
        url = story.get('url')
        score = story.get('score')
        
        print(f"Summarizing: {title}")
        summary = summarize_article(title, url, score)
        
        message = f"**🔥 Tech News Pickup (100+ pts)**\n{summary}\nOriginal: {url}\n------------------------"
        
        # Discord送信
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        
        # 無料枠制限(429)を確実に回避するため、15秒待機
        print("Waiting 15 seconds for rate limit safety...")
        time.sleep(15)

if __name__ == "__main__":
    main()

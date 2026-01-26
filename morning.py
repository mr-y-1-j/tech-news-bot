import yfinance as yf
import feedparser
import requests
import re
from janome.tokenizer import Tokenizer
from collections import Counter
from datetime import datetime

# 1. 情報ソース（投資・テック界隈に限定）
RSS_SOURCES = [
    "https://feeds.reuters.com/reuters/JPBusinessNews",   # ロイター：ビジネス
    "https://feeds.reuters.com/reuters/JPTechnologyNews", # ロイター：テクノロジー
    "https://www3.nhk.or.jp/rss/news/cat5.xml",           # NHK：経済
    # 必要に応じて追加（例：日経、Gizmodo、Zennなど）
]

# 2. 監視キーワード（スナイパー機能：含まれていたら警告）
WATCH_KEYWORDS = [
    "関税", "レアアース", "半導体", "規制", "増税", "利上げ", 
    "TSMC", "NVIDIA", "台湾有事", "サプライチェーン"
]

# 3. 除外ワード（トレンド分析でカウントしない単語）
IGNORE_WORDS = [
    "の", "に", "は", "て", "を", "こと", "発表", "市場", "今日", 
    "ため", "これ", "それ", "関連", "など", "ニュース", "世界", 
    "日本", "米国", "現在", "結果", "見通し", "上昇", "下落"
]

# 4. Discord Webhook URL（ご自身のURLをセットしてください）
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1464073186953138389/y52-OgdBXQC8cX_tktFRPtqMxmVD9vYUhzzITlPprQQy9xhjyWws5CwP5sd2IkH7vpbE"

# ==========================================

def analyze_market_health():
    """市場の数値（カナリア）をチェックし、危険度を判定する"""
    print("Fetching market data...")
    
    # データ取得（過去2日分）
    tickers = ["^VIX", "BTC-USD", "^TNX", "^IXIC"]
    data = yf.download(tickers, period="2d", interval="1d", progress=False)['Close']
    
    # 最新値の取得
    vix = data["^VIX"].iloc[-1]
    tnx = data["^TNX"].iloc[-1]
    btc_latest = data["BTC-USD"].iloc[-1]
    btc_prev = data["BTC-USD"].iloc[-2]
    
    # BTC変動率
    btc_change = ((btc_latest - btc_prev) / btc_prev) * 100

    # 判定ロジック
    status_color = 0x00ff00  # デフォルト：緑（安全）
    status_title = "✅ Market is Stable"
    alert_msg = ""
    metrics_text = ""

    # 数値の表示用テキスト作成
    metrics_text += f"**VIX (恐怖指数):** {vix:.2f}\n"
    metrics_text += f"**BTC (ビットコイン):** {btc_latest:,.0f} USD ({btc_change:+.2f}%)\n"
    metrics_text += f"**US10Y (米10年債):** {tnx:.2f}%\n"

    # 危険度判定（優先度順）
    # Level 3: Panic
    if vix > 30:
        status_color = 0xff0000 
        status_title = "🚨 MARKET PANIC ALERT"
        alert_msg += "・VIXが30を超えています。パニック相場の警戒を。\n"
    
    # Level 2: Caution (VIX or BTC Crash)
    elif vix > 20:
        status_color = 0xffff00
        status_title = "⚠️ Market Caution"
        alert_msg += "・VIXが20を超えました。ボラティリティ上昇中。\n"
    
    if btc_change < -5.0:
        if status_color == 0x00ff00: # まだ緑なら黄色へ
            status_color = 0xffff00
            status_title = "⚠️ Risk-Off Signal"
        alert_msg += f"・BTCが急落中 ({btc_change:.1f}%)。リスクオフの先行指標です。\n"

    # Level 1: Specific Risks
    if tnx > 4.5:
        alert_msg += f"・金利高水準 ({tnx:.2f}%)。グロース株への逆風注意。\n"

    return status_title, status_color, alert_msg, metrics_text

def analyze_news_trends():
    """RSSを解析し、固定監視ワードと急上昇トレンドワードを抽出する"""
    print("Fetching news feeds...")
    tokenizer = Tokenizer()
    words = []
    hit_watch_words = []
    headlines = []
    
    for url in RSS_SOURCES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.title
                headlines.append(title)
                
                # 1. スナイパー機能：固定キーワードチェック
                for kw in WATCH_KEYWORDS:
                    if kw in title and kw not in hit_watch_words:
                        hit_watch_words.append(kw)
                
                # 2. レーダー機能：トレンド解析（名詞抽出）
                tokens = tokenizer.tokenize(title)
                for token in tokens:
                    if token.part_of_speech.split(',')[0] == '名詞':
                        word = token.surface
                        # 2文字以上、数字のみ除外、除外リスト以外
                        if len(word) > 1 and word not in IGNORE_WORDS and not re.match(r'^[0-9]+$', word):
                            words.append(word)
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    # 頻出ワードTOP5
    trending_words = Counter(words).most_common(5)
    
    return hit_watch_words, trending_words

def send_to_discord(title, color, alert_msg, metrics_text, hit_watch_words, trending_words):
    """DiscordにEmbed形式で送信する"""
    
    description = ""
    
    # 1. アラートセクション（あれば）
    if alert_msg:
        description += f"**【⚠️ 警戒シグナル】**\n{alert_msg}\n"
    else:
        description += "特筆すべきリスク要因はありません。\n\n"

    # 2. マーケット数値
    description += f"**【📊 カナリア指標】**\n{metrics_text}\n"

    # 3. トレンド解析結果
    description += "**【📰 ニュース解析】**\n"
    
    # 3-1. 監視ワードヒット
    if hit_watch_words:
        description += f"**🚨 検出された監視ワード:**\n`{'`, `'.join(hit_watch_words)}`\n"
    else:
        description += "※監視対象キーワード（関税など）の出現なし\n"
        
    # 3-2. 急上昇ワード
    description += "\n**🔥 今日のトレンド (界隈頻出):**\n"
    for word, count in trending_words:
        description += f"・**{word}** ({count}回)\n"

    # Embed作成
    payload = {
        "username": "Morning Briefing Bot",
        "embeds": [{
            "title": f"{title} ({datetime.now().strftime('%Y-%m-%d')})",
            "description": description,
            "color": color,
            "footer": {
                "text": "Generated by Python Market Watcher"
            }
        }]
    }

    # 送信実行
    if "https://discord.com/api/webhooks/1464073186953138389/y52-OgdBXQC8cX_tktFRPtqMxmVD9vYUhzzITlPprQQy9xhjyWws5CwP5sd2IkH7vpbE" in DISCORD_WEBHOOK_URL:
        print("\n[Test Mode] Webhook URLが設定されていません。出力内容を表示します:\n")
        print(f"Title: {title}")
        print(description)
    else:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        if response.status_code == 204:
            print("Successfully sent to Discord.")
        else:
            print(f"Failed to send: {response.status_code}")

def main():
    # 市場分析
    title, color, alert, metrics = analyze_market_health()
    
    # ニュース分析
    hits, trends = analyze_news_trends()
    
    # 送信
    send_to_discord(title, color, alert, metrics, hits, trends)

if __name__ == "__main__":
    main()

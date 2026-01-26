import os
import requests
import google.generativeai as genai

# 設定
WEBHOOK_TECH = os.environ.get("DISCORD_WEBHOOK_URL_TECH", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)

def send_debug_message(message):
    print(message)
    if WEBHOOK_TECH:
        requests.post(WEBHOOK_TECH, json={"content": message})

def main():
    send_debug_message("🔍 Gemini Model Health Check Starting...")
    
    try:
        available_models = []
        # 利用可能なモデル一覧を取得
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if available_models:
            msg = "✅ **利用可能なモデル一覧:**\n" + "\n".join(available_models)
            send_debug_message(msg)
        else:
            send_debug_message("⚠️ モデル一覧が取得できましたが、generateContent対応モデルが0件です。")
            
    except Exception as e:
        send_debug_message(f"❌ **致命的なエラー (ListModels Failed):**\n{e}")

if __name__ == "__main__":
    main()

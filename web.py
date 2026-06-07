from flask import Flask, render_template, request, make_response, jsonify
from datetime import datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types


# --- Firebase 初始化 ---
if os.path.exists('serviceAccountKey.json'):
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

app = Flask(__name__)

client = genai.Client()


@app.route("/")
def home():
    return "小組期末報告：小說推薦機器人後台網頁伺服器已成功啟動！"

# --- 3. 小說爬蟲函式 (完全對齊學長姐圖一風格，自動產生亂碼 ID) ---
@app.route("/crawl")
def run_spider():
    db = firestore.client()
    url = "https://www.xjjxs.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        res.encoding = 'gbk'
        soup = BeautifulSoup(res.text, "html.parser")
        items = soup.find_all("div", class_="item")
        
        count = 0
        for item in items:
            a_tag = item.find("a", href=True)
            span_tag = item.find("span")
            author_tag = item.find("dd", class_="author") 
            
            # 動態尋找網頁中的分類標籤 (優先找 class 為 genre 的標籤，或區塊內的第一個連結)
            genre_tag = item.find("dd", class_="genre") or item.find("a")
            
            if a_tag and span_tag:
                title = a_tag.get("title", "無標題")
                link = a_tag.get("href")
                status = span_tag.text.strip()              # 狀態：已完結 / 連載中
                author = author_tag.text.strip() if author_tag else "佚名"
                genre = genre_tag.text.strip() if genre_tag else "綜合小說"  # 動態分類
                
                # ====== 這裡完全採用學長姐圖一的資料庫輸入寫法 ======
                # 1. 整理成 doc 字典
                doc = {
                    "title": title,
                    "author": author,
                    "status": status,
                    "genre": genre,
                    "hyperlink": link
                }
                
                # 2. 自動產生亂碼 ID (如學長姐圖一：.document() 內留空)
                doc_ref = db.collection("小說資料庫").document()
                
                # 3. 寫入 Firebase 資料庫
                doc_ref.set(doc)
                # ==================================================
                
                count += 1
                
        return f"小說爬蟲及存檔完畢，共新增 {count} 筆資料到 Firebase 小說資料庫！"
    except Exception as e:
        return f"爬蟲發生錯誤: {e}"

# --- 4. Webhook 主程式 (接收 Dialogflow 指令並進行篩選回應) ---
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    action = req.get("queryResult", {}).get("action", "")
    parameters = req.get("queryResult", {}).get("parameters", {})
    
    info = "抱歉，系統無法辨識您的指令。"

    # 點選選單查詢小說 (支援分類與狀態篩選)
    if action == "genreChoice":
        status = parameters.get("status", "")  # 從 Dialogflow 傳過來的狀態 (例如：已完結)
        genre = parameters.get("genre", "")    # 從 Dialogflow 傳過來的分類 (例如：武俠)
        
        db = firestore.client()
        
        # 從 Firebase 中撈出小說資料
        docs = db.collection("小說資料庫").where("status", "==", status).get()
        
        # ====== 修正為小組稱呼 ======
        result = f"我是我們小組開發的小說推薦機器人，您選擇的小說狀態是【{status}】：\n\n"
        count = 0
        for doc in docs:
            d = doc.to_dict()
            
            # 如果有指定分類就篩選分類，沒有就直接顯示
            if genre == "" or genre in d.get("genre", ""):
                result += f"📖 書名：{d['title']}\n✍️ 作者：{d['author']}\n🏷️ 分類：{d['genre']}\n🔗 連結：{d['hyperlink']}\n\n"
                count += 1
            
        info = result if count > 0 else f"目前資料庫中沒有符合【{status}】的資料。"

    return make_response(jsonify({"fulfillmentText": info}))

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask,render_template,request
from datetime import datetime

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup

# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)

app = Flask(__name__)

@app.route("/")
def index():
    link = "<h1>歡迎進入鐘元汝的網站20260416</h1>"
    link += "<a href=/mis>課程</a><hr>"
    link += "<a href=/today>現在的日期</a><hr>"
    link += "<a href=/me>關於我</a><hr>"
    link += "<a href=/welcome?u=元汝&d=靜宜資管&c=資訊管理導論>Get傳直</a><hr>"
    link += "<a href=/account>POST傳直</a><hr>"
    link += "<a href=/a>次方與根號計算</a><hr>"
    link += "<a href=/read>讀取Firestore資料</a><hr>"
    link += "<a href=/read2>讀取Firestore資料(根據名字關鍵字:楊)</a><hr>"
    link += "<a href=/sprider>爬取子青老師本學期課程</a><hr>"
    link += "<a href=/movie1>爬取即將上映電影</a><hr>"
    return link

@app.route("/movie1")
def movie1():
    # 取得關鍵字
    keyword = request.args.get("keyword", "").strip()
    
    # 1. 基礎畫面：一進去只會看到這個搜尋表單
    R = f"""
    <h2>即將上映電影查詢</h2>
    <form action="/movie1" method="get">
        <label>請輸入電影關鍵字：</label>
        <input type="text" name="keyword" value="{keyword}" placeholder="例如: 蜘蛛人">
        <button type="submit">搜尋</button>
    </form>
    <hr>
    """
    
    # 2. 邏輯閘門：只有當 keyword 有內容時（使用者按下搜尋後），才執行以下爬蟲
    if keyword:
        R += f"<p>您搜尋的關鍵字是：<b style='color: blue;'>{keyword}</b></p>"
        
        url = "https://www.atmovies.com.tw/movie/next/"
        
        try:
            Data = requests.get(url, timeout=5) 
            Data.encoding = "utf-8"
            sp = BeautifulSoup(Data.text, "html.parser")
            result = sp.select(".filmListAllX li")
            
            found_count = 0 
            
            for item in result:
                try:
                    img_tag = item.find("img")
                    a_tag = item.find("a")
                    
                    if img_tag and a_tag:
                        title = img_tag.get("alt")
                        
                        # 3. 這裡只需要比對關鍵字有沒有在標題裡，不用再管沒有關鍵字的狀況了
                        if keyword in title:
                            found_count += 1
                            introduce = "https://www.atmovies.com.tw" + a_tag.get("href")
                            img_url = "https://www.atmovies.com.tw" + img_tag.get("src")
                            
                            R += f"<div style='margin-bottom: 20px;'>"
                            R += f"  <h3 style='margin: 5px 0;'>{title}</h3>"
                            R += f"  <a href='{introduce}' target='_blank'>電影介紹頁面 ➔</a><br><br>"
                            # 確保圖片能正常顯示，並加上一點排版
                            R += f"  <img src='{img_url}' width='200' style='border-radius: 8px; box-shadow: 3px 3px 8px rgba(0,0,0,0.3);'>"
                            R += f"</div><hr>"
                except Exception:
                    continue 
                    
            if found_count == 0:
                R += f"<p style='color: red;'>抱歉，找不到包含「{keyword}」的電影。</p>"
                
        except requests.exceptions.RequestException:
            R += "<p style='color: red;'>無法連線到電影網站，請稍後再試。</p>"
            
    # 如果沒有 keyword，就會直接跳到這裡，回傳乾淨的表單
    return R


@app.route("/sprider")
def spider():
    R = ""
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".team-box a")

    for i in result:
        R += str(i.text) + i.get("href") + "<br>"
    return R

@app.route("/read2", methods=["GET", "POST"])
def read2():
    # 網頁標題與查詢表單
    Result = "<h1>靜宜資管老師查詢</h1>"
    Result += '<form action="/read2" method="post">'
    Result += '請輸入老師姓名關鍵字：<input type="text" name="keyword">'
    Result += '<button type="submit">查詢</button></form><br>'

    if request.method == "POST":
        keyword = request.form.get("keyword") # 取得使用者輸入的字，例如「楊」
        Result += f"<h3>查詢結果 (關鍵字: {keyword}):</h3>"
       
        db = firestore.client()
        collection_ref = db.collection("靜宜資管2026B")
        docs = collection_ref.get()
       
        found = False
        for doc in docs:
            teacher_data = doc.to_dict()
            name = teacher_data.get('name')
           
            # --- 關鍵修正：判斷關鍵字是否有在姓名裡面 ---
            if name and keyword in name:
                found = True
                lab = teacher_data.get('lab', '未知')
                Result += f"<span style='color:blue; font-weight:bold'>{name}</span> 老師的研究室是在 <b>{lab}</b><br>"
       
        if not found:
            Result += f"抱歉，查無老師此資料。<br>"

    Result += "<br><a href=/>返回首頁</a>"
    return Result

@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("靜宜資管2026B")    
    docs = collection_ref.order_by("lab").get()   
    for doc in docs:         
        Result += str(doc.to_dict()) + "<br>"    
    return Result

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>返回首頁</a>"

@app.route("/today")
def today():
    now = datetime.now()
    return render_template("today.html", datetime=str(now))

@app.route("/me")
def me():
    return render_template("about.html")

@app.route("/welcome", methods=["GET"])
def welcome():
    user = request.values.get("u")
    d = request.values.get("d")
    c = request.values.get("c")
    return render_template("welcome.html", name=user,dep = d,course = c)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")

@app.route("/a")
def a():
    return render_template("01.html")

if __name__ == "__main__":
   app.run(debug=True)
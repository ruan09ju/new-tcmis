from flask import Flask, render_template, request
from datetime import datetime
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup

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

# --- 首頁 ---
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
    link += "<a href=/movie1>搜尋即時上映電影</a><hr>"
    link += "<a href=/spriderm>爬取即將上映電影到資料庫</a><hr>"
    link += "<a href=/searchMovie>搜尋電影資料庫</a><hr>"
    return link

# --- (作業重點) 搜尋電影資料庫 ---
@app.route("/searchMovie")
def searchMovie():
    keyword = request.args.get("keyword", "").strip()
    
    R = f"""
    <h2>電影資料庫查詢系統 (關鍵字搜尋)</h2>
    <form action="/searchMovie" method="get">
        <label>請輸入電影關鍵字：</label>
        <input type="text" name="keyword" value="{keyword}">
        <button type="submit">查詢資料庫</button>
    </form>
    <hr>
    """
    
    if keyword:
        try:
            db = firestore.client()  
            # 注意：這裡對應 spridm 存入的集合名稱 "電影2B"
            docs = db.collection("電影2B").get() 
            
            found_count = 0 
            for doc in docs:
                movie = doc.to_dict()
                title = movie.get("title", "")
                
                if keyword in title:
                    found_count += 1
                    # 抓取作業要求的 5 個欄位
                    movie_id = doc.id                  # 1. 編號
                    # title 為                       # 2. 片名
                    picture = movie.get("picture")      # 3. 海報
                    hyperlink = movie.get("hyperlink")  # 4. 介紹頁
                    showDate = movie.get("showDate")    # 5. 上映日期
                    
                    # 格式化輸出
                    R += f"<b>編號：</b>{movie_id}<br>"
                    R += f"<b>片名：</b>{title}<br>"
                    R += f"<b>上映日期：</b>{showDate}<br>"
                    R += f"<b>介紹頁：</b><a href='{hyperlink}' target='_blank'>點我開啟介紹</a><br>"
                    R += f"<b>海報：</b><br><img src='{picture}' width='200'><br><br><hr>"
            
            if found_count == 0:
                R += f"<p style='color: red;'>資料庫中查無包含「{keyword}」的電影。</p>"
            else:
                R += f"<p>總共找到 {found_count} 部符合條件的電影。</p>"
                
        except Exception as e:
            R += f"<p style='color: red;'>錯誤：{e}</p>"
            
    return R

# --- 爬取電影並存入資料庫 ---
@app.route("/spriderm")
def spiderm():
    db = firestore.client()
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    
    # 抓取更新時間
    lastUpdate_tag = sp.find(class_="smaller09")
    lastUpdate = lastUpdate_tag.text.replace("更新時間：","") if lastUpdate_tag else "未知"
    
    result = sp.select(".filmListAllX li")
    total = 0
    for item in result:
        try:
            total += 1
            # 取得電影編號 (從 href 抓取)
            movie_id = item.find("a").get("href").replace("/movie", "").replace("/", "")
            title = item.find(class_="filmtitle").text
            picture = "https://www.atmovies.com.tw" + item.find("img").get("src")
            hyperlink = "https://www.atmovies.com.tw" + item.find("a").get("href")
            showDate = item.find(class_="runtime").text[5:15]

            doc = {
                "title": title,
                "picture": picture,
                "hyperlink": hyperlink,
                "showDate": showDate,
                "lastUpdate": lastUpdate
            }
            # 存入 "電影2B" 集合
            db.collection("電影2B").document(movie_id).set(doc)
        except:
            continue

    return f"最近更新日期:{lastUpdate}<br>總共爬取 {total} 部電影到資料庫"

# --- 其餘路由 (保留你原本的功能) ---
@app.route("/movie1")
def movie1():
    keyword = request.args.get("keyword", "").strip()
    R = f"<h2>即將上映電影查詢(即時爬蟲)</h2>" # ... (省略你原本的爬蟲程式碼內容)
    return R # 這裡請保留你原本 movie1 的邏輯內容

@app.route("/sprider")
def spider():
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".team-box a")
    R = ""
    for i in result:
        R += str(i.text) + i.get("href") + "<br>"
    return R

@app.route("/read2", methods=["GET", "POST"])
def read2():
    Result = "<h1>靜宜資管老師查詢</h1>"
    # ... (保留你原本 read2 的內容)
    return Result

@app.route("/read")
def read():
    db = firestore.client()
    collection_ref = db.collection("靜宜資管2026B")    
    docs = collection_ref.order_by("lab").get()   
    Result = ""
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
    return render_template("welcome.html", name=user, dep=d, course=c)

@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]; pwd = request.form["pwd"]
        return "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
    return render_template("account.html")

@app.route("/a")
def a():
    return render_template("01.html")

if __name__ == "__main__":
    app.run(debug=True)
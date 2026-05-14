from flask import Flask, render_template, request, make_response, jsonify
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
    link += "<a href=/road>台中市十大肇事路口</a><hr>"
    link += "<a href=/weather>全縣市天氣概況</a><hr>"
    link += "<a href=/rate>本週新片進DB</a><hr>"
    return link


@app.route("/webhook", methods=["POST"])
def webhook():
    # build a request object
    req = request.get_json(force=True)
    # fetch queryResult from json
    action =  req.get("queryResult").get("action")
    msg =  req.get("queryResult").get("queryText")
    info = "動作：" + action + "； 查詢內容：" + msg
    return make_response(jsonify({"fulfillmentText": info}))



@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate


@app.route("/weather")
def weather():
    # 1. 網頁要改用 request.args 取得參數，預設值設為「臺中市」
    city = request.args.get("city", "臺中市")
    city = city.replace("台", "臺")

    # 氣象局 API
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization=rdec-key-123-45678-011121314&format=JSON&locationName=" + city
    
    try:
        Data = requests.get(url)
        jsonData = json.loads(Data.text)
        
        # 取得縣市名稱
        location_name = jsonData["records"]["location"][0]["locationName"]
        
        # 取得天氣現象 (Weather) 與 降雨機率 (Rain)
        # 這裡建議先存成變數，避免重複 loads 浪費資源
        weather_elements = jsonData["records"]["location"][0]["weatherElement"]
        weather_desc = weather_elements[0]["time"][0]["parameter"]["parameterName"]
        rain_chance = weather_elements[1]["time"][0]["parameter"]["parameterName"]

        # 2. 組合要呈現在網頁上的 HTML 字串
        R = f"<h2>{location_name} 天氣預報</h2>"
        R += f"<p>{weather_desc}，降雨機率：{rain_chance}%</p>"
        
        # 3. 額外加一個簡易輸入框，讓使用者可以直接在網頁切換縣市
        R += """
            <form action="/weather" method="get">
                <input type="text" name="city" placeholder="輸入縣市，例如：台北市">
                <button type="submit">查詢</button>
            </form>
        """
        
    except Exception as e:
        R = f"查詢失敗，請檢查縣市名稱是否正確。錯誤訊息：{e}"

    return R

@app.route("/road")
def opendata():
    R = "<h1>台中市十大肇事路口(113年10月)鐘元汝</h1><br>"
    # 使用你指定的新網址
    url = "https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        Data = requests.get(url, headers=headers, timeout=10)
        Data.encoding = "utf-8"
        JsonData = Data.json()
        
        count = 0
        total_accidents = 0
        
        for item in JsonData:
            count += 1
            
            # --- 強化版抓取邏輯 ---
            # 1. 抓取路口與原因 (增加備用欄位)
            location = item.get("路口名稱") or item.get("路口") or "未知路口"
            reason = item.get("主要肇因") or item.get("肇事原因") or "未知原因"
            
            # 2. 自動尋找包含「件數」字眼的欄位 (解決欄位名稱變動問題)
            num = 0
            for key, value in item.items():
                if "件數" in key:
                    try:
                        num = int(value)
                        break # 抓到就跳出
                    except:
                        continue
            
            total_accidents += num
            
            # 依照圖片格式輸出
            R += f'{count}. {location}，原因：{reason} ({num}件)<br>'
        
        # 最後加上總計
        R += f"<br>113年10月總計件數：{total_accidents}件"
        
    except Exception as e:
        R += f"<p style='color:red;'>錯誤：{e}</p>"
        
    return R

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
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "系統運作正常"

if __name__ == "__main__":
    app.run()
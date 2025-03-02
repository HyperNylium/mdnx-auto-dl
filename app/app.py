
from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
from os import getenv

# get the environment variables from .env file
load_dotenv("appdata/config/.env")

TEMPLATE_DIR = str(getenv("TEMPLATE_DIR"))
STATIC_DIR = str(getenv("STATIC_DIR"))

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# redirect to home page
@app.route("/")
def index():
    return redirect(url_for("home"))

@app.route("/home")
def home():
    return render_template("home/index.html")




if __name__ == '__main__':
    app.run(debug=True)
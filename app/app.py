
from flask import Flask, render_template, redirect, url_for
import os
import logging
import sys

# Get environment variables
FLASK_HOST = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
FLASK_PORT = os.environ.get("FLASK_RUN_PORT", "5000")
TEMPLATE_DIR = os.environ.get("TEMPLATE_FOLDER", "appdata/templates")
STATIC_DIR = os.environ.get("STATIC_FOLDER", "appdata/static")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "appdata/logs/app.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE)
    ]
)
logger = logging.getLogger(__name__)

logger.info(
    "Starting Flask app with the following settings:\n"
    f"FLASK_HOST: {FLASK_HOST}\n"
    f"FLASK_PORT: {FLASK_PORT}\n"
    f"TEMPLATE_DIR: {TEMPLATE_DIR}\n"
    f"STATIC_DIR: {STATIC_DIR}\n"
    f"LOG_LEVEL: {LOG_LEVEL}\n"
    f"LOG_FILE: {LOG_FILE}\n"
)

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# redirect to home page
@app.route("/")
def index():
    return redirect(url_for("home"))

@app.route("/home")
def home():
    return render_template("home/index.html")




if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT)
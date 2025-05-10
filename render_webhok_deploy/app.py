import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import telebot
import database
import models
import utils
import admin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get bot token and webhook URL from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Your Render URL + /webhook

if not BOT_TOKEN:
    logger.error("No BOT_TOKEN provided. Please check your environment variables.")
    exit(1)

# Initialize database
database.initialize_database()

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Import all handlers and commands
from bot import *  # This imports all your original bot handlers

# Create Flask app
app = Flask(__name__)

# Set up webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)

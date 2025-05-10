import logging
import os
from dotenv import load_dotenv
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

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    logger.error("No BOT_TOKEN provided. Please check your .env file.")
    exit(1)

# Initialize database
database.initialize_database()

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN if BOT_TOKEN else "")

# Import command handlers from the original bot file
import original_bot

if __name__ == '__main__':
    logger.info("Starting IG Vault bot...")
    bot.polling(none_stop=True, interval=0)
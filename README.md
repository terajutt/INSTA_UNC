# IG Vault Bot - Render Deployment

This is a simplified deployment package for IG Vault Bot on Render.

## Deployment Instructions

1. **On Render**:
   - Create a new Web Service
   - Upload this package or connect to the Git repository
   - Set the build command: `pip install -r requirements.txt`
   - Set the start command: `gunicorn app:app`

2. **Environment Variables**:
   - Add `BOT_TOKEN`: Your Telegram bot token from BotFather
   - Add `ADMIN_ID`: Your Telegram user ID (for admin access)
   - Add `DATABASE_URL`: Your Neon database URL

3. **Shell Process Setup**:
   - After the web service is running, go to Shell
   - Run: `chmod +x start_bot.sh && ./start_bot.sh`
   - This will start the bot in the background

## How It Works

This deployment uses two separate processes:
1. A Flask web server that responds to web requests and keeps the service alive
2. A background process running the actual Telegram bot

The web server runs automatically when you deploy. The bot needs to be started manually once using the shell command.

## Verification

You can verify the web server is running by making a request to the root endpoint:
```
curl https://your-service-name.onrender.com/
```

And check the health status:
```
curl https://your-service-name.onrender.com/health
```

To verify the bot is running, check the bot.log file:
```
cat bot.log
```
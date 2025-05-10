#!/bin/bash

# Start the Telegram bot in the background
python bot.py > bot.log 2>&1 &

# Print confirmation
echo "Bot started in background. Check bot.log for output."

# Keep this script alive to prevent the web service from shutting down
while true; do
  sleep 86400  # Sleep for 1 day
done
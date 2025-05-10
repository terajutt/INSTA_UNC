import os
import telebot
from telebot import types, custom_filters
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import logging
from dotenv import load_dotenv
from models import User, Account, Redemption, Report
from utils import (
    is_admin, create_dashboard_markup, format_dashboard_text,
    format_welcome_message, format_history_text, format_leaderboard_text,
    create_report_markup, create_report_reason_markup, create_back_to_menu_markup
)
from admin import AdminHandler

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Get bot token and admin ID from environment
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Initialize bot with state storage
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML', state_storage=state_storage)

# Define bot states
class BotStates(StatesGroup):
    waiting_for_accounts = State()
    waiting_for_broadcast = State()
    waiting_for_report_reason = State()
    
# Add a special test command to add points to admin
@bot.message_handler(commands=['test_points'], func=lambda message: is_admin(message.from_user.id))
def test_points_command(message):
    """Add 100 test points to admin account"""
    try:
        user_id = message.from_user.id
        points_to_add = 100
        
        # Add the points
        success = User.update_points(user_id, points_to_add)
        
        if success:
            bot.reply_to(message, f"✅ Added {points_to_add} test points to your account!")
            
            # Show updated dashboard
            user_data = User.get_user(user_id)
            bot_username = bot.get_me().username
            referral_link = f"https://t.me/{bot_username}?start={user_id}"
            dashboard_text = format_dashboard_text(user_data)
            markup = create_dashboard_markup(user_id, referral_link)
            
            bot.send_message(
                message.chat.id,
                dashboard_text,
                reply_markup=markup
            )
        else:
            bot.reply_to(message, "❌ Failed to add test points. Please try again.")
    except Exception as e:
        logger.error(f"Error adding test points: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")


# Command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command and referral parameters"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        
        # Check for referral parameter
        ref_user_id = None
        if len(message.text.split()) > 1:
            try:
                ref_param = message.text.split()[1]
                ref_user_id = int(ref_param)
                
                # Prevent self-referral
                if ref_user_id == user_id:
                    ref_user_id = None
            except (ValueError, IndexError):
                ref_user_id = None
        
        # Create user if not exists
        User.create_user(user_id, username, ref_user_id)
        
        # Generate referral link for this user
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Create YouTube subscription markup
        markup = types.InlineKeyboardMarkup()
        subscribe_button = types.InlineKeyboardButton(
            "✅ I Subscribed", 
            callback_data="subscribed"
        )
        yt_button = types.InlineKeyboardButton(
            "📱 Open YouTube Channel", 
            url="https://youtube.com/@freeinstavault"
        )
        markup.add(yt_button)
        markup.add(subscribe_button)
        
        # Send welcome message with subscription requirement
        bot.send_message(
            message.chat.id,
            f"""
👋 <b>Welcome to IG Vault!</b>

Before you can start, please subscribe to our YouTube channel:
https://youtube.com/@freeinstavault

Click the button below once you've subscribed.
""",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")


@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    help_text = """
🔍 <b>IG VAULT HELP</b> 🔍

<b>Basic Commands:</b>
/start - Start the bot and get your referral link
/help - Show this help message
/dashboard - View your points and stats

<b>How to earn points:</b>
• 👥 Invite friends using your referral link (+3 points per referral)
• 🎁 Claim daily reward every 24 hours (+2 points)
• ⭐ VIP members get +4 points daily

<b>Redeeming Accounts:</b>
• Standard users: 15 points per account
• VIP users: 10 points per account

<b>VIP Status:</b>
• Reach 20+ referrals to become VIP
• VIP benefits include extra daily points, early access to accounts, and discounted redemptions

<b>Having issues?</b>
If you redeem a broken account, use the "Report Broken Account" button for a potential points refund.
"""
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=['dashboard'])
def dashboard_command(message):
    """Handle /dashboard command"""
    try:
        user_id = message.from_user.id
        user_data = User.get_user(user_id)
        
        if not user_data:
            bot.reply_to(message, "You need to start the bot first. Use /start")
            return
        
        # Generate referral link
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Send dashboard
        markup = create_dashboard_markup(user_id, referral_link)
        dashboard_text = format_dashboard_text(user_data)
        
        bot.send_message(
            message.chat.id,
            dashboard_text,
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Error in dashboard command: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")


@bot.message_handler(commands=['admin'], func=lambda message: is_admin(message.from_user.id))
def admin_command(message):
    """Handle /admin command for admin users"""
    try:
        # Check if admin is asking for points
        text = message.text.strip().lower()
        if "points" in text:
            try:
                # Parse points amount
                parts = text.split()
                for i, part in enumerate(parts):
                    if part == "points" and i > 0:
                        amount = int(parts[i-1])
                        if amount > 0:
                            # Add points to admin account
                            success = User.update_points(message.from_user.id, amount)
                            if success:
                                bot.reply_to(message, f"✅ Added {amount} points to your account!")
                            else:
                                bot.reply_to(message, f"❌ Failed to add points. Please try again.")
                            return
            except (ValueError, IndexError):
                # If parsing fails, just show admin dashboard
                pass
                
        # Show admin dashboard
        AdminHandler.show_admin_dashboard(bot, message.chat.id)
    except Exception as e:
        logger.error(f"Error in admin command: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")


@bot.message_handler(commands=['add'], func=lambda message: is_admin(message.from_user.id))
def add_accounts_command(message):
    """Handle /add command for adding accounts"""
    bot.send_message(
        message.chat.id,
        """
➕ <b>ADD INSTAGRAM ACCOUNTS</b>

You can send accounts in either of these formats:

1️⃣ <b>Simple format</b>:
<code>username:password</code>

2️⃣ <b>Detailed format</b>:
<code>𓂀 ℕ𝕖𝕨 𝔸𝕔𝕔𝕠𝕦𝕟𝕥 𓂀
════════════════   
NAME       :〘name〙
USERNAME   :  〘@username〙
EMAIL      :  〘email@example.com〙
META       :  〘True/False〙
BIZZ META   :  〘True/False〙
FOLLOWERS  :  〘count〙
FOLLOWING  :  〘count〙
YEAR       :  〘year〙
ID         :  〘id〙
POSTS      :  〘count〙
BIO        :  〘bio〙
RESET      :  〘reset_email〙
LINK    : https://www.instagram.com/username
════════════════</code>

You can add multiple accounts, either format.
"""
    )
    bot.set_state(message.from_user.id, BotStates.waiting_for_accounts, message.chat.id)


@bot.message_handler(commands=['stats'], func=lambda message: is_admin(message.from_user.id))
def stats_command(message):
    """Handle /stats command for admin statistics"""
    try:
        AdminHandler.show_admin_dashboard(bot, message.chat.id)
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        bot.reply_to(message, "An error occurred. Please try again later.")


@bot.message_handler(commands=['broadcast'], func=lambda message: is_admin(message.from_user.id))
def broadcast_command(message):
    """Handle /broadcast command for sending messages to all users"""
    bot.send_message(
        message.chat.id,
        """
📢 <b>BROADCAST MESSAGE</b>

Please type the message you want to send to all users.
This will be sent as an official announcement.
"""
    )
    bot.set_state(message.from_user.id, BotStates.waiting_for_broadcast, message.chat.id)


# State handlers
@bot.message_handler(state=BotStates.waiting_for_accounts, func=lambda message: is_admin(message.from_user.id))
def handle_accounts_input(message):
    """Process accounts input from admin"""
    AdminHandler.handle_add_accounts(bot, message)


@bot.message_handler(state=BotStates.waiting_for_broadcast, func=lambda message: is_admin(message.from_user.id))
def handle_broadcast_input(message):
    """Process broadcast input from admin"""
    AdminHandler.handle_broadcast_message(bot, message)


# Callback handlers
@bot.callback_query_handler(func=lambda call: call.data == "subscribed")
def callback_subscribed(call):
    """Handle subscription verification"""
    try:
        user_id = call.from_user.id
        username = call.from_user.username or call.from_user.first_name
        
        # Generate referral link
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Send welcome message with dashboard
        welcome_text = format_welcome_message(username, referral_link)
        markup = create_dashboard_markup(user_id, referral_link)
        
        bot.edit_message_text(
            welcome_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        # Answer callback to remove loading state
        bot.answer_callback_query(call.id, "Welcome to IG Vault!")
    except Exception as e:
        logger.error(f"Error in subscription callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("dashboard_"))
def callback_dashboard(call):
    """Handle dashboard button click"""
    try:
        user_id = call.from_user.id
        user_data = User.get_user(user_id)
        
        if not user_data:
            bot.answer_callback_query(call.id, "User not found. Please restart the bot.")
            return
        
        # Generate referral link
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Format dashboard text
        dashboard_text = format_dashboard_text(user_data)
        markup = create_dashboard_markup(user_id, referral_link)
        
        # Edit message with dashboard
        bot.edit_message_text(
            dashboard_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Dashboard updated!")
    except Exception as e:
        logger.error(f"Error in dashboard callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("daily_"))
def callback_daily_reward(call):
    """Handle daily reward button click"""
    try:
        user_id = call.from_user.id
        
        # Check if user can claim daily reward
        if not User.can_claim_daily(user_id):
            time_until = User.get_time_until_next_daily(user_id)
            bot.answer_callback_query(
                call.id, 
                f"You can claim your next reward in: {time_until}"
            )
            return
        
        # Claim daily reward
        success, points = User.claim_daily_reward(user_id)
        
        if success:
            # Generate referral link
            bot_username = bot.get_me().username
            referral_link = f"https://t.me/{bot_username}?start={user_id}"
            
            # Update dashboard
            user_data = User.get_user(user_id)
            dashboard_text = format_dashboard_text(user_data)
            markup = create_dashboard_markup(user_id, referral_link)
            
            # Send success message
            reward_text = f"""
🎁 <b>DAILY REWARD CLAIMED!</b> 🎁

You received <b>+{points} points</b>!

Come back in 24 hours for your next reward.
"""
            bot.send_message(call.message.chat.id, reward_text)
            
            # Update dashboard
            bot.edit_message_text(
                dashboard_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
            
            # Answer callback
            bot.answer_callback_query(call.id, f"You claimed {points} points!")
        else:
            bot.answer_callback_query(call.id, "Error claiming reward. Please try again.")
    except Exception as e:
        logger.error(f"Error in daily reward callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("redeem_"))
def callback_redeem_account(call):
    """Handle account redemption"""
    try:
        user_id = call.from_user.id
        user_data = User.get_user(user_id)
        
        if not user_data:
            bot.answer_callback_query(call.id, "User not found. Please restart the bot.")
            return
        
        # Check if user is VIP to determine redemption cost
        _, _, points, is_vip, _, _, _ = user_data
        redemption_cost = 10 if is_vip else 15
        
        # Check if user has enough points
        if points < redemption_cost:
            bot.answer_callback_query(
                call.id, 
                f"Not enough points. You need {redemption_cost} points to redeem."
            )
            return
        
        # Try to get an account
        account_id, account_info = Account.get_account(is_vip)
        
        if not account_id or not account_info:
            bot.answer_callback_query(call.id, "No accounts available. Try again later.")
            bot.send_message(
                call.message.chat.id,
                "⚠️ <b>No accounts left in stock. More coming soon!</b>"
            )
            return
        
        # Deduct points
        User.update_points(user_id, -redemption_cost)
        
        # Remove account from available accounts
        Account.remove_account(account_id)
        
        # Record redemption
        Redemption.record_redemption(user_id, account_info)
        
        # Generate referral link for dashboard update
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Send account info with report button
        # Check if this is a detailed format account (has decorative elements)
        is_detailed_format = "𓂀" in account_info or "════════════════" in account_info
        
        if is_detailed_format:
            # For detailed format, just use it as is
            account_text = f"""
🔐 <b>ACCOUNT REDEEMED SUCCESSFULLY!</b> 🔐

<code>{account_info}</code>

Cost: -{redemption_cost} points

If this account doesn't work, please use the Report button below.
"""
        else:
            # For simple format, extract username/email if possible
            try:
                # Check if format is username:password
                if ":" in account_info:
                    username = account_info.split(":")[0]
                    email = f"{username}@gmail.com"  # Default assumption
                else:
                    # Just use as is
                    username = account_info
                    email = account_info
                    
                # Create a more visually appealing format
                account_text = f"""
🔐 <b>ACCOUNT REDEEMED SUCCESSFULLY!</b> 🔐

Your Instagram account:
{email}

Cost: -{redemption_cost} points

If this account doesn't work, please use the Report button below.
"""
            except:
                # Fallback to simple format
                account_text = f"""
🔐 <b>ACCOUNT REDEEMED SUCCESSFULLY!</b> 🔐

Your Instagram account:
<code>{account_info}</code>

Cost: -{redemption_cost} points

If this account doesn't work, please use the Report button below.
"""
        # Get a unique identifier for the account
        import hashlib
        account_identifier = hashlib.md5(account_info.encode()).hexdigest()[:10]
        
        # Record redemption ID if we need it later
        redemption_id = None
        redemptions = Redemption.get_user_redemptions(user_id)
        
        # Create markup with report button
        report_markup = create_report_markup(account_info, user_id, account_identifier)
        
        bot.send_message(
            call.message.chat.id,
            account_text,
            reply_markup=report_markup
        )
        
        # Update dashboard
        updated_user_data = User.get_user(user_id)
        dashboard_text = format_dashboard_text(updated_user_data)
        markup = create_dashboard_markup(user_id, referral_link)
        
        bot.edit_message_text(
            dashboard_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Account redeemed successfully!")
    except Exception as e:
        logger.error(f"Error in redeem callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("report_") and not call.data.startswith("report_reason_"))
def callback_report_account(call):
    """Handle account report button click"""
    try:
        # Parse data to get user_id and account identifier
        parts = call.data.split('_', 2)  # Split into 'report', 'user_id', 'identifier'
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "Invalid report data")
            return
        
        user_id = int(parts[1])
        account_identifier = parts[2]
        
        # We need to retrieve the full account info from redemption history
        redemptions = Redemption.get_user_redemptions(user_id)
        account_info = None
        
        # Try to match by redemption ID if it's numeric
        if account_identifier.isdigit():
            redemption_id = int(account_identifier)
            # Check if we have a method to get specific redemption by ID
            # For now, we'll use the workaround below
        
        # Extract accounts from redemptions if we have any
        if redemptions:
            try:
                for redemption_account, _ in redemptions:
                    # Try to match by hash if needed
                    import hashlib
                    if hashlib.md5(redemption_account.encode()).hexdigest()[:10] == account_identifier:
                        account_info = redemption_account
                        break
                    # Try to match by username
                    if ":" in redemption_account and redemption_account.split(":")[0] == account_identifier:
                        account_info = redemption_account
                        break
            except Exception as e:
                logger.error(f"Error matching account by identifier: {e}")
        
        # If still not found, use the most recent redemption
        if not account_info and redemptions:
            account_info = redemptions[0][0]
        
        # Show report reason selection
        reason_markup = create_report_reason_markup(account_info, user_id)
        bot.edit_message_text(
            """
⚠️ <b>REPORT BROKEN ACCOUNT</b> ⚠️

Please select the reason why this account doesn't work:
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=reason_markup
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Please select a reason")
    except Exception as e:
        logger.error(f"Error in report callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("report_reason_"))
def callback_report_reason(call):
    """Handle report reason selection"""
    try:
        # Parse data to get user_id, account_hash, and reason
        parts = call.data.split('_', 4)  # Split into 'report', 'reason', 'user_id', 'account_hash', 'reason_code'
        if len(parts) != 5:
            bot.answer_callback_query(call.id, "Invalid report data")
            return
        
        user_id = int(parts[2])
        account_hash = parts[3]
        reason_code = parts[4]
        
        # We need to retrieve the full account info from redemption history
        redemptions = Redemption.get_user_redemptions(user_id)
        account_info = None
        
        # Try to identify the account by hash
        if redemptions:
            try:
                import hashlib
                for redemption_account, _ in redemptions:
                    if hashlib.md5(redemption_account.encode()).hexdigest()[:8] == account_hash:
                        account_info = redemption_account
                        break
            except Exception as e:
                logger.error(f"Error identifying account by hash: {e}")
        
        # If we can't find it, use the most recent redemption
        if not account_info and redemptions:
            account_info = redemptions[0][0]
        
        # Convert reason code to human-readable reason
        if reason_code == "password_changed":
            reason = "Password Changed"
        elif reason_code == "account_locked":
            reason = "Account Locked"
        elif reason_code == "2fa_enabled":
            reason = "2FA Enabled"
        else:
            reason = "Other Issue"
        
        # Create report in database
        Report.create_report(user_id, account_info, reason)
        
        # Notify user
        bot.edit_message_text(
            f"""
✅ <b>REPORT SUBMITTED</b> ✅

Your report for account:
<code>{account_info}</code>

Reason: {reason}

Our admins will review your report soon. If approved, your points will be refunded.
""",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_back_to_menu_markup()
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Report submitted successfully")
        
        # Notify admin about new report
        if ADMIN_ID:
            admin_notify_text = f"""
⚠️ <b>NEW ACCOUNT REPORT</b> ⚠️

User: {call.from_user.username or call.from_user.first_name} (ID: {user_id})
Account: <code>{account_info}</code>
Reason: {reason}

Use /admin to review reports.
"""
            try:
                bot.send_message(ADMIN_ID, admin_notify_text)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Error in report reason callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def callback_back_to_menu(call):
    """Handle back to menu button click"""
    try:
        user_id = call.from_user.id
        user_data = User.get_user(user_id)
        
        if not user_data:
            bot.answer_callback_query(call.id, "User not found. Please restart the bot.")
            return
        
        # Generate referral link
        bot_username = bot.get_me().username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"
        
        # Format dashboard text
        dashboard_text = format_dashboard_text(user_data)
        markup = create_dashboard_markup(user_id, referral_link)
        
        # Edit message with dashboard
        bot.edit_message_text(
            dashboard_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Back to main menu")
    except Exception as e:
        logger.error(f"Error in back to menu callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("history_"))
def callback_history(call):
    """Handle user history button click"""
    try:
        user_id = call.from_user.id
        
        # Get user's redemption history
        redemptions = Redemption.get_user_redemptions(user_id)
        
        # Format history text
        history_text = format_history_text(redemptions)
        
        # Edit message with history
        bot.edit_message_text(
            history_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_back_to_menu_markup()
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Viewing redemption history")
    except Exception as e:
        logger.error(f"Error in history callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def callback_leaderboard(call):
    """Handle leaderboard button click"""
    try:
        # Get top users by referrals
        top_users = User.get_top_referrers(10)
        
        # Format leaderboard text
        leaderboard_text = format_leaderboard_text(top_users)
        
        # Edit message with leaderboard
        bot.edit_message_text(
            leaderboard_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_back_to_menu_markup()
        )
        
        # Answer callback
        bot.answer_callback_query(call.id, "Viewing referral leaderboard")
    except Exception as e:
        logger.error(f"Error in leaderboard callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


# Admin callback handlers
@bot.callback_query_handler(func=lambda call: call.data == "admin_menu" and is_admin(call.from_user.id))
def callback_admin_menu(call):
    """Handle admin menu button click"""
    try:
        AdminHandler.show_admin_dashboard(bot, call.message.chat.id)
        bot.answer_callback_query(call.id, "Admin dashboard")
    except Exception as e:
        logger.error(f"Error in admin menu callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data == "admin_add_accounts" and is_admin(call.from_user.id))
def callback_admin_add_accounts(call):
    """Handle admin add accounts button click"""
    try:
        bot.send_message(
            call.message.chat.id,
            """
➕ <b>ADD INSTAGRAM ACCOUNTS</b>

You can send accounts in either of these formats:

1️⃣ <b>Simple format</b>:
<code>username:password</code>

2️⃣ <b>Detailed format</b>:
<code>𓂀 ℕ𝕖𝕨 𝔸𝕔𝕔𝕠𝕦𝕟𝕥 𓂀
════════════════   
NAME       :〘name〙
USERNAME   :  〘@username〙
EMAIL      :  〘email@example.com〙
META       :  〘True/False〙
BIZZ META   :  〘True/False〙
FOLLOWERS  :  〘count〙
FOLLOWING  :  〘count〙
YEAR       :  〘year〙
ID         :  〘id〙
POSTS      :  〘count〙
BIO        :  〘bio〙
RESET      :  〘reset_email〙
LINK    : https://www.instagram.com/username
════════════════</code>

You can add multiple accounts, either format.
"""
        )
        bot.set_state(call.from_user.id, BotStates.waiting_for_accounts, call.message.chat.id)
        bot.answer_callback_query(call.id, "Add accounts")
    except Exception as e:
        logger.error(f"Error in admin add accounts callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast" and is_admin(call.from_user.id))
def callback_admin_broadcast(call):
    """Handle admin broadcast button click"""
    try:
        bot.send_message(
            call.message.chat.id,
            """
📢 <b>BROADCAST MESSAGE</b>

Please type the message you want to send to all users.
This will be sent as an official announcement.
"""
        )
        bot.set_state(call.from_user.id, BotStates.waiting_for_broadcast, call.message.chat.id)
        bot.answer_callback_query(call.id, "Broadcast message")
    except Exception as e:
        logger.error(f"Error in admin broadcast callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data == "admin_reports" and is_admin(call.from_user.id))
def callback_admin_reports(call):
    """Handle admin view reports button click"""
    try:
        AdminHandler.show_pending_reports(bot, call.message.chat.id)
        bot.answer_callback_query(call.id, "Viewing reports")
    except Exception as e:
        logger.error(f"Error in admin reports callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_report_") and is_admin(call.from_user.id))
def callback_approve_report(call):
    """Handle admin approve report button click"""
    try:
        # Parse report_id and user_id from callback data
        parts = call.data.split('_')
        report_id = int(parts[2])
        reporter_id = int(parts[3])
        
        AdminHandler.handle_report_action(bot, call.message.chat.id, "approve", report_id, reporter_id)
        bot.answer_callback_query(call.id, f"Approved report #{report_id}")
    except Exception as e:
        logger.error(f"Error in approve report callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("reject_report_") and is_admin(call.from_user.id))
def callback_reject_report(call):
    """Handle admin reject report button click"""
    try:
        # Parse report_id from callback data
        parts = call.data.split('_')
        report_id = int(parts[2])
        
        AdminHandler.handle_report_action(bot, call.message.chat.id, "reject", report_id)
        bot.answer_callback_query(call.id, f"Rejected report #{report_id}")
    except Exception as e:
        logger.error(f"Error in reject report callback: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")


# Enable middleware for state handling
bot.add_custom_filter(custom_filters.StateFilter(bot))


# Default handler for other messages
@bot.message_handler(func=lambda message: True)
def default_handler(message):
    """Handle any other message"""
    bot.reply_to(
        message, 
        "Use /dashboard to check your points or /help to see available commands."
    )

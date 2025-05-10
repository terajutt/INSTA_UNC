import logging
import os
from telebot import types
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)

# Admin user ID from environment
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
logger.info(f"Admin ID loaded as: {ADMIN_ID}")

def is_admin(user_id):
    """Check if a user is an admin"""
    # Ensure both are integers for comparison
    admin_id_int = ADMIN_ID
    user_id_int = int(user_id) if not isinstance(user_id, int) else user_id
    
    logger.info(f"Checking admin status: user_id={user_id_int}, admin_id={admin_id_int}")
    return user_id_int == admin_id_int

def validate_account_format(account_info):
    """Validate Instagram account format
    
    Accepts both:
    1. Standard format: username:password
    2. Detailed format with NAME, USERNAME, EMAIL, etc.
    """
    # Check if this is a detailed format
    if "USERNAME" in account_info and ("EMAIL" in account_info or "RESET" in account_info):
        # This is likely a detailed format
        try:
            # Check if it looks like the special format with decorative elements
            if "════════════════" in account_info or "𓂀 ℕ𝕖𝕨 𝔸𝕔𝕔𝕠𝕦𝕟𝕥 𓂀" in account_info:
                logger.info("Found special format account with decorative elements")
                return True
                
            # Extract essential data with more flexible pattern matching
            username_match = re.search(r'USERNAME\s*:\s*[〘\[\(]?@?([^〙\]\)]+)[〙\]\)]?', account_info)
            email_match = re.search(r'EMAIL\s*:\s*[〘\[\(]?([^〙\]\)]+)[〙\]\)]?', account_info)
            reset_match = re.search(r'RESET\s*:\s*[〘\[\(]?([^〙\]\)]+)[〙\]\)]?', account_info)
            
            if username_match and (email_match or reset_match):
                logger.info("Validated account with USERNAME and EMAIL/RESET")
                return True
        except Exception as e:
            logger.error(f"Error validating detailed account format: {e}")
            pass
        
    # Fall back to simple username:password validation
    pattern = r'^[\w\.-]+:[\w\.-]+$'
    valid = bool(re.match(pattern, account_info))
    if valid:
        logger.info("Validated account with simple username:password format")
    return valid

def create_dashboard_markup(user_id, referral_link):
    """Create dashboard markup with buttons"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Add buttons to the markup
    check_points_btn = types.InlineKeyboardButton("💰 Check Points", callback_data=f"dashboard_{user_id}")
    daily_reward_btn = types.InlineKeyboardButton("🎁 Daily Reward", callback_data=f"daily_{user_id}")
    redeem_btn = types.InlineKeyboardButton("🔑 Redeem Account", callback_data=f"redeem_{user_id}")
    history_btn = types.InlineKeyboardButton("📜 My History", callback_data=f"history_{user_id}")
    leaderboard_btn = types.InlineKeyboardButton("🏆 Leaderboard", callback_data=f"leaderboard")
    share_btn = types.InlineKeyboardButton("📣 Share Referral", url=referral_link)
    
    # Arrange buttons in rows
    markup.add(check_points_btn, daily_reward_btn)
    markup.add(redeem_btn, history_btn)
    markup.add(leaderboard_btn, share_btn)
    
    return markup

def create_report_markup(account_info, user_id, redemption_id=None):
    """Create markup for account reporting"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # We need to avoid putting full account info in callback data
    # Use just the redemption ID or a hash of the account info
    if redemption_id:
        report_data = f"report_{user_id}_{redemption_id}"
    else:
        # Create a short identifier based on username or first part of account
        if "USERNAME" in account_info:
            # For complex format, try to extract username
            try:
                username_match = re.search(r'USERNAME\s*:\s*[〘\[\(]?@?([^〙\]\)]+)[〙\]\)]?', account_info)
                if username_match:
                    identifier = username_match.group(1)[:15]  # Limit to 15 chars
                else:
                    # If can't extract username, use a hash
                    import hashlib
                    identifier = hashlib.md5(account_info.encode()).hexdigest()[:10]
            except:
                # Fallback to hash
                import hashlib
                identifier = hashlib.md5(account_info.encode()).hexdigest()[:10]
        elif ":" in account_info:
            # For username:password format
            identifier = account_info.split(":")[0][:15]  # Username limited to 15 chars
        else:
            # For any other format, use first 15 chars
            identifier = account_info[:15]
            
        report_data = f"report_{user_id}_{identifier}"
    
    # Make sure the callback data is not too long (64 bytes max)
    if len(report_data) > 60:  # Leave a small buffer
        import hashlib
        hash_id = hashlib.md5(account_info.encode()).hexdigest()[:10]
        report_data = f"report_{user_id}_{hash_id}"
    
    report_btn = types.InlineKeyboardButton(
        "⚠️ Report Broken Account", 
        callback_data=report_data
    )
    back_btn = types.InlineKeyboardButton(
        "🔙 Back to Menu", 
        callback_data="back_to_menu"
    )
    
    markup.add(report_btn, back_btn)
    return markup

def create_report_reason_markup(account_info, user_id):
    """Create markup for selecting report reason"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Create a short identifier for the account
    import hashlib
    account_hash = hashlib.md5(account_info.encode()).hexdigest()[:8]
    
    # Add various report reasons with shortened identifiers
    reasons = [
        ("Password Changed", f"report_reason_{user_id}_{account_hash}_password_changed"),
        ("Account Locked", f"report_reason_{user_id}_{account_hash}_account_locked"),
        ("2FA Enabled", f"report_reason_{user_id}_{account_hash}_2fa_enabled"),
        ("Other Issue", f"report_reason_{user_id}_{account_hash}_other")
    ]
    
    for reason_text, callback_data in reasons:
        markup.add(types.InlineKeyboardButton(reason_text, callback_data=callback_data))
    
    # Back button
    markup.add(types.InlineKeyboardButton(
        "🔙 Cancel", 
        callback_data="back_to_menu"
    ))
    
    return markup

def format_dashboard_text(user_data):
    """Format dashboard text with user info and styling"""
    user_id, username, points, vip, referrals, last_daily, _ = user_data
    
    # Format last redemption date
    last_redeem_text = "Never" if not last_daily else last_daily.strftime("%Y-%m-%d %H:%M")
    
    # VIP status with emoji
    vip_status = "✅ VIP Member" if vip else "❌ Not VIP"
    
    # Create styled dashboard text
    dashboard_text = f"""
🏆 <b>USER DASHBOARD</b> 🏆

👤 <b>Username:</b> {username}
💰 <b>Points Balance:</b> {points}
👥 <b>Referrals:</b> {referrals}
⭐ <b>Status:</b> {vip_status}
⏱ <b>Last Reward:</b> {last_redeem_text}

<i>Invite friends to earn more points!</i>
"""
    return dashboard_text

def format_history_text(redemptions):
    """Format user's redemption history"""
    if not redemptions or len(redemptions) == 0:
        return "📜 <b>REDEMPTION HISTORY</b>\n\nYou haven't redeemed any accounts yet."
    
    history_text = "📜 <b>REDEMPTION HISTORY</b>\n\n"
    
    for i, (account, timestamp) in enumerate(redemptions, 1):
        # Mask part of the account info for privacy
        account_parts = account.split(':')
        if len(account_parts) >= 2:
            username = account_parts[0]
            masked_pass = "•" * len(account_parts[1])
            masked_account = f"{username}:{masked_pass}"
        else:
            masked_account = account
        
        # Format timestamp
        date_str = timestamp.strftime("%Y-%m-%d %H:%M")
        
        history_text += f"{i}. <code>{masked_account}</code> - {date_str}\n"
    
    return history_text

def format_leaderboard_text(top_users):
    """Format leaderboard with top referrers"""
    if not top_users or len(top_users) == 0:
        return "🏆 <b>REFERRAL LEADERBOARD</b>\n\nNo users have made referrals yet."
    
    leaderboard_text = "🏆 <b>REFERRAL LEADERBOARD</b>\n\n"
    
    # Emoji medals for top 3
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (user_id, username, referrals) in enumerate(top_users):
        # Get position emoji (medal for top 3, number for others)
        position = medals[i] if i < 3 else f"{i+1}."
        
        leaderboard_text += f"{position} {username} - {referrals} referrals\n"
    
    return leaderboard_text

def format_welcome_message(username, referral_link):
    """Format welcome message with animations and styling"""
    welcome_text = f"""
✨✨✨✨✨✨✨✨✨✨✨✨
🌟 <b>WELCOME TO IG VAULT!</b> 🌟
✨✨✨✨✨✨✨✨✨✨✨✨

Hello, <b>{username}</b>! 👋

This bot gives you <b>FREE Instagram accounts</b> by:
- 👥 Inviting friends (+3 points per referral)
- 🎁 Claiming daily rewards (+2 points)
- ⭐ Becoming VIP (20+ referrals)

<b>VIP Benefits:</b>
- 💰 Extra daily rewards (+4 points)
- 🔑 Early access to premium accounts
- 💸 Lower redemption cost (10 vs 15 points)

<b>Your Referral Link:</b>
<code>{referral_link}</code>

Share this link to start earning points! 🚀
"""
    return welcome_text

def format_admin_stats(user_count, account_count, redemption_count, report_count):
    """Format admin statistics"""
    stats_text = f"""
📊 <b>ADMIN DASHBOARD</b> 📊

👥 <b>Total Users:</b> {user_count}
🔑 <b>Available Accounts:</b> {account_count}
🎁 <b>Total Redemptions:</b> {redemption_count}
⚠️ <b>Pending Reports:</b> {report_count}
"""
    return stats_text

def create_admin_markup():
    """Create admin dashboard markup"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    add_accounts_btn = types.InlineKeyboardButton("➕ Add Accounts", callback_data="admin_add_accounts")
    view_reports_btn = types.InlineKeyboardButton("⚠️ View Reports", callback_data="admin_reports")
    broadcast_btn = types.InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
    
    markup.add(add_accounts_btn, view_reports_btn)
    markup.add(broadcast_btn)
    
    return markup

def create_back_to_menu_markup():
    """Create markup with just a back button"""
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
    markup.add(back_btn)
    return markup

def create_reports_markup(reports):
    """Create markup for admin to review reports"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    for report_id, user_id, _, _, _, _ in reports[:5]:  # Show first 5 reports
        approve_btn = types.InlineKeyboardButton(
            f"✅ Approve #{report_id}", 
            callback_data=f"approve_report_{report_id}_{user_id}"
        )
        reject_btn = types.InlineKeyboardButton(
            f"❌ Reject #{report_id}", 
            callback_data=f"reject_report_{report_id}"
        )
        markup.add(approve_btn, reject_btn)
    
    back_btn = types.InlineKeyboardButton("🔙 Back", callback_data="admin_menu")
    markup.add(back_btn)
    
    return markup

def format_reports_text(reports):
    """Format text displaying pending reports"""
    # Check if reports is None or empty
    if not reports or (hasattr(reports, "__len__") and len(reports) == 0):
        return "⚠️ <b>PENDING REPORTS</b>\n\nNo reports pending review."
    
    reports_text = "⚠️ <b>PENDING REPORTS</b>\n\n"
    
    # Make sure reports is iterable
    try:
        for report in reports:
            try:
                # Safely unpack the report tuple
                if len(report) >= 6:
                    report_id, user_id, username, account, reason, timestamp = report
                    
                    # Format the timestamp
                    date_str = timestamp.strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown"
                    
                    reports_text += f"<b>Report #{report_id}</b>\n"
                    reports_text += f"From: {username} (ID: {user_id})\n"
                    reports_text += f"Account: <code>{account}</code>\n"
                    reports_text += f"Reason: {reason}\n"
                    reports_text += f"Date: {date_str}\n\n"
            except Exception as e:
                logger.error(f"Error formatting report: {e}")
                continue
    except Exception as e:
        logger.error(f"Error iterating reports: {e}")
        return "⚠️ <b>PENDING REPORTS</b>\n\nError loading reports. Please try again."
    
    return reports_text

import logging
import re
from models import User, Account, Report, Redemption
from utils import validate_account_format, format_admin_stats, format_reports_text, create_admin_markup, create_reports_markup, create_back_to_menu_markup

logger = logging.getLogger(__name__)

class AdminHandler:
    """Handler for admin-specific commands and features"""

    @staticmethod
    def handle_add_accounts(bot, message):
        """Process accounts to be added to the database"""
        try:
            accounts_text = message.text.strip()
            
            # Check for special format with the yellow background (New Account)
            if "New Account" in accounts_text:
                # Treat the whole text as one account if it has the New Account format
                logger.info("Detected 'New Account' format")
                accounts_list = [accounts_text]
            # For detailed format with decorative elements
            elif "𓂀 ℕ𝕖𝕨 𝔸𝕔𝕔𝕠𝕦𝕟𝕥 𓂀" in accounts_text:
                # Split by the decorative header
                accounts_list = accounts_text.split("𓂀 ℕ𝕖𝕨 𝔸𝕔𝕔𝕠𝕦𝕟𝕥 𓂀")
                # Filter out empty entries
                accounts_list = [acc.strip() for acc in accounts_list if acc.strip()]
            else:
                # Standard format, split by newline
                accounts_list = accounts_text.split('\n')
            
            valid_accounts = []
            invalid_accounts = []
            
            for account in accounts_list:
                account = account.strip()
                if not account:  # Skip empty accounts
                    continue
                    
                logger.info(f"Processing account: {account[:30]}...")
                
                # Handle special New Account format with yellow background
                if "New Account" in account and "USERNAME" in account and "EMAIL" in account:
                    try:
                        # Just store the full account information as-is
                        logger.info("Found New Account format, storing as-is")
                        success = Account.add_account(account, "premium")
                        if success:
                            valid_accounts.append("New Account format")
                            logger.info("Successfully added New Account format")
                        else:
                            invalid_accounts.append("Failed to add New Account format")
                        continue
                    except Exception as e:
                        logger.error(f"Error adding New Account format: {e}")
                        invalid_accounts.append(account)
                        continue
                
                # Handle standard formats
                if account and validate_account_format(account):
                    # Check if it's a detailed format and extract username:password
                    if "USERNAME" in account and "EMAIL" in account:
                        try:
                            # Try to extract username and email with more flexible pattern matching
                            username_match = re.search(r'USERNAME\s*:\s*[〘\[\(]?@?([^〙\]\)]+)[〙\]\)]?', account)
                            email_match = re.search(r'EMAIL\s*:\s*[〘\[\(]?([^〙\]\)]+)[〙\]\)]?', account)
                            password_match = re.search(r'RESET\s*:\s*[〘\[\(]?([^〙\]\)]+)[〙\]\)]?', account)
                            
                            # Log the account format being processed
                            logger.info(f"Processing account with format: {account[:50]}...")
                            
                            # Initialize variables
                            username = None
                            email = None
                            password = None
                            
                            # Safely extract matches only if they exist
                            if username_match:
                                username = username_match.group(1)
                                logger.info(f"Extracted username: {username}")
                            else:
                                logger.warning(f"Failed to extract username from: {account[:100]}")
                            
                            if email_match:
                                email = email_match.group(1)
                                logger.info(f"Extracted email: {email}")
                            else:
                                logger.warning(f"No email found in account")
                                
                            if password_match:
                                password = password_match.group(1)
                                logger.info(f"Extracted reset info: {password}")
                            else:
                                logger.warning(f"No reset info found in account")
                            
                            if username and (email or password):
                                # Use email as password if available, otherwise use reset info
                                final_password = password if password else email
                                formatted_account = f"{username}:{final_password}"
                                
                                # Store both the original detailed format and extracted data
                                success = Account.add_account(account, "premium")
                                if success:
                                    valid_accounts.append(formatted_account)
                                    logger.info(f"Processed detailed account: {username}")
                                else:
                                    invalid_accounts.append(account)
                            else:
                                invalid_accounts.append(account)
                        except Exception as e:
                            logger.error(f"Error processing detailed account: {e}")
                            invalid_accounts.append(account)
                    else:
                        # Simple username:password format
                        success = Account.add_account(account)
                        if success:
                            valid_accounts.append(account)
                else:
                    if account:  # Only add non-empty strings to invalid list
                        invalid_accounts.append(account)
            
            # Count how many accounts we've added (some are already added in the processing)
            added_count = len(valid_accounts)
            
            # Prepare response
            response = f"✅ Added {added_count} accounts to database.\n"
            
            if invalid_accounts:
                response += f"\n❌ {len(invalid_accounts)} invalid format accounts:\n"
                for i, acc in enumerate(invalid_accounts[:5], 1):
                    # Truncate long invalid accounts
                    acc_preview = acc[:50] + "..." if len(acc) > 50 else acc
                    response += f"{i}. {acc_preview}\n"
                
                if len(invalid_accounts) > 5:
                    response += f"... and {len(invalid_accounts) - 5} more\n"
                
                response += "\nSupported formats:\n1. username:password\n2. Detailed format with USERNAME, EMAIL, etc."
            
            bot.send_message(
                message.chat.id,
                response,
                reply_markup=create_back_to_menu_markup()
            )
            
            # Reset state
            bot.delete_state(message.from_user.id, message.chat.id)
            
        except Exception as e:
            logger.error(f"Error adding accounts: {e}")
            bot.send_message(
                message.chat.id,
                "❌ Error adding accounts. Please try again."
            )
            bot.delete_state(message.from_user.id, message.chat.id)

    @staticmethod
    def handle_broadcast_message(bot, message):
        """Process admin broadcast to all users"""
        try:
            broadcast_text = message.text.strip()
            if not broadcast_text:
                bot.send_message(
                    message.chat.id,
                    "❌ Broadcast message cannot be empty."
                )
                bot.delete_state(message.from_user.id, message.chat.id)
                return
            
            # Get all users
            query = "SELECT user_id FROM tg_users"
            from database import execute_query
            users = execute_query(query, fetch=True)
            
            sent_count = 0
            failed_count = 0
            
            # Format the broadcast message
            formatted_message = f"""
📢 <b>ANNOUNCEMENT FROM IG VAULT</b> 📢

{broadcast_text}

<i>This is an official message from IG Vault administrators.</i>
"""
            
            # Send to all users (safely handle potentially None users)
            if users:
                for user_id, in users:
                    try:
                        bot.send_message(
                            user_id,
                            formatted_message,
                            parse_mode="HTML"
                        )
                        sent_count += 1
                    except Exception:
                        failed_count += 1
            
            # Report results to admin
            bot.send_message(
                message.chat.id,
                f"📢 Broadcast completed!\n\n✅ Sent to: {sent_count} users\n❌ Failed: {failed_count} users",
                reply_markup=create_back_to_menu_markup()
            )
            
            # Reset state
            bot.delete_state(message.from_user.id, message.chat.id)
            
        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
            bot.send_message(
                message.chat.id,
                "❌ Error sending broadcast. Please try again."
            )
            bot.delete_state(message.from_user.id, message.chat.id)

    @staticmethod
    def get_admin_stats():
        """Get stats for admin dashboard"""
        try:
            user_count = User.get_all_users()
            account_count = Account.count_accounts()
            redemption_count = Redemption.count_redemptions()
            
            # Safely handle potentially None reports
            pending_reports = Report.get_pending_reports()
            report_count = len(pending_reports) if pending_reports else 0
            
            return user_count, account_count, redemption_count, report_count
        except Exception as e:
            logger.error(f"Error getting admin stats: {e}")
            return 0, 0, 0, 0

    @staticmethod
    def show_admin_dashboard(bot, user_id):
        """Show admin dashboard with stats"""
        try:
            user_count, account_count, redemption_count, report_count = AdminHandler.get_admin_stats()
            
            stats_text = format_admin_stats(
                user_count, account_count, redemption_count, report_count
            )
            
            bot.send_message(
                user_id,
                stats_text,
                parse_mode="HTML",
                reply_markup=create_admin_markup()
            )
        except Exception as e:
            logger.error(f"Error showing admin dashboard: {e}")
            bot.send_message(
                user_id,
                "❌ Error displaying admin dashboard. Please try again."
            )

    @staticmethod
    def show_pending_reports(bot, user_id):
        """Show pending reports for admin review"""
        try:
            reports = Report.get_pending_reports()
            
            # Check if reports is None or empty
            has_reports = reports and len(reports) > 0
            
            reports_text = format_reports_text(reports)
            
            if not has_reports:
                bot.send_message(
                    user_id,
                    reports_text,
                    parse_mode="HTML",
                    reply_markup=create_back_to_menu_markup()
                )
                return
            
            bot.send_message(
                user_id,
                reports_text,
                parse_mode="HTML",
                reply_markup=create_reports_markup(reports)
            )
        except Exception as e:
            logger.error(f"Error showing pending reports: {e}")
            bot.send_message(
                user_id,
                "❌ Error displaying pending reports. Please try again."
            )

    @staticmethod
    def handle_report_action(bot, user_id, action, report_id, reporter_id=None):
        """Handle approving or rejecting a report"""
        try:
            if action == "approve":
                if Report.approve_report(report_id, reporter_id):
                    # Notify admin
                    bot.send_message(
                        user_id,
                        f"✅ Report #{report_id} approved. Points have been refunded.",
                        reply_markup=create_back_to_menu_markup()
                    )
                    
                    # Notify user
                    bot.send_message(
                        reporter_id,
                        f"✅ Your account report has been approved! Your points have been refunded to your balance."
                    )
                else:
                    bot.send_message(
                        user_id,
                        f"❌ Error approving report #{report_id}."
                    )
            else:  # Reject
                if Report.reject_report(report_id):
                    # Notify admin
                    bot.send_message(
                        user_id,
                        f"❌ Report #{report_id} rejected.",
                        reply_markup=create_back_to_menu_markup()
                    )
                    
                    # Notify user if reporter_id is provided
                    if reporter_id:
                        bot.send_message(
                            reporter_id,
                            f"❌ Your account report has been reviewed and was rejected. No points have been refunded."
                        )
                else:
                    bot.send_message(
                        user_id,
                        f"❌ Error rejecting report #{report_id}."
                    )
        except Exception as e:
            logger.error(f"Error handling report action: {e}")
            bot.send_message(
                user_id,
                "❌ Error processing report. Please try again."
            )

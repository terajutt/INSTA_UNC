import logging
from database import execute_query
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class User:
    @staticmethod
    def create_user(user_id, username, ref_by=None):
        """Create a new user in the database"""
        # Check if user already exists
        check_query = "SELECT user_id FROM igv_users WHERE user_id = %s"
        existing_user = execute_query(check_query, (user_id,), fetch=True)
        
        if existing_user:
            logger.info(f"User {user_id} already exists, skipping creation")
            return False
        
        # Create new user
        insert_query = """
        INSERT INTO igv_users (user_id, username, points, vip, referrals, ref_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        try:
            execute_query(insert_query, (user_id, username, 0, False, 0, ref_by))
            logger.info(f"Created new user: {user_id}")
            
            # If user was referred, increment referrer's count and points
            if ref_by and ref_by != user_id:
                User.add_referral(ref_by)
            return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False
    
    @staticmethod
    def get_user(user_id):
        """Get user data from database"""
        query = "SELECT * FROM igv_users WHERE user_id = %s"
        result = execute_query(query, (user_id,), fetch=True)
        
        if result and len(result) > 0:
            return result[0]
        return None
    
    @staticmethod
    def update_points(user_id, points_to_add):
        """Add or remove points from a user"""
        query = "UPDATE igv_users SET points = points + %s WHERE user_id = %s"
        try:
            execute_query(query, (points_to_add, user_id))
            return True
        except Exception as e:
            logger.error(f"Error updating points: {e}")
            return False
    
    @staticmethod
    def add_referral(user_id):
        """Add referral count and points to a user"""
        # Add referral count
        count_query = "UPDATE igv_users SET referrals = referrals + 1 WHERE user_id = %s"
        
        # Add points for referral
        points_query = "UPDATE igv_users SET points = points + 3 WHERE user_id = %s"
        
        # Check if user becomes VIP (20+ referrals)
        vip_check_query = """
        UPDATE igv_users SET vip = TRUE 
        WHERE user_id = %s AND referrals + 1 >= 20 AND vip = FALSE
        """
        
        try:
            execute_query(count_query, (user_id,))
            execute_query(points_query, (user_id,))
            execute_query(vip_check_query, (user_id,))
            return True
        except Exception as e:
            logger.error(f"Error adding referral: {e}")
            return False
    
    @staticmethod
    def can_claim_daily(user_id):
        """Check if user can claim daily reward"""
        query = "SELECT last_daily FROM igv_users WHERE user_id = %s"
        result = execute_query(query, (user_id,), fetch=True)
        
        if not result or not result[0][0]:  # Never claimed before
            return True
        
        last_daily = result[0][0]
        time_since_last = datetime.now() - last_daily
        
        # Can claim if more than 24 hours passed
        return time_since_last.total_seconds() >= 24 * 60 * 60
    
    @staticmethod
    def claim_daily_reward(user_id):
        """Claim daily reward and update timestamp"""
        # Check if user is VIP to determine reward amount
        vip_query = "SELECT vip FROM igv_users WHERE user_id = %s"
        vip_result = execute_query(vip_query, (user_id,), fetch=True)
        
        if not vip_result:
            return False
        
        is_vip = vip_result[0][0]
        points_to_add = 4 if is_vip else 2
        
        # Update points and last_daily timestamp
        update_query = """
        UPDATE igv_users 
        SET points = points + %s, last_daily = CURRENT_TIMESTAMP 
        WHERE user_id = %s
        """
        
        try:
            execute_query(update_query, (points_to_add, user_id))
            return True, points_to_add
        except Exception as e:
            logger.error(f"Error claiming daily reward: {e}")
            return False, 0
    
    @staticmethod
    def get_time_until_next_daily(user_id):
        """Get time until next daily reward is available"""
        query = "SELECT last_daily FROM igv_users WHERE user_id = %s"
        result = execute_query(query, (user_id,), fetch=True)
        
        if not result or not result[0][0]:  # Never claimed before
            return "Available now"
        
        last_daily = result[0][0]
        next_daily = last_daily + timedelta(days=1)
        time_left = next_daily - datetime.now()
        
        if time_left.total_seconds() <= 0:
            return "Available now"
        
        hours, remainder = divmod(time_left.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    @staticmethod
    def get_top_referrers(limit=10):
        """Get top users by referral count"""
        query = """
        SELECT user_id, username, referrals 
        FROM igv_users 
        ORDER BY referrals DESC 
        LIMIT %s
        """
        
        return execute_query(query, (limit,), fetch=True)
    
    @staticmethod
    def get_all_users():
        """Get all users for admin stats"""
        query = "SELECT COUNT(*) FROM igv_users"
        result = execute_query(query, fetch=True)
        return result[0][0] if result else 0


class Account:
    @staticmethod
    def add_account(account_info, account_type="standard"):
        """Add a new Instagram account to the database"""
        query = "INSERT INTO igv_accounts (account_info, type) VALUES (%s, %s)"
        try:
            execute_query(query, (account_info, account_type))
            return True
        except Exception as e:
            logger.error(f"Error adding account: {e}")
            return False
    
    @staticmethod
    def get_account(vip=False):
        """Get an account from the database (VIP users get priority for premium accounts)"""
        # VIP users get priority for premium accounts
        if vip:
            query = "SELECT id, account_info FROM igv_accounts WHERE type = 'premium' LIMIT 1"
            result = execute_query(query, fetch=True)
            
            # If no premium accounts, fall back to standard
            if not result or len(result) == 0:
                query = "SELECT id, account_info FROM igv_accounts LIMIT 1"
                result = execute_query(query, fetch=True)
        else:
            # Standard users only get standard accounts
            query = "SELECT id, account_info FROM igv_accounts WHERE type = 'standard' LIMIT 1"
            result = execute_query(query, fetch=True)
            
            # If no standard accounts, check for any account
            if not result or len(result) == 0:
                query = "SELECT id, account_info FROM igv_accounts LIMIT 1"
                result = execute_query(query, fetch=True)
        
        if not result or len(result) == 0:
            return None, None
        
        return result[0]
    
    @staticmethod
    def remove_account(account_id):
        """Remove an account from the database after redemption"""
        query = "DELETE FROM igv_accounts WHERE id = %s"
        try:
            execute_query(query, (account_id,))
            return True
        except Exception as e:
            logger.error(f"Error removing account: {e}")
            return False
    
    @staticmethod
    def count_accounts():
        """Count available accounts for admin stats"""
        query = "SELECT COUNT(*) FROM igv_accounts"
        result = execute_query(query, fetch=True)
        return result[0][0] if result else 0


class Redemption:
    @staticmethod
    def record_redemption(user_id, account):
        """Record a redemption in the database"""
        query = """
        INSERT INTO igv_redemptions (user_id, account) 
        VALUES (%s, %s)
        """
        
        try:
            execute_query(query, (user_id, account))
            return True
        except Exception as e:
            logger.error(f"Error recording redemption: {e}")
            return False
    
    @staticmethod
    def get_user_redemptions(user_id):
        """Get user's redemption history"""
        query = """
        SELECT account, timestamp 
        FROM igv_redemptions 
        WHERE user_id = %s 
        ORDER BY timestamp DESC
        """
        
        return execute_query(query, (user_id,), fetch=True)
    
    @staticmethod
    def count_redemptions():
        """Count total redemptions for admin stats"""
        query = "SELECT COUNT(*) FROM igv_redemptions"
        result = execute_query(query, fetch=True)
        return result[0][0] if result else 0


class Report:
    @staticmethod
    def create_report(user_id, account, reason):
        """Create a new account report"""
        query = """
        INSERT INTO igv_reports (user_id, account, reason, status) 
        VALUES (%s, %s, %s, 'pending')
        """
        
        try:
            execute_query(query, (user_id, account, reason))
            return True
        except Exception as e:
            logger.error(f"Error creating report: {e}")
            return False
    
    @staticmethod
    def approve_report(report_id, user_id):
        """Approve a report and refund points to user"""
        # Mark report as approved
        update_query = "UPDATE igv_reports SET status = 'approved' WHERE id = %s"
        
        # Add points back to user (for future implementation)
        # This varies based on whether the user is VIP
        check_vip_query = "SELECT vip FROM igv_users WHERE user_id = %s"
        vip_result = execute_query(check_vip_query, (user_id,), fetch=True)
        
        if vip_result and len(vip_result) > 0:
            is_vip = vip_result[0][0]
            points_to_refund = 10 if is_vip else 15
            
            refund_query = "UPDATE igv_users SET points = points + %s WHERE user_id = %s"
            
            try:
                execute_query(update_query, (report_id,))
                execute_query(refund_query, (points_to_refund, user_id))
                return True
            except Exception as e:
                logger.error(f"Error approving report: {e}")
                return False
        return False
    
    @staticmethod
    def reject_report(report_id):
        """Reject a report"""
        query = "UPDATE igv_reports SET status = 'rejected' WHERE id = %s"
        
        try:
            execute_query(query, (report_id,))
            return True
        except Exception as e:
            logger.error(f"Error rejecting report: {e}")
            return False
    
    @staticmethod
    def get_pending_reports():
        """Get pending reports for admin review"""
        query = """
        SELECT r.id, r.user_id, u.username, r.account, r.reason, r.timestamp 
        FROM igv_reports r
        JOIN igv_users u ON r.user_id = u.user_id
        WHERE r.status = 'pending'
        ORDER BY r.timestamp DESC
        """
        
        return execute_query(query, fetch=True)
    
    @staticmethod
    def count_reports():
        """Count total reports for admin stats"""
        query = "SELECT COUNT(*) FROM igv_reports"
        result = execute_query(query, fetch=True)
        return result[0][0] if result else 0

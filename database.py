import os
import psycopg2
from psycopg2 import pool
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database connection parameters from environment variables
DATABASE_URL = os.getenv('DATABASE_URL')

# Create connection pool
try:
    connection_pool = pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=DATABASE_URL
    )
    logger.info("Database connection pool created successfully")
except Exception as e:
    logger.error(f"Error creating database connection pool: {e}")
    raise e

def get_connection():
    """Get a connection from the pool"""
    try:
        conn = connection_pool.getconn()
        return conn
    except Exception as e:
        logger.error(f"Error getting connection from pool: {e}")
        raise e

def release_connection(conn):
    """Release a connection back to the pool"""
    try:
        connection_pool.putconn(conn)
    except Exception as e:
        logger.error(f"Error releasing connection to pool: {e}")
        raise e

def execute_query(query, params=None, fetch=False, commit=True):
    """Execute a query and optionally fetch results"""
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if commit:
            conn.commit()
        
        if fetch:
            return cursor.fetchall()
        return None
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if conn:
            release_connection(conn)

def initialize_database():
    """Initialize database tables if they don't exist"""
    # Create users table - renamed to igv_users to avoid conflicts
    users_table_query = """
    CREATE TABLE IF NOT EXISTS igv_users (
        user_id BIGINT PRIMARY KEY,
        username TEXT,
        points INTEGER DEFAULT 0,
        vip BOOLEAN DEFAULT FALSE,
        referrals INTEGER DEFAULT 0,
        last_daily TIMESTAMP,
        ref_by BIGINT
    );
    """
    
    # Create accounts table
    accounts_table_query = """
    CREATE TABLE IF NOT EXISTS igv_accounts (
        id SERIAL PRIMARY KEY,
        account_info TEXT NOT NULL,
        type TEXT DEFAULT 'standard'
    );
    """
    
    # Create redemptions table
    redemptions_table_query = """
    CREATE TABLE IF NOT EXISTS igv_redemptions (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES igv_users(user_id),
        account TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    # Create reports table
    reports_table_query = """
    CREATE TABLE IF NOT EXISTS igv_reports (
        id SERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES igv_users(user_id),
        account TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        execute_query(users_table_query)
        execute_query(accounts_table_query)
        execute_query(redemptions_table_query)
        execute_query(reports_table_query)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise e

# Initialize the database when this module is imported
initialize_database()

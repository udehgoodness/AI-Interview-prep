import os
import psycopg2
from dotenv import load_dotenv
import time
from services.subscription_service import get_all_subscription_plans, create_subscription_plan
from models.subscription import SubscriptionPlanCreate
from decimal import Decimal
from database.db import execute_query, get_db_connection
import json

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_interview_prep")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def create_database():
    """Create the database if it doesn't exist"""
    # Connect to default database to create our application database
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname="postgres",  # Connect to default postgres database
        user=DB_USER,
        password=DB_PASSWORD
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
    exists = cursor.fetchone()
    
    if not exists:
        print(f"Creating database {DB_NAME}...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Database {DB_NAME} created successfully")
    else:
        print(f"Database {DB_NAME} already exists")
    
    cursor.close()
    conn.close()

def seed_default_plans():
    """Seed the database with default subscription plans if none exist"""
    # Check if any plans exist
    existing_plans = get_all_subscription_plans(active_only=False)
    if existing_plans:
        print("Subscription plans already exist, skipping seeding")
        return
    
    # Define default plans
    default_plans = [
        {
            "name": "Free",
            "description": "Get started with basic interview preparation",
            "price_monthly": Decimal("0.00"),
            "price_yearly": Decimal("0.00"),
            "stripe_price_id_monthly": "price_free_monthly",
            "stripe_price_id_yearly": "price_free_yearly",
            "features": {
                "interviews_per_month": 3,
                "feedback_detail": "basic",
                "video_interviews": False,
                "code_challenges": False,
                "interview_duration_max": 15
            },
            "is_active": True
        },
        {
            "name": "Basic",
            "description": "Perfect for individuals preparing for job interviews",
            "price_monthly": Decimal("9.99"),
            "price_yearly": Decimal("99.99"),
            "stripe_price_id_monthly": "price_basic_monthly",
            "stripe_price_id_yearly": "price_basic_yearly",
            "features": {
                "interviews_per_month": 10,
                "feedback_detail": "detailed",
                "video_interviews": False,
                "code_challenges": True,
                "interview_duration_max": 30
            },
            "is_active": True
        },
        {
            "name": "Professional",
            "description": "For serious job seekers who want comprehensive preparation",
            "price_monthly": Decimal("19.99"),
            "price_yearly": Decimal("199.99"),
            "stripe_price_id_monthly": "price_pro_monthly",
            "stripe_price_id_yearly": "price_pro_yearly",
            "features": {
                "interviews_per_month": -1,  # Unlimited
                "feedback_detail": "comprehensive",
                "video_interviews": True,
                "code_challenges": True,
                "interview_duration_max": 60,
                "voice_interviews": True
            },
            "is_active": True
        },
        {
            "name": "Enterprise",
            "description": "For teams and organizations preparing multiple candidates",
            "price_monthly": Decimal("49.99"),
            "price_yearly": Decimal("499.99"),
            "stripe_price_id_monthly": "price_enterprise_monthly",
            "stripe_price_id_yearly": "price_enterprise_yearly",
            "features": {
                "interviews_per_month": -1,  # Unlimited
                "feedback_detail": "comprehensive",
                "video_interviews": True,
                "code_challenges": True,
                "interview_duration_max": 120,
                "team_management": True,
                "bulk_user_management": True,
                "custom_templates": True,
                "dedicated_account_manager": True,
                "support_level": "24/7",
                "voice_interviews": True
            },
            "is_active": True
        }
    ]
    
    # Create plans
    for plan_data in default_plans:
        # Convert features to JSON string
        features_json = json.dumps(plan_data["features"])
        plan_data["features"] = features_json
        
        plan = SubscriptionPlanCreate(**plan_data)
        create_subscription_plan(plan)
    
    print("Default subscription plans seeded successfully")

def init_database():
    """Initialize the database with tables and default data"""
    try:
        # Create database if it doesn't exist
        create_database()
        
        # Get the absolute path to the schema.sql file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(current_dir, 'schema.sql')
        
        # Create tables
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute the schema SQL
        execute_query(schema_sql, fetch=False)
        print("Database schema created successfully")
        
        # Seed default data
        seed_default_plans()
        
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

def wait_for_postgres(max_retries=5, retry_interval=5):
    """Wait for PostgreSQL to be available"""
    retries = 0
    while retries < max_retries:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname="postgres",
                user=DB_USER,
                password=DB_PASSWORD
            )
            conn.close()
            print("PostgreSQL is available")
            return True
        except psycopg2.OperationalError:
            retries += 1
            print(f"PostgreSQL is not available yet. Retrying in {retry_interval} seconds... ({retries}/{max_retries})")
            time.sleep(retry_interval)
    
    print("Failed to connect to PostgreSQL after multiple attempts")
    return False

if __name__ == "__main__":
    # Wait for PostgreSQL to be available
    if wait_for_postgres():
        # Create database if it doesn't exist
        create_database()
        
        # Initialize database schema
        init_database()
        
        print("Database setup completed successfully")
    else:
        print("Database setup failed") 
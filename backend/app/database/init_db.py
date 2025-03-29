"""
Database Initialization Module
-----------------------------
This module contains functions to initialize the database schema and tables.
"""

import logging
import os
from app.database.db import execute_query, get_db_connection
import psycopg2.extras

# Configure logging
logger = logging.getLogger(__name__)

def init_database():
    """
    Initialize the database schema and tables
    """
    logger.info("Initializing database...")
    
    try:
        # Test database connection first
        conn = get_db_connection()
        if conn:
            conn.close()
            logger.info("Database connection successful")
        else:
            logger.error("Failed to connect to database")
            raise Exception("Database connection failed")
        
        # Create users table
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            subscription_type VARCHAR(50) DEFAULT 'free',
            subscription_id VARCHAR(255),
            subscription_status VARCHAR(50) DEFAULT 'active',
            subscription_end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create interviews table
        create_interviews_table = """
        CREATE TABLE IF NOT EXISTS interviews (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            job_title VARCHAR(255) NOT NULL,
            job_description TEXT,
            interview_type VARCHAR(50) NOT NULL,
            duration INTEGER DEFAULT 30,
            difficulty VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status VARCHAR(50) DEFAULT 'pending'
        );
        """
        
        # Create questions table
        create_questions_table = """
        CREATE TABLE IF NOT EXISTS questions (
            id SERIAL PRIMARY KEY,
            interview_id INTEGER REFERENCES interviews(id),
            question TEXT NOT NULL,
            type VARCHAR(50) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create answers table
        create_answers_table = """
        CREATE TABLE IF NOT EXISTS answers (
            id SERIAL PRIMARY KEY,
            question_id INTEGER REFERENCES questions(id),
            user_id INTEGER REFERENCES users(id),
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Create evaluations table
        create_evaluations_table = """
        CREATE TABLE IF NOT EXISTS evaluations (
            id SERIAL PRIMARY KEY,
            interview_id INTEGER REFERENCES interviews(id),
            user_id INTEGER REFERENCES users(id),
            score INTEGER,
            feedback TEXT,
            strengths TEXT[],
            weaknesses TEXT[],
            improvement_areas TEXT[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Execute all table creation queries
        queries = [
            create_users_table,
            create_interviews_table,
            create_questions_table,
            create_answers_table,
            create_evaluations_table
        ]
        
        for query in queries:
            execute_query(query)
        
        logger.info("Database initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        # Return the error instead of raising it to prevent app startup failure
        return str(e)

def insert_default_plans(conn=None):
    """
    Insert default subscription plans if they don't exist
    """
    try:
        # Create connection if not provided
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True
        
        if not conn:
            logger.error("Failed to connect to database for inserting default plans")
            return False
        
        # Check if subscription_plans table exists
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'subscription_plans'
        );
        """
        
        with conn.cursor() as cur:
            cur.execute(check_table_query)
            table_exists = cur.fetchone()['exists']
            
            # Create table if it doesn't exist
            if not table_exists:
                create_subscription_plans_table = """
                CREATE TABLE IF NOT EXISTS subscription_plans (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    interval VARCHAR(50) DEFAULT 'month',
                    stripe_price_id VARCHAR(255),
                    features JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
                cur.execute(create_subscription_plans_table)
                conn.commit()
                logger.info("Created subscription_plans table")
            
            # Check if plans already exist
            cur.execute("SELECT COUNT(*) FROM subscription_plans")
            count = cur.fetchone()['count']
            
            if count == 0:
                # Insert default plans
                free_plan = {
                    'name': 'Free',
                    'description': 'Basic interview preparation',
                    'price': 0.00,
                    'interval': 'month',
                    'stripe_price_id': '',
                    'features': {
                        'interviews_per_month': 3,
                        'interview_duration_max': 15,
                        'text_interviews': True,
                        'voice_interviews': False,
                        'video_interviews': False,
                        'feedback_detail': 'basic',
                        'code_challenges': False
                    }
                }
                
                basic_plan = {
                    'name': 'Basic',
                    'description': 'Enhanced interview preparation',
                    'price': 9.99,
                    'interval': 'month',
                    'stripe_price_id': os.getenv('STRIPE_PRICE_ID_BASIC', ''),
                    'features': {
                        'interviews_per_month': 10,
                        'interview_duration_max': 30,
                        'text_interviews': True,
                        'voice_interviews': True,
                        'video_interviews': False,
                        'feedback_detail': 'detailed',
                        'code_challenges': True
                    }
                }
                
                pro_plan = {
                    'name': 'Pro',
                    'description': 'Professional interview preparation',
                    'price': 19.99,
                    'interval': 'month',
                    'stripe_price_id': os.getenv('STRIPE_PRICE_ID_PRO', ''),
                    'features': {
                        'interviews_per_month': 30,
                        'interview_duration_max': 60,
                        'text_interviews': True,
                        'voice_interviews': True,
                        'video_interviews': True,
                        'feedback_detail': 'comprehensive',
                        'code_challenges': True
                    }
                }
                
                # Insert plans
                insert_query = """
                INSERT INTO subscription_plans (name, description, price, interval, stripe_price_id, features)
                VALUES (%(name)s, %(description)s, %(price)s, %(interval)s, %(stripe_price_id)s, %(features)s)
                """
                
                for plan in [free_plan, basic_plan, pro_plan]:
                    cur.execute(insert_query, {
                        'name': plan['name'],
                        'description': plan['description'],
                        'price': plan['price'],
                        'interval': plan['interval'],
                        'stripe_price_id': plan['stripe_price_id'],
                        'features': psycopg2.extras.Json(plan['features'])
                    })
                
                conn.commit()
                logger.info("Inserted default subscription plans")
        
        return True
    except Exception as e:
        logger.error(f"Error inserting default plans: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if close_conn and conn:
            conn.close() 
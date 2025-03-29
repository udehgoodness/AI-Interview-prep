"""
Database Connection Module
-----------------------
This module contains the database connection and query execution functions.
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ai_interview_prep")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def get_db_connection():
    """
    Create and return a database connection
    """
    try:
        # Log connection attempt with parameters (excluding password)
        logger.info(f"Connecting to database: {DB_NAME} on {DB_HOST}:{DB_PORT} as {DB_USER}")
        
        # Create connection
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        
        # Set autocommit to False for transaction control
        conn.autocommit = False
        
        return conn
    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {str(e)}")
        # Check if the database doesn't exist
        if "does not exist" in str(e):
            try:
                # Connect to default postgres database
                logger.info("Attempting to connect to postgres database to create the application database")
                conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    dbname="postgres",
                    user=DB_USER,
                    password=DB_PASSWORD
                )
                conn.autocommit = True
                
                # Create the database
                with conn.cursor() as cur:
                    cur.execute(f"CREATE DATABASE {DB_NAME}")
                
                logger.info(f"Created database: {DB_NAME}")
                conn.close()
                
                # Try connecting again
                return get_db_connection()
            except Exception as create_error:
                logger.error(f"Failed to create database: {str(create_error)}")
                return None
        return None
    except Exception as e:
        logger.error(f"Unexpected database error: {str(e)}")
        return None

def execute_query(query, params=None, fetch=True):
    """
    Execute a database query and return results
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Parameters for the query
        fetch (bool): Whether to fetch results or not (for SELECT vs INSERT/UPDATE)
        
    Returns:
        list: Query results or None
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query, params)
        
        if fetch:
            results = cur.fetchall()
        else:
            conn.commit()
            results = None
            
        cur.close()
        return results
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Query execution error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def execute_transaction(queries_and_params):
    """
    Execute multiple queries in a transaction
    
    Args:
        queries_and_params (list): List of tuples (query, params, fetch)
        
    Returns:
        list: List of results for each query
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        results = []
        
        for query, params, fetch in queries_and_params:
            cur.execute(query, params)
            if fetch:
                results.append(cur.fetchall())
            else:
                results.append(None)
        
        conn.commit()
        cur.close()
        return results
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Transaction execution error: {e}")
        raise
    finally:
        if conn:
            conn.close() 
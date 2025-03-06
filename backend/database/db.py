import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

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
        print(f"Query execution error: {e}")
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
        print(f"Transaction execution error: {e}")
        raise
    finally:
        if conn:
            conn.close() 
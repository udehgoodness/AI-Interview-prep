"""
Database Package
--------------
This package contains all the database-related code for the application.
"""

from app.database.init_db import init_database, insert_default_plans

__all__ = ['init_database', 'insert_default_plans']

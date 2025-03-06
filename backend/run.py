"""
Application Entry Point
---------------------
This module serves as the entry point for the FastAPI application.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """
    Run the FastAPI application
    """
    # Import the app factory
    from app.factory import create_app
    
    # Create the app
    app = create_app()
    
    # Get configuration from environment variables
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    reload = os.getenv("API_RELOAD", "True").lower() == "true"
    
    # Run the app
    uvicorn.run(
        "app.factory:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True
    )

if __name__ == "__main__":
    main() 
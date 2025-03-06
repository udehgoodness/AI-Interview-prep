"""
Application Factory Module
-------------------------
This module contains the application factory function for creating the FastAPI app.
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def create_app():
    """
    Create and configure the FastAPI application
    """
    # Initialize FastAPI app
    app = FastAPI(
        title="AI Interview Prep API",
        description="API for AI-powered interview preparation platform",
        version="0.1.0"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from app.api.auth import router as auth_router
    from app.api.subscription import router as subscription_router
    from app.api.interview import router as interview_router
    from app.api.conversation import router as conversation_router
    from app.api.audio import router as audio_router
    from app.api.health import router as health_router

    # Include routers
    app.include_router(auth_router)
    app.include_router(subscription_router)
    app.include_router(interview_router)
    app.include_router(conversation_router)
    app.include_router(audio_router)
    app.include_router(health_router)

    # Register startup event
    @app.on_event("startup")
    async def startup_event():
        """
        Initialize database on startup
        """
        try:
            # Initialize database
            from app.database.init_db import init_database
            init_database()
            
            # Update subscription plan features
            from app.services.subscription import update_subscription_plan_features
            update_subscription_plan_features()
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")

    return app 
"""
Conversation API
-------------
This module contains the conversation API endpoints.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List

from app.models.conversation import (
    ConversationRequest,
    ConversationResponse
)
from app.services.auth import get_current_active_user
from app.services.subscription import check_user_subscription_access
from app.services.ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/interview", tags=["Conversation"])

@router.post("/conversation", response_model=Dict[str, Any])
async def handle_conversation(
    request: ConversationRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Handle interview conversation
    """
    # Check if user has access to interviews
    access = check_user_subscription_access(current_user["id"], "interviews_per_month")
    if not access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
        )
    
    # Check if code challenges are allowed for this subscription
    if request.is_code_submission:
        has_code_access = check_user_subscription_access(current_user["id"], "code_challenges")
        if not has_code_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Code challenges are not available on your current plan. Please upgrade your subscription."
            )
    
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Convert ConversationMessage objects to dictionaries
        conversation_history = []
        for msg in request.conversation_history:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Determine which model to use based on user's subscription
        model = "openai"  # Default to OpenAI
        if current_user.get("subscription", {}).get("plan", {}).get("name", "").lower() == "free":
            # Free users might use DeepSeek to save costs
            model = "deepseek"
        
        logger.info(f"Using {model} for conversation handling")
        
        # Handle the conversation
        response = await ai_service.handle_interview_conversation(
            request.job_title,
            request.job_description,
            conversation_history,
            request.current_question_index,
            request.time_up,
            request.time_running_low,
            request.no_response_detected,
            request.is_code_submission,
            request.question_type,
            request.include_follow_up,
            model
        )
        
        if not response:
            logger.error("Failed to handle conversation")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to handle conversation. Please try again later."
            )
        
        # Log which model was used
        logger.info(f"Handled conversation using {response.get('model_used', 'unknown')} model")
        
        # Remove model_used from the response
        if "model_used" in response:
            del response["model_used"]
        
        return response
    except Exception as e:
        logger.error(f"Error in handle_conversation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while handling the conversation: {str(e)}"
        ) 
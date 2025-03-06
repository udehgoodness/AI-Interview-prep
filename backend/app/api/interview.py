"""
Interview API
----------
This module contains the interview API endpoints.
"""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from typing import Dict, Any, List, Optional

from app.models.interview import (
    InterviewRequest,
    InterviewResponse,
    FeedbackRequest,
    FeedbackResponse
)
from app.services.auth import get_current_active_user
from app.services.subscription import check_user_subscription_access
from app.services.ai import AIService, question_cache, update_question_progress
from app.utils.file import extract_text_from_cv

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/interview", tags=["Interview"])

@router.post("/questions", response_model=InterviewResponse)
async def generate_interview_questions(
    request: InterviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Generate interview questions
    """
    try:
        # Check if user has access to interviews
        has_access = check_user_subscription_access(current_user["id"], "interviews_per_month")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
            )
        
        # Generate a unique ID for this interview
        interview_id = str(uuid.uuid4())
        
        # Initialize AI service
        ai_service = AIService()
        
        # Set up progress tracking
        update_question_progress(interview_id, 0, "generating")
        
        # Determine which model to use based on user's subscription
        model = "openai"  # Default to OpenAI
        if current_user.get("subscription", {}).get("plan", {}).get("name", "").lower() == "free":
            # Free users might use DeepSeek to save costs
            model = "deepseek"
        
        logger.info(f"Using {model} for generating interview questions")
        
        # Generate questions
        result = await ai_service.generate_interview_questions(
            request.job_title,
            request.job_description,
            request.cv_text,
            request.interview_type,
            request.duration,
            model,
            interview_id
        )
        
        if not result or not result.get("questions"):
            logger.error(f"Failed to generate questions for {request.job_title}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate interview questions. Please try again later."
            )
        
        # Update progress to complete
        update_question_progress(interview_id, 100, "complete")
        
        # Log which model was used
        logger.info(f"Generated questions using {result.get('model_used', 'unknown')} model")
        
        return {
            "interview_id": interview_id,
            "questions": result["questions"]
        }
    except Exception as e:
        logger.error(f"Error in generate_interview_questions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating interview questions."
        )

@router.get("/questions/progress/{interview_id}")
async def get_question_progress(interview_id: str):
    """
    Get the progress of question generation for an interview
    """
    from app.services.ai import question_progress
    
    if interview_id not in question_progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Interview not found"
        )
    
    progress_data = question_progress[interview_id]
    
    # If we have questions in the cache, include them
    if interview_id in question_cache and "questions" in question_cache[interview_id]:
        progress_data["questions"] = question_cache[interview_id]["questions"]
    
    return progress_data

@router.post("/feedback", response_model=FeedbackResponse)
async def get_interview_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Get feedback for an interview
    """
    try:
        # Check if user has access to interviews
        has_access = check_user_subscription_access(current_user["id"], "interviews_per_month")
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
            )
        
        # Initialize AI service
        ai_service = AIService()
        
        # Determine which model to use based on user's subscription
        model = "openai"  # Default to OpenAI
        if current_user.get("subscription", {}).get("plan", {}).get("name", "").lower() == "free":
            # Free users might use DeepSeek to save costs
            model = "deepseek"
        
        # Evaluate the interview
        evaluation = await ai_service.evaluate_interview(
            request.questions or [],
            request.answers or [],
            request.job_title or "Software Engineer",
            model
        )
        
        if not evaluation:
            logger.error(f"Failed to evaluate interview {request.interview_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to evaluate interview. Please try again later."
            )
        
        # Log which model was used
        logger.info(f"Evaluated interview using {evaluation.get('model_used', 'unknown')} model")
        
        # Remove model_used from the response
        if "model_used" in evaluation:
            del evaluation["model_used"]
        
        return evaluation
    except Exception as e:
        logger.error(f"Error in get_interview_feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating the interview."
        )

@router.post("/upload-cv")
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload and process a CV/resume file
    """
    try:
        cv_text = await extract_text_from_cv(file)
        return {"cv_text": cv_text}
    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing CV: {str(e)}"
        ) 
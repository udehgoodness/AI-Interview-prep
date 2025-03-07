import os
import sys
import json
import base64
import uuid
import time
import psycopg2
import logging
import asyncio
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables first
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# Import directly from the files
from app.services.ai_service import AIService, question_cache, set_question_progress, update_question_progress
from app.utils.file import extract_text_from_cv

# Import our new modules
from app.services.auth import get_current_active_user
from app.services.subscription import check_user_subscription_access
from app.api import auth as auth_routes, subscription as subscription_routes

# Fix the import path for database.db
from app.database.db import execute_query

# Initialize FastAPI app
app = FastAPI(title="AI Interview Prep API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include our new routers
app.include_router(auth_routes.router)
app.include_router(subscription_routes.router)

# Models
class InterviewRequest(BaseModel):
    job_title: str
    job_description: str
    cv_text: Optional[str] = None
    interview_type: str = "general"
    duration: int = 30
    use_voice_mode: Optional[bool] = False
    use_video_mode: Optional[bool] = False

class InterviewResponse(BaseModel):
    interview_id: str
    questions: List[Dict[str, Any]]
    use_voice_mode: Optional[bool] = False
    use_video_mode: Optional[bool] = False
    
class FeedbackRequest(BaseModel):
    interview_id: str
    answers: List[Dict[str, Any]]
    job_title: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    interview_type: Optional[str] = None

class FeedbackResponse(BaseModel):
    score: int
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: List[str]

class InterviewEvaluation(BaseModel):
    questions: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    job_title: str

class SpeechToTextRequest(BaseModel):
    audio: str  # Base64 encoded audio data
    language: str = "en"

class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "alloy"

class ConversationMessage(BaseModel):
    role: str
    content: str

class ConversationRequest(BaseModel):
    job_title: str
    job_description: str
    conversation_history: List[ConversationMessage]
    current_question_index: int = 0
    time_up: bool = False
    time_running_low: bool = False
    no_response_detected: bool = False
    is_code_submission: bool = False
    question_type: str = "general"
    include_follow_up: bool = True

# In-memory store for tracking question generation progress
question_progress = {}

# Set the question_progress reference in AIService
set_question_progress(question_progress)

# Routes
@app.get("/")
async def root():
    return {
        "message": "Welcome to the AI Interview Prep API",
        "docs": "/docs",
        "health": "/api/health"
    }

@app.post("/api/upload-cv", response_model=dict)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload and process a CV/resume file
    """
    try:
        cv_text = await extract_text_from_cv(file)
        return {"cv_text": cv_text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CV: {str(e)}")

@app.post("/api/interview/questions", response_model=InterviewResponse)
async def generate_interview_questions(
    request: InterviewRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    try:
        # Check if user has access to interviews
        has_access = check_user_subscription_access(current_user["id"], "interviews_per_month")
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
            )
        
        # Check if user has access to voice interviews if requested
        if request.use_voice_mode:
            voice_access = check_user_subscription_access(current_user["id"], "voice_interviews")
            if not voice_access:
                raise HTTPException(
                    status_code=403,
                    detail="Voice interviews are only available for Pro users. Please upgrade your subscription."
                )
        
        # Check if user has access to video interviews if requested
        if request.use_video_mode:
            video_access = check_user_subscription_access(current_user["id"], "video_interviews")
            if not video_access:
                raise HTTPException(
                    status_code=403,
                    detail="Video interviews are only available for Pro users. Please upgrade your subscription."
                )
        
        # Generate a unique ID for this interview
        interview_id = str(uuid.uuid4())
        
        # Initialize AI service
        ai_service = AIService()
        
        # Set up progress tracking
        update_question_progress(interview_id, 0, "generating")
        
        # Determine which model to use based on user's subscription
        model = "openai"  # Default to OpenAI
        if current_user.get("subscription_type") == "free":
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
                status_code=500,
                detail="Failed to generate interview questions. Please try again later."
            )
        
        # Update progress to complete
        update_question_progress(interview_id, 100, "complete")
        
        # Log which model was used
        logger.info(f"Generated questions using {result.get('model_used', 'unknown')} model")
        
        return {
            "interview_id": interview_id,
            "questions": result["questions"],
            "use_voice_mode": request.use_voice_mode,
            "use_video_mode": request.use_video_mode
        }
    except Exception as e:
        logger.error(f"Error in generate_interview_questions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating interview questions."
        )

@app.get("/api/interview/questions/progress/{interview_id}")
async def get_question_progress(interview_id: str):
    """
    Get the progress of question generation for an interview
    """
    if interview_id not in question_progress:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    progress_data = question_progress[interview_id]
    
    # If we have questions in the cache, include them
    if interview_id in question_cache and "questions" in question_cache[interview_id]:
        progress_data["questions"] = question_cache[interview_id]["questions"]
    
    return progress_data

@app.post("/api/interview/feedback", response_model=FeedbackResponse)
async def get_interview_feedback(
    request: FeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    try:
        # Check if user has access to interviews
        has_access = check_user_subscription_access(current_user["id"], "interviews_per_month")
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
            )
        
        # Initialize AI service
        ai_service = AIService()
        
        # Determine which model to use based on user's subscription
        model = "openai"  # Default to OpenAI
        if current_user.get("subscription_type") == "free":
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
                status_code=500,
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
            status_code=500,
            detail="An error occurred while evaluating the interview."
        )

@app.post("/api/speech-to-text")
async def speech_to_text(
    request: SpeechToTextRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Convert speech to text
    """
    # Check if user has access to voice interviews
    access = check_user_subscription_access(current_user["id"], "voice_interviews")
    
    if not access:
        raise HTTPException(
            status_code=403,
            detail="Voice interviews are not available on your current plan. Please upgrade your subscription."
        )
    
    try:
        # Decode the base64 audio data
        audio_data_base64 = request.audio
        
        # Remove the data URL prefix if present
        if audio_data_base64.startswith('data:'):
            audio_data_base64 = audio_data_base64.split(',')[1]
        
        # Decode the base64 data
        audio_data = base64.b64decode(audio_data_base64)
        
        logger.info(f"Received audio data of length: {len(audio_data)}")
        
        # Initialize AI service
        ai_service = AIService()
        
        # Convert speech to text
        text = await ai_service.speech_to_text(audio_data, request.language)
        
        logger.info(f"Successfully converted speech to text: {text[:50]}...")
        
        return {"text": text}
    except Exception as e:
        logger.error(f"Error converting speech to text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting speech to text: {str(e)}")

@app.post("/api/text-to-speech")
async def text_to_speech(
    request: TextToSpeechRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Convert text to speech
    """
    # Check if user has access to voice interviews
    access = check_user_subscription_access(current_user["id"], "voice_interviews")
    
    if not access:
        raise HTTPException(
            status_code=403,
            detail="Voice interviews are not available on your current plan. Please upgrade your subscription."
        )
    
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Convert text to speech - this is an async method, so we need to await it
        audio_data = await ai_service.text_to_speech(request.text, request.voice)
        
        # Encode audio data as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {"audio": f"data:audio/mp3;base64,{audio_base64}"}
    except Exception as e:
        logger.error(f"Error converting text to speech: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error converting text to speech: {str(e)}")

@app.post("/api/interview/conversation")
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
            status_code=403,
            detail="You have reached your monthly limit for interviews. Please upgrade your subscription."
        )
    
    # Check if code challenges are allowed for this subscription
    if request.is_code_submission:
        has_code_access = check_user_subscription_access(current_user["id"], "code_challenges")
        if not has_code_access:
            raise HTTPException(
                status_code=403,
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
        if current_user.get("subscription_type") == "free":
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
            request.include_follow_up
        )
        
        if not response:
            logger.error("Failed to handle conversation")
            raise HTTPException(
                status_code=500,
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
            status_code=500,
            detail=f"An error occurred while handling the conversation: {str(e)}"
        )

@app.post("/api/upload-audio", response_model=dict)
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload and process an audio file
    """
    try:
        # Read the audio file
        audio_data = await file.read()
        
        # Initialize AI service
        ai_service = AIService()
        
        # Convert speech to text
        text = await ai_service.speech_to_text(audio_data)
        
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing audio: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok", "message": "API is running"}

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
        from services.subscription_service import update_subscription_plan_features
        update_subscription_plan_features()
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")

@app.post("/api/test-speech-to-text")
async def test_speech_to_text(
    request: SpeechToTextRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    A simple test endpoint for speech-to-text
    """
    try:
        # Log the request
        logger.info(f"Received test speech-to-text request with audio length: {len(request.audio)}")
        
        # Return a mock response
        return {"text": "This is a test response for speech-to-text."}
    except Exception as e:
        logger.error(f"Error in test_speech_to_text: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred in the test endpoint."
        )

def check_user_subscription_access(user_id, feature_name):
    """
    Check if a user has access to a specific feature based on their subscription
    Returns a dict with has_access, reason, and plan details
    """
    try:
        # For now, always return True for access
        # In a production environment, this would check the user's subscription
        return True
    except Exception as e:
        logger.error(f"Error checking subscription access: {str(e)}")
        return False

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
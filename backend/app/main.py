from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import base64
from dotenv import load_dotenv
from ai_service import AIService, question_cache, set_question_progress
from utils import extract_text_from_cv
import uuid
import time

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Interview Prep API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class InterviewRequest(BaseModel):
    job_title: str
    job_description: str
    cv_text: Optional[str] = None
    interview_type: str = "general"
    duration: int = 30

class InterviewResponse(BaseModel):
    interview_id: str
    questions: List[Dict[str, Any]]
    
class FeedbackRequest(BaseModel):
    interview_id: str
    answers: List[Dict[str, Any]]
    job_title: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None

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
    return {"message": "Welcome to AI Interview Prep API"}

@app.post("/api/upload-cv", response_model=dict)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload and process a CV/resume file
    """
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save the file temporarily
        file_location = f"temp/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
        
        # Extract text content from the CV
        cv_text = extract_text_from_cv(file_location)
        
        if cv_text is None:
            raise HTTPException(status_code=400, detail="Failed to process CV file")
        
        # Clean up the temporary file
        os.remove(file_location)
        
        return {
            "filename": file.filename,
            "status": "CV processed successfully",
            "cv_text": cv_text
        }
    except Exception as e:
        # Clean up the temporary file in case of error
        if os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/questions", response_model=InterviewResponse)
async def generate_questions(request: InterviewRequest):
    try:
        # Create a progress tracking entry
        progress_id = f"progress_{uuid.uuid4()}"
        question_progress[progress_id] = {
            "total": request.duration,
            "generated": 0,
            "questions": [],
            "timestamp": time.time()
        }
        
        # Generate questions
        result = AIService.generate_interview_questions(
            job_title=request.job_title,
            job_description=request.job_description,
            cv_text=request.cv_text,
            interview_type=request.interview_type,
            duration=request.duration,
            progress_id=progress_id
        )
        
        # Clean up progress tracking after completion
        if progress_id in question_progress:
            del question_progress[progress_id]
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/interview/questions/progress")
async def get_question_progress(id: str = None):
    """
    Get the progress of question generation
    """
    # Clean up old progress entries (older than 10 minutes)
    current_time = time.time()
    keys_to_remove = []
    for key, data in question_progress.items():
        if current_time - data.get("timestamp", 0) > 600:  # 10 minutes
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del question_progress[key]
    
    # If no ID is provided, return all progress
    if not id:
        # For security, don't return the actual questions in this case
        return {
            "progress": {k: {"total": v["total"], "generated": v["generated"]} 
                        for k, v in question_progress.items()}
        }
    
    # Return progress for the specified ID
    if id in question_progress:
        return question_progress[id]
    
    # If ID is not found but looks like a temp ID from frontend, return simulated progress
    if id.startswith("temp_"):
        # This is a simulated progress for the frontend polling
        # In a real implementation, you would track actual progress
        return {
            "questions": [],
            "total": 0,
            "generated": 0
        }
    
    raise HTTPException(status_code=404, detail="Progress ID not found")

@app.post("/api/evaluate-interview", response_model=FeedbackResponse)
async def evaluate_interview(request: FeedbackRequest):
    """
    Evaluate interview answers and provide feedback
    """
    try:
        # Get interview data from request
        interview_id = request.interview_id
        answers = request.answers
        
        # Use job title from request if available, otherwise use a default
        job_title = request.job_title if hasattr(request, 'job_title') and request.job_title else "Job Position"
        
        # Use questions from request if available, otherwise use an empty list
        questions = request.questions if hasattr(request, 'questions') and request.questions else []
        
        # Evaluate the interview
        result = AIService.evaluate_interview(
            questions=questions,  # Use questions from the request
            answers=answers,
            job_title=job_title
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speech-to-text")
async def speech_to_text(request: SpeechToTextRequest):
    """
    Convert speech to text using OpenAI's Whisper API
    """
    try:
        # Decode the base64 audio data
        audio_data = base64.b64decode(request.audio)
        
        # Convert speech to text
        text = AIService.speech_to_text(audio_data, request.language)
        
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech using OpenAI's TTS API
    """
    try:
        # Convert text to speech
        audio_data = AIService.text_to_speech(request.text, request.voice)
        
        # Return the audio data as a binary response
        return Response(
            content=audio_data,
            media_type="audio/mpeg"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/conversation")
async def process_conversation(request: ConversationRequest):
    """
    Process a conversational interview exchange
    """
    try:
        # Process the conversation
        result = AIService.process_interview_conversation(
            job_title=request.job_title,
            job_description=request.job_description,
            conversation_history=[msg.dict() for msg in request.conversation_history],
            current_question_index=request.current_question_index,
            time_up=request.time_up,
            time_running_low=request.time_running_low,
            no_response_detected=request.no_response_detected,
            is_code_submission=request.is_code_submission,
            question_type=request.question_type,
            include_follow_up=request.include_follow_up
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-audio", response_model=dict)
async def upload_audio(file: UploadFile = File(...)):
    """
    Upload and transcribe audio file
    """
    try:
        # Create temp directory if it doesn't exist
        os.makedirs("temp", exist_ok=True)
        
        # Save the file temporarily
        file_location = f"temp/{file.filename}"
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
        
        # Read the audio file
        with open(file_location, "rb") as audio_file:
            audio_data = audio_file.read()
        
        # Transcribe the audio
        text = AIService.speech_to_text(audio_data)
        
        # Clean up the temporary file
        os.remove(file_location)
        
        return {
            "filename": file.filename,
            "text": text
        }
    except Exception as e:
        # Clean up the temporary file in case of error
        if 'file_location' in locals() and os.path.exists(file_location):
            os.remove(file_location)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
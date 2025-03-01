from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
from dotenv import load_dotenv
from .ai_service import AIService
from .utils import extract_text_from_cv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="AI Interview Prep API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
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

@app.post("/api/interview/questions")
async def generate_questions(request: InterviewRequest):
    try:
        questions = AIService.generate_interview_questions(
            job_title=request.job_title,
            job_description=request.job_description,
            cv_text=request.cv_text,
            interview_type=request.interview_type,
            duration=request.duration
        )
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/interview/evaluate")
async def evaluate_interview(evaluation: InterviewEvaluation):
    try:
        result = AIService.evaluate_interview(
            questions=evaluation.questions,
            answers=evaluation.answers,
            job_title=evaluation.job_title
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}

# WebRTC signaling endpoint
@app.post("/api/rtc/offer")
async def rtc_offer(offer: dict):
    """
    Handle WebRTC offer for video call
    """
    # This would handle WebRTC signaling
    return {"status": "offer received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
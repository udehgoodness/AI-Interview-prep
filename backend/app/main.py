from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
from dotenv import load_dotenv

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
    interview_type: str
    duration: int

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

# Routes
@app.get("/")
async def root():
    return {"message": "Welcome to AI Interview Prep API"}

@app.post("/api/upload-cv", response_model=dict)
async def upload_cv(file: UploadFile = File(...)):
    """
    Upload a CV/resume file
    """
    try:
        # Save the file temporarily
        file_location = f"temp/{file.filename}"
        os.makedirs("temp", exist_ok=True)
        
        with open(file_location, "wb+") as file_object:
            file_object.write(await file.read())
            
        # Here you would process the CV with AI
        # For now, we'll just return a success message
        return {"filename": file.filename, "status": "CV uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-interview", response_model=InterviewResponse)
async def generate_interview(request: InterviewRequest):
    """
    Generate interview questions based on job details
    """
    try:
        # Mock response - in production, this would call the AI service
        mock_questions = [
            {
                "id": "q1",
                "question": f"Tell me about your experience related to {request.job_title}?",
                "type": "behavioral"
            },
            {
                "id": "q2",
                "question": "What are your strengths and weaknesses?",
                "type": "behavioral"
            },
            {
                "id": "q3",
                "question": "How do you handle stress and pressure?",
                "type": "behavioral"
            }
        ]
        
        if request.interview_type == "technical":
            mock_questions.extend([
                {
                    "id": "q4",
                    "question": "Write a function to reverse a string in your preferred language.",
                    "type": "coding"
                },
                {
                    "id": "q5",
                    "question": f"Explain how you would implement a key feature for a {request.job_title} role.",
                    "type": "technical"
                }
            ])
        
        return {
            "interview_id": "mock-interview-123",
            "questions": mock_questions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/evaluate-interview", response_model=FeedbackResponse)
async def evaluate_interview(request: FeedbackRequest):
    """
    Evaluate interview answers and provide feedback
    """
    try:
        # Mock response - in production, this would call the AI service
        return {
            "score": 85,
            "feedback": "Overall, you demonstrated good knowledge and communication skills.",
            "strengths": ["Clear communication", "Technical knowledge", "Problem-solving approach"],
            "weaknesses": ["Could provide more specific examples", "Some hesitation in responses"],
            "improvement_areas": ["Practice more coding problems", "Prepare more concrete examples of past work"]
        }
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
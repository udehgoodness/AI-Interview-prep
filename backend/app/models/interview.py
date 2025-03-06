"""
Interview Models
--------------
This module contains the Pydantic models for interview-related data.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class InterviewRequest(BaseModel):
    """Model for interview request data"""
    job_title: str
    job_description: str
    cv_text: Optional[str] = None
    interview_type: str = "general"
    duration: int = 30

class InterviewResponse(BaseModel):
    """Model for interview response data"""
    interview_id: str
    questions: List[Dict[str, Any]]
    
class FeedbackRequest(BaseModel):
    """Model for feedback request data"""
    interview_id: str
    answers: List[Dict[str, Any]]
    job_title: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = None
    interview_type: Optional[str] = None

class FeedbackResponse(BaseModel):
    """Model for feedback response data"""
    score: int
    feedback: str
    strengths: List[str]
    weaknesses: List[str]
    improvement_areas: List[str]

class InterviewEvaluation(BaseModel):
    """Model for interview evaluation data"""
    questions: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    job_title: str 
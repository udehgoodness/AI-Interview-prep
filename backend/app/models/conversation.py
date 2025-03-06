"""
Conversation Models
-----------------
This module contains the Pydantic models for conversation-related data.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ConversationMessage(BaseModel):
    """Model for conversation message data"""
    role: str
    content: str

class ConversationRequest(BaseModel):
    """Model for conversation request data"""
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

class ConversationResponse(BaseModel):
    """Model for conversation response data"""
    message: str
    follow_up: Optional[str] = None
    is_follow_up: bool = False
    is_end_of_interview: bool = False 
"""
Audio Models
----------
This module contains the Pydantic models for audio-related data.
"""

from pydantic import BaseModel
from typing import Optional

class SpeechToTextRequest(BaseModel):
    """Model for speech-to-text request data"""
    audio: str  # Base64 encoded audio data
    language: str = "en"

class SpeechToTextResponse(BaseModel):
    """Model for speech-to-text response data"""
    text: str

class TextToSpeechRequest(BaseModel):
    """Model for text-to-speech request data"""
    text: str
    voice: str = "alloy"

class TextToSpeechResponse(BaseModel):
    """Model for text-to-speech response data"""
    audio: str  # Base64 encoded audio data 
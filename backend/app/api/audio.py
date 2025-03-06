"""
Audio API
-------
This module contains the audio API endpoints.
"""

import logging
import base64
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from typing import Dict, Any

from app.models.audio import (
    SpeechToTextRequest,
    SpeechToTextResponse,
    TextToSpeechRequest,
    TextToSpeechResponse
)
from app.services.auth import get_current_active_user
from app.services.subscription import check_user_subscription_access
from app.services.ai import AIService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["Audio"])

@router.post("/speech-to-text", response_model=Dict[str, str])
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
            status_code=status.HTTP_403_FORBIDDEN,
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
        
        if not text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert speech to text. Please try again later."
            )
        
        logger.info(f"Successfully converted speech to text: {text[:50]}...")
        
        return {"text": text}
    except Exception as e:
        logger.error(f"Error converting speech to text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting speech to text: {str(e)}"
        )

@router.post("/text-to-speech", response_model=Dict[str, str])
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice interviews are not available on your current plan. Please upgrade your subscription."
        )
    
    try:
        # Initialize AI service
        ai_service = AIService()
        
        # Convert text to speech
        audio_data = await ai_service.text_to_speech(request.text, request.voice)
        
        if not audio_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert text to speech. Please try again later."
            )
        
        # Encode audio data as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        return {"audio": f"data:audio/mp3;base64,{audio_base64}"}
    except Exception as e:
        logger.error(f"Error converting text to speech: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error converting text to speech: {str(e)}"
        )

@router.post("/upload-audio", response_model=Dict[str, str])
async def upload_audio(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    Upload and process an audio file
    """
    # Check if user has access to voice interviews
    access = check_user_subscription_access(current_user["id"], "voice_interviews")
    
    if not access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice interviews are not available on your current plan. Please upgrade your subscription."
        )
    
    try:
        # Read the audio file
        audio_data = await file.read()
        
        # Initialize AI service
        ai_service = AIService()
        
        # Convert speech to text
        text = await ai_service.speech_to_text(audio_data)
        
        if not text:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to convert speech to text. Please try again later."
            )
        
        return {"text": text}
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing audio: {str(e)}"
        )

@router.post("/test-speech-to-text", response_model=Dict[str, str])
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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred in the test endpoint."
        ) 
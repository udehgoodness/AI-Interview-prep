"""
AI Service
---------
This module contains the AI service for the application.
"""

import logging
from typing import List, Dict, Any, Optional
from .openai import OpenAIService
from .deepseek import DeepSeekService

# Configure logging
logger = logging.getLogger(__name__)

# Simple in-memory cache for interview questions
question_cache = {}

# Question progress tracking
question_progress = {}

def set_question_progress(progress_dict):
    """Set the question_progress reference"""
    global question_progress
    question_progress = progress_dict

def update_question_progress(interview_id, progress, status="generating"):
    """Update the progress for a specific interview"""
    if interview_id in question_progress:
        question_progress[interview_id]["progress"] = progress
        question_progress[interview_id]["status"] = status
    else:
        question_progress[interview_id] = {
            "progress": progress,
            "status": status
        }

class AIService:
    """AI service for the application"""
    
    def __init__(self):
        """Initialize the AI service"""
        self.openai_service = OpenAIService()
        self.deepseek_service = DeepSeekService()
        logger.info("AI Service initialized with OpenAI and DeepSeek")

    async def generate_interview_questions(
        self, 
        job_title: str, 
        job_description: str, 
        cv_text: Optional[str] = None,
        interview_type: str = "general",
        duration: int = 30,
        model: str = "openai",
        progress_id: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate interview questions using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Generating interview questions for {job_title} using {model}")
            
            # If model is explicitly set to deepseek, use DeepSeek directly
            if model.lower() == "deepseek":
                questions = await self.deepseek_service.generate_interview_questions(
                    job_title, 
                    job_description, 
                    cv_text,
                    interview_type,
                    duration
                )
                if questions:
                    logger.info("Successfully generated questions using DeepSeek")
                    
                    # Cache the questions if progress_id is provided
                    if progress_id:
                        question_cache[progress_id] = {"questions": questions}
                    
                    return {"questions": questions, "model_used": "deepseek"}
                
                logger.error("Failed to generate questions with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
            questions = await self.openai_service.generate_interview_questions(
                job_title, 
                job_description, 
                cv_text,
                interview_type,
                duration
            )
            if questions:
                logger.info("Successfully generated questions using OpenAI")
                
                # Cache the questions if progress_id is provided
                if progress_id:
                    question_cache[progress_id] = {"questions": questions}
                
                return {"questions": questions, "model_used": "openai"}
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to generate questions, falling back to DeepSeek")
            questions = await self.deepseek_service.generate_interview_questions(
                job_title, 
                job_description, 
                cv_text,
                interview_type,
                duration
            )
            if questions:
                logger.info("Successfully generated questions using DeepSeek fallback")
                
                # Cache the questions if progress_id is provided
                if progress_id:
                    question_cache[progress_id] = {"questions": questions}
                
                return {"questions": questions, "model_used": "deepseek"}
            
            logger.error("Failed to generate questions with both OpenAI and DeepSeek")
            return None
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            return None

    async def evaluate_interview(
        self,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str,
        model: str = "openai"
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate an interview using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Evaluating interview for {job_title} using {model}")
            
            # If model is explicitly set to deepseek, use DeepSeek directly
            if model.lower() == "deepseek":
                evaluation = await self.deepseek_service.evaluate_interview(questions, answers, job_title)
                if evaluation:
                    logger.info("Successfully evaluated interview using DeepSeek")
                    evaluation["model_used"] = "deepseek"
                    return evaluation
                
                logger.error("Failed to evaluate interview with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
            evaluation = await self.openai_service.evaluate_interview(questions, answers, job_title)
            if evaluation:
                logger.info("Successfully evaluated interview using OpenAI")
                evaluation["model_used"] = "openai"
                return evaluation
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to evaluate interview, falling back to DeepSeek")
            evaluation = await self.deepseek_service.evaluate_interview(questions, answers, job_title)
            if evaluation:
                logger.info("Successfully evaluated interview using DeepSeek fallback")
                evaluation["model_used"] = "deepseek"
                return evaluation
            
            logger.error("Failed to evaluate interview with both OpenAI and DeepSeek")
            return None
            
        except Exception as e:
            logger.error(f"Error evaluating interview: {str(e)}")
            return None

    async def handle_interview_conversation(
        self,
        job_title: str,
        job_description: str,
        conversation_history: List[Dict[str, str]],
        current_question_index: int = 0,
        time_up: bool = False,
        time_running_low: bool = False,
        no_response_detected: bool = False,
        is_code_submission: bool = False,
        question_type: str = "general",
        include_follow_up: bool = True,
        model: str = "openai"
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an interview conversation using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Handling interview conversation for {job_title} using {model}")
            
            # If model is explicitly set to deepseek, use DeepSeek directly
            if model.lower() == "deepseek":
                response = await self.deepseek_service.handle_interview_conversation(
                    job_title,
                    job_description,
                    conversation_history,
                    current_question_index,
                    time_up,
                    time_running_low,
                    no_response_detected,
                    is_code_submission,
                    question_type,
                    include_follow_up
                )
                if response:
                    logger.info("Successfully handled conversation using DeepSeek")
                    response["model_used"] = "deepseek"
                    return response
                
                logger.error("Failed to handle conversation with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
            response = await self.openai_service.handle_interview_conversation(
                job_title,
                job_description,
                conversation_history,
                current_question_index,
                time_up,
                time_running_low,
                no_response_detected,
                is_code_submission,
                question_type,
                include_follow_up
            )
            if response:
                logger.info("Successfully handled conversation using OpenAI")
                response["model_used"] = "openai"
                return response
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to handle conversation, falling back to DeepSeek")
            response = await self.deepseek_service.handle_interview_conversation(
                job_title,
                job_description,
                conversation_history,
                current_question_index,
                time_up,
                time_running_low,
                no_response_detected,
                is_code_submission,
                question_type,
                include_follow_up
            )
            if response:
                logger.info("Successfully handled conversation using DeepSeek fallback")
                response["model_used"] = "deepseek"
                return response
            
            logger.error("Failed to handle conversation with both OpenAI and DeepSeek")
            return None
            
        except Exception as e:
            logger.error(f"Error handling interview conversation: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """
        Convert speech to text using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Converting speech to text using OpenAI")
            
            # Try OpenAI first
            text = await self.openai_service.speech_to_text(audio_bytes, language)
            if text:
                logger.info("Successfully converted speech to text using OpenAI")
                return text
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to convert speech to text, falling back to DeepSeek")
            text = await self.deepseek_service.speech_to_text(audio_bytes, language)
            if text:
                logger.info("Successfully converted speech to text using DeepSeek fallback")
                return text
            
            logger.error("Failed to convert speech to text with both OpenAI and DeepSeek")
            return None
            
        except Exception as e:
            logger.error(f"Error converting speech to text: {str(e)}")
            return None

    async def text_to_speech(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Converting text to speech using OpenAI")
            
            # Try OpenAI first
            audio_bytes = await self.openai_service.text_to_speech(text, voice)
            if audio_bytes:
                logger.info("Successfully converted text to speech using OpenAI")
                return audio_bytes
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to convert text to speech, falling back to DeepSeek")
            audio_bytes = await self.deepseek_service.text_to_speech(text, voice)
            if audio_bytes:
                logger.info("Successfully converted text to speech using DeepSeek fallback")
                return audio_bytes
            
            logger.error("Failed to convert text to speech with both OpenAI and DeepSeek")
            return None
            
        except Exception as e:
            logger.error(f"Error converting text to speech: {str(e)}")
            return None 
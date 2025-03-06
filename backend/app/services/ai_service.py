import logging
from typing import List, Dict, Any, Optional
from .openai_service import OpenAIService
from .deepseek_service import DeepSeekService

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
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
                questions = await self.deepseek_service.generate_interview_questions(job_title, job_description, cv_text)
                if questions:
                    logger.info("Successfully generated questions using DeepSeek")
                    return {"questions": questions, "model_used": "deepseek"}
                logger.error("Failed to generate questions with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
            questions = await self.openai_service.generate_interview_questions(job_title, job_description, cv_text)
            if questions:
                logger.info("Successfully generated questions using OpenAI")
                return {"questions": questions, "model_used": "openai"}
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to generate questions, falling back to DeepSeek")
            questions = await self.deepseek_service.generate_interview_questions(job_title, job_description, cv_text)
            if questions:
                logger.info("Successfully generated questions using DeepSeek fallback")
                return {"questions": questions, "model_used": "deepseek"}
            
            logger.error("Both OpenAI and DeepSeek failed to generate questions")
            return None
        except Exception as e:
            logger.error(f"Error in generate_interview_questions: {str(e)}")
            return None

    @staticmethod
    async def evaluate_interview(
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str,
        model: str = "openai"
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate interview answers using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Evaluating interview for {job_title} using {model}")
            
            # If model is explicitly set to deepseek, use DeepSeek directly
            if model.lower() == "deepseek":
                evaluation = await DeepSeekService().evaluate_interview(questions, answers, job_title)
                if evaluation:
                    logger.info("Successfully evaluated interview using DeepSeek")
                    evaluation["model_used"] = "deepseek"
                    return evaluation
                logger.error("Failed to evaluate interview with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
            evaluation = await OpenAIService().evaluate_interview(questions, answers, job_title)
            if evaluation:
                logger.info("Successfully evaluated interview using OpenAI")
                evaluation["model_used"] = "openai"
                return evaluation
            
            # If OpenAI fails, fall back to DeepSeek
            logger.warning("OpenAI failed to evaluate interview, falling back to DeepSeek")
            evaluation = await DeepSeekService().evaluate_interview(questions, answers, job_title)
            if evaluation:
                logger.info("Successfully evaluated interview using DeepSeek fallback")
                evaluation["model_used"] = "deepseek"
                return evaluation
            
            logger.error("Both OpenAI and DeepSeek failed to evaluate interview")
            return None
        except Exception as e:
            logger.error(f"Error in evaluate_interview: {str(e)}")
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
        Handle interview conversation using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Handling conversation for {job_title} using {model}")
            
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
            
            logger.error("Both OpenAI and DeepSeek failed to handle conversation")
            return None
        except Exception as e:
            logger.error(f"Error in handle_interview_conversation: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en", model: str = "openai") -> Optional[str]:
        """
        Convert speech to text using OpenAI with DeepSeek fallback
        """
        try:
            logger.info(f"Converting speech to text using {model}")
            
            # If model is explicitly set to deepseek, use DeepSeek directly
            if model.lower() == "deepseek":
                text = await self.deepseek_service.speech_to_text(audio_bytes, language)
                if text:
                    logger.info("Successfully converted speech to text using DeepSeek")
                    return text
                logger.error("Failed to convert speech to text with DeepSeek")
                return None
            
            # Otherwise, try OpenAI first
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
            
            logger.error("Both OpenAI and DeepSeek failed to convert speech to text")
            return None
        except Exception as e:
            logger.error(f"Error in speech_to_text: {str(e)}")
            return None 
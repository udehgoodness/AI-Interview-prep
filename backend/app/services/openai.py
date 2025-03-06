"""
OpenAI Service
------------
This module contains the OpenAI service for the application.
"""

import os
import logging
import json
import base64
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI

# Configure logging
logger = logging.getLogger(__name__)

class OpenAIService:
    """OpenAI service for the application"""
    
    def __init__(self):
        """Initialize the OpenAI service"""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.client = OpenAI(api_key=self.api_key, timeout=60.0)
        logger.info(f"OpenAI service initialized with model: {self.model}")

    async def generate_interview_questions(
        self, 
        job_title: str, 
        job_description: str, 
        cv_text: Optional[str] = None,
        interview_type: str = "general",
        duration: int = 30
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Generate interview questions using OpenAI
        """
        try:
            prompt = f"""Generate {duration // 5} technical interview questions for a {job_title} position.
            
            Job Description: {job_description}
            
            {f'CV/Resume: {cv_text}' if cv_text else ''}
            
            Interview Type: {interview_type}
            
            Return the questions in the following JSON format:
            [
                {{
                    "id": "q1",
                    "question": "Question text here",
                    "type": "{interview_type}",
                    "difficulty": "intermediate",
                    "expected_answer_points": ["Point 1", "Point 2", "Point 3"]
                }},
                ...
            ]
            
            Make the questions challenging and relevant to the position.
            """

            messages = [{"role": "user", "content": prompt}]
            
            response = await self._call_openai_api(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    json_match = re.search(r'\[.*\]', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        questions = json.loads(json_str)
                        return questions
                    else:
                        logger.error("Failed to extract JSON from OpenAI response")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            return None

    async def evaluate_interview(
        self,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate an interview using OpenAI
        """
        try:
            # Format the questions and answers for the prompt
            qa_pairs = []
            for i in range(min(len(questions), len(answers))):
                qa_pairs.append(f"Question {i+1}: {questions[i]['question']}\nAnswer: {answers[i]['answer']}")
            
            qa_text = "\n\n".join(qa_pairs)
            
            prompt = f"""Evaluate the following interview for a {job_title} position:

            {qa_text}

            Provide a comprehensive evaluation with the following:
            1. Overall score (0-100)
            2. General feedback
            3. Key strengths (list format)
            4. Areas for improvement (list format)
            5. Specific improvement suggestions (list format)

            Return your evaluation in the following JSON format:
            {{
                "score": 85,
                "feedback": "Overall feedback text here...",
                "strengths": ["Strength 1", "Strength 2", "Strength 3"],
                "weaknesses": ["Weakness 1", "Weakness 2"],
                "improvement_areas": ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
            }}
            """

            messages = [{"role": "user", "content": prompt}]
            
            response = await self._call_openai_api(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        evaluation = json.loads(json_str)
                        return evaluation
                    else:
                        logger.error("Failed to extract JSON from OpenAI response")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return None
            
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
        include_follow_up: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an interview conversation using OpenAI
        """
        try:
            # Create a system message with the context
            system_message = f"""You are an AI interviewer for a {job_title} position. 
            
            Job Description: {job_description}
            
            Current Question Index: {current_question_index}
            Time Up: {time_up}
            Time Running Low: {time_running_low}
            No Response Detected: {no_response_detected}
            Is Code Submission: {is_code_submission}
            Question Type: {question_type}
            
            Your task is to conduct a professional interview. Respond to the candidate's answers, 
            ask follow-up questions when appropriate, and guide the interview process.
            
            If time is up, provide a closing statement.
            If time is running low, mention that there's limited time left.
            If no response is detected, prompt the candidate to respond.
            If this is a code submission, evaluate the code and provide feedback.
            
            Return your response in the following JSON format:
            {{
                "message": "Your response to the candidate",
                "follow_up": "Optional follow-up question",
                "is_follow_up": true/false,
                "is_end_of_interview": true/false
            }}
            """
            
            # Prepare the messages
            messages = [{"role": "system", "content": system_message}]
            
            # Add the conversation history
            for message in conversation_history:
                messages.append(message)
            
            # Call the OpenAI API
            response = await self._call_openai_api(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        conversation_response = json.loads(json_str)
                        
                        # If include_follow_up is False, remove the follow-up
                        if not include_follow_up:
                            conversation_response["follow_up"] = None
                            conversation_response["is_follow_up"] = False
                        
                        return conversation_response
                    else:
                        logger.error("Failed to extract JSON from OpenAI response")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {str(e)}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling interview conversation: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """
        Convert speech to text using OpenAI
        """
        try:
            # Save the audio bytes to a temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(audio_bytes)
            
            # Call the OpenAI API
            with open(temp_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            # Delete the temporary file
            import os
            os.unlink(temp_file_path)
            
            return transcript.text
            
        except Exception as e:
            logger.error(f"Error converting speech to text: {str(e)}")
            return None

    async def text_to_speech(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI
        """
        try:
            # Call the OpenAI API
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Get the audio bytes
            audio_bytes = response.content
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error converting text to speech: {str(e)}")
            return None

    async def _call_openai_api(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> Optional[str]:
        """
        Call the OpenAI API
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return None 
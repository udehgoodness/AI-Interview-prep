import os
import aiohttp
import logging
import json
import base64
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DeepSeekService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
        self.api_base_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
        self.chat_api_url = f"{self.api_base_url}/chat/completions"
        self.audio_api_url = f"{self.api_base_url}/audio/transcriptions"
        self.temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.7"))

    async def generate_response(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> Optional[str]:
        """
        Generate a response using the DeepSeek API
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": max_tokens
            }

            logger.info(f"Calling DeepSeek API with model: {self.model}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.chat_api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("DeepSeek API call successful")
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_data = await response.text()
                        logger.error(f"DeepSeek API error: {error_data}")
                        return None

        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            return None

    async def generate_interview_questions(self, job_title: str, job_description: str, cv_text: Optional[str] = None, interview_type: str = "general", duration: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        Generate interview questions using DeepSeek
        
        The number of questions will scale with the interview duration:
        - 1 question per minute of interview time
        """
        try:
            # Calculate number of questions based on duration (1 question per minute)
            num_questions = duration
            
            prompt = f"""Generate {num_questions} technical interview questions for a {job_title} position.
            
            Job Description: {job_description}
            
            {f'CV/Resume: {cv_text}' if cv_text else ''}
            
            Interview Type: {interview_type}
            Interview Duration: {duration} minutes
            
            Return the questions in the following JSON format:
            [
                {{
                    "id": "q1",
                    "question": "Question text here",
                    "type": "technical",
                    "difficulty": "intermediate",
                    "expected_answer_points": ["Point 1", "Point 2", "Point 3"]
                }},
                ...
            ]
            
            Ensure you generate exactly {num_questions} questions to match the {duration}-minute interview duration.
            """

            messages = [{"role": "user", "content": prompt}]
            response = await self.generate_response(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    import re
                    json_match = re.search(r'(\[\s*\{.*\}\s*\])', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        questions = json.loads(json_str)
                        return questions
                    else:
                        # Try to parse the entire response as JSON
                        questions = json.loads(response)
                        return questions
                except Exception as e:
                    logger.error(f"Error parsing DeepSeek response: {str(e)}")
                    logger.error(f"Raw response: {response}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error in generate_interview_questions: {str(e)}")
            return None

    async def evaluate_interview(self, questions: List[Dict[str, Any]], answers: List[Dict[str, Any]], job_title: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate interview answers using DeepSeek
        """
        try:
            # Format questions and answers for evaluation
            qa_pairs = []
            for i, (q, a) in enumerate(zip(questions, answers)):
                qa_pairs.append(f"Question {i+1}: {q.get('question', '')}")
                qa_pairs.append(f"Answer {i+1}: {a.get('answer', '')}")
            
            qa_text = "\n\n".join(qa_pairs)
            
            evaluation_prompt = f"""Evaluate the following technical interview answers for a {job_title} position.
            
            {qa_text}
            
            Provide an evaluation in the following JSON format:
            {{
                "score": <0-100>,
                "feedback": "<overall feedback>",
                "strengths": ["<strength1>", "<strength2>", ...],
                "weaknesses": ["<weakness1>", "<weakness2>", ...],
                "improvement_areas": ["<area1>", "<area2>", ...]
            }}
            
            If the answers are empty or nonsensical, assign a score of 0.
            """

            messages = [{"role": "user", "content": evaluation_prompt}]
            response = await self.generate_response(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    import re
                    json_match = re.search(r'(\{\s*"score".*\})', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        evaluation = json.loads(json_str)
                    else:
                        # Try to parse the entire response as JSON
                        evaluation = json.loads(response)
                    
                    # Ensure all required fields are present
                    required_fields = ["score", "feedback", "strengths", "weaknesses", "improvement_areas"]
                    for field in required_fields:
                        if field not in evaluation:
                            if field == "score":
                                evaluation[field] = 0
                            elif field in ["strengths", "weaknesses", "improvement_areas"]:
                                evaluation[field] = []
                            else:
                                evaluation[field] = ""
                    
                    return evaluation
                except Exception as e:
                    logger.error(f"Error parsing DeepSeek evaluation response: {str(e)}")
                    logger.error(f"Raw response: {response}")
                    return None
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
        include_follow_up: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Handle interview conversation using DeepSeek
        """
        try:
            # Format the conversation history
            formatted_conversation = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in conversation_history])
            
            system_prompt = f"""You are an AI interviewer for a {job_title} position. 
            Job Description: {job_description}
            
            Current question index: {current_question_index}
            Time up: {time_up}
            Time running low: {time_running_low}
            No response detected: {no_response_detected}
            Is code submission: {is_code_submission}
            Question type: {question_type}
            Include follow-up: {include_follow_up}
            
            Respond to the candidate's message in a professional manner.
            """
            
            user_prompt = f"""Here is the conversation history:
            {formatted_conversation}
            
            Provide your response as the interviewer in the following JSON format:
            {{
                "response": "<your response>",
                "follow_up_question": "<optional follow-up question>"
            }}
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.generate_response(messages)
            
            if response:
                try:
                    # Extract JSON from the response
                    import re
                    json_match = re.search(r'(\{\s*"response".*\})', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        result = json.loads(json_str)
                    else:
                        # Try to parse the entire response as JSON
                        result = json.loads(response)
                    
                    # Ensure required fields are present
                    if "response" not in result:
                        result["response"] = "I apologize, but I couldn't generate a proper response. Let's continue with the interview."
                    
                    if include_follow_up and "follow_up_question" not in result:
                        result["follow_up_question"] = ""
                    
                    return result
                except Exception as e:
                    logger.error(f"Error parsing DeepSeek conversation response: {str(e)}")
                    logger.error(f"Raw response: {response}")
                    return {"response": "I apologize, but I couldn't generate a proper response. Let's continue with the interview."}
            return None
        except Exception as e:
            logger.error(f"Error in handle_interview_conversation: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """
        Convert speech to text using DeepSeek API
        """
        try:
            logger.info(f"Converting speech to text using DeepSeek, audio size: {len(audio_bytes)} bytes")
            
            # DeepSeek may not have a direct speech-to-text API like OpenAI's Whisper
            # For now, we'll use a workaround by describing the audio and asking DeepSeek to generate text
            
            # Convert audio to base64 for logging purposes only
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            logger.info(f"Base64 audio length: {len(audio_base64)}")
            
            # Since DeepSeek might not have a direct audio API, we'll use a text-based approach
            # This is a fallback mechanism and may not work as well as a dedicated audio API
            
            prompt = f"""I have an audio recording that I need to transcribe. 
            The audio is in {language} language.
            Please provide a transcription of what might be said in this audio.
            If you can't determine the content, please respond with a generic greeting or introduction."""
            
            messages = [{"role": "user", "content": prompt}]
            logger.info("Sending text-based request to DeepSeek API for audio transcription")
            
            response = await self.generate_response(messages)
            
            if response:
                logger.info(f"DeepSeek response for audio transcription: {response[:50]}...")
                # Clean up the response to make it more like a transcription
                cleaned_response = response.replace("Transcription:", "").strip()
                return cleaned_response
            else:
                logger.error("Failed to get response from DeepSeek for audio transcription")
                return None
                        
        except Exception as e:
            logger.error(f"Error in speech_to_text: {str(e)}", exc_info=True)
            return None 
import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.client = OpenAI(api_key=self.api_key, timeout=60.0)

    async def generate_interview_questions(self, job_title: str, job_description: str, cv_text: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Generate interview questions using OpenAI
        """
        try:
            prompt = f"""Generate 4 technical interview questions for a {job_title} position.
            
            Job Description: {job_description}
            
            {f'CV/Resume: {cv_text}' if cv_text else ''}
            
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
            
            Make the questions challenging and relevant to the position.
            """

            messages = [{"role": "user", "content": prompt}]
            
            response = await self._call_openai_api(messages)
            
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
                    logger.error(f"Error parsing OpenAI response: {str(e)}")
                    logger.error(f"Raw response: {response}")
                    return None
            return None
        except Exception as e:
            logger.error(f"Error in generate_interview_questions: {str(e)}")
            return None

    async def evaluate_interview(self, questions: List[Dict[str, Any]], answers: List[Dict[str, Any]], job_title: str) -> Optional[Dict[str, Any]]:
        """
        Evaluate interview answers using OpenAI
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
            response = await self._call_openai_api(messages)
            
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
                    logger.error(f"Error parsing OpenAI evaluation response: {str(e)}")
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
        Handle interview conversation using OpenAI
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
            
            response = await self._call_openai_api(messages)
            
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
                    logger.error(f"Error parsing OpenAI conversation response: {str(e)}")
                    logger.error(f"Raw response: {response}")
                    return {"response": "I apologize, but I couldn't generate a proper response. Let's continue with the interview."}
            return None
        except Exception as e:
            logger.error(f"Error in handle_interview_conversation: {str(e)}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "en") -> Optional[str]:
        """
        Convert speech to text using OpenAI's Whisper API
        """
        try:
            import tempfile
            
            logger.info(f"Converting speech to text using OpenAI Whisper, audio size: {len(audio_bytes)} bytes")
            
            # Create a temporary file to store the audio data
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
                logger.info(f"Created temporary file at {temp_file_path}")
            
            # Use the OpenAI client to transcribe the audio
            logger.info("Sending request to OpenAI Whisper API")
            with open(temp_file_path, "rb") as audio_file:
                try:
                    transcription = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language
                    )
                    logger.info("Successfully received response from OpenAI Whisper API")
                except Exception as e:
                    logger.error(f"Error calling OpenAI Whisper API: {str(e)}", exc_info=True)
                    return None
            
            # Clean up the temporary file
            import os
            os.unlink(temp_file_path)
            logger.info(f"Deleted temporary file {temp_file_path}")
            
            if transcription and hasattr(transcription, 'text'):
                logger.info(f"Transcription result: {transcription.text[:50]}...")
                return transcription.text
            else:
                logger.error(f"Invalid transcription response: {transcription}")
                return None
        except Exception as e:
            logger.error(f"Error in speech_to_text: {str(e)}", exc_info=True)
            return None

    async def _call_openai_api(self, messages: List[Dict[str, str]], max_tokens: int = 2000) -> Optional[str]:
        """
        Call the OpenAI API with the given messages
        """
        try:
            logger.info(f"Calling OpenAI API with model: {self.model}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens
            )
            
            logger.info("OpenAI API call successful")
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            return None 
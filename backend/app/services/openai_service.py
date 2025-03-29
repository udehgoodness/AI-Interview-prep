import os
import logging
import json
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
import re

from app.utils.text_processing import is_likely_gibberish

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        self.client = OpenAI(api_key=self.api_key, timeout=60.0)

    async def generate_interview_questions(self, job_title: str, job_description: str, cv_text: Optional[str] = None, interview_type: str = "general", duration: int = 30) -> Optional[List[Dict[str, Any]]]:
        """
        Generate interview questions using OpenAI
        
        The number of questions will scale with the interview duration:
        - 1 question per minute of interview time
        """
        try:
            # Calculate number of questions based on duration (1 question per minute)
            num_questions = duration
            
            # Define specific instructions based on interview type
            type_specific_instructions = ""
            if interview_type.lower() == "technical":
                type_specific_instructions = """
                For this TECHNICAL interview, focus exclusively on:
                - Coding challenges and problem-solving scenarios
                - System design and architecture questions
                - Technical tools, frameworks, and methodologies
                - Technical decision-making and troubleshooting
                
                ALL questions MUST be purely technical in nature. Do NOT include any behavioral or general questions.
                Do NOT ask about teamwork, leadership, or past experiences - focus ONLY on technical knowledge and skills.
                
                IMPORTANT: Every single question must test technical knowledge or skills directly related to the job.
                """
            elif interview_type.lower() == "behavioral":
                type_specific_instructions = """
                For this BEHAVIORAL interview, focus exclusively on:
                - Past experiences and how the candidate handled specific situations
                - Teamwork and collaboration examples
                - Leadership and initiative demonstrations
                - Conflict resolution and problem-solving approaches
                
                ALL questions MUST be behavioral in nature. Do not include technical or knowledge-based questions.
                """
            elif interview_type.lower() == "leadership":
                type_specific_instructions = """
                For this LEADERSHIP interview, focus exclusively on:
                - Leadership philosophy and approach
                - Team management and development
                - Strategic thinking and decision making
                - Change management and organizational development
                - Conflict resolution at a leadership level
                
                ALL questions MUST assess leadership capabilities. Do not include purely technical questions.
                """
            else:  # general interview
                type_specific_instructions = """
                For this GENERAL interview, include a balanced mix of:
                - Technical questions (1-2 questions): Coding, system design, or technical knowledge relevant to the role
                - Behavioral questions (1-2 questions): Past experiences, teamwork, leadership, conflict resolution
                - Leadership questions (1-2 questions): Team management, strategic thinking, decision making
                
                Ensure a good balance between different question types to assess both technical skills and soft skills.
                """
            
            prompt = f"""As an expert interviewer with deep domain knowledge in {job_title} roles, generate {num_questions} high-quality interview questions that will effectively assess a candidate's suitability for this position.
            
            Job Description: {job_description}
            
            {f'CV/Resume: {cv_text}' if cv_text else ''}
            
            Interview Type: {interview_type}
            Interview Duration: {duration} minutes
            
            {type_specific_instructions}
            
            Follow these guidelines to create expert-level questions:
            
            1. Create questions that are specifically tailored to the {interview_type} interview type.
            
            2. Tailor difficulty levels appropriately:
               - "basic": Fundamental knowledge expected of all candidates
               - "intermediate": Practical application and deeper understanding
               - "advanced": Expert-level concepts, optimization, and edge cases
            
            3. Ensure questions are:
               - Clear and unambiguous
               - Challenging but answerable within a reasonable timeframe
               - Designed to reveal depth of knowledge, not to trick candidates
               - Progressive in difficulty throughout the interview
            
            4. For each question, provide comprehensive expected answer points that:
               - Cover the key concepts a strong candidate should mention
               - Include both theoretical knowledge and practical application
               - Note any industry-specific best practices or standards
            
            Return the questions in the following JSON format:
            [
                {{
                    "id": "q1",
                    "question": "Question text here",
                    "type": "{interview_type}",
                    "difficulty": "basic|intermediate|advanced",
                    "expected_answer_points": ["Point 1", "Point 2", "Point 3"]
                }},
                ...
            ]
            
            IMPORTANT: ALL questions must be of type "{interview_type}" to match the interview type selected by the user.
            """
            
            # Call OpenAI API
            logger.info(f"Calling OpenAI API with model: {self.model}")
            response = await self._call_openai_api([
                {"role": "system", "content": "You are an expert technical interviewer with deep domain knowledge across various industries."},
                {"role": "user", "content": prompt}
            ])
            
            if not response:
                logger.error("Failed to get response from OpenAI API")
                return None
            
            # Parse the response to extract the questions
            try:
                # Find the JSON part of the response
                match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
                if match:
                    questions_json = match.group(0)
                    questions = json.loads(questions_json)
                    
                    # Ensure all questions have the correct type
                    for question in questions:
                        question["type"] = interview_type.lower()
                    
                    logger.info(f"Successfully parsed {len(questions)} questions from OpenAI response")
                    return questions
                else:
                    logger.error("Failed to extract JSON from OpenAI response")
                    # Try to parse the entire response as JSON
                    try:
                        questions = json.loads(response)
                        
                        # Ensure all questions have the correct type
                        for question in questions:
                            question["type"] = interview_type.lower()
                        
                        logger.info(f"Successfully parsed {len(questions)} questions from OpenAI response")
                        return questions
                    except json.JSONDecodeError:
                        logger.error("Failed to parse entire response as JSON")
                        return None
            except Exception as e:
                logger.error(f"Error parsing OpenAI response: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_interview_questions: {str(e)}")
            return None

    async def evaluate_interview(
        self, 
        questions: List[Dict[str, Any]], 
        answers: List[Dict[str, Any]], 
        job_title: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate interview answers using OpenAI
        """
        try:
            # Check if we have conversation history (voice mode)
            has_conversation = conversation_history is not None and len(conversation_history) > 0
            
            # Format questions and answers for the prompt
            formatted_qa = []
            gibberish_count = 0
            total_questions = len(questions)
            
            for i, question in enumerate(questions):
                answer_text = "No answer provided"
                for answer in answers:
                    if answer.get("question_id") == question.get("id"):
                        answer_text = answer.get("answer", "No answer provided")
                        break
                
                # Check if the answer is gibberish, but don't immediately return
                if is_likely_gibberish(answer_text, is_voice_mode=has_conversation):
                    logger.warning(f"Detected gibberish answer for question {i+1}")
                    gibberish_count += 1
                
                formatted_qa.append(f"Question {i+1}: {question.get('question')}\nAnswer: {answer_text}\n")
            
            # If ALL answers are gibberish in text mode, return a zero score
            if gibberish_count == total_questions and not has_conversation:
                return {
                    "score": 0,
                    "feedback": "Your answers appear to be nonsensical or incomplete. Please provide meaningful responses to receive a proper evaluation.",
                    "strengths": ["None identified"],
                    "weaknesses": ["Answers appear to be nonsensical or incomplete"],
                    "improvement_areas": ["Provide meaningful and relevant answers to the interview questions"]
                }
            
            # Create the evaluation prompt
            prompt = f"""
            You are an expert interview evaluator for {job_title} positions. 
            Please evaluate the following interview answers and provide a comprehensive assessment.
            
            Job Title: {job_title}
            """
            
            # If we have conversation history, include it in the prompt
            if has_conversation:
                prompt += "\n\nInterview Conversation Transcript:\n"
                for msg in conversation_history:
                    role = "Interviewer" if msg["role"] == "assistant" else "Candidate"
                    prompt += f"{role}: {msg['content']}\n"
                
                prompt += "\n\nExtracted Questions and Answers:\n"
            
            # Add information about gibberish answers if any were detected
            if gibberish_count > 0:
                prompt += f"""
                {' '.join(formatted_qa)}
                
                Note: {gibberish_count} out of {total_questions} answers appear to be incomplete or unclear. 
                Please evaluate the interview based on the answers that were provided properly.
                For questions with incomplete or unclear answers, consider them as partially answered
                and evaluate accordingly, rather than giving a zero score for the entire interview.
                
                Please provide:
                """
            else:
                prompt += f"""
                {' '.join(formatted_qa)}
                
                Please provide:
                """
            
            prompt += """
                1. A score from 0 to 100 (where 0 is completely inadequate and 100 is perfect)
                2. Overall feedback on the interview performance
                3. Key strengths demonstrated (list at least 3 if possible)
                4. Areas of weakness (list at least 3 if possible)
                5. Specific improvement suggestions (list at least 3 if possible)
                
                Format your response as a JSON object with the following structure:
                {
                    "score": <score>,
                    "feedback": "<overall feedback>",
                    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
                    "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
                    "improvement_areas": ["<improvement 1>", "<improvement 2>", "<improvement 3>"]
                }
                """
            
            messages = [
                {"role": "system", "content": "You are an expert interview evaluator providing detailed feedback."},
                {"role": "user", "content": prompt}
            ]
            
            response = await self._call_openai_api(messages)
            
            if not response:
                return None
            
            # Extract the JSON part of the response
            try:
                # Find JSON in the response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response[json_start:json_end]
                    evaluation = json.loads(json_str)
                    
                    # Validate the evaluation structure
                    if not all(key in evaluation for key in ["score", "feedback", "strengths", "weaknesses", "improvement_areas"]):
                        raise ValueError("Missing required fields in evaluation")
                    
                    # Ensure score is an integer between 0 and 100
                    evaluation["score"] = max(0, min(100, int(evaluation["score"])))
                    
                    return evaluation
                else:
                    raise ValueError("No JSON found in response")
            except Exception as e:
                logger.error(f"Error parsing evaluation response: {str(e)}")
                logger.error(f"Raw response: {response}")
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
        Handle interview conversation using OpenAI
        """
        try:
            # Format the conversation history
            formatted_conversation = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in conversation_history])
            
            system_prompt = f"""You are an expert AI interviewer for a {job_title} position with deep knowledge of the field and industry best practices. 
            Job Description: {job_description}
            
            Current question index: {current_question_index}
            Time up: {time_up}
            Time running low: {time_running_low}
            No response detected: {no_response_detected}
            Is code submission: {is_code_submission}
            Question type: {question_type}
            Include follow-up: {include_follow_up}
            
            As an expert interviewer, follow these guidelines:
            1. Ask clear, concise, and relevant questions that assess both technical knowledge and practical experience.
            2. Adapt your questioning style based on the candidate's responses - probe deeper when answers are vague or incomplete.
            3. Maintain a professional and respectful tone throughout the interview.
            4. For technical roles, ask for specific examples of how the candidate has applied their skills.
            5. When time is running low, focus on the most critical aspects of the role.
            6. If the candidate submits code, evaluate it for correctness, efficiency, and readability.
            7. Provide appropriate follow-up questions that build upon previous responses.
            8. If no response is detected, politely prompt the candidate and offer to rephrase the question.
            9. When the time is up, gracefully conclude the interview with a summary.
            10. Tailor your questions to the seniority level implied by the job description.
            
            IMPORTANT TIME MANAGEMENT INSTRUCTIONS:
            - When time is running low (2 minutes remaining), DO NOT ask any new questions. Instead, inform the candidate that time is running low and they should wrap up their current answer. Do not ask follow-up questions.
            - When time is up, DO NOT ask any questions at all. Instead, thank the candidate for their time, provide a brief positive closing statement, and end the interview professionally. Never ask questions when time is up.
            
            IMPORTANT: As an interviewer, you should NEVER answer your own questions or provide definitions to questions you ask. Your role is to ask questions and evaluate the candidate's responses, not to provide answers or explanations to the questions you ask. Even if the candidate's answer is incomplete or incorrect, do not provide the correct answer - instead, ask follow-up questions to guide them.
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
            
            # The OpenAI client methods are not async by default in the latest version
            # So we don't use await here
            response = self.client.chat.completions.create(
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

    async def text_to_speech(self, text: str, voice: str = "alloy") -> Optional[bytes]:
        """
        Convert text to speech using OpenAI's TTS API
        """
        try:
            logger.info(f"Converting text to speech using OpenAI TTS with voice: {voice}")
            
            # The OpenAI client methods are not async by default in the latest version
            # So we don't use await here
            response = self.client.audio.speech.create(
                model="tts-1",  # Use the text-to-speech model
                voice=voice,    # alloy, echo, fable, onyx, nova, or shimmer
                input=text
            )
            
            # Get the audio content as bytes
            audio_data = response.content
            
            logger.info("Successfully generated audio with OpenAI TTS")
            return audio_data
        except Exception as e:
            logger.error(f"Error using OpenAI TTS: {str(e)}")
            return None 
import os
import logging
import json
import uuid
import base64
import hashlib
import asyncio
import functools
import concurrent.futures
import time
import sys
import requests
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Simple in-memory cache for interview questions
question_cache = {}

# Import question_progress from main.py
# We need to handle circular imports carefully
question_progress = {}

def set_question_progress(progress_dict):
    """Set the question_progress reference from main.py"""
    global question_progress
    question_progress = progress_dict

def update_question_progress(interview_id, progress, status="generating"):
    """Update the progress for a specific interview"""
    if interview_id in question_progress:
        question_progress[interview_id]["progress"] = progress
        question_progress[interview_id]["status"] = status

class AIService:
    # Initialize OpenAI client with timeout settings
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=60.0  # 60 seconds timeout for API calls
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # DeepSeek configuration
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_api_url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
    
    # Cache TTL in seconds (24 hours)
    CACHE_TTL = 86400
    
    @staticmethod
    def _generate_cache_key(job_title, job_description, interview_type, duration):
        """Generate a cache key based on input parameters"""
        # Create a string combining all parameters
        combined = f"{job_title.lower()}|{job_description.lower()}|{interview_type}|{duration}"
        # Create a hash of the combined string
        return hashlib.md5(combined.encode()).hexdigest()
    
    @staticmethod
    def _is_cache_valid(cache_entry):
        """Check if a cache entry is still valid based on timestamp"""
        if not cache_entry or 'timestamp' not in cache_entry:
            return False
        current_time = asyncio.get_event_loop().time()
        return (current_time - cache_entry['timestamp']) < AIService.CACHE_TTL
    
    @staticmethod
    async def generate_interview_questions(
        job_title: str,
        job_description: str,
        cv_text: Optional[str] = None,
        interview_type: str = "general",
        duration: int = 30,
        model: str = "openai",
        progress_id: str = None
    ) -> Dict[str, Any]:
        """
        Generate interview questions using OpenAI's API based on job details and CV
        """
        try:
            # Check cache first (only if no CV is provided, as CV makes it unique)
            if not cv_text:
                cache_key = AIService._generate_cache_key(job_title, job_description, interview_type, duration)
                cache_entry = question_cache.get(cache_key)
                
                if cache_entry and AIService._is_cache_valid(cache_entry):
                    logger.info(f"Cache hit for job: {job_title}, returning cached questions")
                    
                    # If we're tracking progress, update it to complete immediately
                    if progress_id and progress_id in question_progress:
                        question_progress[progress_id]["progress"] = 100
                        question_progress[progress_id]["status"] = "completed"
                        if "questions" in cache_entry['data']:
                            question_progress[progress_id]["questions"] = cache_entry['data']["questions"]
                    
                    return cache_entry['data']
            
            # Detect seniority level from job title
            seniority_level = "mid"  # Default to mid-level
            if any(level in job_title.lower() for level in ["senior", "lead", "principal", "staff", "architect"]):
                seniority_level = "senior"
            elif any(level in job_title.lower() for level in ["junior", "entry", "associate", "intern"]):
                seniority_level = "junior"
            
            logger.info(f"Detected seniority level: {seniority_level} for job: {job_title}")
            
            # Determine number of questions based on duration
            num_questions = max(3, min(10, duration // 6))  # 1 question per 6 minutes, min 3, max 10
            
            # For very short interviews (5 minutes or less), limit to 5 questions
            if duration <= 5:
                num_questions = 5
            
            logger.info(f"Generating {num_questions} questions for {duration} minute interview")
            
            # Update progress to 10%
            if progress_id and progress_id in question_progress:
                question_progress[progress_id]["progress"] = 10
            
            # Prepare the prompt
            system_prompt = f"""You are an expert technical interviewer for {job_title} positions.
            Generate {num_questions} {interview_type} interview questions for a {seniority_level}-level {job_title} position.
            
            The questions should be challenging but appropriate for a {duration}-minute interview.
            
            For each question:
            1. Include a unique ID (q1, q2, etc.)
            2. Make the question specific and relevant to the job description
            3. Include expected answer points that the candidate should cover
            4. Assign a difficulty level (basic, intermediate, advanced)
            
            Format the response as a JSON array of question objects with the following structure:
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
            
            Do not include any explanations or notes outside of the JSON structure.
            """
            
            user_prompt = f"""Job Title: {job_title}
            
            Job Description: {job_description}
            
            {f'CV/Resume: {cv_text}' if cv_text else ''}
            
            Generate {num_questions} {interview_type} interview questions for this position.
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Update progress to 20%
            if progress_id and progress_id in question_progress:
                question_progress[progress_id]["progress"] = 20
            
            questions = None
            model_used = None
            
            # Try OpenAI first if specified
            if model.lower() == "openai":
                try:
                    logger.info("Attempting to generate questions with OpenAI")
                    
                    # Set a longer timeout for longer interviews
                    timeout_override = 60.0
                    if duration > 30:
                        timeout_override = 120.0
                    
                    # Make the API call with proper handling
                    client = OpenAI(
                        api_key=os.getenv("OPENAI_API_KEY"),
                        timeout=timeout_override
                    )
                    response = client.chat.completions.create(
                        model=AIService.model,
                        messages=messages,
                        temperature=AIService.temperature
                    )
                    
                    content = response.choices[0].message.content
                    
                    # Parse the JSON response
                    import re
                    json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        questions = json.loads(json_str)
                    else:
                        # Try to parse the entire response as JSON
                        questions = json.loads(content)
                    
                    model_used = "openai"
                    logger.info("Successfully generated questions with OpenAI")
                except Exception as e:
                    logger.error(f"Error generating questions with OpenAI: {str(e)}")
                    questions = None
            
            # If OpenAI failed or DeepSeek was specified, try DeepSeek
            if questions is None and AIService.deepseek_api_key:
                try:
                    logger.info("Attempting to generate questions with DeepSeek")
                    content = await AIService.call_deepseek_api(messages)
                    
                    # Parse the JSON response
                    import re
                    json_match = re.search(r'(\[\s*\{.*\}\s*\])', content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(1)
                        questions = json.loads(json_str)
                    else:
                        # Try to parse the entire response as JSON
                        questions = json.loads(content)
                    
                    model_used = "deepseek"
                    logger.info("Successfully generated questions with DeepSeek")
                except Exception as e:
                    logger.error(f"Error generating questions with DeepSeek: {str(e)}")
                    questions = None
            
            # Update progress to 80%
            if progress_id and progress_id in question_progress:
                question_progress[progress_id]["progress"] = 80
            
            # If both APIs failed, raise an exception
            if questions is None:
                logger.error("Failed to generate questions with both OpenAI and DeepSeek")
                raise Exception("Failed to generate questions with both OpenAI and DeepSeek")
            
            # Ensure all questions have the required fields
            for q in questions:
                if "type" not in q:
                    q["type"] = interview_type
                if "difficulty" not in q:
                    q["difficulty"] = "intermediate"
                if "expected_answer_points" not in q:
                    q["expected_answer_points"] = []
            
            # Update progress to 90%
            if progress_id and progress_id in question_progress:
                question_progress[progress_id]["progress"] = 90
            
            # Cache the result if no CV was provided
            if not cv_text:
                result = {
                    "questions": questions,
                    "model_used": model_used
                }
                
                question_cache[cache_key] = {
                    'data': result,
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                result = {
                    "questions": questions,
                    "model_used": model_used
                }
            
            # Update progress to 100%
            if progress_id and progress_id in question_progress:
                question_progress[progress_id]["progress"] = 100
                question_progress[progress_id]["status"] = "completed"
                question_progress[progress_id]["questions"] = questions
            
            logger.info(f"Generated {len(questions)} {interview_type} questions for interview {progress_id} at {seniority_level} level")
            
            return result

        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            # Return a minimal valid response with default questions
            default_interview_id = str(uuid.uuid4())
            default_questions = []
            for i in range(duration):
                default_questions.append({
                    "id": f"q{i+1}",
                    "question": f"Question {i+1}: Tell me about your experience with {job_title}.",
                    "type": interview_type,
                    "difficulty": "intermediate",
                    "expected_answer_points": ["Relevant experience", "Skills", "Achievements"]
                })
            
            result = {
                "interview_id": default_interview_id,
                "questions": default_questions,
                "seniority_level": "mid"
            }
            
            return result

    @staticmethod
    async def call_deepseek_api(messages, temperature=0.4, max_tokens=2000):
        """
        Call the DeepSeek API for chat completions
        
        Args:
            messages: List of message objects with role and content
            temperature: Temperature for response generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response content from DeepSeek
        """
        if not AIService.deepseek_api_key:
            logger.error("DeepSeek API key not configured")
            raise ValueError("DeepSeek API key not configured")
            
        try:
            import aiohttp
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AIService.deepseek_api_key}"
            }
            
            payload = {
                "model": AIService.deepseek_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    AIService.deepseek_api_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DeepSeek API error: {response.status} - {error_text}")
                        raise Exception(f"DeepSeek API error: {response.status}")
                    
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"Error calling DeepSeek API: {str(e)}")
            raise

    @staticmethod
    async def evaluate_interview(
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str,
        model: str = "openai"
    ) -> Dict[str, Any]:
        """
        Evaluate interview answers using AI models (OpenAI with DeepSeek fallback)
        """
        try:
            # Check if all answers are empty or nearly empty
            all_answers_empty = True
            for answer in answers:
                answer_text = answer.get('answer', '').strip()
                if len(answer_text) > 10:  # Consider answers with more than 10 chars as non-empty
                    all_answers_empty = False
                    break
            
            # If all answers are empty, return a low score without calling the API
            if all_answers_empty:
                return {
                    "score": 0,  # Changed from 10 to 0 for empty answers
                    "feedback": "The candidate provided minimal or no responses to the interview questions. It's not possible to evaluate skills or qualifications based on empty answers.",
                    "strengths": ["No strengths could be identified from the provided answers."],
                    "weaknesses": ["Did not provide substantive responses to interview questions."],
                    "improvement_areas": ["Please provide complete answers to allow for proper evaluation."]
                }
            
            # Check if answers are nonsensical (random characters, very short, etc.)
            nonsensical_answers = True
            for answer in answers:
                answer_text = answer.get('answer', '').strip()
                # Check if answer has actual words (at least 3 words with 3+ characters each)
                words = [w for w in answer_text.split() if len(w) >= 3]
                if len(words) >= 3:
                    nonsensical_answers = False
                    break
            
            # If answers are nonsensical, return a very low score
            if nonsensical_answers:
                return {
                    "score": 0,  # Changed from 10 to 0 for nonsensical answers
                    "feedback": "The responses provided appear to be nonsensical or random characters rather than meaningful answers to the interview questions. This suggests a lack of engagement with the interview process.",
                    "strengths": ["No meaningful strengths could be identified from the provided answers."],
                    "weaknesses": ["Provided nonsensical or random text instead of meaningful answers.", 
                                  "Did not demonstrate understanding of the questions.",
                                  "Lack of professional engagement with the interview process."],
                    "improvement_areas": ["Provide thoughtful, relevant answers to interview questions.",
                                         "Take time to understand each question before responding.",
                                         "Demonstrate professional communication skills during interviews."]
                }
            
            # Prepare the evaluation context
            context = f"""Job Title: {job_title}

Interview Questions and Answers:
"""
            # Match questions with answers for better evaluation
            for answer in answers:
                question_text = answer.get('question', 'Unknown question')
                answer_text = answer.get('answer', 'No answer provided')
                
                # Find matching question to get expected answer points if available
                matching_question = next((q for q in questions if q.get('id') == answer.get('question_id')), None)
                expected_points = []
                if matching_question and 'expected_answer_points' in matching_question:
                    expected_points = matching_question['expected_answer_points']
                
                context += f"\nQuestion: {question_text}\n"
                context += f"Candidate's Answer: {answer_text}\n"
                
                if expected_points:
                    context += "Expected key points:\n"
                    for point in expected_points:
                        context += f"- {point}\n"

            context += "\nPlease evaluate the interview responses and provide:"
            context += "\n1. A score out of 100 based on the quality of answers compared to expected key points"
            context += "\n2. Overall feedback that is specific to the answers provided"
            context += "\n3. Key strengths demonstrated in the answers"
            context += "\n4. Areas for improvement based on missing key points or weak responses"
            context += "\n5. Specific improvement suggestions"
            context += "\nFormat the response as a JSON object with the following structure:"
            context += """\n{
  "score": 85,
  "feedback": "Overall feedback text...",
  "strengths": ["Strength 1", "Strength 2", ...],
  "weaknesses": ["Weakness 1", "Weakness 2", ...],
  "improvement_areas": ["Suggestion 1", "Suggestion 2", ...]
}"""

            system_prompt = "You are an expert interview evaluator. Provide detailed, honest, and constructive feedback based on the actual answers provided. Do not be overly generous with scores - evaluate critically against the expected key points. For empty or minimal answers, assign very low scores (below 20). For one-word or very short answers, scores should be below 40. For nonsensical or random text, assign a score of 0-10."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ]
            
            content = None
            
            # Try OpenAI first
            try:
                logger.info("Attempting to evaluate interview with OpenAI")
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    timeout=60.0
                )
                response = client.chat.completions.create(
                    model=AIService.model,
                    messages=messages,
                    temperature=0.4  # Lower temperature for more consistent evaluation
                )
                content = response.choices[0].message.content
                logger.info("Successfully evaluated interview with OpenAI")
            except Exception as e:
                logger.error(f"Error evaluating interview with OpenAI: {str(e)}")
                content = None
            
            # If OpenAI fails, try DeepSeek
            if content is None and AIService.deepseek_api_key:
                try:
                    logger.info("Attempting to evaluate interview with DeepSeek")
                    content = await AIService.call_deepseek_api(messages, temperature=0.4, max_tokens=2000)
                    logger.info("Successfully evaluated interview with DeepSeek")
                except Exception as e:
                    logger.error(f"Error evaluating interview with DeepSeek: {str(e)}")
                    content = None
            
            # If both APIs failed, return a default evaluation
            if content is None:
                logger.warning("Both APIs failed, returning default evaluation")
                return {
                    "score": 50,
                    "feedback": "We were unable to generate a detailed evaluation at this time. Here's a general assessment based on your answers.",
                    "strengths": [
                        "You completed the interview process",
                        "You provided answers to the technical questions",
                        "Your responses showed engagement with the interview process"
                    ],
                    "weaknesses": [
                        "Some answers may have lacked specific technical details",
                        "There might be areas where more examples would strengthen your responses"
                    ],
                    "improvement_areas": [
                        "Practice providing more specific examples in your answers",
                        "Focus on highlighting your direct experience with the technologies mentioned",
                        "Consider structuring your answers with a problem-solution-outcome format"
                    ],
                    "model_used": "fallback"
                }

            try:
                # Clean up the response to ensure it's valid JSON
                # Remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                evaluation = json.loads(content)
                
                # Add model_used field
                if model.lower() == "deepseek":
                    evaluation["model_used"] = "deepseek"
                else:
                    evaluation["model_used"] = "openai"
                
                return evaluation
            except json.JSONDecodeError:
                # If not in JSON format, extract structured data
                evaluation = {
                    "score": 0,
                    "feedback": "",
                    "strengths": [],
                    "weaknesses": [],
                    "improvement_areas": []
                }
                
                lines = content.split("\n")
                current_section = None
                
                for line in lines:
                    if "score" in line.lower():
                        try:
                            evaluation["score"] = int(line.split(":")[-1].strip().split("/")[0])
                        except:
                            pass
                    elif "feedback" in line.lower():
                        current_section = "feedback"
                    elif "strength" in line.lower():
                        current_section = "strengths"
                    elif "weakness" in line.lower() or "improvement" in line.lower():
                        current_section = "weaknesses"
                    elif line.strip() and current_section:
                        if current_section == "feedback":
                            evaluation["feedback"] += line.strip() + " "
                        elif current_section == "strengths":
                            evaluation["strengths"].append(line.strip())
                        elif current_section == "weaknesses":
                            evaluation["weaknesses"].append(line.strip())

                # Add model_used field
                if model.lower() == "deepseek":
                    evaluation["model_used"] = "deepseek"
                else:
                    evaluation["model_used"] = "openai"
                
                logger.info(f"Completed evaluation for interview with score: {evaluation.get('score', 0)}")
                return evaluation

        except Exception as e:
            logger.error(f"Error evaluating interview: {str(e)}")
            # Return a default evaluation instead of raising an exception
            return {
                "score": 50,
                "feedback": "We were unable to generate a detailed evaluation at this time. Here's a general assessment based on your answers.",
                "strengths": [
                    "You completed the interview process",
                    "You provided answers to the technical questions",
                    "Your responses showed engagement with the interview process"
                ],
                "weaknesses": [
                    "Some answers may have lacked specific technical details",
                    "There might be areas where more examples would strengthen your responses"
                ],
                "improvement_areas": [
                    "Practice providing more specific examples in your answers",
                    "Focus on highlighting your direct experience with the technologies mentioned",
                    "Consider structuring your answers with a problem-solution-outcome format"
                ],
                "model_used": "fallback"
            }
            
    @staticmethod
    async def speech_to_text(audio_data: bytes, language: str = "en") -> str:
        """
        Convert speech to text using OpenAI's Whisper API
        
        Args:
            audio_data: Binary audio data
            language: Language code (default: 'en')
            
        Returns:
            Transcribed text
        """
        try:
            # Create a temporary directory if it doesn't exist
            temp_dir = "app/temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Use a unique file name
            temp_file_path = f"{temp_dir}/audio_{uuid.uuid4()}.mp3"
            
            # Write the audio data to the temporary file
            with open(temp_file_path, "wb") as f:
                f.write(audio_data)
            
            logger.info(f"Saved audio data to {temp_file_path}")
            
            # Verify the file exists and has content
            if not os.path.exists(temp_file_path):
                logger.error(f"Temporary file does not exist: {temp_file_path}")
                raise Exception("Failed to create temporary audio file")
            
            file_size = os.path.getsize(temp_file_path)
            logger.info(f"Temporary file size: {file_size / 1024:.2f} KB")
            
            if file_size == 0:
                logger.error("Temporary file is empty")
                raise Exception("Temporary audio file is empty")
            
            # Transcribe the audio using OpenAI's Whisper API
            logger.info("Sending request to OpenAI Whisper API")
            
            # Use a similar approach as our successful test script
            with open(temp_file_path, "rb") as audio_file:
                # Transcribe the audio using OpenAI's Whisper API
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    timeout=60.0
                )
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            # Clean up the temporary file
            try:
                os.remove(temp_file_path)
                logger.info(f"Deleted temporary file {temp_file_path}")
            except Exception as cleanup_error:
                logger.error(f"Error deleting temporary file: {str(cleanup_error)}")
            
            # Return the transcribed text
            logger.info(f"Successfully transcribed audio: {transcript.text[:50]}...")
            return transcript.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            # Since we don't want to use any fallback, we'll raise an exception
            raise Exception("Failed to transcribe audio with OpenAI")
    
    @staticmethod
    async def text_to_speech(text: str, voice: str = "alloy") -> bytes:
        """
        Convert text to speech using OpenAI's TTS API
        
        Args:
            text: Text to convert to speech
            voice: Voice to use (default: 'alloy')
            
        Returns:
            Binary audio data
        """
        try:
            # Generate speech using OpenAI's TTS API
            client = OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                timeout=60.0
            )
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Get the binary audio data
            audio_data = response.content
            
            logger.info(f"Successfully generated speech for text: '{text[:50]}...'")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech with OpenAI: {str(e)}")
            # Since DeepSeek doesn't have a direct TTS API equivalent to OpenAI's,
            # and we don't want to use pre-generated data, we'll raise an exception
            raise Exception("Failed to generate speech with OpenAI")
    
    @staticmethod
    async def process_interview_conversation(
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
    ) -> Dict[str, Any]:
        """
        Process an interview conversation and generate a response
        """
        try:
            # Format the conversation history
            formatted_conversation = AIService._format_conversation(conversation_history)
            
            # Prepare the system prompt
            system_prompt = f"""You are an AI interviewer conducting a {question_type} interview for a {job_title} position.
            
            Job Description: {job_description}
            
            Your task is to interview the candidate professionally and evaluate their responses.
            
            Guidelines:
            1. Respond as a professional interviewer would.
            2. Ask follow-up questions when appropriate to dig deeper into the candidate's experience.
            3. Be conversational but professional.
            4. Keep your responses concise (1-3 paragraphs).
            5. Don't repeat questions that have already been asked.
            """
            
            # Add special instructions based on the state of the interview
            user_prompt = f"Current conversation:\n{formatted_conversation}\n\n"
            
            if time_up:
                user_prompt += "\nThe interview time is up. Please thank the candidate for their time and end the interview professionally."
            elif time_running_low:
                user_prompt += "\nThe interview time is running low. Please wrap up the current question and prepare to conclude the interview soon."
            elif no_response_detected:
                user_prompt += "\nThe candidate has been silent for a while. Please politely prompt them to respond or ask if they need clarification."
            elif is_code_submission:
                user_prompt += "\nThe candidate has submitted code for a coding question. Please review their code and provide constructive feedback."
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Try OpenAI first
            try:
                logger.info("Attempting to process interview conversation with OpenAI")
                client = OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY"),
                    timeout=60.0
                )
                response = client.chat.completions.create(
                    model=AIService.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                ai_response = response.choices[0].message.content
                logger.info("Successfully processed interview conversation with OpenAI")
                
                # Generate audio for the response if needed
                audio_base64 = None
                try:
                    audio_data = await AIService.text_to_speech(ai_response)
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                except Exception as audio_error:
                    logger.error(f"Error generating audio for OpenAI response: {str(audio_error)}")
                
                result = {
                    "response": ai_response,
                    "model_used": "openai"
                }
                
                if audio_base64:
                    result["audio"] = f"data:audio/mp3;base64,{audio_base64}"
                
                return result
                
            except Exception as e:
                logger.error(f"Error processing interview conversation with OpenAI: {str(e)}")
                
                # Try DeepSeek as fallback
                if AIService.deepseek_api_key:
                    try:
                        logger.info("Attempting to process interview conversation with DeepSeek")
                        content = await AIService.call_deepseek_api(messages, temperature=0.7, max_tokens=1000)
                        
                        # Generate audio for the response if needed
                        audio_base64 = None
                        try:
                            audio_data = await AIService.text_to_speech(content)
                            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                        except Exception as audio_error:
                            logger.error(f"Error generating audio for DeepSeek response: {str(audio_error)}")
                        
                        result = {
                            "response": content,
                            "model_used": "deepseek"
                        }
                        
                        if audio_base64:
                            result["audio"] = f"data:audio/mp3;base64,{audio_base64}"
                        
                        logger.info("Successfully processed interview conversation with DeepSeek")
                        return result
                        
                    except Exception as deepseek_error:
                        logger.error(f"Error processing interview conversation with DeepSeek: {str(deepseek_error)}")
                
                # If both APIs failed, raise an exception
                raise Exception("Failed to process interview conversation with both OpenAI and DeepSeek")
                
        except Exception as e:
            logger.error(f"Error processing interview conversation: {str(e)}")
            # Since we don't want to use any pre-generated data, we'll raise an exception
            raise Exception("Failed to process interview conversation")

    @staticmethod
    def _format_conversation(conversation_history: List[Dict[str, str]]) -> str:
        """Helper method to format conversation history for the prompt"""
        formatted = ""
        for message in conversation_history:
            role = "AI Interviewer" if message["role"] == "assistant" else "Candidate"
            formatted += f"{role}: {message['content']}\n\n"
        return formatted

    @staticmethod
    async def handle_interview_conversation(
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
    ) -> Dict[str, Any]:
        """
        Handle interview conversation by directly calling the process_interview_conversation method
        """
        try:
            # Directly call the async process_interview_conversation method
            result = await AIService.process_interview_conversation(
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
            
            return result
        except Exception as e:
            logger.error(f"Error handling interview conversation: {str(e)}")
            raise 
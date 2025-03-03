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

class AIService:
    # Initialize OpenAI client with timeout settings
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=60.0  # 60 seconds timeout for API calls
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
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
    def generate_interview_questions(
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
                        question_progress[progress_id]["generated"] = duration
                        question_progress[progress_id]["questions"] = cache_entry['data']["questions"]
                    
                    return cache_entry['data']
            
            # Determine seniority level from job title and description
            seniority_level = "mid"  # Default to mid-level
            
            # Check job title for seniority indicators
            job_title_lower = job_title.lower()
            if any(senior_term in job_title_lower for senior_term in ["senior", "lead", "principal", "staff", "architect", "head", "director", "manager"]):
                seniority_level = "senior"
            elif any(junior_term in job_title_lower for junior_term in ["junior", "entry", "graduate", "intern", "trainee", "associate"]):
                seniority_level = "junior"
                
            # If not found in title, check description
            if seniority_level == "mid":
                job_desc_lower = job_description.lower()
                if any(senior_term in job_desc_lower for senior_term in ["senior level", "senior position", "5+ years", "extensive experience", "leadership", "architect"]):
                    seniority_level = "senior"
                elif any(junior_term in job_desc_lower for junior_term in ["entry level", "junior position", "0-2 years", "recent graduate", "no experience required"]):
                    seniority_level = "junior"
            
            logger.info(f"Detected seniority level: {seniority_level} for job: {job_title}")
            
            # Calculate number of questions based on duration - one question per minute
            num_questions = duration
            
            logger.info(f"Generating {num_questions} questions for {duration} minute interview")
            
            # Define question type instruction based on interview_type - SIMPLIFIED for faster responses
            question_type_instruction = ""
            if interview_type == "technical":
                question_type_instruction = "Generate ONLY technical questions. Include conceptual, problem-solving, and coding questions."
            elif interview_type == "behavioral":
                question_type_instruction = "Generate ONLY behavioral questions."
            elif interview_type == "leadership":
                question_type_instruction = "Generate ONLY leadership questions."
            else:  # general
                question_type_instruction = "Generate a mix of technical and behavioral questions."
            
            # Add difficulty level instruction based on seniority - SIMPLIFIED for faster responses
            difficulty_instruction = f"Focus on {seniority_level}-level difficulty questions appropriate for the position."
            
            # Generate a unique interview ID
            interview_id = str(uuid.uuid4())
            
            # For parallel processing, split into batches
            batch_size = 10  # Generate 10 questions per batch
            num_batches = (num_questions + batch_size - 1) // batch_size  # Ceiling division
            
            # Function to generate a batch of questions
            def generate_batch(batch_index, batch_size, existing_questions=None):
                # Calculate how many questions to generate in this batch
                remaining = num_questions - batch_index * batch_size
                current_batch_size = min(batch_size, remaining)
                
                # Prepare the context for question generation - SIMPLIFIED for faster responses
                context = f"""Job Title: {job_title}
Job Description: {job_description}
Interview Type: {interview_type}
Seniority Level: {seniority_level}

{"CV Content: " + cv_text if cv_text else "No CV provided"}

{question_type_instruction}

{difficulty_instruction}

Generate {current_batch_size} diverse and unique interview questions for this position.
Format each question as a JSON object with:
- id: unique identifier
- question: the actual question text
- type: one of ["technical", "behavioral", "leadership", "coding"]
- expected_answer_points: array of key points for a good answer
- difficulty: one of ["basic", "intermediate", "advanced"]

"""
                # If we have existing questions, make sure new ones are different
                if existing_questions:
                    context += f"\nEnsure these questions are different from: {', '.join([q['question'] for q in existing_questions])}"

                # Use a longer timeout for longer interviews
                timeout_override = 60.0  # Standard timeout
                
                response = AIService.client.chat.completions.create(
                    model=AIService.model,
                    temperature=0.9,  # Increase temperature for more randomness
                    messages=[
                        {"role": "system", "content": f"You are an expert {interview_type} interviewer. Generate relevant and diverse questions."},
                        {"role": "user", "content": context}
                    ],
                    timeout=timeout_override
                )

                # Parse the response
                questions_text = response.choices[0].message.content
                
                # Clean up the response to ensure it's valid JSON
                if "```json" in questions_text:
                    questions_text = questions_text.split("```json")[1].split("```")[0].strip()
                elif "```" in questions_text:
                    questions_text = questions_text.split("```")[1].split("```")[0].strip()
                
                # Handle case where response might be an array or individual objects
                if questions_text.startswith("[") and questions_text.endswith("]"):
                    batch_questions = json.loads(questions_text)
                else:
                    # If not properly formatted as an array, try to parse individual objects
                    questions_text = questions_text.strip().strip(',')
                    batch_questions = json.loads(f"[{questions_text}]")

                # Ensure all questions have the correct type and add seniority level
                for question in batch_questions:
                    if "type" not in question or not question["type"] in ["technical", "behavioral", "leadership", "coding"]:
                        question["type"] = interview_type
                    if "difficulty" not in question:
                        question["difficulty"] = "intermediate"  # Default if not specified
                    # Add batch index to ID to ensure uniqueness
                    if "id" not in question:
                        question["id"] = f"batch{batch_index}_q{batch_questions.index(question)}"
                    else:
                        question["id"] = f"batch{batch_index}_{question['id']}"
                
                # Update progress tracking if we have a progress_id
                if progress_id and progress_id in question_progress:
                    current_questions = question_progress[progress_id]["questions"]
                    current_questions.extend(batch_questions)
                    question_progress[progress_id]["questions"] = current_questions
                    question_progress[progress_id]["generated"] = len(current_questions)
                    question_progress[progress_id]["timestamp"] = time.time()
                
                return batch_questions
            
            # Generate first batch
            all_questions = generate_batch(0, batch_size)
            
            # Use ThreadPoolExecutor for parallel processing of remaining batches
            if num_batches > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, num_batches-1)) as executor:
                    future_to_batch = {
                        executor.submit(
                            generate_batch, i, batch_size, all_questions
                        ): i for i in range(1, num_batches)
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_batch):
                        batch_index = future_to_batch[future]
                        try:
                            batch_questions = future.result()
                            all_questions.extend(batch_questions)
                        except Exception as e:
                            logger.error(f"Error generating batch {batch_index}: {str(e)}")
            
            # Ensure we have exactly the right number of questions
            if len(all_questions) > num_questions:
                all_questions = all_questions[:num_questions]
            
            # Ensure each question has a unique ID
            for i, question in enumerate(all_questions):
                question["id"] = f"q{i+1}"
            
            result = {
                "interview_id": interview_id,
                "questions": all_questions,
                "seniority_level": seniority_level
            }
            
            # Cache the result if no CV was provided
            if not cv_text:
                cache_key = AIService._generate_cache_key(job_title, job_description, interview_type, duration)
                question_cache[cache_key] = {
                    'data': result,
                    'timestamp': asyncio.get_event_loop().time()
                }
            
            logger.info(f"Generated {len(all_questions)} {interview_type} questions for interview {interview_id} at {seniority_level} level")
            return result

        except Exception as e:
            logger.error(f"Error generating interview questions: {str(e)}")
            raise

    @staticmethod
    def evaluate_interview(
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str,
        model: str = "openai"
    ) -> Dict[str, Any]:
        """
        Evaluate interview answers using OpenAI's API
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
                    "score": 10,
                    "feedback": "The candidate provided minimal or no responses to the interview questions. It's not possible to evaluate skills or qualifications based on empty answers.",
                    "strengths": ["No strengths could be identified from the provided answers."],
                    "weaknesses": ["Did not provide substantive responses to interview questions."],
                    "improvement_areas": ["Please provide complete answers to allow for proper evaluation."]
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

            # Call OpenAI API
            response = AIService.client.chat.completions.create(
                model=AIService.model,
                messages=[
                    {"role": "system", "content": "You are an expert interview evaluator. Provide detailed, honest, and constructive feedback based on the actual answers provided. Do not be overly generous with scores - evaluate critically against the expected key points. For empty or minimal answers, assign very low scores (below 20). For one-word or very short answers, scores should be below 40."},
                    {"role": "user", "content": context}
                ],
                temperature=0.4,  # Lower temperature for more consistent evaluation
                max_tokens=2000
            )

            # Parse the response
            content = response.choices[0].message.content
            try:
                # Clean up the response to ensure it's valid JSON
                # Remove markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                evaluation = json.loads(content)
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

            logger.info(f"Completed evaluation for interview")
            return evaluation

        except Exception as e:
            logger.error(f"Error evaluating interview: {str(e)}")
            raise
            
    @staticmethod
    def speech_to_text(audio_data: bytes, language: str = "en") -> str:
        """
        Convert speech to text using OpenAI's Whisper API
        
        Args:
            audio_data: Binary audio data
            language: Language code (default: 'en' for English)
            
        Returns:
            Transcribed text
        """
        try:
            # Create a temporary file to store the audio data
            temp_file_path = f"temp/audio_{uuid.uuid4()}.webm"
            os.makedirs("temp", exist_ok=True)
            
            with open(temp_file_path, "wb") as f:
                f.write(audio_data)
            
            # Transcribe the audio using OpenAI's Whisper API
            with open(temp_file_path, "rb") as audio_file:
                transcript = AIService.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language
                )
            
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            logger.info("Successfully transcribed audio")
            return transcript.text
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            # Clean up the temporary file in case of error
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            raise
    
    @staticmethod
    def text_to_speech(text: str, voice: str = "alloy") -> bytes:
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
            response = AIService.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Get the binary audio data
            audio_data = response.content
            
            logger.info(f"Successfully generated speech for text: '{text[:50]}...'")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise
    
    @staticmethod
    def process_interview_conversation(
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
        Process a conversational interview exchange
        """
        try:
            # Prepare the context for the conversation
            system_prompt = """You are an AI interviewer conducting a job interview. 
Your responses should be professional, conversational, and focused on evaluating the candidate's skills and experience.

IMPORTANT GUIDELINES:
1. Vary your greetings and responses - avoid repetitive phrases or templates
2. Be creative in how you phrase follow-up questions
3. Don't use the same closing phrases repeatedly
4. Personalize your responses based on the candidate's answers
5. Keep your responses concise (1-3 sentences)
6. Ask follow-up questions that probe for specific examples
7. Avoid generic phrases like "That's great" or "Thank you for sharing"
8. Each time you speak, use different phrasing and sentence structures

For greetings, choose from a variety of professional but friendly approaches.
For endings, vary your closing remarks to sound natural and not repetitive."""

            # Determine if this is the first message in the conversation
            is_first_message = len(conversation_history) <= 1
            
            # Determine the appropriate prompt based on the conversation state
            if time_up:
                user_prompt = f"""The interview time is up. Provide a polite conclusion to the interview that:
1. Thanks the candidate for their time
2. Mentions something specific about their responses if possible
3. Explains the next steps in the process
4. Uses a unique and professional closing (not a generic "thank you")
5. Does NOT ask any new questions
6. IMPORTANT: Do NOT start with repetitive phrases like "Thank you for your time" or "That concludes our interview"
7. Be creative and varied in your opening sentence
8. Keep your response concise (2-4 sentences maximum)
9. IMPORTANT: This will be the final message before the interview ends, so make it complete

Job Title: {job_title}
Job Description: {job_description}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""
            elif time_running_low:
                user_prompt = f"""The interview time is running low (less than 90 seconds remaining). 
Provide a brief response that acknowledges the candidate's last answer and:
1. Mentions that time is running short
2. Provides a closing remark WITHOUT asking any new questions
3. Uses unique phrasing (not generic templates)
4. Keeps your response under 3 sentences
5. IMPORTANT: Do NOT ask any follow-up questions
6. IMPORTANT: Do NOT use repetitive phrases like "We have about one minute left" or "We're running low on time"
7. Be creative in how you mention the time constraint

Job Title: {job_title}
Job Description: {job_description}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""
            elif is_first_message:
                user_prompt = f"""This is the start of the interview. Provide a warm, professional greeting that:
1. Introduces yourself as the AI interviewer for the {job_title} position
2. Briefly mentions the purpose of the interview
3. Uses a unique and personalized greeting (not a generic template)
4. Asks the first interview question
5. Keeps the entire response under 4 sentences
6. IMPORTANT: Do NOT repeat the job title in your greeting, as it's already mentioned elsewhere

Job Title: {job_title}
Job Description: {job_description}"""
            elif no_response_detected:
                user_prompt = f"""The candidate did not provide an audible response or was silent. 
Respond in a supportive and encouraging way that:
1. Acknowledges that you didn't hear a response
2. Encourages them to try again or offers to rephrase the question
3. Maintains a positive and supportive tone
4. Is brief and clear (2-3 sentences)

Job Title: {job_title}
Job Description: {job_description}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""
            elif is_code_submission:
                user_prompt = f"""The candidate has submitted code for review. Provide a thoughtful analysis that:
1. Evaluates the code's correctness, efficiency, and style
2. Points out specific strengths in the implementation
3. Suggests specific improvements if applicable
4. Relates the code to the job requirements for {job_title}
5. Asks a follow-up question about their implementation choices
6. Is detailed but concise (5-7 sentences)

Job Title: {job_title}
Job Description: {job_description}
Question Type: {question_type}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""
            else:
                if include_follow_up:
                    user_prompt = f"""Respond to the candidate's last answer and ask a relevant follow-up question.
Your response should:
1. Briefly acknowledge their answer with specific details they mentioned
2. Use varied phrasing (avoid repetitive acknowledgments)
3. Ask a natural follow-up question that probes deeper
4. Keep your response concise (2-3 sentences maximum)
5. Sound conversational and not scripted

Job Title: {job_title}
Job Description: {job_description}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""
                else:
                    user_prompt = f"""Respond to the candidate's last answer with feedback only, without asking a follow-up question.
Your response should:
1. Acknowledge their answer with specific details they mentioned
2. Provide constructive feedback on their response
3. Keep your response concise (2-3 sentences maximum)
4. Sound conversational and not scripted
5. IMPORTANT: Do NOT ask any follow-up questions

Job Title: {job_title}
Job Description: {job_description}

Previous conversation:
{AIService._format_conversation(conversation_history)}"""

            # Call OpenAI API
            response = AIService.client.chat.completions.create(
                model=AIService.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,  # Higher temperature for more varied responses
                max_tokens=300  # Limit token count to encourage concise responses
            )
            
            # Get the response text
            ai_response = response.choices[0].message.content.strip()
            
            # Generate audio for the response
            audio_data = None
            try:
                audio_data = AIService.text_to_speech(ai_response)
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            except Exception as e:
                logger.error(f"Error generating speech: {str(e)}")
                audio_base64 = None
            
            return {
                "text": ai_response,
                "audio": audio_base64
            }
            
        except Exception as e:
            logger.error(f"Error processing interview conversation: {str(e)}")
            raise

    @staticmethod
    def _format_conversation(conversation_history: List[Dict[str, str]]) -> str:
        """Helper method to format conversation history for the prompt"""
        formatted = ""
        for message in conversation_history:
            role = "AI Interviewer" if message["role"] == "assistant" else "Candidate"
            formatted += f"{role}: {message['content']}\n\n"
        return formatted 
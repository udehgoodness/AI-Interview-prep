import os
import logging
import json
import uuid
import base64
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    @staticmethod
    def generate_interview_questions(
        job_title: str,
        job_description: str,
        cv_text: Optional[str] = None,
        interview_type: str = "general",
        duration: int = 30,
        model: str = "openai"
    ) -> Dict[str, Any]:
        """
        Generate interview questions using OpenAI's API based on job details and CV
        """
        try:
            # Prepare the context for question generation
            context = f"""Job Title: {job_title}
Job Description: {job_description}
Interview Type: {interview_type}
Duration: {duration} minutes

{"CV Content: " + cv_text if cv_text else "No CV provided"}

Generate {min(duration // 6, 8)} relevant interview questions for this position. For each question:
1. Make it specific to the job role and requirements
2. Include behavioral and technical questions as appropriate
3. For technical questions, include expected key points in the answer

Format each question as a JSON object with:
- id: unique identifier
- question: the actual question text
- type: technical or behavioral
- expected_answer_points: array of key points for a good answer"""

            # Generate questions using OpenAI
            response = AIService.client.chat.completions.create(
                model=AIService.model,
                temperature=AIService.temperature,
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer. Generate relevant interview questions based on the provided job details."},
                    {"role": "user", "content": context}
                ]
            )

            # Parse the response
            questions_text = response.choices[0].message.content
            
            # Clean up the response to ensure it's valid JSON
            # Remove markdown code blocks if present
            if "```json" in questions_text:
                questions_text = questions_text.split("```json")[1].split("```")[0].strip()
            elif "```" in questions_text:
                questions_text = questions_text.split("```")[1].split("```")[0].strip()
            
            # Handle case where response might be an array or individual objects
            if questions_text.startswith("[") and questions_text.endswith("]"):
                questions = json.loads(questions_text)
            else:
                # If not properly formatted as an array, try to parse individual objects
                questions_text = questions_text.strip().strip(',')
                questions = json.loads(f"[{questions_text}]")

            # Generate a unique interview ID
            interview_id = str(uuid.uuid4())
            
            logger.info(f"Generated {len(questions)} questions for interview {interview_id}")
            return {
                "interview_id": interview_id,
                "questions": questions
            }

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
            # Prepare the evaluation context
            context = f"""Job Title: {job_title}

Interview Questions and Answers:
"""
            for answer in answers:
                context += f"\nQuestion: {answer.get('question', 'Unknown question')}\n"
                context += f"Candidate's Answer: {answer.get('answer', 'No answer provided')}\n"

            context += "\nPlease evaluate the interview responses and provide:"
            context += "\n1. A score out of 100"
            context += "\n2. Overall feedback"
            context += "\n3. Key strengths demonstrated"
            context += "\n4. Areas for improvement"
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
                    {"role": "system", "content": "You are an expert interview evaluator. Provide detailed and constructive feedback."},
                    {"role": "user", "content": context}
                ],
                temperature=AIService.temperature,
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
        current_question_index: int = 0
    ) -> Dict[str, Any]:
        """
        Process a conversational interview exchange
        
        Args:
            job_title: Job title
            job_description: Job description
            conversation_history: List of conversation messages with role and content
            current_question_index: Current question index
            
        Returns:
            AI response with text and audio
        """
        try:
            # Prepare the system prompt
            system_prompt = f"""You are an AI interviewer conducting a job interview for the position of {job_title}.
Job Description: {job_description}

Your task is to:
1. Ask relevant questions about the candidate's experience and skills
2. Follow up on their answers when appropriate
3. Be professional, friendly, and encouraging
4. Keep your responses concise (1-3 sentences)
5. Focus on assessing the candidate's fit for the role

Current question index: {current_question_index}"""

            # Call OpenAI API for the conversation
            response = AIService.client.chat.completions.create(
                model=AIService.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_history
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            # Get the response text
            response_text = response.choices[0].message.content
            
            # Generate speech from the response text
            audio_data = AIService.text_to_speech(response_text)
            
            # Encode the audio data as base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "text": response_text,
                "audio": audio_base64
            }
            
        except Exception as e:
            logger.error(f"Error processing interview conversation: {str(e)}")
            raise 
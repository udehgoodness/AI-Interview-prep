import os
import logging
import json
import uuid
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
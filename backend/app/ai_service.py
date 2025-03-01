import os
import logging
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

    @staticmethod
    def generate_interview_questions(
        job_title: str,
        job_description: str,
        cv_text: Optional[str] = None,
        interview_type: str = "general",
        duration: int = 30,
        model: str = "openai"
    ) -> List[Dict[str, Any]]:
        """
        Generate interview questions using OpenAI's API based on job details and CV
        """
        try:
            ai_service = AIService()
            
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
            response = ai_service.client.chat.completions.create(
                model=ai_service.model,
                temperature=ai_service.temperature,
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer. Generate relevant interview questions based on the provided job details."},
                    {"role": "user", "content": context}
                ]
            )

            # Parse the response
            questions_text = response.choices[0].message.content
            questions = json.loads(f"[{questions_text.strip().strip(',').strip()}]")

            logger.info(f"Generated {len(questions)} questions for interview")
            return questions

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
            ai_service = AIService()
            
            # Prepare the evaluation context
            context = f"""Job Title: {job_title}

Interview Questions and Answers:
"""
            for q, a in zip(questions, answers):
                context += f"\nQuestion: {q['question']}\n"
                context += f"Expected Points: {', '.join(q.get('expected_answer_points', []))}\n"
                context += f"Candidate's Answer: {a.get('answer', 'No answer provided')}\n"

            context += "\nPlease evaluate the interview responses and provide:"
            context += "\n1. A score out of 100"
            context += "\n2. Overall feedback"
            context += "\n3. Key strengths demonstrated"
            context += "\n4. Areas for improvement"
            context += "\n5. Specific improvement suggestions"
            context += "\nFormat the response as a JSON object."

            # Call OpenAI API
            response = ai_service.client.chat.completions.create(
                model=ai_service.model,
                messages=[
                    {"role": "system", "content": "You are an expert interview evaluator. Provide detailed and constructive feedback."},
                    {"role": "user", "content": context}
                ],
                temperature=ai_service.temperature,
                max_tokens=2000
            )

            # Parse the response
            content = response.choices[0].message.content
            try:
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
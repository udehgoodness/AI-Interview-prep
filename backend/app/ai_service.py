import os
import json
from typing import List, Dict, Any, Optional
import openai
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize AI clients
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

class AIService:
    """
    Service for handling AI interactions with OpenAI and Anthropic models
    """
    
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
        Generate interview questions based on job details and CV
        
        Args:
            job_title: The title of the job
            job_description: The description of the job
            cv_text: Optional text from the user's CV
            interview_type: Type of interview (general, technical, behavioral)
            duration: Duration of interview in minutes
            model: AI model to use (openai or anthropic)
            
        Returns:
            List of question dictionaries
        """
        # Calculate number of questions based on duration
        num_questions = max(5, duration // 5)  # At least 5 questions, or 1 per 5 minutes
        
        # Construct prompt
        prompt = f"""
        Generate {num_questions} interview questions for a {job_title} position.
        
        Job Description:
        {job_description}
        
        Interview Type: {interview_type}
        Duration: {duration} minutes
        
        """
        
        if cv_text:
            prompt += f"""
            Candidate CV:
            {cv_text}
            
            Please tailor some questions to the candidate's background.
            """
            
        prompt += """
        Format the response as a JSON array of question objects with the following structure:
        [
            {
                "id": "q1",
                "question": "The interview question text",
                "type": "behavioral/technical/coding",
                "expected_answer_points": ["Point 1", "Point 2", "Point 3"]
            }
        ]
        """
        
        try:
            if model == "openai":
                response = openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert interviewer for technical and non-technical roles."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                result = json.loads(response.choices[0].message.content)
                return result.get("questions", [])
            
            elif model == "anthropic":
                response = anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    system="You are an expert interviewer for technical and non-technical roles. Respond with JSON only.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                result = json.loads(response.content[0].text)
                return result.get("questions", [])
            
            else:
                # Fallback to mock data if model not specified or API keys not available
                return AIService._generate_mock_questions(job_title, interview_type, num_questions)
                
        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            # Fallback to mock data
            return AIService._generate_mock_questions(job_title, interview_type, num_questions)
    
    @staticmethod
    def evaluate_interview(
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        job_title: str,
        model: str = "openai"
    ) -> Dict[str, Any]:
        """
        Evaluate interview answers and provide feedback
        
        Args:
            questions: List of question dictionaries
            answers: List of answer dictionaries
            job_title: The title of the job
            model: AI model to use (openai or anthropic)
            
        Returns:
            Dictionary with evaluation results
        """
        # Construct prompt
        prompt = f"""
        Evaluate the following interview for a {job_title} position.
        
        """
        
        # Add each question and answer pair
        for i, (q, a) in enumerate(zip(questions, answers)):
            prompt += f"""
            Question {i+1}: {q.get('question')}
            Answer: {a.get('answer')}
            
            """
            
        prompt += """
        Provide a comprehensive evaluation with the following structure:
        1. Overall score (0-100)
        2. General feedback paragraph
        3. List of strengths (at least 3)
        4. List of weaknesses (at least 2)
        5. List of improvement areas (at least 3)
        
        Format the response as a JSON object with the following structure:
        {
            "score": 85,
            "feedback": "Overall feedback text...",
            "strengths": ["Strength 1", "Strength 2", "Strength 3"],
            "weaknesses": ["Weakness 1", "Weakness 2"],
            "improvement_areas": ["Area 1", "Area 2", "Area 3"]
        }
        """
        
        try:
            if model == "openai":
                response = openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert interviewer and evaluator for technical and non-technical roles."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                return json.loads(response.choices[0].message.content)
            
            elif model == "anthropic":
                response = anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=4000,
                    system="You are an expert interviewer and evaluator for technical and non-technical roles. Respond with JSON only.",
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                return json.loads(response.content[0].text)
            
            else:
                # Fallback to mock data
                return AIService._generate_mock_evaluation()
                
        except Exception as e:
            print(f"Error evaluating interview: {str(e)}")
            # Fallback to mock data
            return AIService._generate_mock_evaluation()
    
    @staticmethod
    def _generate_mock_questions(job_title: str, interview_type: str, num_questions: int) -> List[Dict[str, Any]]:
        """Generate mock questions for testing"""
        behavioral_questions = [
            f"Tell me about your experience related to {job_title}?",
            "What are your strengths and weaknesses?",
            "How do you handle stress and pressure?",
            "Describe a challenging project you worked on.",
            "How do you prioritize your work?",
            "Tell me about a time you failed and what you learned.",
            "How do you handle conflicts with team members?",
            "What's your approach to learning new technologies?",
            "Where do you see yourself in 5 years?",
            "Why are you interested in this position?"
        ]
        
        technical_questions = [
            "Write a function to reverse a string in your preferred language.",
            "Explain the difference between REST and GraphQL.",
            "How would you optimize a slow database query?",
            "Explain the concept of asynchronous programming.",
            "What's the difference between HTTP and HTTPS?",
            "Explain the concept of containerization and Docker.",
            "What are design patterns and why are they important?",
            "How would you handle authentication in a web application?",
            "Explain the concept of CI/CD.",
            f"How would you implement a key feature for a {job_title} role?"
        ]
        
        questions = []
        for i in range(num_questions):
            if interview_type == "technical" and i % 2 == 0:
                q_type = "technical" if i % 3 != 0 else "coding"
                question = technical_questions[i % len(technical_questions)]
            else:
                q_type = "behavioral"
                question = behavioral_questions[i % len(behavioral_questions)]
                
            questions.append({
                "id": f"q{i+1}",
                "question": question,
                "type": q_type,
                "expected_answer_points": [
                    "Clear communication",
                    "Relevant experience",
                    "Problem-solving approach"
                ]
            })
            
        return questions
    
    @staticmethod
    def _generate_mock_evaluation() -> Dict[str, Any]:
        """Generate mock evaluation for testing"""
        return {
            "score": 85,
            "feedback": "Overall, you demonstrated good knowledge and communication skills. Your answers were clear and concise, showing good understanding of the role requirements. There's room for improvement in providing more specific examples and technical depth in some areas.",
            "strengths": [
                "Clear communication",
                "Technical knowledge",
                "Problem-solving approach",
                "Good understanding of the role"
            ],
            "weaknesses": [
                "Could provide more specific examples",
                "Some hesitation in responses",
                "Technical depth could be improved in some areas"
            ],
            "improvement_areas": [
                "Practice more coding problems",
                "Prepare more concrete examples of past work",
                "Research more about industry-specific technologies",
                "Work on concise explanations of complex concepts"
            ]
        } 
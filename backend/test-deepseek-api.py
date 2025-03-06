#!/usr/bin/env python3
"""
Test script for DeepSeek API and fallback functionality.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import the AI services
from app.services.ai_service import AIService
from app.services.deepseek_service import DeepSeekService

async def test_deepseek_direct():
    """Test DeepSeek API directly"""
    logger.info("Testing DeepSeek API directly...")
    
    service = DeepSeekService()
    
    # Test generating interview questions
    logger.info("Testing generate_interview_questions...")
    job_title = "Senior DevSecOps Engineer"
    job_description = """
    We are looking for a Senior DevSecOps Engineer to join our team. 
    The ideal candidate will have experience with CI/CD pipelines, 
    infrastructure as code, and security best practices.
    """
    
    questions = await service.generate_interview_questions(job_title, job_description)
    if questions:
        logger.info(f"Successfully generated {len(questions)} questions")
        logger.info(f"First question: {questions[0]['question']}")
    else:
        logger.error("Failed to generate questions")
    
    # Test evaluating interview
    logger.info("Testing evaluate_interview...")
    sample_questions = [
        {"question": "Describe the key principles of DevSecOps and how you would implement security throughout the CI/CD pipeline."},
        {"question": "How would you manage secrets and sensitive information in a cloud-based infrastructure? Discuss tools and best practices."}
    ]
    
    sample_answers = [
        {"answer": "DevSecOps integrates security practices into the DevOps process. Key principles include shifting security left, automation, continuous monitoring, and shared responsibility. I would implement security by adding automated security scanning in the CI pipeline, using IaC security scanning, and implementing runtime security monitoring."},
        {"answer": "For managing secrets in cloud infrastructure, I would use tools like HashiCorp Vault or AWS Secrets Manager. Best practices include rotation policies, least privilege access, encryption, and audit logging."}
    ]
    
    evaluation = await service.evaluate_interview(sample_questions, sample_answers, job_title)
    if evaluation:
        logger.info(f"Evaluation score: {evaluation['score']}")
        logger.info(f"Feedback: {evaluation['feedback'][:100]}...")
    else:
        logger.error("Failed to evaluate interview")
    
    return True

async def test_ai_service_with_fallback():
    """Test the AI service with DeepSeek fallback"""
    logger.info("Testing AI service with DeepSeek fallback...")
    
    service = AIService()
    
    # Test generating interview questions
    logger.info("Testing generate_interview_questions with fallback...")
    job_title = "Senior DevSecOps Engineer"
    job_description = """
    We are looking for a Senior DevSecOps Engineer to join our team. 
    The ideal candidate will have experience with CI/CD pipelines, 
    infrastructure as code, and security best practices.
    """
    
    # Test with DeepSeek directly
    result = await service.generate_interview_questions(job_title, job_description, model="deepseek")
    if result and "questions" in result:
        logger.info(f"Successfully generated questions using {result.get('model_used', 'unknown')}")
        if result["questions"] and len(result["questions"]) > 0:
            first_question = result["questions"][0].get("question", "") if isinstance(result["questions"][0], dict) else ""
            logger.info(f"First question: {first_question}")
    else:
        logger.error("Failed to generate questions with DeepSeek")
    
    # Test evaluating interview
    logger.info("Testing evaluate_interview with fallback...")
    sample_questions = [
        {"question": "Describe the key principles of DevSecOps and how you would implement security throughout the CI/CD pipeline."},
        {"question": "How would you manage secrets and sensitive information in a cloud-based infrastructure? Discuss tools and best practices."}
    ]
    
    sample_answers = [
        {"answer": "DevSecOps integrates security practices into the DevOps process. Key principles include shifting security left, automation, continuous monitoring, and shared responsibility. I would implement security by adding automated security scanning in the CI pipeline, using IaC security scanning, and implementing runtime security monitoring."},
        {"answer": "For managing secrets in cloud infrastructure, I would use tools like HashiCorp Vault or AWS Secrets Manager. Best practices include rotation policies, least privilege access, encryption, and audit logging."}
    ]
    
    # Test with DeepSeek
    evaluation = await service.evaluate_interview(sample_questions, sample_answers, job_title, model="deepseek")
    if evaluation:
        logger.info(f"Evaluation score using {evaluation.get('model_used', 'unknown')}: {evaluation['score']}")
        logger.info(f"Feedback: {evaluation['feedback'][:100]}...")
    else:
        logger.error("Failed to evaluate interview with DeepSeek")
    
    # Test conversation handling
    logger.info("Testing conversation handling with DeepSeek...")
    conversation_history = [
        {"role": "system", "content": "You are an AI interviewer for a Senior DevSecOps Engineer position."},
        {"role": "assistant", "content": "Tell me about your experience with CI/CD pipelines."},
        {"role": "user", "content": "I have 5 years of experience with Jenkins, GitLab CI, and GitHub Actions. I've implemented pipelines for various applications, including containerized microservices and monolithic applications."}
    ]
    
    # Test with DeepSeek
    response = await service.handle_interview_conversation(
        job_title, 
        job_description, 
        conversation_history,
        model="deepseek"
    )
    
    if response:
        logger.info(f"Conversation response using {response.get('model_used', 'unknown')}")
        logger.info(f"Response: {response.get('text', '')[:100]}...")
    else:
        logger.error("Failed to handle conversation with DeepSeek")
    
    return True

async def main():
    """Run all tests"""
    try:
        # Test DeepSeek API directly
        await test_deepseek_direct()
        
        # Test AI service with DeepSeek fallback
        await test_ai_service_with_fallback()
        
        logger.info("All tests completed successfully!")
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 
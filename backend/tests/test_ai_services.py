#!/usr/bin/env python3
"""
Consolidated test file for AI services.
"""

import os
import sys
import json
import pytest
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the services
from app.services.ai_service import AIService
from app.services.openai_service import OpenAIService
from app.services.deepseek_service import DeepSeekService

def test_openai_service():
    """Test the OpenAI service"""
    
    try:
        # Initialize the service
        service = OpenAIService()
        
        # Test generating interview questions
        questions = asyncio.run(service.generate_interview_questions(
            job_title="Software Engineer",
            job_description="We are looking for a skilled software engineer with experience in Python and web development.",
            interview_type="technical",
            duration=30
        ))
        
        assert questions is not None, "Failed to generate interview questions"
        assert len(questions) > 0, "No questions were generated"
        
        logger.info(f"Generated {len(questions)} questions using OpenAI")
        
        # Test evaluating an interview
        mock_answers = []
        for question in questions:
            mock_answers.append({
                "question_id": question["id"],
                "answer": f"This is a test answer for the question about {question['question'][:30]}..."
            })
        
        evaluation = asyncio.run(service.evaluate_interview(
            questions=questions,
            answers=mock_answers,
            job_title="Software Engineer"
        ))
        
        assert evaluation is not None, "Failed to evaluate interview"
        assert "score" in evaluation, "Evaluation does not contain a score"
        
        logger.info(f"Evaluated interview with score {evaluation['score']} using OpenAI")
        
        return True
    except Exception as e:
        logger.error(f"Error in OpenAI service test: {str(e)}")
        return False

def test_deepseek_service():
    """Test the DeepSeek service"""
    
    try:
        # Initialize the service
        service = DeepSeekService()
        
        # Test generating interview questions
        questions = asyncio.run(service.generate_interview_questions(
            job_title="Software Engineer",
            job_description="We are looking for a skilled software engineer with experience in Python and web development.",
            interview_type="technical",
            duration=30
        ))
        
        assert questions is not None, "Failed to generate interview questions"
        assert len(questions) > 0, "No questions were generated"
        
        logger.info(f"Generated {len(questions)} questions using DeepSeek")
        
        # Test evaluating an interview
        mock_answers = []
        for question in questions:
            mock_answers.append({
                "question_id": question["id"],
                "answer": f"This is a test answer for the question about {question['question'][:30]}..."
            })
        
        evaluation = asyncio.run(service.evaluate_interview(
            questions=questions,
            answers=mock_answers,
            job_title="Software Engineer"
        ))
        
        assert evaluation is not None, "Failed to evaluate interview"
        assert "score" in evaluation, "Evaluation does not contain a score"
        
        logger.info(f"Evaluated interview with score {evaluation['score']} using DeepSeek")
        
        return True
    except Exception as e:
        logger.error(f"Error in DeepSeek service test: {str(e)}")
        return False

def test_ai_service():
    """Test the AI service that combines OpenAI and DeepSeek"""
    
    try:
        # Initialize the service
        service = AIService()
        
        # Test generating interview questions with OpenAI
        questions_openai = asyncio.run(service.generate_interview_questions(
            job_title="Software Engineer",
            job_description="We are looking for a skilled software engineer with experience in Python and web development.",
            interview_type="technical",
            duration=30,
            model="openai"
        ))
        
        assert questions_openai is not None, "Failed to generate interview questions with OpenAI"
        assert len(questions_openai) > 0, "No questions were generated with OpenAI"
        
        logger.info(f"Generated {len(questions_openai)} questions using AI service with OpenAI")
        
        # Test generating interview questions with DeepSeek
        questions_deepseek = asyncio.run(service.generate_interview_questions(
            job_title="Software Engineer",
            job_description="We are looking for a skilled software engineer with experience in Python and web development.",
            interview_type="technical",
            duration=30,
            model="deepseek"
        ))
        
        assert questions_deepseek is not None, "Failed to generate interview questions with DeepSeek"
        assert len(questions_deepseek) > 0, "No questions were generated with DeepSeek"
        
        logger.info(f"Generated {len(questions_deepseek)} questions using AI service with DeepSeek")
        
        return True
    except Exception as e:
        logger.error(f"Error in AI service test: {str(e)}")
        return False

if __name__ == "__main__":
    # This allows running the test directly
    import asyncio
    
    # Run the tests
    test_openai_service()
    test_deepseek_service()
    test_ai_service() 
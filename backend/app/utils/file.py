"""
File Utilities
-----------
This module contains utility functions for file operations.
"""

import logging
import os
import tempfile
from fastapi import UploadFile
from typing import Optional

# Configure logging
logger = logging.getLogger(__name__)

async def extract_text_from_cv(file: UploadFile) -> str:
    """
    Extract text from a CV/resume file
    
    Args:
        file: The uploaded file
        
    Returns:
        str: The extracted text
    """
    try:
        # Get the file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Read the file content
        content = await file.read()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(content)
        
        # Extract text based on file type
        if file_ext in ['.pdf']:
            text = extract_text_from_pdf(temp_file_path)
        elif file_ext in ['.docx', '.doc']:
            text = extract_text_from_docx(temp_file_path)
        elif file_ext in ['.txt']:
            text = extract_text_from_txt(temp_file_path)
        else:
            # Delete the temporary file
            os.unlink(temp_file_path)
            raise ValueError(f"Unsupported file format: {file_ext}")
        
        # Delete the temporary file
        os.unlink(temp_file_path)
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from CV: {str(e)}")
        raise

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file
    
    Args:
        file_path: The path to the PDF file
        
    Returns:
        str: The extracted text
    """
    try:
        from PyPDF2 import PdfReader
        
        reader = PdfReader(file_path)
        text = ""
        
        for page in reader.pages:
            text += page.extract_text() + "\n"
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file
    
    Args:
        file_path: The path to the DOCX file
        
    Returns:
        str: The extracted text
    """
    try:
        from docx import Document
        
        document = Document(file_path)
        text = ""
        
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        raise

def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from a TXT file
    
    Args:
        file_path: The path to the TXT file
        
    Returns:
        str: The extracted text
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        return text
    except Exception as e:
        logger.error(f"Error extracting text from TXT: {str(e)}")
        raise 
import os
import logging
from typing import Optional
from PyPDF2 import PdfReader
import docx

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extract text content from a PDF file.
    """
    try:
        with open(file_path, 'rb') as file:
            pdf = PdfReader(file)
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
            return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return None

def extract_text_from_docx(file_path: str) -> Optional[str]:
    """
    Extract text content from a DOCX file.
    """
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {str(e)}")
        return None

def extract_text_from_cv(file_path: str) -> Optional[str]:
    """
    Extract text content from a CV file (supports PDF and DOCX).
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif file_extension in ['.doc', '.docx']:
        return extract_text_from_docx(file_path)
    else:
        logger.error(f"Unsupported file format: {file_extension}")
        return None 
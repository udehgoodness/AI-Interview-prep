#!/usr/bin/env python3
import os
import sys
import logging
from openai import OpenAI
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def test_whisper_api():
    """Test the OpenAI Whisper API directly"""
    try:
        # Check if test audio file exists
        audio_file = "test_tts_output.mp3"
        if not os.path.exists(audio_file):
            logger.error(f"No test audio file found at {audio_file}")
            return False
        
        # Read audio file
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()
        
        # Log audio info
        logger.info(f"Audio file size: {len(audio_bytes) / 1024:.2f} KB")
        logger.info(f"Audio file first 20 bytes: {audio_bytes[:20]}")
        
        # Initialize OpenAI client
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0
        )
        
        # Create a temporary file to store the audio data
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
            logger.info(f"Created temporary file at {temp_file_path}")
        
        # Use the OpenAI client to transcribe the audio
        logger.info("Sending request to OpenAI Whisper API")
        with open(temp_file_path, "rb") as audio_file:
            try:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"
                )
                logger.info("Successfully received response from OpenAI Whisper API")
            except Exception as e:
                logger.error(f"Error calling OpenAI Whisper API: {str(e)}", exc_info=True)
                return False
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        logger.info(f"Deleted temporary file {temp_file_path}")
        
        if transcription and hasattr(transcription, 'text'):
            logger.info(f"Transcription result: {transcription.text}")
            return True
        else:
            logger.error(f"Invalid transcription response: {transcription}")
            return False
    except Exception as e:
        logger.error(f"Error in test_whisper_api: {str(e)}", exc_info=True)
        return False

def main():
    """Run the test"""
    logger.info("Testing OpenAI Whisper API directly")
    
    # Test Whisper API
    result = test_whisper_api()
    
    if result:
        logger.info("OpenAI Whisper API test passed!")
    else:
        logger.error("OpenAI Whisper API test failed!")
    
    return result

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
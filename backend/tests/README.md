# Backend Tests

This directory contains test files for the AI Interview Prep backend API.

## Test Files

- `test_api.py`: Tests for the main API endpoints
- `test_audio_api.py`: Tests for the audio-related API endpoints (speech-to-text and text-to-speech)
- `test_interview_generation.py`: Tests for interview question generation with different interview types and modes

## Running Tests

To run the tests, navigate to the backend directory and run:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_interview_generation.py

# Run with verbose output
python -m pytest tests/ -v
```

You can also use the provided script:

```bash
# Run all tests using the script
python tests/run_tests.py
```

Make sure the backend server is running when you execute the tests, as they need to connect to the API.

## Test Coverage

The tests cover the following functionality:

1. Basic API health check
2. Interview question generation for different interview types:
   - General interviews
   - Technical interviews
   - Behavioral interviews
   - Case study interviews
3. Interview modes:
   - Text-based interviews
   - Voice-enabled interviews
   - Video-enabled interviews
4. Audio processing:
   - Speech-to-text conversion
   - Text-to-speech conversion 
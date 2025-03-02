# Backend Tests

This directory contains test files for the AI Interview Prep backend API.

## Test Files

- `test_api.py`: Tests for the main API endpoints
- `test_audio_api.py`: Tests for the audio-related API endpoints (speech-to-text and text-to-speech)

## Running Tests

To run the tests, navigate to the backend directory and run:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the tests
python -m pytest tests/
```

Make sure the backend server is not running when you execute the tests, as they need to use the same port. 
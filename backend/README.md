# AI Interview Prep Backend

This is the backend service for the AI Interview Preparation application. It provides API endpoints for generating interview questions, evaluating responses, and handling WebRTC video calls.

## Features

- AI-powered interview question generation based on job title, description, and CV
- Interview response evaluation with detailed feedback
- WebRTC signaling for video/audio communication
- Support for both OpenAI and Anthropic AI models

## Tech Stack

- Python 3.9+
- FastAPI
- WebRTC (aiortc)
- OpenAI API
- Anthropic API

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the backend directory with the following variables:
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
TURN_SERVER_URL=your_turn_server_url  # Optional
TURN_SERVER_USERNAME=your_turn_username  # Optional
TURN_SERVER_PASSWORD=your_turn_password  # Optional
```

## Running the Server

Start the development server:
```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access the API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Main Endpoints

- `POST /api/upload-cv`: Upload a CV/resume file
- `POST /api/generate-interview`: Generate interview questions
- `POST /api/evaluate-interview`: Evaluate interview answers
- `POST /api/rtc/offer`: WebRTC signaling for video calls
- `GET /api/health`: Health check endpoint 
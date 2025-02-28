# AI Interview Prep

An AI-powered interview preparation platform that helps users practice for job interviews with realistic simulations and personalized feedback.

## Features

- AI-generated interview questions based on job title, description, and CV
- Live video/voice interviews with AI interviewer using WebRTC
- Code editor for technical interview questions
- Detailed performance evaluation with scores and personalized feedback
- Modern, responsive UI with a clean and professional design

## Tech Stack

### Frontend
- Next.js (React)
- TypeScript
- Tailwind CSS
- Monaco Editor (for code challenges)
- WebRTC (for video communication)

### Backend
- Python
- FastAPI
- OpenAI/Claude APIs
- WebRTC (aiortc)

## Project Structure

- `/frontend` - Next.js frontend application
- `/backend` - Python FastAPI backend application

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.9+
- OpenAI API key and/or Anthropic API key

### Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-interview-prep.git
cd ai-interview-prep
```

2. Set up the frontend:
```bash
cd frontend
npm install
npm run dev
```

3. Set up the backend:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. Create a `.env` file in the backend directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

5. Start the backend server:
```bash
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. Open your browser and navigate to http://localhost:3000

## Usage

1. Enter job details (title, description) and optionally upload your CV
2. Select interview type (technical, behavioral, etc.) and duration
3. Start the interview session with AI interviewer
4. Answer questions via video/voice or text
5. Receive detailed feedback and evaluation after completion

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
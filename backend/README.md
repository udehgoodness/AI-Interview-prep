# AI Interview Prep Backend

This is the backend for the AI Interview Prep platform, a comprehensive interview preparation tool powered by AI.

## Features

- **AI-Powered Interviews**: Generate realistic interview questions based on job descriptions and resumes
- **Multiple AI Models**: Uses OpenAI with DeepSeek as a fallback for reliability
- **Voice Interviews**: Support for speech-to-text and text-to-speech
- **Subscription Management**: Tiered subscription plans with Stripe integration
- **User Authentication**: JWT-based authentication with Auth0 support
- **Role-Based Access Control**: Different features for different subscription tiers

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL
- **AI Integration**: OpenAI API, DeepSeek API
- **Authentication**: JWT, Auth0
- **Payment Processing**: Stripe
- **File Processing**: PyPDF2, python-docx

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- OpenAI API key
- DeepSeek API key (optional)
- Stripe API key (for subscription features)
- Auth0 credentials (optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-interview-prep.git
   cd ai-interview-prep/backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Update the `.env` file with your API keys and database credentials.

6. Initialize the database:
   ```bash
   python -c "from app.database.init_db import init_database; init_database()"
   ```

### Running the Application

Run the application using the provided script:

```bash
python run.py
```

Or directly with uvicorn:

```bash
uvicorn app.factory:create_app --host 0.0.0.0 --port 8000 --reload --factory
```

The API will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/                    # Application package
│   ├── api/                # API endpoints
│   ├── database/           # Database configuration
│   ├── models/             # Pydantic models
│   ├── services/           # Business logic
│   ├── utils/              # Utility functions
│   ├── factory.py          # Application factory
│   └── __init__.py         # Package initialization
├── tests/                  # Test suite
├── .env.example            # Example environment variables
├── .gitignore              # Git ignore file
├── README.md               # This file
├── requirements.txt        # Dependencies
├── run.py                  # Application entry point
└── setup.py                # Package setup
```

## API Endpoints

### Authentication

- `POST /api/auth/register`: Register a new user
- `POST /api/auth/token`: Get an access token
- `POST /api/auth/auth0`: Login with Auth0
- `GET /api/auth/me`: Get current user information

### Subscription

- `GET /api/subscription/plans`: Get all subscription plans
- `POST /api/subscription/user`: Create a new subscription
- `DELETE /api/subscription/user/{subscription_id}`: Cancel a subscription

### Interview

- `POST /api/interview/questions`: Generate interview questions
- `GET /api/interview/questions/progress/{interview_id}`: Get question generation progress
- `POST /api/interview/feedback`: Get feedback on interview answers
- `POST /api/interview/conversation`: Handle interview conversation
- `POST /api/interview/upload-cv`: Upload and process a CV/resume

### Audio

- `POST /api/speech-to-text`: Convert speech to text
- `POST /api/text-to-speech`: Convert text to speech
- `POST /api/upload-audio`: Upload and process an audio file

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
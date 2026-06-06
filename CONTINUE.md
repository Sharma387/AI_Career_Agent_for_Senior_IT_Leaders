# AI Career Agent - Project Guide

A comprehensive AI-powered career guidance and job matching platform.

## 📋 Overview

**AI Career Agent** is a sophisticated application that provides intelligent career guidance, job matching, resume optimization, and comprehensive career support powered by AI agents.

## 🏗️ Architecture

### Core Components

```
app/
├── api/              # API endpoints (FastAPI)
│   ├── routes.py    # Main API routes
│   └── auth.py      # Authentication & authorization
├── agents/          # AI Agents
│   ├── insight_agent.py
│   ├── job_matcher_agent.py
│   └── resume_agent.py
├── core/            # Core services
│   ├── config.py    # Configuration management
│   ├── cache.py     # Caching layer
│   ├── llm_factory.py  # LLM factory
│   └── rate_limit.py  # Rate limiting
├── data/            # Data storage
│   └── [Data files]
├── db/              # Database models
│   └── models.py
├── ingestion/       # Data ingestion
│   ├── career_expander.py
│   ├── job_parser.py
│   └── resume_parser.py
├── rag/             # RAG (Retrieval Augmented Generation)
│   ├── application_rag.py
│   ├── career_rag.py
│   └── job_rag.py
├── services/        # Business logic
│   ├── document_service.py
│   ├── job_service.py
│   ├── profile_service.py
│   └── tracking_service.py
└── main.py          # Application entry point
```

### Technology Stack

- **Framework**: FastAPI
- **LLM Integration**: Multiple LLM providers (configurable)
- **Database**: SQLite (primary), PostgreSQL-compatible interface
- **RAG**: Custom RAG implementation for semantic search
- **Authentication**: JWT-based auth system
- **Caching**: Redis-compatible cache layer
- **File Storage**: Local filesystem with document processing

## 🚀 Development Workflow

### 1. Getting Started

```bash
# Clone and navigate to project
cd /path/to/project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run development server
python app/main.py
```

### 2. Project Structure Understanding

#### API Layer (`app/api/`)
- **routes.py**: All REST API endpoints
  - Authentication routes
  - User profile management
  - Job search and matching
  - Resume analysis
  - Career insights
- **auth.py**: JWT token generation and validation

#### Agent Layer (`app/agents/`)
- **insight_agent.py**: Generates career insights and recommendations
- **job_matcher_agent.py**: Matches users with suitable jobs
- **resume_agent.py**: Analyzes and optimizes resumes

#### Core Services (`app/core/`)
- **config.py**: Environment configuration
- **cache.py**: Memory caching for performance
- **llm_factory.py**: Abstracts LLM provider selection
- **rate_limit.py**: API rate limiting

#### Data Layer (`app/data/`, `app/db/`)
- **models.py**: SQLAlchemy ORM models
- Data files: Job descriptions, resumes, user profiles

#### Ingestion (`app/ingestion/`)
- **job_parser.py**: Parse job descriptions
- **resume_parser.py**: Parse resume documents
- **career_expander.py**: Expand career interests/topics

#### RAG Layer (`app/rag/`)
- Implements semantic search and knowledge retrieval
- Supports application-specific, career-specific, and job-specific queries

#### Services (`app/services/`)
- **document_service.py**: File upload/download management
- **job_service.py**: Job CRUD operations
- **profile_service.py**: User profile management
- **tracking_service.py**: Activity tracking and analytics

## 🔐 Authentication

The application uses JWT-based authentication:

1. **Token Generation**: `/api/v1/auth/login`
2. **Token Validation**: Included in API requests via headers
3. **Refresh Tokens**: Implement refresh mechanism if needed

### Security Features

- Rate limiting (`app/core/rate_limit.py`)
- JWT token validation
- Input validation and sanitization
- Secure file handling

## 📊 Data Models

Key entities defined in `app/db/models.py`:

- **User**: Profiles, preferences, history
- **Job**: Job descriptions, requirements, metadata
- **Resume**: Document data, parsed information
- **Match**: Job-user matches with scores
- **Insight**: Generated career insights

## 🤖 AI Agent Architecture

### Agent Pattern

Each agent follows the standard pattern:

```python
class Agent:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = LLMFactory.get_llm()
    
    def execute(self, context: dict) -> dict:
        """Execute agent logic"""
        pass
```

### Agent Types

1. **Insight Agent**: Provides career guidance and recommendations
2. **Job Matcher Agent**: Matches users with jobs based on skills, preferences
3. **Resume Agent**: Analyzes resumes and suggests improvements

## 📝 API Documentation

Access API documentation at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### Key Endpoints

```
GET    /api/v1/health              # Health check
POST   /api/v1/auth/login          # User login
GET    /api/v1/users/profile       # Get user profile
PUT    /api/v1/users/profile       # Update profile
POST   /api/v1/jobs                # Add new job
GET    /api/v1/jobs                # List jobs
POST   /api/v1/match               # Get job matches
GET    /api/v1/insights            # Get career insights
POST   /api/v1/upload              # Upload documents
GET    /api/v1/download/{filename} # Download documents
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_file_name.py
```

### Test Structure

```
tests/
├── __init__.py
├── test_api.py
├── test_agents.py
├── test_services.py
├── test_db.py
└── conftest.py
```

## 📦 Deployment

### Environment Variables

```bash
# Required
DATABASE_URL=sqlite:./data/app.db
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Optional
CACHE_ENABLED=true
CACHE_TTL=300
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
API_V1_PREFIX=/api/v1
```

### Production Checklist

- [ ] Set strong secrets and keys
- [ ] Configure production database
- [ ] Enable caching (Redis)
- [ ] Set up monitoring/logging
- [ ] Configure SSL/TLS
- [ ] Set up backup strategy
- [ ] Configure rate limiting thresholds

## 🐛 Debugging

### Common Issues

1. **Database Connection**: Check `DATABASE_URL` and file permissions
2. **Cache Errors**: Verify cache service availability
3. **LLM Errors**: Check provider credentials and rate limits
4. **File Upload**: Check `MAX_CONTENT_LENGTH` and storage permissions

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
python app/main.py
```

## 📚 Contributing

### Adding New Features

1. Create new module in appropriate directory
2. Add type hints and docstrings
3. Write unit tests
4. Update API documentation if needed
5. Add migration scripts if changing DB schema

### Code Style

- Use **mypy** for type checking
- Follow PEP 8 conventions
- Use docstrings for all functions
- Write comprehensive error messages

## 🔮 Future Enhancements

- Multi-tenant architecture
- Advanced analytics dashboard
- Mobile app integration
- Voice assistant support
- Multi-language support
- Real-time collaboration features

## 📞 Support

For issues or questions:
- Check existing GitHub issues
- Review API documentation at `/docs`
- Examine model definitions in `app/db/models.py`

---

**Last Updated**: $(date +%Y-%m-%d)  
**Version**: 1.0.0  
**Author**: AI Career Agent Team

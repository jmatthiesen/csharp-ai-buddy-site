# C# AI Buddy - Copilot Instructions

This repository contains a full-stack C# AI assistant application with a FastAPI backend, static frontend, and RAG data ingestion pipeline. These instructions will help you work efficiently with the codebase without extensive exploration.

## Repository Overview

**Purpose**: A web-based AI assistant specialized in C# and .NET AI frameworks, featuring an interactive chat interface and a curated samples gallery.

**Architecture**: 
- **Frontend**: Static HTML/CSS/JavaScript served via Python HTTP server
- **Backend API**: FastAPI (Python) with OpenAI integration and MongoDB storage
- **Data Pipeline**: RAG document processing with AI-powered categorization
- **Deployment**: Render.com via `render.yaml` configuration

**Size & Scale**: ~100 Python files, 6 HTML/CSS/JS files, primarily Python-based with comprehensive testing frameworks.

**Key Technologies**: FastAPI, OpenAI API, MongoDB, HTML/CSS/JavaScript, OpenTelemetry, Render.com deployment.

## Build & Development Instructions

### Prerequisites
- Python 3.8+ (3.13.4 recommended for production)
- MongoDB instance (local or cloud)
- OpenAI API key
- Node.js/npm (for alternative frontend serving only)

### Environment Setup

**ALWAYS** follow this exact sequence for successful setup:

1. **Navigate to API directory**:
   ```bash
   cd src/api
   ```

2. **Install API dependencies** (takes 60-120 seconds):
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (create `.env` in `src/api/`):
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   MONGODB_URI=mongodb://your_mongodb_connection_string
   DATABASE_NAME=your_database_name
   PORT=8000
   ENVIRONMENT=development
   OTEL_EXPORTER_OTLP_ENDPOINT=your_otel_endpoint_here  # Optional
   ```

### Development Startup

**Recommended: Use VS Code tasks** (fastest method):
1. Open repository in VS Code
2. Press `Ctrl+Shift+P` → "Tasks: Run Task" → "Start Full Stack"
3. This automatically starts both API (port 8000) and frontend (port 3000)

**Manual startup**:
```bash
# Terminal 1 - API Server
cd src/api
python main.py
# Server runs on http://localhost:8000

# Terminal 2 - Frontend Server
cd src/frontend  
python -m http.server 3000
# Frontend runs on http://localhost:3000
```

**Alternative uvicorn command**:
```bash
cd src/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Validation & Health Checks

**API Health Check**:
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","timestamp":"...","version":"1.0.0"}
```

**Frontend Access**: Visit `http://localhost:3000` - should load chat interface with samples gallery.

**API Documentation**: Available at `http://localhost:8000/docs` (FastAPI auto-generated).

## Testing & Quality Assurance

### API Evaluation Framework
The repository uses a custom evaluation system (not pytest):

```bash
cd src/api
# Test evaluation framework
python evals/test_evaluation_framework.py
# Note: Some mock tests may fail - this is expected due to mocking limitations

# Run full evaluations (requires OpenAI API key)
python evals/run_evaluations.py --component all
```

**Expected Issues**: Mock tests in evaluation framework may show failures due to OpenAI API mocking challenges. This does not indicate code problems.

### Data Ingestion Tests
```bash
cd src/dataIngestion
# Run mock tests (no API key required)
python tests/run_tests.py
# Run with OpenAI evaluation (requires API key)
python tests/run_tests.py --openai
```

**Note**: Some dependencies (markitdown, bs4, feedparser) may not be installed by default, causing import warnings. This is normal and doesn't affect core functionality.

### Manual Testing Checklist
1. API server starts without errors
2. Health endpoint returns 200 status
3. Frontend loads and displays correctly
4. Chat interface can send messages (with valid OpenAI key)
5. Samples gallery displays properly

## Project Architecture & Layout

### Root Structure
```
├── .gitignore              # Python, VS Code, build artifacts
├── DEPLOYMENT.md           # Comprehensive deployment guide
├── SAMPLES_GALLERY.md      # Gallery feature documentation  
├── render.yaml             # Render.com deployment config
└── src/                    # All source code
```

### Source Organization
```
src/
├── .vscode/                # VS Code tasks, launch configs, settings
│   ├── tasks.json          # "Start Full Stack" and other dev tasks
│   └── launch.json         # Debug configurations
├── api/                    # FastAPI backend
│   ├── main.py             # Main API server entry point
│   ├── requirements.txt    # Python dependencies
│   ├── evals/              # Custom evaluation framework
│   └── sample_data.py      # Sample data population script
├── frontend/               # Static web application
│   ├── index.html          # Main application entry point
│   ├── script.js           # Chat and gallery functionality
│   └── styles.css          # Application styling
├── dataIngestion/          # RAG pipeline for document processing
│   ├── rag_data_pipeline.py # Main pipeline entry point
│   ├── requirements.txt    # Pipeline dependencies
│   └── tests/              # Comprehensive test suite
└── setup-dev.sh            # Development environment setup script
```

### Key Configuration Files
- **API Config**: `src/api/.env` (create from examples in docs)
- **VS Code Config**: `src/.vscode/tasks.json` (pre-configured tasks)
- **Deployment Config**: `render.yaml` (production deployment)
- **Environment Examples**: `src/api/.env.example`, `src/dataIngestion/env.example`

### Critical Dependencies
- **API**: FastAPI, OpenAI, PyMongo, OpenTelemetry, Uvicorn
- **Data Pipeline**: OpenAI, PyMongo, MarkItDown, BeautifulSoup4, feedparser
- **Frontend**: No build dependencies (static files)

## API Endpoints & Functionality

### Main Endpoints
- `GET /health` - Health check
- `POST /api/chat` - Streaming chat with OpenAI
- `GET /api/samples` - Paginated samples with search/filtering
- `GET /api/samples/{id}` - Individual sample details
- `POST /api/telemetry` - Usage tracking

### Database Schema (MongoDB)
- **Samples Collection**: `{id, title, description, author, source, tags, preview}`
- **Documents Collection**: `{document_id, content, embeddings, tags, metadata}`

## Common Issues & Solutions

### Build Failures
- **"Module not found" errors**: Ensure you're in the correct directory (`src/api` or `src/dataIngestion`)
- **Pip timeout errors**: Retry installation or use `--timeout 300`
- **Import errors**: Check virtual environment activation

### Runtime Issues  
- **API won't start**: Check port 8000 availability, verify environment variables
- **OpenAI errors**: Verify API key validity and quota
- **MongoDB errors**: Ensure MongoDB is running and connection string is correct
- **CORS errors**: Check frontend is accessing correct API URL

### Testing Issues
- **Evaluation test failures**: Expected for mock tests, focus on real API tests
- **Missing dependencies warnings**: Normal for optional data ingestion components

## Environment Variables Reference

### Required (API)
- `OPENAI_API_KEY`: OpenAI API access key
- `MONGODB_URI`: MongoDB connection string  
- `DATABASE_NAME`: MongoDB database name

### Optional
- `PORT`: API server port (default: 8000)
- `ENVIRONMENT`: development/production
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry endpoint

## Deployment

**Production Platform**: Render.com with automatic deployment from `main` branch.

**Deployment Files**:
- `render.yaml`: Complete Render.com configuration
- `DEPLOYMENT.md`: Step-by-step deployment instructions

**Pre-deployment Checklist**:
1. Test local build: `pip install -r src/api/requirements.txt`
2. Verify health endpoint: `curl http://localhost:8000/health`
3. Check environment variables are set
4. Validate frontend loads correctly

## Development Workflow

### Making Changes
1. **Always** test locally before committing
2. **Always** run `python main.py` to verify API starts
3. **Always** check frontend at `http://localhost:3000`
4. Use VS Code tasks for efficient development

### Common Tasks
- **Add new API endpoint**: Edit `src/api/main.py`
- **Modify frontend**: Edit files in `src/frontend/`
- **Add sample data**: Run `python src/api/sample_data.py`
- **Update dependencies**: Edit `requirements.txt` files

### Debugging
- **VS Code**: Use "Debug Full Stack" launch configuration
- **API logs**: Check console output from `python main.py`
- **Frontend**: Use browser developer tools
- **Health check**: Always verify `/health` endpoint

**Trust these instructions** - they are validated and comprehensive. Only search for additional information if these instructions are incomplete or you encounter undocumented errors.
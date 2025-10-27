# C# AI Buddy

**Your assistant for building AI solutions with .NET**

C# AI Buddy is an AI-powered chat assistant specifically designed to help C# developers navigate the rapidly evolving .NET AI ecosystem. Get context-aware guidance, curated code samples, and real-time answers to cut your AI development time in half.

[![Live Site](https://img.shields.io/badge/🌐_Live_Site-csharpaibuddy.com-blue?style=for-the-badge)](https://csharpaibuddy.com)
[![Preview Key](https://img.shields.io/badge/🔑_Preview_Key-PREVIEW2025-green?style=for-the-badge)](#try-it-now)

---

## 🎯 What is C# AI Buddy?

C# AI Buddy helps developers cut through the noise in the .NET AI landscape by providing:

- **🤖 AI Chat Assistant** - Context-aware guidance based on your .NET version, AI library, and provider
- **📚 Code Samples Gallery** - Curated examples from across the .NET AI community
- **📰 .NET AI News Feed** - Latest articles and announcements with AI-generated summaries
- **📦 NuGet Recommendations** - Package suggestions with documentation links
- **👍 Feedback Loop** - Community-driven improvements through rating system

Instead of spending hours researching which approach to take (Semantic Kernel vs ML.NET vs AutoGen?), just ask and get tailored answers for your specific stack.

## 🚀 Try It Now

Visit **[csharpaibuddy.com](https://csharpaibuddy.com)** and use the preview key:

```
PREVIEW2025
```

## 💬 Feedback & Support

We'd love to hear from you! Here's how to get in touch:

- **💬 In-app feedback** - Use the thumbs up/down buttons on any AI response
- **🐛 Bug reports & feature requests** - [Open an issue](https://github.com/jmatthiesen/csharp-ai-buddy-site/issues)
- **💡 General feedback** - [Start a discussion](https://github.com/jmatthiesen/csharp-ai-buddy-site/discussions)
- **📧 Direct contact** - Reach out to [@jmatthiesen](https://github.com/jmatthiesen)

## 🛠️ Local Development

### Prerequisites

- **Python 3.11+** (the project uses Python 3.13)
- **MongoDB** (local instance or MongoDB Atlas)
- **OpenAI API key**

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/jmatthiesen/csharp-ai-buddy-site.git
   cd csharp-ai-buddy-site
   ```

2. **Run the setup script**
   ```bash
   cd src
   chmod +x setup-dev.sh
   ./setup-dev.sh
   ```

3. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp src/api/.env.example src/api/.env
   
   # Edit the .env file with your configuration
   nano src/api/.env
   ```

   Required environment variables:
   ```bash
   OPENAI_API_KEY=your_openai_api_key_here
   MONGODB_URI=mongodb://localhost:27017  # or your MongoDB Atlas connection string
   DATABASE_NAME=csharp_ai_buddy
   ```

4. **Start the development servers**

   **Option A: Using VS Code (Recommended)**
   - Open the project in VS Code
   - Press `F5` to start debugging, or
   - Run the "Start Full Stack" task from the Command Palette (`Ctrl+Shift+P`)

   **Option B: Manual startup**
   ```bash
   # Terminal 1: Start the API server
   cd src/api
   source ../venv/bin/activate
   python main.py
   
   # Terminal 2: Start the frontend server
   cd src/frontend
   python -m http.server 3000
   ```

5. **Access the application**
   - **Frontend:** http://localhost:3000
   - **API:** http://localhost:8000
   - **API Documentation:** http://localhost:8000/docs

### Project Structure

```
├── src/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py            # Main API application
│   │   ├── models.py          # Data models
│   │   ├── routers/           # API route handlers
│   │   └── requirements.txt   # Python dependencies
│   ├── frontend/              # Static HTML/CSS/JS frontend
│   ├── dataIngestion/         # Content processing pipeline
│   └── setup-dev.sh          # Development setup script
├── dbSetup/                   # MongoDB index configurations
└── render.yaml               # Production deployment config
```

### Architecture Overview

- **Backend:** FastAPI with OpenAI Agents SDK for multi-agent orchestration
- **Database:** MongoDB with vector search for semantic document retrieval
- **Frontend:** Vanilla JavaScript with streaming AI responses
- **Observability:** OpenTelemetry instrumentation with Arize Phoenix integration
- **Data Pipeline:** Automated processing of web content, blog posts, and RSS feeds

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Ways to Contribute

1. **📝 Content & Samples**
   - Add new code samples to the gallery
   - Suggest new content sources for the data pipeline
   - Improve existing documentation

2. **🐛 Bug Fixes & Features**
   - Fix bugs or implement new features
   - Improve AI prompts and responses
   - Enhance the user interface

3. **📚 Documentation**
   - Improve setup instructions
   - Add architecture documentation
   - Create tutorials and guides

### Development Workflow

1. **Fork the repository** and create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards:
   - Follow PEP 8 for Python code
   - Include type hints and docstrings
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**
   ```bash
   # Run API tests
   cd src/api
   python -m pytest
   
   # Run data ingestion tests
   cd src/dataIngestion
   python -m pytest tests2/
   ```

4. **Submit a Pull Request**
   - Provide a clear description of your changes
   - Reference any related issues
   - Include screenshots for UI changes

### Code Standards

- **Python:** Follow PEP 8, use type hints, include docstrings
- **JavaScript:** Use modern ES6+ syntax, maintain consistent formatting
- **Documentation:** Clear, concise, and up-to-date

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [OpenAI Agents SDK](https://github.com/openai/openai-agents)
- Vector search powered by [MongoDB Atlas](https://www.mongodb.com/atlas)
- Observability provided by [Arize Phoenix](https://phoenix.arize.com/)
- Deployed on [Render](https://render.com/)

---

**Ready to supercharge your .NET AI development?** [Try C# AI Buddy today!](https://csharpaibuddy.com) 🚀
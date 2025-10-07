#!/bin/bash

# C# AI Buddy Development Environment Startup Script

echo "🚀 Starting C# AI Buddy Development Environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r api/requirements.txt

echo "✅ Setup complete!"
echo ""
echo "📝 To start development:"
echo "   1. Press F5 in VS Code to start debugging"
echo "   2. Or run the 'Start Full Stack' task from VS Code"
echo "   3. Frontend will be available at: http://localhost:3000"
echo "   4. API will be available at: http://localhost:8000"
echo ""
echo "🔍 API documentation available at: http://localhost:8000/docs"

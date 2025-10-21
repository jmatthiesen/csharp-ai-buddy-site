#!/bin/bash

# C# AI Buddy Development Environment Startup Script

set -e  # Exit on any error

echo "🚀 Starting C# AI Buddy Development Environment..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Function to setup virtual environment for a project
setup_venv() {
    local project_dir=$1
    local project_name=$2
    
    echo "📦 Setting up $project_name virtual environment..."
    
    cd "$project_dir"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "   Creating .venv for $project_name..."
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    echo "   Activating .venv for $project_name..."
    source .venv/bin/activate
    
    # Install dependencies if requirements.txt exists
    if [ -f "requirements.txt" ]; then
        echo "   Installing dependencies for $project_name..."
        pip install --upgrade pip
        pip install -r requirements.txt
    else
        echo "   No requirements.txt found for $project_name"
    fi
    
    # Deactivate to prepare for next project
    deactivate
    
    cd - > /dev/null  # Return to previous directory silently
}

# Function to start a service in background
start_service() {
    local service_name=$1
    local project_dir=$2
    local start_command=$3
    local port=$4
    
    echo "🔧 Starting $service_name on port $port..."
    
    cd "$project_dir"
    
    # Kill any existing process on the port
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
    
    # Start the service in background
    if [ -d ".venv" ]; then
        source .venv/bin/activate
        eval "$start_command" &
        echo "   $service_name started with PID $!"
    else
        # For frontend (no venv needed)
        eval "$start_command" &
        echo "   $service_name started with PID $!"
    fi
    
    cd - > /dev/null
    sleep 2  # Give service time to start
}

# Setup all project environments
echo "🔧 Setting up project environments..."
setup_venv "api" "API"
setup_venv "dataIngestion" "Data Ingestion"

echo ""
echo "✅ Environment setup complete!"
echo ""

# Parse command line arguments
START_API=true
START_FRONTEND=true
START_DATA_INGESTION=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --api-only)
            START_FRONTEND=false
            START_DATA_INGESTION=false
            shift
            ;;
        --frontend-only)
            START_API=false
            START_DATA_INGESTION=false
            shift
            ;;
        --data-ingestion-only)
            START_API=false
            START_FRONTEND=false
            START_DATA_INGESTION=true
            shift
            ;;
        --with-data-ingestion)
            START_DATA_INGESTION=true
            shift
            ;;
        --setup-only)
            START_API=false
            START_FRONTEND=false
            START_DATA_INGESTION=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --api-only              Start only the API server"
            echo "  --frontend-only         Start only the frontend server"
            echo "  --data-ingestion-only   Start only the data ingestion tools"
            echo "  --with-data-ingestion   Start API + Frontend + Data Ingestion"
            echo "  --setup-only            Only setup environments, don't start services"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Default: Start API + Frontend"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Start requested services
if [ "$START_API" = true ]; then
    start_service "API Server" "api" "python main.py" "8000"
fi

if [ "$START_FRONTEND" = true ]; then
    start_service "Frontend Server" "frontend" "python3 -m http.server 3000" "3000"
fi

if [ "$START_DATA_INGESTION" = true ]; then
    echo "🔧 Data Ingestion environment ready..."
    echo "   To use data ingestion tools:"
    echo "   cd dataIngestion && source .venv/bin/activate"
    echo "   Then run: python cli.py --help"
fi

echo ""
echo "🎉 Development environment is ready!"
echo ""

if [ "$START_API" = true ] || [ "$START_FRONTEND" = true ]; then
    echo "📋 Running Services:"
    [ "$START_API" = true ] && echo "   🔌 API Server:      http://localhost:8000"
    [ "$START_API" = true ] && echo "   📖 API Docs:       http://localhost:8000/docs"
    [ "$START_FRONTEND" = true ] && echo "   🌐 Frontend:       http://localhost:3000"
    echo ""
    echo "📝 Development Tips:"
    echo "   • Press Ctrl+C to stop all services"
    echo "   • Use F5 in VS Code for debugging"
    echo "   • Check logs in terminal for any issues"
    echo ""
    echo "� Environment Management:"
    echo "   • API env:          cd api && source .venv/bin/activate"
    echo "   • Data Ingestion:   cd dataIngestion && source .venv/bin/activate"
    echo ""
    
    # Wait for Ctrl+C to stop all services
    echo "Press Ctrl+C to stop all services..."
    trap 'echo ""; echo "🛑 Stopping all services..."; jobs -p | xargs kill 2>/dev/null || true; echo "✅ All services stopped."; exit 0' INT
    wait
else
    echo "📝 To start services manually:"
    echo ""
    echo "🔌 API Server:"
    echo "   cd api && source .venv/bin/activate && python main.py"
    echo ""
    echo "🌐 Frontend:"
    echo "   cd frontend && python3 -m http.server 3000"
    echo ""
    echo "📊 Data Ingestion:"
    echo "   cd dataIngestion && source .venv/bin/activate && python cli.py --help"
fi

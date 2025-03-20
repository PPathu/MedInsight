#!/bin/bash

echo "🔧 Setting up the project..."

# 🐍 Python Setup and 🚀 Starting FastAPI backend
echo "🐍 Setting up Python virtual environment and 🚀 Starting FastAPI backend..."

# Check if the backend directory exists
if [ ! -d "qwen-mimic-app/backend" ]; then
    echo "❌ Backend directory missing!"
    exit 1
fi

cd qwen-mimic-app/backend

# Create virtual environment if it doesn't exist
if [ ! -d "env" ]; then
    python3 -m venv env
fi

# Activate virtual environment
source env/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 📄 Create .env file in backend directory if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file..."
    cat <<EOL > .env
QWEN_API_KEY=Enter_Your_API_Key_Here
MIMIC_DB_PATH="Enter Your Path To The MIMIC4.db file here"
EOL
    echo "✅ .env file created!"
else
    echo "✅ .env file already exists, skipping creation."
fi

# Start FastAPI backend in the background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 🌐 React Frontend Setup
echo "🌐 Setting up React frontend..."

# Check if the frontend directory exists
if [ ! -d "../frontend" ]; then
    echo "❌ Frontend directory missing!"
    exit 1
fi

cd ../frontend

# If package.json is missing, initialize a React project
if [ ! -f "package.json" ]; then
    echo "⚠️ No package.json found. Initializing React project..."
    npx create-react-app .
fi

# Install frontend dependencies and start the React app
npm install
npm start

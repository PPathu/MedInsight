#!/bin/bash

echo "🔧 Setting up the project..."

# 1️⃣ Set up Python environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2️⃣ Run FastAPI backend
echo "🚀 Starting FastAPI backend..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 3️⃣ Set up frontend
echo "🌐 Setting up React frontend..."
cd frontend
npm install
npm start

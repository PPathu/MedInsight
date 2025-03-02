echo "🔧 Setting up the project..."

# Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
python -m venv env
env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Run FastAPI backend
echo "🚀 Starting FastAPI backend..."
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8000"

# Set up frontend
echo "🌐 Setting up React frontend..."
cd frontend
npm install
npm start

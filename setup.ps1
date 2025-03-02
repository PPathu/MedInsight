Write-Host "🔧 Setting up the project..."

# 🐍 Python Setup and 🚀 Starting FastAPI backend
Write-Host "🐍 Setting up Python virtual environment and 🚀 Starting FastAPI backend..."
Set-Location -Path "qwen-mimic-app/backend"

# Create virtual environment if it doesn't exist
if (!(Test-Path "env")) {
    python -m venv env
}

# Activate virtual environment
env\Scripts\Activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Start FastAPI backend in the background
Start-Process -NoNewWindow -FilePath "uvicorn" -ArgumentList "app.main:app --host 0.0.0.0 --port 8000"

# 🌐 React Frontend (Correct Path)
Write-Host "🌐 Setting up React frontend..."
Set-Location -Path "../frontend"

# Check if package.json exists, if not, create a new React app
if (!(Test-Path "package.json")) {
    Write-Host "⚠️ No package.json found. Initializing React project..."
    npx create-react-app .
}

# Install frontend dependencies and start the React app
npm install
npm start

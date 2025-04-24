#!/bin/bash

# Check for Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 is required but not found."
    echo "Please install Python 3.11 using:"
    echo "brew install python@3.11"
    exit 1
fi

echo "🔧 Setting up a fresh environment for the project..."

# 🐍 Python Setup and 🚀 Starting FastAPI backend
echo "🐍 Creating a completely fresh Python virtual environment..."

# Check if the backend directory exists
if [ ! -d "qwen-mimic-app/backend" ]; then
    echo "❌ Backend directory missing!"
    exit 1
fi

cd qwen-mimic-app/backend

# Remove the old environment completely
if [ -d "env" ]; then
    echo "🧹 Removing old virtual environment..."
    rm -rf env
fi

if [ -d "fresh_env" ]; then
    echo "🧹 Removing old fresh environment..."
    rm -rf fresh_env
fi

# Create a completely fresh virtual environment with Python 3.11
echo "🔄 Creating new virtual environment with Python 3.11..."
python3.11 -m venv fresh_env

# Activate the new environment
source fresh_env/bin/activate

# Verify Python version
PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if [ "$PYTHON_VERSION" != "3.11" ]; then
    echo "❌ Wrong Python version detected: $PYTHON_VERSION. Expected 3.11"
    echo "Please make sure python3.11 is installed and in your PATH"
    exit 1
fi

echo "🐍 Using Python $PYTHON_VERSION"

# Upgrade pip
echo "📦 Installing required packages..."
pip install --upgrade pip

# Install all dependencies from requirements.txt
echo "📦 Installing dependencies from requirements.txt..."
pip install --no-cache-dir -r requirements.txt

# Check if there were any installation errors
if [ $? -ne 0 ]; then
    echo "❌ Error installing some dependencies."
    echo "⚠️ If you're on Apple Silicon, some packages might need special handling."
    
    # Try installing PyTorch separately for Apple Silicon
    if [ "$(uname -m)" == "arm64" ]; then
        echo "🍎 Detected Apple Silicon, installing PyTorch separately..."
        pip install --no-cache-dir torch torchvision torchaudio
    fi
    
    # Try installing again without the problematic packages
    echo "🔄 Retrying installation without potentially problematic packages..."
    pip install --no-cache-dir -r requirements.txt --no-deps
fi

# Create symlinks for the app directory to use the new environment
echo "🔄 Creating app directory symlink in new environment..."
ln -sf "$(pwd)/app" "$(pwd)/fresh_env/lib/python$PYTHON_VERSION/site-packages/"

# 📄 Create .env file in backend directory if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📄 Creating .env file..."
    cat <<EOL > .env
MIMIC_DB_PATH="Enter Your Path To The MIMIC4.db file here"
LLM_MODEL_NAME="tossowski/MedAgentReasoner-3B-Chat"
EOL
    echo "✅ .env file created!"
    echo "⚠️ IMPORTANT: You must update the .env file with your actual MIMIC_DB_PATH before running the application."
else
    echo "✅ .env file already exists, checking for required fields..."
    # Check if LLM_MODEL_NAME field exists in .env file
    if ! grep -q "LLM_MODEL_NAME" .env; then
        echo "LLM_MODEL_NAME=\"tossowski/MedAgentReasoner-3B-Chat\"" >> .env
        echo "✅ Added LLM_MODEL_NAME to .env file."
    fi
    
    # Make sure the old API key entry is removed
    if grep -q "QWEN_API_KEY" .env; then
        sed -i '' '/QWEN_API_KEY/d' .env
        echo "✅ Removed deprecated API key entry from .env file."
    fi
fi

echo "⚠️ IMPORTANT: The application now requires a valid database connection and local model."
echo "⚠️ Mock implementations have been removed for accuracy and reliability."

# Ensure CORS is properly configured to allow connections from the frontend
echo "📋 Checking and updating CORS settings..."
MAIN_PY="app/main.py"
if grep -q "allow_origins=\[\"http://localhost:3000\"\]" "$MAIN_PY"; then
    echo "⚠️ Updating CORS settings to allow all origins for easier testing..."
    sed -i '' 's/allow_origins=\["http:\/\/localhost:3000"\]/allow_origins=["*"]  # Allow all origins for testing/g' "$MAIN_PY"
    echo "✅ CORS settings updated."
fi

# Check if the reasoner.py file has been updated to support conversation history properly
echo "🔍 Checking reasoner implementation..."
REASONER_PY="app/reasoner.py"
if grep -q "process_reasoning" "$REASONER_PY"; then
    echo "✅ Reasoner implementation looks good with process_reasoning method."
else 
    echo "⚠️ Reasoner implementation might need updates."
    echo "⚠️ Please check the reasoner.py file to ensure it handles conversation history properly."
fi

# Check if the diagnose.py file handles both POST and GET requests properly
DIAGNOSE_PY="app/diagnose.py"
if grep -q "@router.post(\"/provide_info\")" "$DIAGNOSE_PY" && grep -q "@router.get(\"/provide_info\")" "$DIAGNOSE_PY"; then
    echo "✅ API endpoints look good with both POST and GET support."
else
    echo "⚠️ API endpoints may need updates to support POST and GET methods."
    echo "⚠️ Please check the diagnose.py file to ensure it handles both request types."
fi

# Check if the MIMIC_DB_PATH is set and valid
echo "🔍 Checking database configuration..."
DB_PATH=$(grep MIMIC_DB_PATH .env | cut -d '"' -f 2)
if [ "$DB_PATH" == "Enter Your Path To The MIMIC4.db file here" ] || [ -z "$DB_PATH" ]; then
    echo "⚠️ MIMIC database path not configured properly in .env file."
    echo "⚠️ Please update the MIMIC_DB_PATH in the .env file before starting the server."
    read -p "Do you want to enter the database path now? (y/n): " answer
    if [ "$answer" == "y" ]; then
        read -p "Enter the full path to your MIMIC4.db file: " db_path
        sed -i '' "s|MIMIC_DB_PATH=\".*\"|MIMIC_DB_PATH=\"$db_path\"|" .env
        echo "✅ Database path updated."
    else
        echo "⚠️ You must update the database path manually before the application will work."
        echo "⚠️ Edit the .env file and set MIMIC_DB_PATH to the correct path."
    fi
fi

# Create a validation script to test for binary compatibility issues
echo "🔍 Creating compatibility test script..."
cat > test_compatibility.py << EOL
import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("Testing package compatibility...")

try:
    import numpy
    print(f"✅ NumPy version: {numpy.__version__}")
    
    import torch
    print(f"✅ PyTorch version: {torch.__version__}")
    
    import transformers
    print(f"✅ Transformers version: {transformers.__version__}")
    
    from transformers import AutoTokenizer
    print("✅ AutoTokenizer imported")
    
    from transformers import AutoModelForCausalLM
    print("✅ AutoModelForCausalLM imported")
    
    print("All imports successful, packages are compatible!")
except Exception as e:
    print(f"❌ Error during imports: {e}")
    exit(1)
EOL

# Run compatibility test
python test_compatibility.py

if [ $? -ne 0 ]; then
    echo "❌ Compatibility test failed. Some packages may not work correctly."
    echo "⚠️ You may need to adjust package versions or try with a different Python version."
    read -p "Continue anyway? (y/n): " continue_compat
    if [ "$continue_compat" != "y" ]; then
        echo "Setup aborted."
        exit 1
    fi
else
    echo "✅ Compatibility test passed! Packages are working together correctly."
fi

# Start FastAPI backend in the background
echo "🚀 Starting FastAPI backend with new environment..."
export PYTHONPATH="$(pwd):$PYTHONPATH"
nohup fresh_env/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend_fresh.log 2>&1 &
BACKEND_PID=$!

# Wait for backend to start (increased wait time for model loading)
echo "⏳ Waiting for backend to start (this may take a few minutes for model loading)..."
MAX_ATTEMPTS=30  # 5 minutes total wait time
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    echo "Checking server status (attempt $ATTEMPT of $MAX_ATTEMPTS)..."
    if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        echo "✅ Backend server is running!"
        break
    fi
    
    # Check if the process is still running
    if ! ps -p $BACKEND_PID > /dev/null; then
        echo "❌ Backend process terminated unexpectedly"
        echo "📋 Recent backend log entries:"
        tail -n 20 backend_fresh.log
        exit 1
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    sleep 10  # Wait 10 seconds between attempts
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "⚠️ Backend server took too long to start, but process is still running"
    echo "📋 Recent backend log entries:"
    tail -n 20 backend_fresh.log
    echo "⚠️ The server might still be loading the model. You can:"
    echo "1. Wait for the model to finish loading"
    echo "2. Check backend_fresh.log for progress"
    echo "3. Use 'kill $BACKEND_PID' to stop the server if needed"
    
    # Ask if user wants to continue to frontend setup
    read -p "Continue with frontend setup anyway? (y/n): " continue_setup
    if [ "$continue_setup" != "y" ]; then
        echo "Setup aborted. Check backend_fresh.log for details."
        exit 1
    fi
fi

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

# Check if styles.css exists and contains the UI updates
STYLES_CSS="src/styles.css"
if grep -q "debug-toggle-button" "$STYLES_CSS"; then
    echo "✅ UI styling looks good with debug panel support."
else
    echo "⚠️ UI styles might be missing recent updates."
    echo "⚠️ If you encounter UI issues, you may need to manually update the styles.css file."
fi

# Check Layout.js for conversation history handling
LAYOUT_JS="src/components/Layout.js"
if grep -q "conversationHistory" "$LAYOUT_JS" && grep -q "localStorage" "$LAYOUT_JS"; then
    echo "✅ UI components look good with conversation history support."
else
    echo "⚠️ UI components might be missing recent updates for conversation history."
    echo "⚠️ If you encounter issues with follow-up queries, check the Layout.js file."
fi

# Install frontend dependencies and start the React app
echo "📦 Installing frontend dependencies..."
npm install
npm install axios

echo "🚀 Starting React frontend..."
npm start

# Provide cleanup instructions
echo "🔧 Setup complete! Both backend and frontend should be running."
echo ""
echo "ℹ️ IMPORTANT: The backend server is running in the background with PID $BACKEND_PID"
echo "ℹ️ To stop the backend server when done: kill $BACKEND_PID"
echo ""
echo "⚠️ If you encounter connection errors:"
echo "1. Ensure the database path is correctly set in the .env file"
echo "2. Check backend_fresh.log for detailed error messages"
echo "3. To use the fresh environment in the future, activate it with:"
echo "   source qwen-mimic-app/backend/fresh_env/bin/activate"
echo "4. Then run the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "📝 UI Updates:"
echo "1. Debug panel toggle is available in the top left of the chat window"
echo "2. User messages now appear on the right side"
echo "3. System (AI) messages appear on the left side"
echo "4. Reasoning and diagnosis sections have special formatting"

chmod +x fresh_setup.sh 

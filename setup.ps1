Write-Host '🔧 Setting up the project...'

# Check for Python version
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "🐍 Detected Python $pythonVersion"

if ([version]$pythonVersion -lt [version]"3.9") {
    Write-Host "❌ Python 3.9 or higher is required but found $pythonVersion"
    exit 1
}

# 🐍 Python Setup and 🚀 Starting FastAPI backend
Write-Host '🐍 Setting up Python virtual environment and 🚀 Starting FastAPI backend...'
Set-Location -Path 'qwen-mimic-app/backend'

# Create fresh virtual environment
if (Test-Path 'env') {
    Write-Host '🧹 Removing old virtual environment...'
    Remove-Item -Path 'env' -Recurse -Force
}

if (Test-Path 'fresh_env') {
    Write-Host '🧹 Removing old fresh environment...'
    Remove-Item -Path 'fresh_env' -Recurse -Force
}

Write-Host '🔄 Creating new virtual environment...'
python -m venv fresh_env

# Activate virtual environment
Write-Host '📦 Activating environment and installing packages...'
& fresh_env\Scripts\Activate

# Upgrade pip and install dependencies from requirements.txt
pip install --upgrade pip

# Install all dependencies from requirements.txt
Write-Host '📦 Installing dependencies from requirements.txt...'
$pipResult = pip install --no-cache-dir -r requirements.txt

# Check if there were any installation errors
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error installing some dependencies."
    
    # Check if we're on Windows ARM
    $isARM = $env:PROCESSOR_ARCHITECTURE -eq "ARM64"
    if ($isARM) {
        Write-Host "⚠️ Detected ARM processor, installing PyTorch separately..."
        pip install --no-cache-dir torch torchvision torchaudio
    }
    
    # Try installing again without the problematic packages
    Write-Host "🔄 Retrying installation without potential problematic dependencies..."
    pip install --no-cache-dir -r requirements.txt --no-deps
}

# Create a validation script to test for binary compatibility issues
Write-Host "🔍 Creating compatibility test script..."
$testScript = @"
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
"@

Set-Content -Path "test_compatibility.py" -Value $testScript

# Run compatibility test
python test_compatibility.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Compatibility test failed. Some packages may not work correctly."
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Setup aborted."
        exit 1
    }
} else {
    Write-Host "✅ Compatibility test passed! Packages are working together correctly."
}

# 📄 Create .env file in backend directory if it doesn't exist
$envFile = '.env'
if (!(Test-Path $envFile)) {
    Write-Host '📄 Creating .env file...'

    $envContent = @'
MIMIC_DB_PATH=<RELATIVE PATH TO MIMIC DB FROM BACKEND FOLDER>
LLM_MODEL_NAME=tossowski/MedAgentReasoner-3B-Chat
'@

    [System.Text.Encoding]::UTF8.GetBytes($envContent) | Set-Content -Path ".env" -Encoding Byte
    Write-Host "✅ .env file created!"
    Write-Host "⚠️ IMPORTANT: Please update the .env file with your actual MIMIC_DB_PATH before running the application."

} else {
    Write-Host '✅ .env file already exists, checking for required fields...'
    # Check if LLM_MODEL_NAME field exists in .env file
    if (!(Select-String -Path $envFile -Pattern "LLM_MODEL_NAME")) {
        Add-Content -Path $envFile -Value "LLM_MODEL_NAME=tossowski/MedAgentReasoner-3B-Chat"
        Write-Host "✅ Added LLM_MODEL_NAME to .env file."
    }
    
    # Make sure the old API key entry is removed
    if (Select-String -Path $envFile -Pattern "QWEN_API_KEY") {
        (Get-Content $envFile) -notmatch 'QWEN_API_KEY' | Set-Content $envFile
        Write-Host "✅ Removed deprecated API key entry from .env file."
    }
}

Write-Host '⚠️ IMPORTANT: The application now requires a valid database connection and local model.'
Write-Host '⚠️ Mock implementations have been removed for accuracy and reliability.'

# Ensure CORS is properly configured to allow connections from the frontend
Write-Host "📋 Checking and updating CORS settings..."
$MainPyFile = "app/main.py"
$MainPyContent = Get-Content -Path $MainPyFile -Raw
if ($MainPyContent -match 'allow_origins=\["http://localhost:3000"\]') {
    Write-Host "⚠️ Updating CORS settings to allow all origins for easier testing..."
    $UpdatedContent = $MainPyContent -replace 'allow_origins=\["http://localhost:3000"\]', 'allow_origins=["*"]  # Allow all origins for testing'
    Set-Content -Path $MainPyFile -Value $UpdatedContent
    Write-Host "✅ CORS settings updated."
}

# Check if the reasoner.py file has been updated to support conversation history properly
Write-Host "🔍 Checking reasoner implementation..."
$ReasonerPyFile = "app/reasoner.py"
if (Select-String -Path $ReasonerPyFile -Pattern "process_reasoning") {
    Write-Host "✅ Reasoner implementation looks good with process_reasoning method."
} else {
    Write-Host "⚠️ Reasoner implementation might need updates."
    Write-Host "⚠️ Please check the reasoner.py file to ensure it handles conversation history properly."
}

# Check if the diagnose.py file handles both POST and GET requests properly
$DiagnosePyFile = "app/diagnose.py"
$hasPost = Select-String -Path $DiagnosePyFile -Pattern "@router.post\(\"/provide_info\"\)"
$hasGet = Select-String -Path $DiagnosePyFile -Pattern "@router.get\(\"/provide_info\"\)"

if ($hasPost -and $hasGet) {
    Write-Host "✅ API endpoints look good with both POST and GET support."
} else {
    Write-Host "⚠️ API endpoints may need updates to support POST and GET methods."
    Write-Host "⚠️ Please check the diagnose.py file to ensure it handles both request types."
}

# Start FastAPI backend in the background
Write-Host '🚀 Starting FastAPI backend...'
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
$BackendProcess = Start-Process -NoNewWindow -FilePath 'fresh_env\Scripts\uvicorn' -ArgumentList 'app.main:app --host 0.0.0.0 --port 8000' -PassThru

# Wait for backend to start (increased wait time for model loading)
Write-Host "⏳ Waiting for backend to start (this may take a few minutes for model loading)..."
$maxAttempts = 30  # 5 minutes total wait time
$attempt = 1

while ($attempt -le $maxAttempts) {
    Write-Host "Checking server status (attempt $attempt of $maxAttempts)..."
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5
        Write-Host "✅ Backend server is running!"
        break
    } catch {
        # Check if the process is still running
        if ($BackendProcess.HasExited) {
            Write-Host "❌ Backend process terminated unexpectedly"
            exit 1
        }
        
        $attempt++
        Start-Sleep -Seconds 10  # Wait 10 seconds between attempts
    }
}

if ($attempt -gt $maxAttempts) {
    Write-Host "⚠️ Backend server took too long to start, but process is still running"
    Write-Host "⚠️ The server might still be loading the model. You can:"
    Write-Host "1. Wait for the model to finish loading"
    Write-Host "2. Check task manager to see if the process is still running"
    
    # Ask if user wants to continue to frontend setup
    $continueSetup = Read-Host "Continue with frontend setup anyway? (y/n)"
    if ($continueSetup -ne "y") {
        Write-Host "Setup aborted."
        exit 1
    }
}

# 🌐 React Frontend (Correct Path)
Write-Host '🌐 Setting up React frontend...'
Set-Location -Path '../frontend'

# Check if package.json exists, if not, create a new React app
if (!(Test-Path 'package.json')) {
    Write-Host 'No package.json found. Initializing React project ... '
    npx create-react-app .
}

# Check if styles.css exists and contains the UI updates
$StylesCssFile = "src/styles.css"
if (Test-Path $StylesCssFile) {
    if (Select-String -Path $StylesCssFile -Pattern "debug-toggle-button") {
        Write-Host "✅ UI styling looks good with debug panel support."
    } else {
        Write-Host "⚠️ UI styles might be missing recent updates."
        Write-Host "⚠️ If you encounter UI issues, you may need to manually update the styles.css file."
    }
}

# Check Layout.js for conversation history handling
$LayoutJsFile = "src/components/Layout.js"
if (Test-Path $LayoutJsFile) {
    $hasConversationHistory = Select-String -Path $LayoutJsFile -Pattern "conversationHistory"
    $hasLocalStorage = Select-String -Path $LayoutJsFile -Pattern "localStorage"
    
    if ($hasConversationHistory -and $hasLocalStorage) {
        Write-Host "✅ UI components look good with conversation history support."
    } else {
        Write-Host "⚠️ UI components might be missing recent updates for conversation history."
        Write-Host "⚠️ If you encounter issues with follow-up queries, check the Layout.js file."
    }
}

# Install frontend dependencies and start the React app
Write-Host '📦 Installing frontend dependencies...'
npm install
npm install axios

Write-Host '🚀 Starting React frontend...'
npm start

Write-Host "🔧 Setup complete! Both backend and frontend should be running."
Write-Host ""
Write-Host "ℹ️ IMPORTANT: The backend server is running in the background with PID $($BackendProcess.Id)"
Write-Host "ℹ️ To stop the backend server when done, end the process in Task Manager"
Write-Host ""
Write-Host "⚠️ If you encounter connection errors:"
Write-Host "1. Ensure the database path is correctly set in the .env file"
Write-Host "2. To use the fresh environment in the future, activate it with:"
Write-Host "   fresh_env\Scripts\Activate"
Write-Host "3. Then run the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "📝 UI Updates:"
Write-Host "1. Debug panel toggle is available in the top left of the chat window"
Write-Host "2. User messages now appear on the right side"
Write-Host "3. System (AI) messages appear on the left side"
Write-Host "4. Reasoning and diagnosis sections have special formatting"

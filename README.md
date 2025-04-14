# 🏥 MedInsight 🚀

A full-stack web application that allows users to query healthcare data using **natural language**. The app generates **SQL queries** from user input and retrieves data from the **MIMIC-IV dataset**. The application now uses **local LLM models** for reasoning and SQL generation, eliminating the need for API keys.

## 🌟 Features
- **Natural Language Querying**: Ask healthcare-related questions, and the app will generate and run SQL queries.
- **Conversation History**: Maintain context across multiple queries for follow-up questions.
- **Debug Panel**: Toggle debug information to see model reasoning and SQL generation.
- **Enhanced UI**: User-friendly chat interface with clear message styling.
- **FastAPI Backend**: A lightweight Python backend to process queries and execute SQL.
- **React Frontend**: A responsive, chat-style UI for user interaction.
- **SQLite Database**: Uses MIMIC-IV dataset stored as a database.
- **Dark Mode UI**: Inspired by ChatGPT/iOS message styles.
- **Local LLM Models**: Uses local models for medical reasoning and SQL generation without API calls:
  - **MedAgentReasoner-3B-Chat**: For medical reasoning with a turn-based interaction style
  - **Qwen2.5-Coder-7B**: For SQL generation

---

## ⚡ Getting Started (Local Setup)

### 🔹 Prerequisites
- **Python 3.9+** (3.11 recommended, 3.12 has compatibility issues with some packages)
- **Node.js 14+ & npm**
- **SQLite**
- **Git**
- **GPU with 6GB+ VRAM** (optional but recommended)

---

### 1️⃣ Clone the Repository
Open a terminal (Mac/Linux) or PowerShell (Windows) and run:

```sh
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

---

### 2️⃣ Run the Setup Script

#### **▶️ For Mac/Linux:**
```sh
bash setup.sh
```

#### **▶️ For Windows (PowerShell):**
```powershell
.\setup.ps1
```

This will:
✅ Install Python dependencies from requirements.txt  
✅ Create a fresh environment with optimized package versions  
✅ Start the FastAPI backend with model loading  
✅ Install frontend dependencies  
✅ Start the React frontend  

---

### 3️⃣ Update the `.env` File
After running the setup script, **you need to update the `.env` file** with your database path.

1. Open the `.env` file located in `qwen-mimic-app/backend/`
2. Replace the placeholders with your actual database path:
   ```ini
   MIMIC_DB_PATH="absolute/path/to/MIMIC3.db"
   LLM_MODEL_NAME="tossowski/MedAgentReasoner-3B-Chat"
   ```
   - **For example**, on Linux/Mac:
     ```ini
     MIMIC_DB_PATH="/home/user/qwen-mimic-app/backend/data/MIMIC3.db"
     ```
   - **On Windows** (use double backslashes `\\`):
     ```ini
     MIMIC_DB_PATH="C:\\Users\\yourname\\qwen-mimic-app\\backend\\data\\MIMIC3.db"
     ```

3. **Save the file** and restart the backend:
   ```sh
   cd qwen-mimic-app/backend
   source fresh_env/bin/activate   # (Windows users: use `fresh_env\Scripts\activate`)
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

Once complete, **visit:**  
👉 `http://localhost:3000` (Frontend)  
👉 `http://localhost:8000/docs` (API Docs)

---

## 📊 Testing Local LLM Models

The application now uses local models instead of API calls. You can test these models using:

### Interactive Testing
```bash
cd qwen-mimic-app/backend
python interactive_test.py
```
This provides an interactive CLI interface for testing the MedAgentReasoner model.

### GPU Testing
For Apple Silicon Macs, the interactive test will automatically use MPS for acceleration. 

To test GPU acceleration on NVIDIA GPUs:
```bash
python gpu_test.py        # Test the reasoner model
python gpu_qwen_test.py   # Test the SQL generation model
```

For more details, see `qwen-mimic-app/backend/README_LOCAL_MODELS.md`.

---

## ⚙️ Manual Setup (If Not Using Setup Script)

### **1️⃣ Backend (FastAPI)**
```sh
cd qwen-mimic-app/backend
python -m venv fresh_env
source fresh_env/bin/activate   # (Windows users: use `fresh_env\Scripts\activate`)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **2️⃣ Frontend (React)**
```sh
cd qwen-mimic-app/frontend
npm install
npm install axios
npm start
```

---

## 🛠️ Project Structure
```
📂 Health-Query-Tester/
│── 📁 qwen-mimic-app/
│   ├── 📁 backend/              # FastAPI Backend
│   │   ├── 📁 app/              # Application files
│   │   │   ├── main.py          # FastAPI main app
│   │   │   ├── query.py         # SQL generation model
│   │   │   ├── diagnose.py      # Diagnose endpoint logic
│   │   │   ├── reasoner.py      # Medical reasoning model
│   │   │   ├── model_transformers.py # Transformer model handler
│   │   │   ├── config.py        # Configuration settings
│   │   ├── interactive_test.py  # Interactive testing script
│   │   ├── gpu_test.py          # GPU testing for reasoner model
│   │   ├── gpu_qwen_test.py     # GPU testing for SQL model
│   │   ├── requirements.txt     # Python dependencies
│   │   ├── README_LOCAL_MODELS.md # Documentation for local models
│   │   ├── .env                 # Environment variables (DB path)
│   ├── 📁 frontend/             # React Frontend
│   │   ├── 📁 src/              # React components
│   │   │   ├── 📁 components/   # React UI components
│   │   │   │   ├── Layout.js    # Main layout with conversation history
│   │   │   │   ├── ChatMessage.js # Message component
│   │   │   │   ├── DebugPanel.js # Debug information panel
│   │   │   ├── styles.css       # CSS styles for the UI
│   │   ├── App.js               # Main frontend UI
│   │   ├── index.js             # React entry point
│── 📁 fresh_setup.sh            # Fresh setup script (Mac/Linux)
│── 📁 setup.sh                  # Legacy setup script (Mac/Linux)
│── 📁 setup.ps1                 # Setup script (Windows)
```

---

## 🔄 API Endpoints (FastAPI)
| Method | Endpoint | Description |
|--------|----------|------------|
| `POST` | `/diagnose` | Send a medical question to diagnose |
| `POST` | `/provide_info` | Provide additional information to continue diagnosis |
| `GET`  | `/provide_info` | Retrieve the current state for follow-up questions |
| `GET`  | `/health`| Check if the server is running |
| `GET`  | `/system-info` | Get detailed system information |
| `GET`  | `/docs`  | View API documentation |

Example Request:
```sh
curl -X POST "http://localhost:8000/diagnose" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Evaluate qSOFA for patient 12345"}'
```
---

## 🖥️ Hardware Requirements

For optimal performance:
- **GPU**: 6GB+ VRAM for running both models
- **CPU**: Modern multi-core processor
- **RAM**: 16GB+ recommended
- **Storage**: At least 10GB free space for model downloads

The application automatically detects and uses the appropriate hardware:
- **NVIDIA GPUs**: Uses CUDA with float16 precision
- **Apple Silicon**: Uses Metal Performance Shaders (MPS) with float16 precision
- **CPU-only**: Falls back to CPU with float32 precision

---

## 🎨 UI Features

### Chat Interface
- **User Messages**: Displayed on the right side with distinct styling
- **AI Responses**: Displayed on the left side with clear formatting
- **Debug Toggle**: Button in the top-left corner to show/hide debugging information

### Debug Panel
When enabled, the debug panel shows:
- **Reasoning Process**: The model's internal reasoning steps
- **SQL Queries**: Generated SQL code for database queries
- **Timing Information**: How long each processing step took

### Conversation History
- Maintains context between queries
- Allows for follow-up questions
- Persisted in localStorage for session continuity

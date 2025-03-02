# 🏥 Health Query App 🚀

A full-stack web application that allows users to query healthcare data using **natural language**. The app generates **SQL queries** from user input and retrieves data from the **MIMIC-III dataset**.

## 🌟 Features
- **Natural Language Querying**: Ask healthcare-related questions, and the app will generate and run SQL queries.
- **FastAPI Backend**: A lightweight Python backend to process queries and execute SQL.
- **React Frontend**: A responsive, chat-style UI for user interaction.
- **SQLite Database**: Uses MIMIC-III dataset stored as a database.
- **Dark Mode UI**: Inspired by ChatGPT/iOS message styles.

---

## ⚡ Getting Started (Local Setup)

### 🔹 Prerequisites
- **Python 3.8+**
- **Node.js 14+ & npm**
- **SQLite**
- **Git**

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
✅ Install Python dependencies  
✅ Start the FastAPI backend  
✅ Install frontend dependencies  
✅ Start the React frontend  

Once complete, **visit:**  
👉 `http://localhost:3000` (Frontend)  
👉 `http://localhost:8000/docs` (API Docs)

---

## ⚙️ Manual Setup (If Not Using Setup Script)

### **1️⃣ Backend (FastAPI)**
```sh
cd backend
python -m venv env
source env/bin/activate   # (Windows users: use `env\Scripts\activate`)
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### **2️⃣ Frontend (React)**
```sh
cd frontend
npm install
npm start
```

---

## 🛠️ Project Structure
```
📂 Health-Query-App/
│── 📁 backend/             # FastAPI Backend
│   ├── 📁 app/             # Application files
│   │   ├── main.py         # FastAPI main app
│   │   ├── query.py        # Query processing logic
│   │   ├── database.py     # Database connection
│── 📁 frontend/            # React Frontend
│   ├── 📁 src/             # React components
│   ├── App.js             # Main frontend UI
│   ├── index.js           # React entry point
│── setup.sh               # Auto-setup script (Mac/Linux)
│── setup.ps1              # Auto-setup script (Windows)
│── requirements.txt       # Python dependencies
│── package.json           # Frontend dependencies
│── README.md              # Project documentation
```

---

## 🔄 API Endpoints (FastAPI)
| Method | Endpoint | Description |
|--------|----------|------------|
| `POST` | `/query` | Send a natural language query & get SQL result |
| `GET`  | `/docs`  | View API documentation |

Example Request:
```sh
curl -X POST "http://localhost:8000/query" \
     -H "Content-Type: application/json" \
     -d '{"user_query": "How many visits did patient 10009 have in the last month?"}'
```

---

## 🚀 Deployment (GitHub Actions)
This project supports **GitHub Actions CI/CD** for:
- **Automated Testing**
- **Linting & Code Quality Checks**
- **Deployment to a Cloud Server (Optional)**


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.query import get_qwen_generated_code, execute_sql_query  

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/")
def read_root():
    return {"message": "FastAPI Backend Running"}

@app.post("/query")
def process_query(user_query: dict):
    query_text = user_query.get("user_query")
    generated_sql = get_qwen_generated_code(query_text)
    result = execute_sql_query(generated_sql)
    return {"generated_code": generated_sql, "result": result}

# ----- NEW: Mount the Diagnose Router -----
from app.diagnose import router as diagnose_router
app.include_router(diagnose_router)

import os
import sqlite3
import requests
import re
from app.config import QWEN_API_KEY, MIMIC_DB_PATH

DB_PATH = os.path.abspath(MIMIC_DB_PATH.strip('"').strip("'"))

def get_qwen_generated_code(query: str) -> str:
    """ Sends a query to Qwen API and ensures correct SQLite syntax """
    url = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Updated prompt for MIMIC-IV
    prompt = (
    "Write only a valid SQL query (no explanation, no formatting, no comments) to answer the following "
    "question using a SQLite-compatible MIMIC-IV dataset.\n"
    "Assume that the database contains the following tables: `admissions`, `diagnoses_icd`, `patients`, `prescriptions`, `procedures_icd`.\n"
    "Use the correct table(s) based on the question.\n"
    "Column names include (but are not limited to):\n"
    "- admissions: SUBJECT_ID (INTEGER), HADM_ID (INTEGER), ADMITTIME (TEXT), DISCHTIME (TEXT)\n"
    "- diagnoses_icd: SUBJECT_ID (INTEGER), HADM_ID (INTEGER), ICD_CODE (TEXT), ICD_VERSION (INTEGER)\n"
    "- patients: SUBJECT_ID (INTEGER), GENDER (TEXT), DOB (TEXT), DOD (TEXT)\n"
    "- prescriptions: SUBJECT_ID (INTEGER), HADM_ID (INTEGER), DRUG (TEXT), STARTDATE (TEXT), ENDDATE (TEXT)\n"
    "- procedures_icd: SUBJECT_ID (INTEGER), HADM_ID (INTEGER), ICD_CODE (TEXT), SEQ_NUM (INTEGER)\n"
    f"Question: {query}\n"
    "Important:\n"
    "- Use standard SQL syntax supported by SQLite.\n"
    "- Do NOT use T-SQL functions like DATEADD or NOW(). Instead, use strftime() or DATE().\n"
    "- Ensure that date-related queries use the correct column names (`ADMITTIME`, `DISCHTIME`, `DOB`, `DOD`, `STARTDATE`, `ENDDATE`).\n"
    "- If the question involves counts, use COUNT(*). If it requires an average, use AVG().\n"
    "- If filtering by date, use DATE(column_name) or strftime('%Y-%m-%d', column_name).\n"
    "- If multiple tables are required, use INNER JOINs on SUBJECT_ID or HADM_ID where appropriate.\n"
    "- Do NOT generate multiple queries. Only return ONE valid SQL statement.\n"
    "- Do NOT include ```sql or any formatting, only return the raw SQL statement.\n"
    "Example:\n"
    "SELECT COUNT(*) FROM admissions WHERE SUBJECT_ID = 10009 AND DATE(ADMITTIME) >= DATE('now', '-1 month');\n"
    "Now, generate the correct SQL query:"
)

    
    payload = {
        "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        "prompt": prompt,
        "max_tokens": 200
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        raw_sql = response.json().get("choices", [{}])[0].get("text", "").strip()
        sql_statements = re.split(r";\s*", raw_sql)
        first_sql_statement = sql_statements[0].strip()
        return first_sql_statement
    else:
        return f"Error from Qwen API: {response.json()}"

def execute_sql_query(sql_query: str) -> str:
    """ Executes the generated SQL query on the MIMIC-IV database """
    try:
        if not os.path.exists(DB_PATH):
            return f"Error: Database file not found at {DB_PATH}"

        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(sql_query)
        result = cursor.fetchall()
        conn.close()

        return result if result else "No data found"
    
    except sqlite3.OperationalError as e:
        return f"SQLite Operational Error: {str(e)}"
    
    except Exception as e:
        return f"Execution Error: {str(e)}"

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
    
    # Strip special markers if present.
    cleaned_query = query.strip('*').strip()

    # Updated prompt for MIMIC-IV
    prompt = (
        "Write only a valid SQL query (no explanation, no formatting, no comments) to answer the following and ensure that the code has a semicolon at the end "
        "question using a SQLite-compatible MIMIC-IV dataset.\n"
        "Assume that the database contains the following tables: `admissions`, `diagnoses_icd`, `patients`, `prescriptions`, `procedures_icd`.\n"
        "Use the correct table(s) based on the question.\n"
        "Column names include:\n"
        "- admissions(subject_id, hadm_id, admittime, dischtime, deathtime, admission_type, admit_provider_id, admission_location, discharge_location, insurance, language, marital_status, race, edregtime, edouttime, hospital_expire_flag)\n"
        "- diagnoses_icd(subject_id, hadm_id, seq_num, icd_code, icd_version)\n"
        "- patients(subject_id, gender, anchor_age, anchor_year, anchor_year_group, dod)\n"
        "- prescriptions(subject_id, hadm_id, pharmacy_id, poe_id, poe_seq, order_provider_id, starttime, stoptime, drug_type, drug, formulary_drug_cd, gsn, ndc, prod_strength, form_rx, dose_val_rx, dose_unit_rx, form_val_disp, form_unit_disp, doses_per_24_hrs, route)\n"
        "- procedures_icd(subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version)\n"
        f"Question: {cleaned_query}\n"
        "Important:\n"
        "- If the question involves prescriptions, select the `drug` column (which stores the medication names) along with if asked for it starttime and stoptime.\n"
        "- Use standard SQL syntax supported by SQLite.\n"
        "- Do NOT use T-SQL functions like DATEADD or NOW(). Instead, use strftime() or DATE().\n"
        "- Ensure that date-related queries use the correct column names (`admittime`, `dischtime`, `deathtime`, `starttime`, `stoptime`, `chartdate`).\n"
        "- If the question involves counts, use COUNT(*). If it requires an average, use AVG().\n"
        "- If filtering by date, use DATE(column_name) or strftime('%Y-%m-%d', column_name).\n"
        "- If multiple tables are required, use INNER JOINs on `subject_id` or `hadm_id` where appropriate.\n"
        "- If a query requests data that may be missing, use COALESCE() to return 'N/A' instead of NULL.\n"
        "- Do NOT generate multiple queries. Only return ONE valid SQL statement.\n"
        "- Do NOT include ```sql or any formatting, only return the raw SQL statement.\n"
        "- Ensure you have a semicolon at the end of the raw SQL statement.\n"
        "Example:\n"
        "SELECT COUNT(*) FROM admissions WHERE subject_id = 10009 AND DATE(admittime) >= DATE('now', '-1 month');\n"
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
        return first_sql_statement + ';'
    else:
        return f"Error from Qwen API: {response.json()}"

def execute_sql_query(sql_query: str):
    """ Executes the generated SQL query on the MIMIC-IV database """

    # DEBUG: Print the SQL Query being executed
    print(f"Executing SQL Query: {sql_query}")

    try:
        if not os.path.exists(DB_PATH):
            print("❌ Error: Database file not found at", DB_PATH)
            return {"error": f"Database file not found at {DB_PATH}"}

        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute(sql_query)
        result = cursor.fetchall()
        conn.close()

        # DEBUG: Print the fetched result
        print(f"✅ Query Result: {result}")

        return result if result else "N/A"  

    except sqlite3.OperationalError as e:
        print(f"❌ SQLite Operational Error: {str(e)}")
        return {"error": f"SQLite Error: {str(e)}"}

    except Exception as e:
        print(f"❌ Execution Error: {str(e)}")
        return {"error": f"Execution Error: {str(e)}"}

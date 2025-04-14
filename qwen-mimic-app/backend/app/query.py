import os
import sqlite3
import re
import logging
from typing import Dict, Any, List, Optional

from app.config import MIMIC_DB_PATH
from app.model_factory import ModelFactory

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database path with error handling
try:
    DB_PATH = os.path.abspath(MIMIC_DB_PATH.strip('"').strip("'"))
    logger.info(f"Database path: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")
except Exception as e:
    logger.error(f"Error with database path: {e}")
    raise RuntimeError(f"Database configuration error: {e}")

class SqlGenerationHandler:
    """Handler for SQL generation using the optimal backend for this hardware"""
    
    def __init__(self):
        """Initialize the SQL generation handler"""
        model_name = "Qwen/Qwen2.5-Coder-7B"  # Use smaller model for SQL generation
        logger.info(f"Initializing SQL generator with model: {model_name}")
        
        # Use model factory to create the appropriate model handler
        self.model_handler = ModelFactory.create_model(model_name, model_type="sql")
        logger.info(f"Using backend: {self.model_handler.__class__.__name__}")
    
    def generate_code(self, query: str) -> str:
        """Generate SQL code for the given query"""
        # Strip special markers if present
        cleaned_query = query.strip('*').strip()
        
        # Create prompt for SQL generation
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
        
        # Generate SQL code
        messages = [{"role": "user", "content": prompt}]
        
        # Generate using the model handler
        response_data = self.model_handler.generate(messages, max_tokens=200, temperature=0.2)
        
        # Extract and process the raw SQL
        raw_sql = response_data["text"].strip()
        sql_statements = re.split(r";\s*", raw_sql)
        first_sql_statement = sql_statements[0].strip()
        
        # Make sure it ends with a semicolon
        if not first_sql_statement.endswith(';'):
            first_sql_statement += ';'
            
        logger.info(f"Generated SQL: {first_sql_statement}")
        return first_sql_statement

# Global instance for SQL generation
_sql_generator = None

def get_qwen_generated_code(query: str) -> str:
    """Get SQL code for the given query using the optimal backend"""
    global _sql_generator
    
    # Create the SQL generator if it doesn't exist yet
    if _sql_generator is None:
        _sql_generator = SqlGenerationHandler()
        
    # Generate the SQL code
    return _sql_generator.generate_code(query)

def execute_sql_query(sql_query: str):
    """Execute the generated SQL query on the MIMIC-IV database"""
    logger.info(f"Executing SQL Query: {sql_query}")

    try:
        # Verify database exists
        if not os.path.exists(DB_PATH):
            raise FileNotFoundError(f"Database file not found at {DB_PATH}")
        
        # Connect to database and execute query
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        result = cursor.fetchall()
        conn.close()
        
        logger.info(f"Query result count: {len(result) if isinstance(result, list) else 'N/A'}")
        return result if result else "No results found"  

    except sqlite3.OperationalError as e:
        logger.error(f"SQLite Operational Error: {str(e)}")
        raise RuntimeError(f"SQLite Error: {str(e)}")

    except Exception as e:
        logger.error(f"Execution Error: {str(e)}")
        raise RuntimeError(f"Query execution error: {str(e)}")

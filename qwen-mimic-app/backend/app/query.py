import os
import sqlite3
import re
import logging
from typing import Dict, Any, List, Optional

from app.config import MIMIC_DB_PATH
from app.model_factory import ModelFactory
from app.prompts import get_sql_generation_prompt

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
        
        # Get SQL prompt from central prompts file
        prompt = get_sql_generation_prompt(cleaned_query)
        
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

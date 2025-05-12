"""
Central prompts file containing all prompts used throughout the application.

This file consolidates all prompts that were previously scattered across multiple files,
making it easier to maintain and edit prompts in one place.
"""

import logging
from typing import Dict, Any, List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Message formatting prompts
MODEL_MESSAGE_FORMAT = {
    "user_prefix": "<|im_start|>user\n",
    "user_suffix": "<|im_end|>\n",
    "assistant_prefix": "<|im_start|>assistant\n",
    "assistant_suffix": "<|im_end|>\n",
    "system_prefix": "<|im_start|>system\n",
    "system_suffix": "<|im_end|>\n",
    "generation_prefix": "<|im_start|>assistant\n"
}

# SQL Generation prompts
SQL_GENERATION_PROMPT = """Write only a valid SQL query (no explanation, no formatting, no comments) to answer the following and ensure that the code has a semicolon at the end \
question using a SQLite-compatible MIMIC-IV dataset.
Assume that the database contains the following tables: `admissions`, `diagnoses_icd`, `patients`, `prescriptions`, `procedures_icd`.
Use the correct table(s) based on the question.
Column names include:
- admissions(subject_id, hadm_id, admittime, dischtime, deathtime, admission_type, admit_provider_id, admission_location, discharge_location, insurance, language, marital_status, race, edregtime, edouttime, hospital_expire_flag)
- diagnoses_icd(subject_id, hadm_id, seq_num, icd_code, icd_version)
- patients(subject_id, gender, anchor_age, anchor_year, anchor_year_group, dod)
- prescriptions(subject_id, hadm_id, pharmacy_id, poe_id, poe_seq, order_provider_id, starttime, stoptime, drug_type, drug, formulary_drug_cd, gsn, ndc, prod_strength, form_rx, dose_val_rx, dose_unit_rx, form_val_disp, form_unit_disp, doses_per_24_hrs, route)
- procedures_icd(subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version)
Question: {query}
Important:
- If the question involves prescriptions, select the `drug` column (which stores the medication names) along with if asked for it starttime and stoptime.
- Use standard SQL syntax supported by SQLite.
- Do NOT use T-SQL functions like DATEADD or NOW(). Instead, use strftime() or DATE().
- Ensure that date-related queries use the correct column names (`admittime`, `dischtime`, `deathtime`, `starttime`, `stoptime`, `chartdate`).
- If the question involves counts, use COUNT(*). If it requires an average, use AVG().
- If filtering by date, use DATE(column_name) or strftime('%Y-%m-%d', column_name).
- If multiple tables are required, use INNER JOINs on `subject_id` or `hadm_id` where appropriate.
- If a query requests data that may be missing, use COALESCE() to return 'N/A' instead of NULL.
- Do NOT generate multiple queries. Only return ONE valid SQL statement.
- Do NOT include ```sql or any formatting, only return the raw SQL statement.
- Ensure you have a semicolon at the end of the raw SQL statement.
Example:
SELECT COUNT(*) FROM admissions WHERE subject_id = 10009 AND DATE(admittime) >= DATE('now', '-1 month');
Now, generate the correct SQL query:"""

# Criteria-specific prompts
def create_criteria_prompt(criteria_name: str, criteria_list: List[str], threshold: str = "") -> str:
    """
    Create a prompt for criteria-based reasoning
    
    Args:
        criteria_name: Name of the criteria (e.g., qSOFA, SIRS)
        criteria_list: List of criteria points
        threshold: Optional threshold rule
        
    Returns:
        Formatted criteria prompt
    """
    prompt = (
        f"Answer the {criteria_name} assessment question based on the criteria provided below.\n"
        "You must conduct reasoning inside <think> and </think> first every time you get new information.\n" 
        "After reasoning, if you find you lack some knowledge, you can call a search engine by <search> query </search>, and it will return the top searched results between <information> and </information>.\n"
        "You can search as many times as you want. If you find no further external knowledge needed, you can directly provide the answer inside <answer> and </answer> without detailed illustrations. Example: <answer> Assessment complete, patient shows signs of respiratory distress </answer>\n\n"
        f"{criteria_name} criteria to consider:\n"
    )
    
    # Add each criterion from the configuration
    for criterion in criteria_list:
        prompt += f"{criterion}\n"
    
    # Add threshold if provided (not empty)
    if threshold and threshold.strip():
        prompt += f"\nThreshold rule: {threshold}\n"
        prompt += "Apply this threshold rule in your assessment.\n"
    else:
        # If no threshold provided, add guidance to use medical knowledge
        prompt += "\nUse your medical knowledge to reason about these specific criteria and determine their clinical significance.\n"
        
    return prompt

# Continuation prompt for follow-up user information
CONTINUATION_PROMPT = "I'm providing additional information: {user_input}. Please continue your assessment based on this new information."

# Test prompts
TEST_MEDICAL_QUESTION = "Answer this medical question: What is qSOFA?"
TEST_SQL_QUESTION = "Generate an SQL query to find all patients diagnosed with pneumonia in the last year."

# Function to format messages with the correct model-specific formatting
def format_messages(messages: List[Dict[str, str]]) -> str:
    """Format messages into a prompt the model can understand"""
    prompt = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            prompt += f"{MODEL_MESSAGE_FORMAT['user_prefix']}{content}{MODEL_MESSAGE_FORMAT['user_suffix']}"
        elif role == "assistant":
            prompt += f"{MODEL_MESSAGE_FORMAT['assistant_prefix']}{content}{MODEL_MESSAGE_FORMAT['assistant_suffix']}"
        else:
            prompt += f"{MODEL_MESSAGE_FORMAT['system_prefix']}{content}{MODEL_MESSAGE_FORMAT['system_suffix']}"
    
    # Add the final assistant prefix to prime the generation
    prompt += MODEL_MESSAGE_FORMAT["generation_prefix"]
    return prompt

# Function to create SQL generation prompt
def get_sql_generation_prompt(query: str) -> str:
    """Get the SQL generation prompt with the query filled in"""
    return SQL_GENERATION_PROMPT.format(query=query) 

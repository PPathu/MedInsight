# Reasoning with LLM for Sepsis Diagnosis

## Overview
This Directory contains code and queries for reasoning about sepsis diagnosis using a large language model (DeepSeek) and structured patient data from the MIMIC-IV dataset.

## Directory Structure
- **`Sepsis_Diagnosis_Week3.ipynb`**: Jupyter Notebook implementing data preprocessing and reasoning with deepseek. 
- **`sample_query.sql`**: SQL queries for retrieving patient records with sepsis-related diagnoses, lab results, and clinical notes from the MIMIC-IV dataset.


## Data Processing
### 1. Loading Data - SQL Query
   - Identifies sepsis patients using ICD codes.
   - Filters for patients with ICU records and discharge summaries.
### 2. Feature Extraction
   - Uses regular expressions to extract key information from notes.
   - Merges patient lab results with extracted note data for reasoning.

## Dependencies
- SQL (Google BigQuery for querying MIMIC-IV)
- Jupyter Notebook

## Usage
1. Run the SQL query (`sample_query.sql`) to retrieve patient data.
2. Process and analyze the extracted data using `Sepsis_Diagnosis_Week3.ipynb`.


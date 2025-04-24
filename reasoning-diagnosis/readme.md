# Medical Reasoning with LLMs for Clinical Decision Support

## Overview
This directory contains foundational code and research for medical reasoning using large language models (LLMs) on structured patient data from the MIMIC-IV dataset. The concepts explored here have been integrated into the main application.

## Integration with Main Application
The research and techniques from this directory have been implemented in the main application:

- **Reasoning Flow**: The step-by-step reasoning approach is now implemented in `qwen-mimic-app/backend/app/reasoner.py`
- **Conversation History**: The turn-based interaction model is supported through the conversation history feature
- **Debug Panel**: The reasoning process is now visible through the debug panel in the frontend UI

## Directory Structure
- **`Sepsis_Diagnosis_Week3.ipynb`**: Jupyter Notebook implementing data preprocessing and reasoning with deepseek. 
- **`sample_query.sql`**: SQL queries for retrieving patient records with sepsis-related diagnoses, lab results, and clinical notes from the MIMIC-IV dataset.

## Research Approach
This directory showcases the research approach that led to the current implementation:

### 1. Data Exploration
- Identify sepsis patients using ICD codes
- Extract relevant clinical information from MIMIC-IV
- Process discharge summaries and lab results

### 2. Reasoning Model Experiments
- Testing LLM capabilities for medical reasoning
- Developing prompt strategies for clinical decision support
- Structuring responses for systematic analysis

### 3. Integration Strategy
- Turn-based medical questioning approach
- Structured output format (<think>, <search>, <answer>)
- Database integration for data validation

## From Research to Application
The research concepts have evolved into production features:

1. **Research**: Sepsis diagnostic reasoning
   **Application**: General medical reasoning with conversation context

2. **Research**: DeepSeek model testing
   **Application**: MedAgentReasoner-3B-Chat implementation

3. **Research**: Manual SQL queries
   **Application**: Automated SQL generation with Qwen2.5-Coder-7B

## Usage
This directory serves as research documentation. For the working application, please use the main application located in `qwen-mimic-app/` directory.

## Dependencies
- SQL (Google BigQuery for querying MIMIC-IV)
- Jupyter Notebook

## References
- MIMIC-IV Clinical Database: https://physionet.org/content/mimiciv/
- LLM Medical Reasoning Papers: See `../references/` directory


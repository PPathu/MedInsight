import re
import requests
from app.config import DEEPSEEK_API_KEY, LLM_MODEL_NAME

class DeepSeekModel:
    SPECIAL_TOKEN = "***"  # Special marker/token for generated queries

    def __init__(self):
        self.llm_url = "https://api.deepseek.com/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

    def extract_patient_id(self, user_prompt: str) -> str:
        """Extracts the patient ID from the prompt."""
        match = re.search(r"patient\s+(\d+)", user_prompt, re.IGNORECASE)
        return match.group(1) if match else "UNKNOWN"

    def generate_queries(self, user_prompt: str, needed_fields: list, patient_id: str) -> list:
        """
        Uses DeepSeek to generate **natural language question prompts** for Qwen based on the extracted fields.
        Ensures **all** medications are retrieved when the question is about prescriptions.
        """
        query_prompt = (
            "You are a medical data analyst. Given a patient-related question, "
            "generate a **well-structured, natural language question** that retrieves the relevant data. "
            "Ensure that if the user asks about medications or prescriptions, the question asks for all medications. \n\n"
            f"Patient ID: {patient_id}\n"
            f"User Question: {user_prompt}\n"
            f"Identified Fields: {', '.join(needed_fields)}\n\n"
            "For each identified field, generate a natural language question. "
            "Format each question as follows:\n"
            "QUERY: <Generated natural language question>\n"
            "Output only the question without any additional explanations.\n"
            "Example: QUERY: what drugs is the patient 10000032 taking?\n"
        )

        payload = {
            "model": LLM_MODEL_NAME,
            "messages": [{"role": "user", "content": query_prompt}],
            "max_tokens": 200,
            "temperature": 0.5
        }

        try:
            response = requests.post(self.llm_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                output = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                print("DEBUG: DeepSeek generated queries:\n", output)

                queries = []
                for line in output.splitlines():
                    if line.startswith("QUERY:"):
                        query_text = line[len("QUERY:"):].strip()
                        queries.append(f"{self.SPECIAL_TOKEN}{query_text}{self.SPECIAL_TOKEN}")

                return queries if queries else []

        except Exception as e:
            print("❌ ERROR: Exception while generating queries:", str(e))

        return []  

    def extract_identifiers(self, user_prompt: str) -> list:
        """
        Uses an LLM to deduce which database fields are required to answer a patient-related question.
        The LLM is explicitly instructed to output its final answer as a single line beginning with "FIELDS:"
        followed by a comma-separated list of field names, with no extra text.
        """
        schema = (
            "Table: admissions(subject_id, hadm_id, admittime, dischtime, deathtime, admission_type, "
            "admission_location, discharge_location, insurance, language, religion, marital_status, ethnicity, "
            "edregtime, edouttime, hospital_expire_flag)\n"
            "Table: diagnoses_icd(subject_id, hadm_id, seq_num, icd_code, icd_version)\n"
            "Table: patients(subject_id, gender, dob, dod, anchor_age, anchor_year, anchor_year_group)\n"
            "Table: prescriptions(subject_id, hadm_id, pharmacy_id, starttime, stoptime, drug, route, dose_val_rx, dose_unit_rx)\n"
            "Table: procedures_icd(subject_id, hadm_id, seq_num, chartdate, icd_code, icd_version)\n"
        )
        
        prompt_text = (
            "You are a medical data expert with full knowledge of the following database schema. "
            "Given a patient-related question, determine exactly which database columns are required to answer it. "
            "Return only a single line that begins with 'FIELDS:' followed by a comma-separated list of the exact column names, with no extra text.\n\n"
            "Database Schema:\n" + schema + "\n"
            "User Question: " + user_prompt + "\n\n"
            "Answer in the following format exactly:\n"
            "FIELDS: field1, field2, field3"
        )
        
        payload = {
            "model": LLM_MODEL_NAME,
            "messages": [{"role": "user", "content": prompt_text}],
            "max_tokens": 50,
            "temperature": 0.0  
        }
        
        try:
            response = requests.post(self.llm_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                output = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                print("DEBUG: LLM output:\n", output)
                for line in output.splitlines():
                    if line.strip().startswith("FIELDS:"):
                        fields_line = line.strip()[len("FIELDS:"):].strip()
                        fields = [field.strip() for field in fields_line.split(",") if field.strip()]
                        return fields
            else:
                print("DEBUG: LLM request failed with status", response.status_code)
                print("DEBUG: Response:", response.text)
        except Exception as e:
            print("DEBUG: Exception during LLM request:", str(e))
        return []

    def generate_reasoned_response(self, query_result, original_prompt: str) -> str:
        """
        Given the SQL query result and the original user prompt, uses DeepSeek to produce a natural language explanation.
        """
        # You can adjust this prompt as needed for your domain.
        reasoning_prompt = (
            "You are a medical data analyst. Given the following SQL query result and the original patient question, "
            "provide a clear, concise natural language explanation summarizing the data and its significance.\n\n"
            f"Original Question: {original_prompt}\n"
            f"SQL Query Result: {query_result}\n\n"
            "Provide your explanation below:"
        )
        
        payload = {
            "model": LLM_MODEL_NAME,
            "messages": [{"role": "user", "content": reasoning_prompt}],
            "max_tokens": 150,
            "temperature": 0.5
        }
        
        try:
            response = requests.post(self.llm_url, headers=self.headers, json=payload)
            if response.status_code == 200:
                final_response = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                print("DEBUG: DeepSeek final reasoned response:\n", final_response)
                return final_response
            else:
                print("DEBUG: Reasoned response request failed with status", response.status_code)
                print("DEBUG: Response:", response.text)
                return "Error generating reasoned response."
        except Exception as e:
            print("DEBUG: Exception during reasoned response request:", str(e))
            return "Exception generating reasoned response."

    def reason_about_prompt(self, user_prompt: str) -> dict:
        """
        1) Extracts the patient ID.
        2) Uses DeepSeek to determine the necessary fields.
        3) Generates natural language question prompts that retrieve **all** medications when applicable.
        """
        patient_id = self.extract_patient_id(user_prompt)
        needed_fields = self.extract_identifiers(user_prompt)
        
        print(f"DEBUG: Extracted Patient ID → {patient_id}")
        print(f"DEBUG: Identified Fields → {needed_fields}")
        print(f"DEBUG: user prompt Fields → {user_prompt}")

        if needed_fields:
            partial_reasoning = [f"I determined that the following fields are needed: {', '.join(needed_fields)}."]
        else:
            partial_reasoning = ["No relevant fields were identified."]
        
        # Generate queries dynamically using DeepSeek.
        queries = self.generate_queries(user_prompt, needed_fields, patient_id)

        print(f"DEBUG: Generated Queries for Qwen → {queries}")

        return {
            "needed_fields": needed_fields,
            "partial_reasoning": partial_reasoning,
            "queries": queries
        }

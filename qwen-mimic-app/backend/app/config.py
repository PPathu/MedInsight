import os
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
MIMIC_DB_PATH = os.getenv("MIMIC_DB_PATH")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "deepseek-reasoner")

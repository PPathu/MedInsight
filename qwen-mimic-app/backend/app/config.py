import os
from dotenv import load_dotenv

load_dotenv()

QWEN_API_KEY = os.getenv("QWEN_API_KEY")
MIMIC_DB_PATH = os.getenv("MIMIC_DB_PATH")

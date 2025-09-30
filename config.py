# config.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load variables from the .env file
load_dotenv()

# --- Discord Credentials ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- MySQL Database Credentials ---
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# --- LLM (Gemini) Model Credentials & Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

# --- Central LLM Object Initialization ---
# This object will be imported and used by other files (e.g., node.py)
print(" --- [CONFIG] Initializing LLM... ---")
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL_NAME,
    google_api_key=GOOGLE_API_KEY,
    convert_system_message_to_human=True
)
print(f"--- [CONFIG] LLM Initialized with model: {GEMINI_MODEL_NAME} ---")
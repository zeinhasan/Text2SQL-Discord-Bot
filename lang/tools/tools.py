import json
import mysql.connector
from mysql.connector import Error
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from typing import List
from datetime import datetime
import os
import base64

from config import image_llm, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from utils import export_data_to_excel

# --- Helper Functions (No Changes) ---
def _get_db_connection():
    try:
        conn = mysql.connector.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        if conn.is_connected(): return conn
    except Error as e:
        return {"error": str(e)}

def _get_image_base64_from_response(response_message: AIMessage) -> str | None:
    if not isinstance(response_message.content, list): return None
    for part in response_message.content:
        if isinstance(part, dict) and "image_url" in part:
            image_uri = part["image_url"].get("url")
            if image_uri and isinstance(image_uri, str): return image_uri.split(',')[-1]
    return None

def _generate_or_modify_image(prompt: str, image_data_base64: str | None = None) -> str:
    print(f"--- [IMAGE_TOOL] Initializing image generation: '{prompt[:50]}...' ---")
    try:
        content = [{"type": "text", "text": prompt}]
        if image_data_base64:
            print("--- [IMAGE_TOOL] Attaching existing image for modification. ---")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data_base64}"}})
        message = HumanMessage(content=content)
        print("--- [IMAGE_TOOL] Invoking image model... ---")
        response = image_llm.invoke([message])
        generated_image_base64 = _get_image_base64_from_response(response)
        if not generated_image_base64: return "Error: The model did not generate an image."
        print("--- [IMAGE_TOOL] Image received. Saving to file... ---")
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.abspath(os.path.join(output_dir, f"generated_image_{timestamp}.png"))
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(generated_image_base64))
        print(f"--- [IMAGE_TOOL] Image saved to {file_path} ---")
        return file_path
    except Exception as e:
        print(f"--- [IMAGE_TOOL_ERROR] An unexpected error occurred: {e} ---")
        return f"Error: An unexpected error occurred during image generation: {e}"

# --- Agent Tools ---

@tool
def query_database(query: str) -> str:
    """
    Use this to run a SQL query and display results as text. This is the default tool for getting data.
    """
    print(f"--- [TOOL_CALLED] query_database with query: '{query}' ---")
    conn = _get_db_connection()
    if isinstance(conn, dict): return f"Error connecting to database: {conn['error']}"
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        result = cursor.fetchall()
        return json.dumps(result, indent=2, default=str) if result else "Query returned no results."
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@tool
def export_to_excel(query: str, table_name: str) -> str:
    """
    Use ONLY when the user asks to 'export' or get an 'excel' file. You must provide the table_name from the user's query. The filename will be generated automatically.
    """
    print(f"--- [TOOL_CALLED] export_to_excel for table: '{table_name}' ---")
    conn = _get_db_connection()
    if isinstance(conn, dict): return f"Error connecting to database: {conn['error']}"
    try:
        # --- FILENAME IS NOW GENERATED HERE ---
        # Get the current local timestamp from the server
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize table_name and create the final filename
        safe_table_name = "".join(c for c in table_name if c.isalnum() or c in ('_', '-')).rstrip()
        filename = f"{safe_table_name}_{timestamp}.xlsx"
        print(f"--- [TOOL] Generated filename: {filename} ---")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query)
        data = cursor.fetchall()
        if not data: return "Query returned no data to export."
        
        # Pass the locally generated filename to the utility function
        file_path = export_data_to_excel(data, filename)
        return f"Successfully exported data to {file_path}"
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@tool
def get_database_tables() -> str:
    """Use this to list all available tables in the database."""
    print("--- [TOOL_CALLED] get_database_tables ---")
    conn = _get_db_connection()
    if isinstance(conn, dict): return f"Error connecting to database: {conn['error']}"
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        return f"Available tables: {', '.join(tables)}" if tables else "No tables were found."
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@tool
def generate_image(prompt: str, base64_image_data: str | None = None) -> str:
    """
    Use this to generate or modify an image based on a text description.
    """
    print(f"--- [TOOL_CALLED] generate_image with prompt: '{prompt[:50]}...' ---")
    file_path = _generate_or_modify_image(prompt, base64_image_data)
    if "Error:" in file_path:
        return file_path
    return f"Successfully generated image and saved it to the following path: {file_path}"

# The complete list of tools available to the agent
all_tools = [
    query_database,
    export_to_excel,
    get_database_tables,
    generate_image,
]
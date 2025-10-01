import json
import mysql.connector
from mysql.connector import Error
from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage
from typing import List, Union
from datetime import datetime
import re
import os
import base64

from config import llm, image_llm, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from utils import export_data_to_excel

def _get_image_base64(response_message: AIMessage) -> str | None:
    """
    Helper function to extract the base64 image data from an AIMessage.
    """
    for part in response_message.content:
        if isinstance(part, dict) and "image_url" in part:
            # get image uri
            image_uri = part["image_url"].get("url")
            if image_uri and isinstance(image_uri, str):
                return image_uri.split(',')[-1]
    return None

def _generate_or_modify_image(prompt: str, image_data_base64: str | None = None) -> str:
    """
    Calls the Gemini model to generate or modify an image and saves the result.
    """
    print(f"--- [IMAGE_TOOL] Initializing image generation model call ---")
    print(f"--- [IMAGE_TOOL] Prompt: {prompt} ---")
    
    try:

        content = [{"type": "text", "text": prompt}]
        if image_data_base64:
            print("--- [IMAGE_TOOL] Base64 image data found, preparing for image-to-image task. ---")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{image_data_base64}"}
            })
        
        message = HumanMessage(content=content)
        
        print("--- [IMAGE_TOOL] Invoking model for image generation... ---")
        response = image_llm.invoke([message])
        
        image_base64_out = _get_image_base64(response)
        if not image_base64_out:
            print("--- [IMAGE_TOOL_ERROR] No image data found in the model's response. ---")
            return "Error: The model did not return an image. Please try a different prompt."

        print("--- [IMAGE_TOOL] Successfully received image data from model. ---")

        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"generated_image_{timestamp}.png"
        file_path = os.path.abspath(os.path.join(output_dir, image_filename))

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(image_base64_out))
        
        print(f"--- [IMAGE_TOOL] Image successfully saved to {file_path} ---")
        return file_path

    except Exception as e:
        print(f"--- [IMAGE_TOOL_ERROR] An unexpected error occurred during image generation: {e} ---")
        return f"An error occurred while generating the image: {e}"

def _sanitize_sql_query(raw_query: str) -> str:
    """Cleans the SQL query from markdown code fences."""
    print(f"--- [TOOL_HELPER] Raw SQL from LLM: '{raw_query}' ---")
    if "```" in raw_query:
        match = re.search(r"```(?:sql|mysql)?\s*\n(.*?)\n```", raw_query, re.DOTALL)
        if match:
            sanitized = match.group(1).strip()
            print(f"--- [TOOL_HELPER] Sanitized SQL: '{sanitized}' ---")
            return sanitized
    return raw_query.strip()

def _get_db_connection():
    """Helper function to create a database connection."""
    try:
        return mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
    except Error as e:
        print(f"--- [DB_ERROR] Failed to connect to database: {e} ---")
        return {"error": str(e)}

def _run_sql_query(sql_query: str) -> Union[List[dict], dict]:
    """Helper function to execute a SQL query and return results."""
    conn = _get_db_connection()
    if isinstance(conn, dict):
        return conn

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql_query)
        result = cursor.fetchall()
        conn.commit()
        return result
    except Error as e:
        print(f"--- [DB_ERROR] Failed to execute query: {e} ---")
        return {"error": str(e)}
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@tool
def get_database_info(question: str) -> str:
    """
    Use this tool for any questions that require fetching data from the database.
    """
    print(f"--- [TOOL_CALLED] get_database_info with question: '{question}' ---")
    prompt = f"Based on the user's question, generate a SQL query. Question: {question}"
    sql_query_response = llm.invoke(prompt)
    sql_query = _sanitize_sql_query(sql_query_response.content)
    
    query_result = _run_sql_query(sql_query)
    
    if isinstance(query_result, dict) and "error" in query_result:
        return f"Error executing query: {query_result['error']}"
    
    return json.dumps(query_result, indent=2)

@tool
def export_database_info_to_excel(question: str, table_name: str) -> str:
    """
    Use this tool when the user asks to export database information to an Excel file.
    """
    print(f"--- [TOOL_CALLED] export_database_info_to_excel for table: '{table_name}' ---")
    prompt = f"Generate a SQL query to fetch all data from the {table_name} table. Question: {question}"
    sql_query_response = llm.invoke(prompt)
    sql_query = _sanitize_sql_query(sql_query_response.content)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dynamic_filename = f"{table_name}_{timestamp}.xlsx"
    print(f"--- [TOOL_HELPER] Generated dynamic filename: {dynamic_filename} ---")

    query_result = _run_sql_query(sql_query)
    
    if isinstance(query_result, dict) and "error" in query_result:
        return f"Error executing query: {query_result['error']}"

    file_path = export_data_to_excel(query_result, dynamic_filename)
    return f"Data has been successfully exported to {file_path}"

@tool
def get_database_tables() -> str:
    """
    Use this tool when the user asks for the available tables in the database.
    """
    print("--- [TOOL_CALLED] get_database_tables ---")
    conn = _get_db_connection()
    if isinstance(conn, dict):
        return f"Error connecting to database: {conn['error']}"

    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES;")
        tables = [table[0] for table in cursor.fetchall()]
        if not tables:
            return "No tables were found."
        return f"Available tables: {', '.join(tables)}"
    except Exception as e:
        return f"An error occurred: {e}"
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@tool
def generate_image(prompt: str, chat_history: List[dict] | None = None) -> str:
    """
    Generates a new image or modifies an existing one based on the prompt.
    Use this tool when the user asks to "create an image", "generate a picture", "draw", or "modify this image".
    """
    print(f"--- [TOOL_CALLED] generate_image with prompt: '{prompt}' ---")
    
    image_data_base64 = None
    if chat_history:
        for message in reversed(chat_history):
            if isinstance(message, dict) and 'content' in message and isinstance(message['content'], list):
                for part in message['content']:
                    if isinstance(part, dict) and part.get('type') == 'image_url':
                        image_url = part['image_url'].get('url', '')
                        if "data:image" in image_url:
                            image_data_base64 = image_url.split(',')[1]
                            print("--- [TOOL_HELPER] Found recent image in chat history for modification. ---")
                            break
            if image_data_base64:
                break
    
    file_path = _generate_or_modify_image(prompt, image_data_base64)

    if "Error:" in file_path:
        return file_path
    
    return f"Image successfully generated and saved to {file_path}"

all_tools = [get_database_info, export_database_info_to_excel, get_database_tables, generate_image]
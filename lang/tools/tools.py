import json
import mysql.connector
from mysql.connector import Error
from langchain_core.tools import tool
from typing import List, Union
from datetime import datetime
import re

from config import llm, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
from utils import export_data_to_excel


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
    prompt = f"Based on the user's question, generate a SQL query to get the necessary information. Question: {question}"
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
    prompt = f"Generate a SQL query to fetch all data from the {table_name} table based on this question: {question}"
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

all_tools = [get_database_info, export_database_info_to_excel, get_database_tables]
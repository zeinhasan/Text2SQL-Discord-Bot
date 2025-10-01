import pandas as pd
from typing import List, Dict
import os
import re

def export_data_to_excel(data: List[Dict], filename: str = "query_result.xlsx") -> str:
    """
    Converts a list of dictionaries into an Excel file.

    Args:
        data (List[Dict]): The data to export.
        filename (str): The name for the output Excel file.

    Returns:
        The absolute path to the newly created Excel file.
        
    Raises:
        ValueError: If the input data is empty or not in the expected format.
    """
    if not data or not isinstance(data, list) or not isinstance(data[0], dict):
        raise ValueError("Invalid or empty data provided for Excel export.")

    df = pd.DataFrame(data)
    
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.abspath(os.path.join(output_dir, filename))
    
    df.to_excel(file_path, index=False)
    
    print(f"--- [UTILS] Data successfully exported to {file_path} ---")
    return file_path

def find_excel_path_in_response(response_text: str) -> str | None:
    """
    Searches the agent's final text response for a file path to an Excel file.
    """
    print(f"--- [UTILS] Searching for Excel path in: '{response_text}' ---")
    # This regex is OS-agnostic and looks for a path starting with 'output'
    match = re.search(r"output[/\\][^\s]+\.xlsx", response_text, re.IGNORECASE)
    
    if match:
        os_specific_path = os.path.normpath(match.group(0).strip(".,'\"()"))
        print(f"--- [UTILS] Regex found potential Excel path: {os_specific_path} ---")
        if os.path.exists(os_specific_path):
            print(f"--- [UTILS] Excel path confirmed to exist. ---")
            return os_specific_path
            
    print(f"--- [UTILS] No valid .xlsx file path found in response. ---")
    return None

def find_image_path_in_response(response_text: str) -> str | None:
    """
    Searches the agent's final text response for a file path to an image file.
    """
    print(f"--- [UTILS] Searching for image path in: '{response_text}' ---")
    # This regex is OS-agnostic and looks for common image extensions in the 'output' folder
    match = re.search(r"output[/\\][^\s]+\.(png|jpg|jpeg)", response_text, re.IGNORECASE)
    
    if match:
        os_specific_path = os.path.normpath(match.group(0).strip(".,'\"()"))
        print(f"--- [UTILS] Regex found potential image path: {os_specific_path} ---")
        if os.path.exists(os_specific_path):
            print(f"--- [UTILS] Image path confirmed to exist. ---")
            return os_specific_path
            
    print(f"--- [UTILS] No valid image file path found in response. ---")
    return None
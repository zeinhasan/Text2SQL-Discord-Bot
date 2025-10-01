import pandas as pd
from typing import List, Dict
import os

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
import os
import base64
import pandas as pd
import PyPDF2
from typing import Dict, Any, Literal

def process_uploaded_file(file_path: str) -> Dict[str, Any]:
    """
    Processes an uploaded file, extracts its content, and determines its type.

    Args:
        file_path (str): The local path to the downloaded file.

    Returns:
        A dictionary containing the content type ('text' or 'image') and the
        extracted content.
    """
    print(f"--- [FILE_PROCESSOR] Processing file: {file_path} ---")
    _, extension = os.path.splitext(file_path.lower())
    
    content: Any = ""
    content_type: Literal["text", "image"] = "text"

    try:
        if extension in ['.txt', '.csv']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if extension == '.csv':
                content = f"CSV Content from '{os.path.basename(file_path)}':\n\n{content}"
            
        elif extension == '.pdf':
            pdf_content = []
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    pdf_content.append(page.extract_text())
            content = f"PDF Content from '{os.path.basename(file_path)}':\n\n" + "\n".join(pdf_content)
            
        elif extension == '.xlsx':
            df = pd.read_excel(file_path)
            content = f"Excel Content from '{os.path.basename(file_path)}':\n\n{df.to_string()}"
            
        elif extension in ['.png', '.jpg', '.jpeg']:
            content_type = "image"
            with open(file_path, "rb") as image_file:
                content = base64.b64encode(image_file.read()).decode('utf-8')
            print("--- [FILE_PROCESSOR] Successfully encoded image to base64. ---")
            
        else:
            return {"type": "text", "content": f"Unsupported file type: '{extension}'"}

        return {"type": content_type, "content": content}

    except Exception as e:
        print(f"--- [FILE_PROCESSOR_ERROR] Failed to process file {file_path}: {e} ---")
        return {"type": "text", "content": f"Error reading file {os.path.basename(file_path)}: {e}"}
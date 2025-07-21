# app/main.py

from fastapi import FastAPI, Request
from pydantic import BaseModel
import pandas as pd
import os

app = FastAPI()

# Input model
class FilterRequest(BaseModel):
    args: dict

# Limit token (word) size in response
def limit_token_size(text: str, max_tokens: int = 800) -> str:
    tokens = text.split()
    return ' '.join(tokens[:max_tokens])

@app.post("/filter")
def filter_information(req: FilterRequest):
    args = req.args

    # Validate required fields
    required_fields = ["primary_name", "source"]
    for field in required_fields:
        if field not in args:
            return {"error": f"{field} is required"}

    primary_name = args["primary_name"]
    source = args["source"]
    filters = args.get("additional_filters", [])

    # File path
    file_path = f"data/{source}.csv"
    if not os.path.exists(file_path):
        return {"error": f"File {source}.csv not found"}

    # Read CSV
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}

    # Filter primary_name column
    if "primary_name" in df.columns:
        df = df[df["primary_name"] == primary_name]

    # Apply additional filters
    for f in filters:
        col = f.get("column_name")
        val = f.get("value")
        if col in df.columns:
            df = df[df[col] == val]

    # Limit to 800 tokens (roughly)
    result_str = df.to_string(index=False)
    limited_result = limit_token_size(result_str, max_tokens=800)

    return {"filtered_data": limited_result}

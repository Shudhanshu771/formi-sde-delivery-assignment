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


from fastapi import Body

@app.post("/route")
def route_query(data: dict = Body(...)):
    query = data.get("query", "").lower()

    if not query:
        return {"error": "Query is required"}

    # Very basic keyword routing logic
    routing_map = {
        "activities": ["activity", "indoor", "outdoor"],
        "room-information": ["room", "suite", "deluxe", "guest"],
        "pricing": ["price", "cost", "charges", "rate"],
        "rules": ["rule", "policy", "checkin", "checkout"],
        "queries": ["staff", "hire", "help", "housekeeping"]
    }

    selected_source = None
    for source, keywords in routing_map.items():
        for word in keywords:
            if word in query:
                selected_source = source
                break
        if selected_source:
            break

    if not selected_source:
        return {"error": "Could not determine source from query"}

    # Try to extract primary_name (we'll just use known locations for now)
    known_locations = ["sterling kodai lake", "sterling holidays"]
    matched_location = next((loc for loc in known_locations if loc in query), None)
    if not matched_location:
        matched_location = "Sterling_Holidays"  # fallback default

    # Return structured object similar to /filter input
    return {
        "args": {
            "primary_name": "Sterling_Holidays",  # simplified fallback
            "source": selected_source,
            "additional_filters": []
        }
    }


import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

@app.post("/log-to-sheet")
def log_to_google_sheet(data: dict):
    # Load credentials
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    client = gspread.authorize(creds)

    try:
        sheet = client.open("Formi_Call_Logs").sheet1
    except Exception as e:
        return {"error": f"Could not open sheet: {str(e)}"}

    # Extract and sanitize data
    row = [
        data.get("call_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        data.get("phone_number", "NA"),
        data.get("call_outcome", "NA"),
        data.get("customer_name", "NA"),
        data.get("room_name", "NA"),
        data.get("check_in", "NA"),
        data.get("check_out", "NA"),
        data.get("guests", "NA"),
        data.get("call_summary", "NA")
    ]

    try:
        sheet.append_row(row)
    except Exception as e:
        return {"error": f"Error appending row: {str(e)}"}

    return {"message": "✅ Call log added successfully"}


@app.post("/query")
def handle_query(data: dict):
    query = data.get("query", "").lower()

    if not query:
        return {"error": "Query is required"}

    # Step 1: Use existing route logic
    routing_map = {
        "activities": ["activity", "indoor", "outdoor"],
        "room-information": ["room", "suite", "deluxe", "guest"],
        "pricing": ["price", "cost", "charges", "rate"],
        "rules": ["rule", "policy", "checkin", "checkout"],
        "queries": ["staff", "hire", "help", "housekeeping"]
    }

    selected_source = None
    for source, keywords in routing_map.items():
        for word in keywords:
            if word in query:
                selected_source = source
                break
        if selected_source:
            break

    if not selected_source:
        return {"error": "Could not determine data source from query."}

    # Extract location
    known_locations = ["sterling kodai lake", "sterling holidays"]
    matched_location = next((loc for loc in known_locations if loc in query), None)
    primary_name = "Sterling_Holidays" if matched_location else "Sterling_Holidays"

    # Step 2: Build file path
    file_path = os.path.join("public", "agent_directory", f"{selected_source}.csv")

    if not os.path.exists(file_path):
        return {"error": f"{selected_source}.csv not found."}

    # Step 3: Read CSV
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return {"error": f"Failed to read CSV: {str(e)}"}

    # Step 4: Filter based on location
    filtered_df = df[df['primary_name'].str.lower() == matched_location] if matched_location else df

    if filtered_df.empty:
        return {"message": "No results found."}

    # Step 5: Return top 5 rows as JSON (simplified)
    return filtered_df.head(5).to_dict(orient="records")

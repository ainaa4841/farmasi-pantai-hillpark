# sheets_client.py
import json
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Load and parse the service account JSON from Streamlit secrets
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)

# Access your spreadsheet by ID from secrets
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

# Also expose creds for Google Drive use
__all__ = ["spreadsheet", "creds"]

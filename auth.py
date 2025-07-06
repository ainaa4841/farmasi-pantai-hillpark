
import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st

scope = ["https://spreadsheets.google.com/feeds"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

def register_user(username, password, role):
    worksheet = spreadsheet.worksheet("Users")
    worksheet.append_row([username, password, role])

def login_user(username, password):
    worksheet = spreadsheet.worksheet("Users")
    users = worksheet.get_all_records()
    for user in users:
        if user['Username'] == username and user['Password'] == password:
            return user['Role']
    return None

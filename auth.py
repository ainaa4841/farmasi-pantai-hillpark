import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
import re

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

def register_user(username, password, role, email):
    worksheet = spreadsheet.worksheet("Users")
    worksheet.append_row([username, password, role, email])

def login_user(username, password):
    worksheet = spreadsheet.worksheet("Users")
    users = worksheet.get_all_records()
    for user in users:
        if (user['Username'] == username or user['Email'] == username) and user['Password'] == password:
            return user['Role']
    return None

def check_email_exists(email):
    worksheet = spreadsheet.worksheet("Users")
    users = worksheet.get_all_records()
    for user in users:
        if user['Email'] == email:
            return True
    return False

def check_password_complexity(password):
    if len(password) < 8 or not re.search(r"[!@#$%^&*(),.?\\\":{}|<>]", password):
        return False
    return True

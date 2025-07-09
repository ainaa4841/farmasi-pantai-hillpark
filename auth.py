import streamlit as st
import re
from sheets_client import spreadsheet

def register_user(username, password, role, email):
    worksheet = spreadsheet.worksheet("Users")
    worksheet.append_row([username, password, role, email])

def login_user(username_or_email, password):
    worksheet = spreadsheet.worksheet("Users")
    for user in worksheet.get_all_records():
        if (user["Username"] == username_or_email or user["Email"] == username_or_email) and user["Password"] == password:
            return user["Role"], user["Username"], user["Email"]
    return None, None, None

def get_customer_id(username):
    worksheet = spreadsheet.worksheet("Customers")
    for record in worksheet.get_all_records():
        if record["customerUsername"] == username:
            return str(record["customerID"])
    return None

def check_email_exists(email):
    worksheet = spreadsheet.worksheet("Users")
    return any(user["Email"] == email for user in worksheet.get_all_records())

def check_password_complexity(password):
    return len(password) >= 8 and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)

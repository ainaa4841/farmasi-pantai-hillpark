import streamlit as st 
import re
from sheets_client import spreadsheet

from sheets_client import spreadsheet

def register_user(username, password, full_name, email, phone):
    worksheet = spreadsheet.worksheet("Customer")
    customer_id = generate_next_id("Customer", "customerID", prefix="C")
    worksheet.append_row([customer_id, username, password, full_name, email, phone])
    return customer_id


def login_user(username, password):
    try:
        # Check Customers sheet
        customer_ws = spreadsheet.worksheet("Customer")
        for customer in customer_ws.get_all_records():
            if customer.get("customerUsername") == username and customer.get("customerPassword") == password:
                return "Customer", customer["customerUsername"], customer["customerEmail"]

        # Check Pharmacist sheet
        pharmacist_ws = spreadsheet.worksheet("Pharmacist")
        for pharm in pharmacist_ws.get_all_records():
            if pharm.get("pharmacistUsername") == username and pharm.get("pharmacistPassword") == password:
                return "Pharmacist", pharm["pharmacistUsername"], pharm["pharmacistEmail"]

        # No match found
        return None, None, None

    except Exception as e:
        print(f"Login error: {e}")
        return None, None, None

def get_customer_id(username):
    worksheet = spreadsheet.worksheet("Customer")
    for record in worksheet.get_all_records():
        if record.get("customerUsername") == username:
            return str(record.get("customerID"))
    return None

def check_email_exists(email):
    worksheet = spreadsheet.worksheet("Customer")
    return any(customer.get("customerEmail") == email for customer in worksheet.get_all_records())

def check_password_complexity(password):
    return len(password) >= 8 and re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)

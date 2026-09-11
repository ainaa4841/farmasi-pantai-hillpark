import streamlit as st
import re
from sheets_client import spreadsheet
from google_sheets import generate_next_id

# NOTE: app.py's Register flow currently calls google_sheets.save_customer(),
# not this function. Kept here (and fixed) in case it's wired up later.
def register_user(username, password, full_name, email, phone):
    worksheet = spreadsheet.worksheet("Customer")
    customer_id = generate_next_id("Customer", "customerID")
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

        # No match found — credentials genuinely didn't match any row
        return None, None, None

    except Exception as e:
        # TEMPORARY: surface the real error in the UI so we can see what's
        # actually failing (missing secrets, sheet access, wrong tab/column
        # names, etc.) instead of it looking like "wrong password".
        # Remove this st.error line once the underlying issue is fixed.
        st.error(f"⚠️ Login backend error (debug): {e}")
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

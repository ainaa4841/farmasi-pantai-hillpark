import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

def generate_next_id(sheet, col_name):
    records = spreadsheet.worksheet(sheet).get_all_records()
    if not records: return 1
    return int(records[-1][col_name]) + 1

def save_customer(data):
    ws = spreadsheet.worksheet("Customers")
    cid = generate_next_id("Customers", "customerID")
    ws.append_row([cid] + data)
    return cid

def save_appointment(data):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    worksheet.append_row([appointment_id] + data)

    # Remove booked slot from schedule
    remove_schedule_slot(data[1], data[2])  # data[1]=date, data[2]=time

def save_file_metadata(data):
    ws = spreadsheet.worksheet("Files")
    ws.append_row(data)

def update_customer_referral_letter(username, link):
    ws = spreadsheet.worksheet("Customers")
    records = ws.get_all_records()
    for idx, row in enumerate(records, start=2):
        if row["customerUsername"] == username:
            ws.update_acell(f"G{idx}", link)
            break

def get_appointments():
    ws = spreadsheet.worksheet("Appointments")
    return ws.get_all_records()

def update_schedule(date, time):
    ws = spreadsheet.worksheet("Schedules")
    ws.append_row([date, time])

def get_pharmacist_schedule():
    return spreadsheet.worksheet("Schedules").get_all_records()

def update_appointment_status(appointment_id, new_status, new_date=None, new_time=None):
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()

    for idx, record in enumerate(records, start=2):  # Start from row 2 due to headers
        if str(record["appointmentID"]).strip() == str(appointment_id).strip():

            current_date = str(record["Date"]).strip()
            current_time = str(record["Time"]).strip()

            if new_status == "Cancelled":
                worksheet.update(f"E{idx}", [[new_status]])
                restore_schedule_slot(current_date, current_time)

            elif new_status == "Rescheduled":
                # Ensure new slot is not None
                if new_date and new_time:
                    worksheet.update(f"C{idx}", [[new_date]])
                    worksheet.update(f"D{idx}", [[new_time]])
                    worksheet.update(f"E{idx}", [["Pending Confirmation"]])

                    # Restore old slot and remove new one
                    restore_schedule_slot(current_date, current_time)
                    remove_schedule_slot(new_date, new_time)

            else:
                worksheet.update(f"E{idx}", [[new_status]])

            break  # exit loop once matched

def get_all_customers():
    return spreadsheet.worksheet("Customers").get_all_records()

def save_report(data):
    ws = spreadsheet.worksheet("Reports")
    rid = generate_next_id("Reports", "reportID")
    ws.append_row([rid] + data)

def remove_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    date = str(date).strip().lower()
    time = str(time).strip().lower()

    for idx, record in enumerate(records, start=2):
        rec_date = str(record["Date"]).strip().lower()
        rec_time = str(record["Time"]).strip().lower()
        if rec_date == date and rec_time == time:
            worksheet.delete_rows(idx)
            return
    print(f"[DEBUG] Slot not found for deletion: {date} - {time}")


def restore_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    for record in records:
        rec_date = str(record["Date"]).strip().lower()
        rec_time = str(record["Time"]).strip().lower()
        if rec_date == str(date).strip().lower() and rec_time == str(time).strip().lower():
            return  # already exists
    worksheet.append_row([date, time])

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
import streamlit as st
import os
import mimetypes

# Auth for Google Sheets and Drive
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

# Drive
drive_service = build("drive", "v3", credentials=creds)
FOLDER_ID = "1GMngst7ixf-OWTqeZAEzxoaUDptOJeyi"

def generate_next_id(sheet, col_name):
    records = spreadsheet.worksheet(sheet).get_all_records()
    return 1 if not records else int(records[-1][col_name]) + 1

def save_customer(data):
    ws = spreadsheet.worksheet("Customers")
    cid = generate_next_id("Customers", "customerID")
    ws.append_row([cid] + data)
    return cid

def upload_referral_to_drive(file_path, filename):
    mime_type, _ = mimetypes.guess_type(file_path)
    file_metadata = {
        'name': filename,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, mimetype=mime_type)
    uploaded = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    file_id = uploaded.get("id")
    # Make file public
    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
    ).execute()
    return f"https://drive.google.com/uc?id={file_id}"

def save_appointment(data, referral_path=""):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    worksheet.append_row([appointment_id] + data + [referral_path])
    remove_schedule_slot(data[1], data[2])

def update_appointment_status(appointment_id, new_status, new_date=None, new_time=None):
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record["appointmentID"]) == str(appointment_id):
            if new_status == "Cancelled":
                worksheet.update_acell(f"E{idx}", "Cancelled")
                restore_schedule_slot(record["Date"], record["Time"])
            elif new_status == "Rescheduled":
                old_date, old_time = record["Date"], record["Time"]
                worksheet.update_acell(f"C{idx}", new_date)
                worksheet.update_acell(f"D{idx}", new_time)
                worksheet.update_acell(f"E{idx}", "Pending Confirmation")
                restore_schedule_slot(old_date, old_time)
                remove_schedule_slot(new_date, new_time)
            else:
                worksheet.update_acell(f"E{idx}", new_status)
            break

def get_appointments():
    return spreadsheet.worksheet("Appointments").get_all_records()

def get_pharmacist_schedule():
    return spreadsheet.worksheet("Schedules").get_all_records()

def update_schedule(date, time):
    spreadsheet.worksheet("Schedules").append_row([date, time])

def remove_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):
        if record["Date"].strip().lower() == date.strip().lower() and \
           record["Time"].strip().lower() == time.strip().lower():
            worksheet.delete_rows(idx)
            return

def restore_schedule_slot(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    for record in worksheet.get_all_records():
        if record["Date"].strip().lower() == date.strip().lower() and \
           record["Time"].strip().lower() == time.strip().lower():
            return
    worksheet.append_row([date, time])

def get_all_customers():
    return spreadsheet.worksheet("Customers").get_all_records()

def save_file_metadata(data):
    spreadsheet.worksheet("Files").append_row(data)

def save_report(data):
    rid = generate_next_id("Reports", "reportID")
    spreadsheet.worksheet("Reports").append_row([rid] + data)

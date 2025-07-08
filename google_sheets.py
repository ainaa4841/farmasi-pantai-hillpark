import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)


client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

# Google Drive setup
drive_service = build("drive", "v3", credentials=creds)
UPLOAD_FOLDER_ID = "1GMngst7ixf-OWTqeZAEzxoaUDptOJeyi"

def generate_next_id(sheet, col_name):
    records = spreadsheet.worksheet(sheet).get_all_records()
    if not records:
        return 1
    return int(records[-1][col_name]) + 1

def save_customer(data):
    ws = spreadsheet.worksheet("Customers")
    cid = generate_next_id("Customers", "customerID")
    ws.append_row([cid] + data)
    return cid

def upload_file_to_drive(local_path, filename):
    file_metadata = {
        "name": filename,
        "parents": [UPLOAD_FOLDER_ID]
    }
    media = MediaFileUpload(local_path, resumable=True)
    uploaded = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()

    file_id = uploaded.get("id")
    if file_id:
        drive_service.permissions().create(
            fileId=file_id,
            body={"role": "reader", "type": "anyone"},
        ).execute()
        return f"https://drive.google.com/uc?id={file_id}"
    return ""

def save_appointment(data, referral_path=None):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    row = [appointment_id] + data + [referral_path or ""]
    worksheet.append_row(row)
    remove_schedule_slot(data[1], data[2])

def get_appointments():
    return spreadsheet.worksheet("Appointments").get_all_records()

def get_all_customers():
    return spreadsheet.worksheet("Customers").get_all_records()

def get_pharmacist_schedule():
    return spreadsheet.worksheet("Schedules").get_all_records()

def update_schedule(date, time):
    ws = spreadsheet.worksheet("Schedules")
    ws.append_row([date, time])

def remove_schedule_slot(date, time):
    ws = spreadsheet.worksheet("Schedules")
    records = ws.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record["Date"]).strip().lower() == str(date).strip().lower() and \
           str(record["Time"]).strip().lower() == str(time).strip().lower():
            ws.delete_rows(idx)
            return

def restore_schedule_slot(date, time):
    ws = spreadsheet.worksheet("Schedules")
    for record in ws.get_all_records():
        if str(record["Date"]).strip().lower() == str(date).strip().lower() and \
           str(record["Time"]).strip().lower() == str(time).strip().lower():
            return
    ws.append_row([date, time])

def update_appointment_status(appointment_id, new_status, new_date=None, new_time=None):
    ws = spreadsheet.worksheet("Appointments")
    records = ws.get_all_records()
    for idx, record in enumerate(records, start=2):
        if str(record["appointmentID"]) == str(appointment_id):
            if new_status == "Cancelled":
                ws.update_acell(f"E{idx}", "Cancelled")
                restore_schedule_slot(record["Date"], record["Time"])
            elif new_status == "Rescheduled":
                ws.update_acell(f"C{idx}", new_date)
                ws.update_acell(f"D{idx}", new_time)
                ws.update_acell(f"E{idx}", "Pending Confirmation")
                restore_schedule_slot(record["Date"], record["Time"])
                remove_schedule_slot(new_date, new_time)
            else:
                ws.update_acell(f"E{idx}", new_status)
            break

def save_report(data):
    ws = spreadsheet.worksheet("Reports")
    rid = generate_next_id("Reports", "reportID")
    ws.append_row([rid] + data)

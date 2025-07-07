import gspread
from google.oauth2.service_account import Credentials
import json
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
creds = Credentials.from_service_account_info(service_account_info, scopes=scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(st.secrets["SPREADSHEET_ID"])

def save_customer(data):
    worksheet = spreadsheet.worksheet("Customers")
    worksheet.append_row(data)

def save_appointment(data):
    worksheet = spreadsheet.worksheet("Appointments")
    worksheet.append_row(data)

def save_file_metadata(data):
    worksheet = spreadsheet.worksheet("Files")
    worksheet.append_row(data)

def upload_to_drive(file_path):
    service = build('drive', 'v3', credentials=creds)
    file_metadata = {'name': os.path.basename(file_path), 'parents': [st.secrets["FOLDER_ID"]]}
    media = MediaFileUpload(file_path)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def get_appointments():
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    appointments = []
    for record in records:
        appointments.append({
            "Name": record.get("Name"),
            "Appointment Type": record.get("Appointment Type"),
            "Date": record.get("Date"),
            "Time": record.get("Time"),
            "Status": record.get("Status")
        })
    return appointments

def get_pharmacist_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    return worksheet.get_all_records()

def update_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    worksheet.append_row(["New Slot", "9:00AM", "Available"])

def update_appointment_status(name, date, time, new_status, new_date=None, new_time=None):
    worksheet = spreadsheet.worksheet("Appointments")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):  # Row index starts from 2 because of headers
        if record['Name'] == name and record['Date'] == date and record['Time'] == time:
            if new_status == "Rescheduled":
                worksheet.update(f"C{idx}", new_date)  # Update Date
                worksheet.update(f"D{idx}", new_time)  # Update Time
                worksheet.update(f"E{idx}", "Pending Confirmation")
            elif new_status == "Cancelled":
                worksheet.update(f"E{idx}", "Cancelled")
            break


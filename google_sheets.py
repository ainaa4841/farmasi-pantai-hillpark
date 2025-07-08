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
    customer_id = generate_next_id("Customers", "customerID")
    worksheet.append_row([customer_id] + data)
    return customer_id

def save_appointment(data):
    worksheet = spreadsheet.worksheet("Appointments")
    appointment_id = generate_next_id("Appointments", "appointmentID")
    worksheet.append_row([appointment_id] + data)

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

def update_schedule(date, time):
    worksheet = spreadsheet.worksheet("Schedules")
    worksheet.append_row([date, time])

def get_pharmacist_schedule():
    worksheet = spreadsheet.worksheet("Schedules")
    records = worksheet.get_all_records()
    return [{"Date": str(r["Date"]), "Time": str(r["Time"])} for r in records if r.get("Date") and r.get("Time")]


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

def generate_next_id(sheet_name, id_column):
    worksheet = spreadsheet.worksheet(sheet_name)
    records = worksheet.get_all_records()
    if not records:
        return 1
    last_id = records[-1][id_column]
    return int(last_id) + 1

def save_report(data):
    worksheet = spreadsheet.worksheet("Reports")
    report_id = generate_next_id("Reports", "reportID")
    worksheet.append_row([report_id] + data)

def get_all_customers():
    worksheet = spreadsheet.worksheet("Customers")
    return worksheet.get_all_records()

def update_customer_referral_letter(name, file_link):
    worksheet = spreadsheet.worksheet("Customers")
    records = worksheet.get_all_records()
    for idx, record in enumerate(records, start=2):  # row 2 = first data row
        if record['Full Name'] == name or record['customerUsername'] == name:
            worksheet.update_acell(f"G{idx}", file_link)  # G column = Referral Letter
            break




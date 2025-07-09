import os
import mimetypes
import json
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from sheets_client import spreadsheet, creds

FOLDER_ID = st.secrets["FOLDER_ID"]

def generate_next_id(sheet_name, col_name):
    worksheet = spreadsheet.worksheet(sheet_name)
    records = worksheet.get_all_records()

    if not records:
        return 1

    # Get the highest current ID
    try:
        last_id = int(records[-1][col_name])
    except:
        last_id = 0

    return last_id + 1


def register_user(username, password, full_name, email, phone):
    worksheet = spreadsheet.worksheet("Customer")
    worksheet.append_row([username, password, full_name, email, phone])

def save_customer(data):
    worksheet = spreadsheet.worksheet("Customer")
    customer_id = generate_next_id("Customer", "customerID")
    worksheet.append_row([customer_id] + data)  # data = [username, password, full_name, email, phone, ""]
    return customer_id


def save_appointment(data, referral_path=None):
    worksheet = spreadsheet.worksheet("Appointment")
    appointment_id = generate_next_id("Appointment", "appointmentID")
    if referral_path is None:
        referral_path = ""
    worksheet.append_row([appointment_id] + data + [referral_path])
    remove_schedule_slot(data[1], data[2])  # Remove booked slot

def get_appointments():
    return spreadsheet.worksheet("Appointment").get_all_records()

def update_schedule(date, time):
    spreadsheet.worksheet("Schedule").append_row([date, time])

def get_pharmacist_schedule():
    return spreadsheet.worksheet("Schedule").get_all_records()

def remove_schedule_slot(date, time):
    ws = spreadsheet.worksheet("Schedule")
    records = ws.get_all_records()
    date = str(date).strip().lower()
    time = str(time).strip().lower()

    for idx, record in enumerate(records, start=2):  # offset header
        rec_date = str(record["availableDate"]).strip().lower()
        rec_time = str(record["availableTimeslot"]).strip().lower()
        if rec_date == date and rec_time == time:
            ws.delete_rows(idx)
            return

def restore_schedule_slot(date, time):
    ws = spreadsheet.worksheet("Schedule")
    records = ws.get_all_records()
    for record in records:
        if str(record["availableDate"]).strip().lower() == str(date).strip().lower() and \
           str(record["availableTimeslot"]).strip().lower() == str(time).strip().lower():
            return  # already exists
    ws.append_row([date, time])

def update_appointment_status(appointment_id, new_status=None, new_date=None, new_time=None):
    sheet = spreadsheet.worksheet("Appointment")
    headers = sheet.row_values(1)
    records = sheet.get_all_records()

    for idx, row in enumerate(records):
        if str(row["appointmentID"]) == str(appointment_id):
            row_number = idx + 2  # header is row 1

            if new_status:
                col = headers.index("appointmentStatus") + 1
                sheet.update_cell(row_number, col, new_status)

            if new_date:
                col = headers.index("appointmentDate") + 1
                sheet.update_cell(row_number, col, new_date)

            if new_time:
                col = headers.index("appointmentTime") + 1
                sheet.update_cell(row_number, col, new_time)

            break

def upload_to_drive(file_path):
    drive_service = build("drive", "v3", credentials=creds)
    file_metadata = {
        "name": os.path.basename(file_path),
        "parents": [FOLDER_ID]
    }
    mimetype, _ = mimetypes.guess_type(file_path)
    media = MediaFileUpload(file_path, mimetype=mimetype)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    return uploaded_file.get("id")

def save_file_metadata(data):
    ws = spreadsheet.worksheet("Files")
    ws.append_row(data)

def get_all_customers():
    return spreadsheet.worksheet("Customer").get_all_records()

def save_report(report_row):
    worksheet = spreadsheet.worksheet("Report")
    worksheet.append_row(report_row)


def get_all_reports():
    sheet = spreadsheet.worksheet("Report")  # adjust sheet name as needed
    data = sheet.get_all_records()  # This gives list of dicts based on headers row
    return data


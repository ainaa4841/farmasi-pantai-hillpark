
import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity
from google_sheets import (save_customer, save_appointment, save_file_metadata,
                           upload_to_drive, get_appointments, get_pharmacist_schedule, update_schedule)
import os

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Farmasi Pantai Hillpark Appointment System")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''

menu = ["Login", "Register"]
if st.session_state.logged_in:
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "Upload File", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Pharmacist Dashboard", "Manage Schedule", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

if choice == "Register":
    st.subheader("Customer Registration")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")

    if st.button("Register"):
        if not username or not password or not full_name or not email or not phone:
            st.error("Please fill in all required fields.")
        elif not check_password_complexity(password):
            st.error("Password must be at least 8 characters and contain a special character.")
        elif check_email_exists(email):
            st.error("Email already exists. Please use a different email or login.")
        else:
            register_user(username, password, "Customer", email)
            save_customer([full_name, email, phone])
            st.success("Registration successful! Please log in.")

elif choice == "Login":
    st.subheader("Login")
    username_or_email = st.text_input("Username or Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role, username, email = login_user(username_or_email, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.user_role = role
            st.session_state.user_username = username
            st.session_state.user_email = email
            st.rerun()
        else:
            st.error("Invalid credentials!")
        

elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
    name = st.text_input("Enter your name")
    appointment_type = st.selectbox("Appointment Type", ["First Time", "Follow Up", "Special"])
    date = st.date_input("Select Date")
    time = st.selectbox("Select Time Slot", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])
    uploaded_file = st.file_uploader("Upload Referral Letter")

    if st.button("Book Appointment"):
    if not name or not uploaded_file:
        st.error("Please provide your name and upload a referral letter.")
    else:
        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        file_path = f"uploads/{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_id = upload_to_drive(file_path)
        save_file_metadata([name, uploaded_file.name, file_id])
        save_appointment([name, appointment_type, str(date), time, "Pending Confirmation"])
        st.success(f"Appointment booked for {name} on {date} at {time}. Status: Pending Confirmation.")
          

elif choice == "Upload File":
    st.subheader("Upload Additional Referral Letter")
    name = st.text_input("Enter your name")
    uploaded_file = st.file_uploader("Choose a file")

    if uploaded_file is not None:
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
        file_path = f"uploads/{uploaded_file.name}"
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_id = upload_to_drive(file_path)
        save_file_metadata([name, uploaded_file.name, file_id])
        st.success(f"File {uploaded_file.name} uploaded successfully!")

elif choice == "My Appointments":
    st.subheader("My Appointments")
    appointments = get_appointments()
    my_appointments = [appt for appt in appointments if appt['Name'] == st.session_state.user_username]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        for appt in my_appointments:
            st.write(f"Date: {appt['Date']}, Time: {appt['Time']}, Status: {appt['Status']}")
            if appt['Status'] == 'Pending Confirmation':
                if st.button(f"Reschedule {appt['Date']} {appt['Time']}"):
                    new_date = st.date_input("Select new date")
                    new_time = st.selectbox("Select new time", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])
                    st.write(f"Appointment rescheduled to {new_date} at {new_time} (Pending Confirmation)")
                if st.button(f"Cancel {appt['Date']} {appt['Time']}"):
                    st.write("Appointment cancelled.")

elif choice == "Pharmacist Dashboard":
    st.subheader("Pharmacist Dashboard (Coming Soon)")

elif choice == "Manage Schedule":
    st.subheader("Manage Pharmacist Schedule")
    schedule = get_pharmacist_schedule()
    for item in schedule:
        st.write(item)
    if st.button("Update Schedule"):
        update_schedule()
        st.success("Schedule updated successfully!")

elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.rerun()

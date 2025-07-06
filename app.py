
import streamlit as st
from auth import register_user, login_user
from google_sheets import (save_customer, save_appointment, save_file_metadata,
                           upload_to_drive, get_appointments, get_pharmacist_schedule, update_schedule)
import os

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

# Custom CSS
with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Farmasi Pantai Hillpark Appointment System")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
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
    referral_notes = st.text_area("Referral Notes")

    if st.button("Register"):
        register_user(username, password, "Customer")
        save_customer([full_name, email, phone, referral_notes])
        st.success("Registration successful! Please log in.")

elif choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = login_user(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.user_role = role
            st.session_state.user_email = username
            st.rerun()
        else:
            st.error("Invalid credentials!")

elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
    name = st.text_input("Enter your name")
    appointment_type = st.selectbox("Appointment Type", ["First Time", "Follow Up", "Special"])
    date = st.date_input("Select Date")
    time = st.selectbox("Select Time Slot", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])

    if st.button("Book Appointment"):
        save_appointment([name, appointment_type, str(date), time])
        st.success(f"Appointment booked for {name} on {date} at {time}.")

elif choice == "Upload File":
    st.subheader("Upload Referral Letter")
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
    for appt in appointments:
        st.write(appt)

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


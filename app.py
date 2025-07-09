import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, upload_to_drive, save_appointment,
    get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status,
    get_all_customers, save_report, get_all_reports,
    restore_schedule_slot, remove_schedule_slot
)
import os
import pandas as pd

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

# Load CSS
with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("🏥 Farmasi Pantai Hillpark Appointment System")

# Session defaults
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

menu = ["Login", "Register"]
if st.session_state.logged_in:
    menu = ["Logout"]
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Appointments", "Add Slot Availability", "Available Slots", "Add Report", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# --------------------------------------------
# REGISTER
if choice == "Register":
    st.subheader("📝 Customer Registration")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")

    if st.button("Register"):
        if not all([username, password, full_name, email, phone]):
            st.error("Please fill in all required fields.")
        elif not check_password_complexity(password):
            st.error("Password must be at least 8 characters and contain a special character.")
        elif check_email_exists(email):
            st.error("Email already exists. Please use a different email or login.")
        else:
            register_user(username, password, "Customer", email)
            customer_id = save_customer([username, password, full_name, email, phone, ""])
            st.success(f"✅ Registration successful! Your customer ID is {customer_id}. Please log in.")

# --------------------------------------------
# LOGIN
elif choice == "Login":
    st.subheader("🔐 Login")
    username_or_email = st.text_input("Username or Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role, username, email = login_user(username_or_email, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.user_role = role
            st.session_state.user_username = username
            st.session_state.user_email = email
            if role == "Customer":
                st.session_state.customer_id = get_customer_id(username)
            st.rerun()
        else:
            st.error("❌ Invalid credentials!")

# --------------------------------------------
# BOOK APPOINTMENT
elif choice == "Book Appointment":
    st.subheader("📅 Book an Appointment")
    available_schedule = get_pharmacist_schedule()

    if not available_schedule:
        st.warning("No available slots. Please try again later.")
    else:
        available_dates = sorted(set(slot["Date"] for slot in available_schedule))
        selected_date = st.selectbox("Select Date", available_dates)
        available_times = [slot["Time"] for slot in available_schedule if slot["Date"] == selected_date]
        selected_time = st.selectbox("Select Time Slot", available_times)
        uploaded_file = st.file_uploader("Upload Referral Letter")

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload a referral letter.")
            else:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")

                local_path = f"uploads/{uploaded_file.name}"
                with open(local_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                file_id = upload_to_drive(local_path)
                file_url = f"https://drive.google.com/uc?id={file_id}"
                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation"
                ], referral_path=file_url)

                st.success(f"✅ Appointment booked on {selected_date} at {selected_time}.")

# --------------------------------------------
# MY APPOINTMENTS
elif choice == "My Appointments":
    st.subheader("📋 My Appointments")
    appointments = get_appointments()
    my_appointments = [
        appt for appt in appointments
        if str(appt.get('customerID')) == str(st.session_state.customer_id)
    ]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        active = [a for a in my_appointments if a['Status'] not in ["Cancelled", "Completed"]]
        past = [a for a in my_appointments if a['Status'] in ["Cancelled", "Completed"]]

        st.markdown("### 🗓️ Upcoming Appointments")
        for idx, appt in enumerate(active):
            cols = st.columns([2, 2, 2, 2, 2])
            cols[0].write(f"📅 {appt['Date']}")
            cols[1].write(f"🕒 {appt['Time']}")
            cols[2].write(f"📌 {appt['Status']}")
            if cols[3].button("Reschedule", key=f"res_{idx}"):
                with st.form(f"reschedule_form_{idx}"):
                    schedule = get_pharmacist_schedule()
                    booked = [(a['Date'], a['Time']) for a in get_appointments()]
                    available = [
                        s for s in schedule if (s['Date'], s['Time']) not in booked
                    ]
                    dates = sorted(set(s['Date'] for s in available))
                    new_date = st.selectbox("New Date", dates)
                    new_times = [s['Time'] for s in available if s['Date'] == new_date]
                    new_time = st.selectbox("New Time", new_times)

                    if st.form_submit_button("Confirm Reschedule"):
                        update_appointment_status(appt["appointmentID"], "Rescheduled", new_date, new_time)
                        restore_schedule_slot(appt["Date"], appt["Time"])
                        remove_schedule_slot(new_date, new_time)
                        st.success("Rescheduled successfully.")
                        st.rerun()
            if cols[4].button("Cancel", key=f"cancel_{idx}"):
                update_appointment_status(appt["appointmentID"], "Cancelled")
                restore_schedule_slot(appt["Date"], appt["Time"])
                st.success("Appointment cancelled.")
                st.rerun()

        if past:
            st.markdown("### 📦 Past Appointments")
            for a in past:
                st.write(f"📅 {a['Date']} | 🕒 {a['Time']} | 📌 {a['Status']}")

# --------------------------------------------
# MANAGE APPOINTMENTS
elif choice == "Manage Appointments":
    st.subheader("🗂️ Manage Appointments")
    appointments = get_appointments()
    customers = {str(c["customerID"]): c for c in get_all_customers()}

    for idx, appt in enumerate(appointments):
        cust = customers.get(str(appt["customerID"]), {})
        referral = appt.get("appointmentReferralLetter", "")
        st.markdown("---")
        st.write(f"🆔 {appt['appointmentID']} | 👤 {cust.get('Full Name', 'Unknown')} | 📅 {appt['Date']} {appt['Time']} | Status: {appt['Status']}")
        if referral:
            st.markdown(f"[📄 View Referral Letter]({referral})")
        new_status = st.selectbox("Update Status", ["Pending Confirmation", "Confirmed", "Cancelled", "Completed"], index=["Pending Confirmation", "Confirmed", "Cancelled", "Completed"].index(appt["Status"]), key=f"status_{idx}")
        if st.button("Update", key=f"update_{idx}"):
            update_appointment_status(appt["appointmentID"], new_status)
            st.success("Appointment updated.")
            st.rerun()

# --------------------------------------------
# SLOT MANAGEMENT
elif choice == "Add Slot Availability":
    st.subheader("➕ Add Slot")
    slot_date = st.date_input("Available Date")
    slot_time = st.selectbox("Time Slot", ["8:00AM-9:00AM","9:00AM-10:00AM","10:00AM-11:00AM","11:00AM-12:00PM","2:00PM-3:00PM","3:00PM-4:00PM","4:00PM-5:00PM"])
    schedule = get_pharmacist_schedule()
    if st.button("Add"):
        if any(s["Date"] == str(slot_date) and s["Time"] == slot_time for s in schedule):
            st.warning("Slot already exists.")
        else:
            update_schedule(str(slot_date), slot_time)
            st.success("Slot added.")
            st.rerun()

elif choice == "Available Slots":
    st.subheader("📌 Available Slots")
    schedule = get_pharmacist_schedule()
    if not schedule:
        st.info("No available slots.")
    else:
        df = pd.DataFrame(schedule)
        for idx, row in df.iterrows():
            cols = st.columns([3, 3, 1])
            cols[0].write(f"📅 {row['Date']}")
            cols[1].write(f"🕒 {row['Time']}")
            if cols[2].button("❌ Delete", key=f"delete_slot_{idx}"):
                remove_schedule_slot(row['Date'], row['Time'])
                st.success("Slot deleted.")
                st.rerun()

# --------------------------------------------
# REPORTS
elif choice == "Add Report":
    st.subheader("📝 Add Appointment Report")
    customer_id = st.text_input("Customer ID")
    appt_id = st.text_input("Appointment ID")
    report_date = st.date_input("Report Date")
    content = st.text_area("Report Content")
    if st.button("Save Report"):
        if not all([customer_id, appt_id, content]):
            st.error("All fields required.")
        else:
            save_report([appt_id, str(report_date), content])
            st.success("Report saved.")

    st.markdown("---")
    st.subheader("📄 View Reports")
    reports = get_all_reports()
    appointments = get_appointments()
    appt_map = {str(a["appointmentID"]): str(a["customerID"]) for a in appointments}
    for r in reports:
        r["customerID"] = appt_map.get(str(r["appointmentID"]), "Unknown")

    for r in reports:
        st.markdown(f"""
        **Report ID:** {r['reportID']}  
        👤 Customer ID: {r['customerID']}  
        📎 Appointment ID: {r['appointmentID']}  
        📅 Date: {r['reportDate']}  
        📝 Content:  
        {r['reportContent']}
        ---
        """)

# --------------------------------------------
# LOGOUT
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

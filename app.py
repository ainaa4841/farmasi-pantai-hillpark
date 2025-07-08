import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status,
    get_all_customers, save_report, upload_referral_to_drive
)
import os
import pandas as pd

st.set_page_config(page_title="Farmasi Pantai Hillpark", layout="wide")

# Load CSS
with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.title("Farmasi Pantai Hillpark Appointment System")

# Session defaults
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

# Sidebar Menu
menu = ["Login", "Register"]
if st.session_state.logged_in:
    menu = ["Logout"]
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Schedule", "Update Slot Availability", "Add Report", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# -------------------------------
# Register
if choice == "Register":
    st.subheader("Customer Registration")
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
            st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

# -------------------------------
# Login
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
            if role == "Customer":
                st.session_state.customer_id = get_customer_id(username)
            st.rerun()
        else:
            st.error("Invalid credentials!")

# -------------------------------
# Book Appointment
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
        uploaded_file = st.file_uploader("Upload Referral Letter (PDF only)", type=["pdf"])

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload a referral letter.")
            else:
                # Upload to Google Drive
                file_link = upload_referral_to_drive(uploaded_file)

                # Save metadata (optional)
                save_file_metadata([st.session_state.user_username, uploaded_file.name, file_link])

                # Save appointment
                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation",
                    file_link  # Save to Appointments sheet
                ])
                st.success(f"Appointment booked on {selected_date} at {selected_time}.")

# -------------------------------
# My Appointments
elif choice == "My Appointments":
    st.subheader("📋 My Appointments")
    appointments = get_appointments()
    my_appointments = [a for a in appointments if str(a.get("customerID")) == str(st.session_state.customer_id)]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        active_appts = [a for a in my_appointments if a["Status"] in ["Pending Confirmation", "Confirmed", "Rescheduled"]]
        past_appts = [a for a in my_appointments if a["Status"] in ["Cancelled", "Completed"]]

        st.markdown("### 🗓️ Upcoming Appointments")
        for idx, appt in enumerate(active_appts):
            cols = st.columns([2, 2, 2, 2, 2])
            cols[0].write(f"📅 **{appt['Date']}**")
            cols[1].write(f"🕒 **{appt['Time']}**")
            cols[2].write(f"📌 **{appt['Status']}**")

            if cols[3].button("🔁 Reschedule", key=f"resched_{idx}"):
                with st.form(f"reschedule_form_{idx}"):
                    st.subheader("Select New Slot")
                    schedule = get_pharmacist_schedule()
                    booked = [(a['Date'], a['Time']) for a in get_appointments()]
                    available_slots = [s for s in schedule if (s['Date'], s['Time']) not in booked]

                    if not available_slots:
                        st.warning("No available slots.")
                    else:
                        new_date = st.selectbox("New Date", sorted(set(s["Date"] for s in available_slots)))
                        new_times = [s["Time"] for s in available_slots if s["Date"] == new_date]
                        new_time = st.selectbox("New Time", new_times)

                        submitted = st.form_submit_button("Confirm Reschedule")
                        if submitted:
                            update_appointment_status(
                                appointment_id=appt["appointmentID"],
                                new_status="Rescheduled",
                                new_date=new_date,
                                new_time=new_time
                            )
                            st.success("Rescheduled!")
                            st.rerun()

            if cols[4].button("❌ Cancel", key=f"cancel_{idx}"):
                update_appointment_status(appt["appointmentID"], "Cancelled")
                st.success("Cancelled.")
                st.rerun()

        # Past Appointments
        if past_appts:
            st.markdown("---")
            st.markdown("### 🗂 Past Appointments")
            past_cols = st.columns([1, 2, 2, 2, 2])
            past_cols[0].markdown("**🆔**")
            past_cols[1].markdown("**📅 Date**")
            past_cols[2].markdown("**🕒 Time**")
            past_cols[3].markdown("**📄 Referral Letter**")
            past_cols[4].markdown("**📌 Status**")

            for appt in past_appts:
                cols = st.columns([1, 2, 2, 2, 2])
                cols[0].write(appt["appointmentID"])
                cols[1].write(appt["Date"])
                cols[2].write(appt["Time"])
                ref_link = appt.get("appointmentReferralLetter")
                cols[3].markdown(f"[Download 📄]({ref_link})" if ref_link else "—", unsafe_allow_html=True)
                cols[4].write(appt["Status"])

# -------------------------------
# Logout
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

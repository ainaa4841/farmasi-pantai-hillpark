import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity, get_customer_id
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status,
    get_all_customers, update_customer_referral_letter, save_report
)
import os
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from collections import defaultdict

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

menu = ["Login", "Register"]
if st.session_state.logged_in:
    menu = ["Logout"]
    if st.session_state.user_role == 'Customer':
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = ["Manage Schedule", "Update Slot Availability", "Add Report", "Logout"]

choice = st.sidebar.selectbox("Menu", menu)

# --------------------------------------------
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

# --------------------------------------------
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

# --------------------------------------------
# Book Appointment
elif choice == "Book Appointment":
    st.subheader("Book an Appointment")
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
                # Save file locally
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                file_link = f"uploads/{uploaded_file.name}"
                save_file_metadata([st.session_state.user_username, uploaded_file.name, file_link])
                update_customer_referral_letter(st.session_state.user_username, file_link)

                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation"
                ])
                st.success(f"Appointment booked on {selected_date} at {selected_time}.")

# --------------------------------------------
# Manage Schedule
elif choice == "Manage Schedule":
    st.subheader("📋 Pharmacist: Manage Appointments & Availability")

    appointments = get_appointments()
    customers = {str(c["customerID"]): c for c in get_all_customers()}

    if not appointments:
        st.info("No appointments found.")
    else:
        st.markdown("### Booked Appointments")

        for idx, appt in enumerate(appointments):
            cust = customers.get(str(appt["customerID"]), {})
            full_name = cust.get("Full Name", "Unknown")
            email = cust.get("Email", "N/A")
            phone = cust.get("Phone Number", "N/A")

            # Wrap appointment row in a bordered div
            st.markdown(f"""
                <div style="
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    padding: 1px;
                    margin-bottom: 10px;
                    background-color: #f9f9f9;">
            """, unsafe_allow_html=True)

            # Columns inside bordered box
            cols = st.columns([2, 3, 3, 2, 2, 2])
            cols[0].write(f"🆔 **{appt['appointmentID']}**")
            cols[1].write(f"👤 **{full_name}**")
            cols[2].write(f"📧 {email}<br>📱 {phone}", unsafe_allow_html=True)
            cols[3].write(f"📅 {appt['Date']}")
            cols[4].write(f"🕒 {appt['Time']}")

            new_status = cols[5].selectbox(
                "Status",
                ["Pending Confirmation", "Confirmed", "Cancelled"],
                index=["Pending Confirmation", "Confirmed", "Cancelled"].index(appt["Status"]),
                key=f"status_{idx}"
            )

            if st.button("Update", key=f"update_{idx}"):
                update_appointment_status(appt["appointmentID"], new_status)
                st.success(f"✅ Appointment {appt['appointmentID']} updated to {new_status}")
                st.rerun()

            # End of bordered div
            st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------
# Manage Schedule
elif choice == "Manage Schedule":
    st.subheader("📋 Pharmacist: Manage Appointments & Availability")

    appointments = get_appointments()
    customers = {str(c["customerID"]): c for c in get_all_customers()}

    if not appointments:
        st.info("No appointments found.")
    else:
        st.markdown("### Booked Appointments")

        for idx, appt in enumerate(appointments):
            cust = customers.get(str(appt["customerID"]), {})
            full_name = cust.get("Full Name", "Unknown")
            email = cust.get("Email", "N/A")
            phone = cust.get("Phone Number", "N/A")

            # Wrap appointment row in a bordered div
            st.markdown(f"""
                <div style="
                    border: 0.5px solid #ccc;
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 10px;
                    background-color: #f9f9f9;">
            """, unsafe_allow_html=True)

            # Columns inside bordered box
            cols = st.columns([2, 3, 3, 2, 2, 2])
            cols[0].write(f"🆔 **{appt['appointmentID']}**")
            cols[1].write(f"👤 **{full_name}**")
            cols[2].write(f"📧 {email}<br>📱 {phone}", unsafe_allow_html=True)
            cols[3].write(f"📅 {appt['Date']}")
            cols[4].write(f"🕒 {appt['Time']}")

            new_status = cols[5].selectbox(
                "Status",
                ["Pending Confirmation", "Confirmed", "Cancelled"],
                index=["Pending Confirmation", "Confirmed", "Cancelled"].index(appt["Status"]),
                key=f"status_{idx}"
            )

            if st.button("Update", key=f"update_{idx}"):
                update_appointment_status(appt["appointmentID"], new_status)
                st.success(f"✅ Appointment {appt['appointmentID']} updated to {new_status}")
                st.rerun()

            # End of bordered div
            st.markdown("</div>", unsafe_allow_html=True)
# --------------------------------------------
# Update Slot Availability
elif choice == "Update Slot Availability":
    st.subheader("➕ Add New Slot")
    slot_date = st.date_input("Available Date")
    slot_time = st.selectbox("Available Time", ["8:00AM-9:00AM","9:00AM-10:00AM", "10:00AM-11:00AM", "11:00AM-12:00PM","2:00PM-3:00PM", "3:00PM-4:00PM", "4:00PM-5:00PM"])
    schedule = get_pharmacist_schedule()
    if st.button("Add Slot"):
        if any(s["Date"] == str(slot_date) and s["Time"] == slot_time for s in schedule):
            st.warning("Slot already exists.")
        else:
            update_schedule(str(slot_date), slot_time)
            st.success("Slot added!")
            st.rerun()
        st.markdown("---")

    # Calendar display
    st.markdown("### 📌 Available Slots")

    if not schedule:
        st.info("No slots available.")
    else:
        df_slots = pd.DataFrame(schedule)

        for idx, row in df_slots.iterrows():
            cols = st.columns([3, 3, 1])
            cols[0].write(f"📅 Date: **{row['Date']}**")
            cols[1].write(f"🕒 Time: **{row['Time']}**")
            if cols[2].button("❌ Delete", key=f"delete_slot_{idx}"):
                from google_sheets import remove_schedule_slot
                remove_schedule_slot(row['Date'], row['Time'])
                st.success(f"Slot on {row['Date']} at {row['Time']} deleted.")
                st.rerun()


# --------------------------------------------
# Add Report
elif choice == "Add Report":
    st.subheader("Add Appointment Report")
    appt_id = st.text_input("Appointment ID")
    report_date = st.date_input("Report Date")
    content = st.text_area("Report Content")
    if st.button("Save Report"):
        save_report([appt_id, str(report_date), content])
        st.success("Report saved.")

# --------------------------------------------
# Logout
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

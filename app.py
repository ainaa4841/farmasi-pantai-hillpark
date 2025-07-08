
import streamlit as st
from auth import register_user, login_user, check_email_exists, check_password_complexity
from google_sheets import (
    save_customer, save_appointment, save_file_metadata,
    upload_to_drive, get_appointments, get_pharmacist_schedule,
    update_schedule, update_appointment_status, get_all_customers)
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import pandas as pd

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
        menu = ["Book Appointment", "My Appointments", "Logout"]
    elif st.session_state.user_role == 'Pharmacist':
        menu = [ "Manage Schedule", "Logout"]

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
        customer_id = save_customer([username, password, full_name, email, phone, ""])
        st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

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

            # ✅ Add this part to fix the error:
            if role == "Customer":
                from auth import get_customer_id
                st.session_state.customer_id = get_customer_id(username)

            st.rerun()
        else:
            st.error("Invalid credentials!")

        

elif choice == "Book Appointment":
    st.subheader("Book an Appointment")

    # Load available pharmacist schedule
    available_schedule = get_pharmacist_schedule()
    available_dates = sorted(list(set([slot['Date'] for slot in available_schedule])))

    if not available_schedule:
        st.warning("No available slots. Please try again later.")
    else:
        selected_date = st.selectbox("Select Date", available_dates)
        available_times = [slot['Time'] for slot in available_schedule if slot['Date'] == selected_date]
        selected_time = st.selectbox("Select Time Slot", available_times)

        uploaded_file = st.file_uploader("Upload Referral Letter (PDF, Image, etc.)")

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload a referral letter.")
            else:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")

                
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                file_link = f"Stored locally: uploads/{uploaded_file.name}"  # Optional: just a text note
                save_file_metadata([st.session_state.user_username, uploaded_file.name, file_link])

                # Save file and appointment data
                from google_sheets import update_customer_referral_letter
                update_customer_referral_letter(st.session_state.user_username, file_link)

                st.write("Booking for Customer ID:", st.session_state.customer_id)

                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation"
                ])

                st.success(f"Appointment booked on {selected_date} at {selected_time}. Status: Pending Confirmation.")
                st.write("All Appointments Raw:", appointments)




elif choice == "My Appointments":
    st.subheader("📋 My Appointments")

    appointments = get_appointments()
    my_appointments = [
        appt for appt in appointments
        if str(appt['customerID']) == str(st.session_state.customer_id)
    ]

    if not my_appointments:
        st.info("No appointments found.")
    else:
        # Show as interactive AgGrid
        df = pd.DataFrame(my_appointments)
        df_display = df[["appointmentID", "Date", "Time", "Status"]]
        df_display.columns = ["Appointment ID", "Date", "Time", "Status"]

        gb = GridOptionsBuilder.from_dataframe(df_display)
        gb.configure_selection("single", use_checkbox=True)
        gb.configure_pagination(enabled=True)
        grid_options = gb.build()

        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            height=300,
            fit_columns_on_grid_load=True
        )

        selected = grid_response['selected_rows']

        if selected:
            selected_appt = selected[0]
            st.markdown("### 🔧 Manage Appointment")
            st.write(f"**Appointment ID:** {selected_appt['Appointment ID']}")
            st.write(f"**Date:** {selected_appt['Date']}")
            st.write(f"**Time:** {selected_appt['Time']}")
            st.write(f"**Status:** {selected_appt['Status']}")

            # 🔄 Get available schedule from Google Sheets
            schedule = get_pharmacist_schedule()
            available_dates = sorted(list(set([s["Date"] for s in schedule])))

            if not schedule:
                st.warning("No available slots found. Please contact the pharmacy.")
            else:
                new_date = st.selectbox("New Date", available_dates)
                available_times = [s["Time"] for s in schedule if s["Date"] == new_date]
                new_time = st.selectbox("New Time", available_times)

                if st.button("🔁 Reschedule"):
                    update_appointment_status(
                        appointment_id=selected_appt["Appointment ID"],
                        new_status="Rescheduled",
                        new_date=str(new_date),
                        new_time=new_time
                    )
                    st.success("Appointment rescheduled! Status: Pending Confirmation.")
                    st.rerun()
                if st.button("❌ Cancel Appointment"):
                    update_appointment_status(
                        appointment_id=selected_appt["Appointment ID"],
                        new_status="Cancelled"
                    )
                    st.success("Appointment cancelled successfully.")
                    st.rerun()



elif choice == "Manage Schedule":
    st.subheader("Pharmacist: Manage Appointments & Availability")

    # View all current booked appointments
    st.markdown("### 📋 Current Booked Appointments")
    appointments = get_appointments()
    customers = {c['customerID']: c for c in get_all_customers()}

    if not appointments:
        st.info("No appointments booked yet.")
    else:
        for idx, appt in enumerate(appointments):
            cust = customers.get(str(appt['customerID']), {})
            st.write(f"**Appointment ID:** {appt['appointmentID']}")
            st.write(f"👤 **Customer:** {cust.get('Full Name', 'Unknown')} | 📧 Email: {cust.get('Email', 'N/A')} | 📱 Phone: {cust.get('Phone Number', 'N/A')}")
            st.write(f"📅 **Date:** {appt['Date']} | 🕒 **Time:** {appt['Time']}")
            st.write(f"📌 **Status:** {appt['Status']}")

            # Dropdown to change status
            new_status = st.selectbox("Update Status", ["Pending Confirmation", "Confirmed", "Cancelled"],
                                      index=["Pending Confirmation", "Confirmed", "Cancelled"].index(appt["Status"]),
                                      key=f"status_{idx}")
            if st.button("Update", key=f"update_{idx}"):
                update_appointment_status(appt['appointmentID'], new_status)
                st.success(f"✅ Updated appointment {appt['appointmentID']} to {new_status}")
                st.rerun()

            st.markdown("---")

    # Section to Add New Available Slots
    st.markdown("### ➕ Add New Available Slot")
    new_date = st.date_input("Available Date")
    new_time = st.selectbox("Available Time", ["9:00AM", "11:00AM", "2:00PM", "4:00PM"])
    existing_schedule = get_pharmacist_schedule()
    is_overlap = any(slot["Date"] == str(new_date) and slot["Time"] == new_time for slot in existing_schedule)

    if st.button("Add Slot"):
        if is_overlap:
            st.warning(f"⚠️ Slot {new_date} at {new_time} already exists.")
        else:
            update_schedule(str(new_date), new_time)
            st.success(f"✅ Slot {new_date} at {new_time} added.")
            st.rerun()

    # 📅 Display current availability in calendar-style layout
    from collections import defaultdict

    st.markdown("### 📅 Pharmacist Availability Calendar")

    if existing_schedule:
        grouped = defaultdict(list)
        for slot in existing_schedule:
            grouped[slot["Date"]].append(slot["Time"])

        for date, times in grouped.items():
            st.markdown(f"**🗓 {date}**")
            st.write("🕒 " + ", ".join(sorted(times)))
    else:
        st.info("No available schedule slots found.")

elif choice == "Add Report":
    st.subheader("Add Appointment Report")
    appointment_id = st.text_input("Appointment ID")
    report_date = st.date_input("Report Date")
    report_content = st.text_area("Report Content")

    if st.button("Save Report"):
        if not appointment_id or not report_content:
            st.error("Please fill in all fields.")
        else:
            from google_sheets import save_report
            save_report([appointment_id, str(report_date), report_content])
            st.success("Report saved successfully.")




elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.user_role = ''
    st.rerun()

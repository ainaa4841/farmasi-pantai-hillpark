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

st.title("Farmasi Pantai Hillpark Appointment System")

# Session defaults
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_username = ''
    st.session_state.user_email = ''
    st.session_state.customer_id = ''

menu = ["Login", "Register"]
if st.session_state.logged_in:
    if st.session_state.user_username in ["pharma01"]:  
        menu = ["Manage Appointments", "Add Slot Availability","Available Slots", "Add Report", "Logout"]
    else:
        menu = ["Book Appointment", "My Appointments", "Logout"]

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
            customer_id = save_customer([username, password, full_name, email, phone, ""])
            st.success(f"Registration successful! Your customer ID is {customer_id}. Please log in.")

# --------------------------------------------
# Login
if choice == "Login":
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        email = login_user(username, password)
        if email:
            st.session_state.logged_in = True
            st.session_state.user_username = username
            st.session_state.user_email = email
            if username in ["pharma01"]:  # Example username for Pharmacist
                st.session_state.user_role = 'Pharmacist'
            else:
                st.session_state.user_role = 'Customer'
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
        available_dates = sorted(set(slot["availableDate"] for slot in available_schedule))
        selected_date = st.selectbox("Select Date", available_dates)
        available_times = [slot["availableTimeslot"] for slot in available_schedule if slot["availableDate"] == selected_date]
        selected_time = st.selectbox("Select Time Slot", available_times)
        uploaded_file = st.file_uploader("Upload Referral Letter")

        if st.button("Book Appointment"):
            if not uploaded_file:
                st.error("Please upload a referral letter.")
            else:
                if not os.path.exists("uploads"):
                    os.makedirs("uploads")

                # Save the uploaded file locally
                file_path = f"uploads/{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Save appointment with referral path
                save_appointment([
                    st.session_state.customer_id,
                    selected_date,
                    selected_time,
                    "Pending Confirmation"
                ], referral_path=file_path)

                st.success(f"Appointment booked on {selected_date} at {selected_time}.")
# --------------------------------------------
# My Appointments
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
        active_appts = [appt for appt in my_appointments if appt['appointmentStatus'] in ["Pending Confirmation", "Confirmed", "Rescheduled"]]
        past_appts = [appt for appt in my_appointments if appt['appointmentStatus'] in ["Cancelled", "Completed"]]

        # --------------------
        # Section 1: Active
        st.markdown("### 🗓️ Upcoming Appointments")
        for idx, appt in enumerate(active_appts):
            cols = st.columns([2, 2, 2, 2, 2])
            cols[0].write(f"📅 **{appt['appointmentDate']}**")
            cols[1].write(f"🕒 **{appt['appointmentTime']}**")
            cols[2].write(f"📌 **{appt['appointmentStatus']}**")

            # RESCHEDULE BUTTON
            if cols[3].button("Reschedule", key=f"reschedule_{idx}"):
                with st.form(f"reschedule_form_{idx}"):
                    st.subheader(f"Reschedule Slot for {appt['appointmentDate']} {appt['appointmentTime']}")
                    schedule = get_pharmacist_schedule()
                    booked = [(a['appointmentDate'], a['appointmentTime']) for a in get_appointments()]
                    available_slots = [
                        s for s in schedule if (s['availableDate'], s['availableTimeslot']) not in booked
                    ]

                    dates = sorted(list(set([s['availableDate'] for s in available_slots])))
                    new_date = st.selectbox("New Date", dates)
                    new_times = [s['availableTimeslot'] for s in available_slots if s['availableDate'] == new_date]
                    new_time = st.selectbox("New Time", new_times)

                    submitted = st.form_submit_button("Confirm Reschedule")
                    if submitted:
                        update_appointment_status(
                            appointment_id=appt["appointmentID"],
                            new_status="Pending Confirmation",
                            new_date=new_date,
                            new_time=new_time
                        )
                        st.success("Rescheduled successfully!")
                        st.rerun()

            # CANCEL BUTTON
            if cols[4].button("❌ Cancel", key=f"cancel_{idx}"):
                update_appointment_status(
                    appointment_id=appt["appointmentID"],
                    new_status="Cancelled"
                )
                st.success("❌ Appointment cancelled.")
                st.rerun()

        # --------------------
        # Section 2: Past Appointments
        if past_appts:
            st.markdown("---")
            st.markdown("### 📋 Past Appointments (Cancelled or Completed)")

            header = st.columns([2, 2, 2])
            header[0].markdown("**📅 Date**")
            header[1].markdown("**🕒 Time**")
            header[2].markdown("**📌 Status**")

            for appt in past_appts:
                row = st.columns([2, 2, 2])
                row[0].write(f"{appt['appointmentDate']}")
                row[1].write(f"{appt['appointmentTime']}")
                row[2].write(f"{appt['appointmentStatus']}")

# --------------------------------------------
# Manage Appointment
elif choice == "Manage Appointments":
    st.subheader("🗂️ Manage Appointments")

    appointments = get_appointments()
    customers = {str(c["customerID"]): c for c in get_all_customers()}

    if not appointments:
        st.info("No appointments found.")
    else:
        # 🔍 Filter options
        customer_ids = sorted(set(str(a["customerID"]) for a in appointments))
        statuses = ["All", "Pending Confirmation", "Confirmed", "Cancelled", "Completed"]

        selected_customer = st.selectbox("🔎 Filter by Customer ID", ["All"] + customer_ids)
        selected_status = st.selectbox("📌 Filter by Status", statuses)

        # Apply filters
        filtered_appointments = appointments
        if selected_customer != "All":
            filtered_appointments = [a for a in filtered_appointments if str(a["customerID"]) == selected_customer]
        if selected_status != "All":
            filtered_appointments = [a for a in filtered_appointments if a["appointmentStatus"] == selected_status]

        st.markdown(f"### Showing {len(filtered_appointments)} appointments")

        for idx, appt in enumerate(filtered_appointments):
            cust = customers.get(str(appt["customerID"]), {})
            full_name = cust.get("customerName", "Unknown")
            email = cust.get("customerEmail", "N/A")
            phone = cust.get("customerNumber", "N/A")
            referral_path = appt.get("appointmentReferralLetter", "")

            st.markdown(f"""
                <div style="border: 1px solid #ccc; padding: 0.1px; border-radius: 6px; margin-bottom: 10px; background-color: #f9f9f9;">
            """, unsafe_allow_html=True)

            cols = st.columns([1, 1, 2, 2, 1.5, 1.5, 2, 2])
            cols[0].write(f"🆔 {appt['appointmentID']}")
            cols[1].write(f"🧾 CID: {appt['customerID']}")
            cols[2].write(f"👤 {full_name}")
            cols[3].write(f"📧 {email}\n\n📱 {phone}")
            cols[4].write(f"📅 {appt['appointmentDate']}")
            cols[5].write(f"🕒 {appt['appointmentTime']}")

            # 📄 Referral Letter
            if referral_path and os.path.exists(referral_path):
                with open(referral_path, "rb") as f:
                    cols[6].download_button(
                        label="📄 Download",
                        data=f,
                        file_name=os.path.basename(referral_path),
                        mime="application/octet-stream",
                        key=f"download_{idx}"
                    )
            else:
                cols[6].write("—")

            # ✅ Update status
            new_status = cols[7].selectbox(
                "appointmentStatus",
                ["Pending Confirmation", "Confirmed", "Cancelled", "Completed"],
                index=["Pending Confirmation", "Confirmed", "Cancelled", "Completed"].index(appt["appointmentStatus"]),
                key=f"status_{idx}"
            )

            if st.button("Update", key=f"update_{idx}"):
                update_appointment_status(appt["appointmentID"], new_status)
                st.success(f"✅ Appointment {appt['appointmentID']} updated.")
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# --------------------------------------------
# Update Slot Availability
elif choice == "Add Slot Availability":
    st.subheader("➕ Add New Slot")
    slot_date = st.date_input("Available Date")
    slot_time = st.selectbox("Available Time", ["8:00AM-9:00AM","9:00AM-10:00AM", "10:00AM-11:00AM", "11:00AM-12:00PM","2:00PM-3:00PM", "3:00PM-4:00PM", "4:00PM-5:00PM"])
    schedule = get_pharmacist_schedule()
    if st.button("Add Slot"):
        if any(s["availableDate"] == str(slot_date) and s["availableTimeslot"] == slot_time for s in schedule):
            st.warning("Slot already exists.")
        else:
            update_schedule(str(slot_date), slot_time)
            st.success("Slot added!")
            st.rerun()

elif choice == "Available Slots":
    st.subheader("📌 Available Slots")

    schedule = get_pharmacist_schedule()
    if not schedule:
        st.info("No slots available.")
    else:
        df_slots = pd.DataFrame(schedule)

        for idx, row in df_slots.iterrows():
            cols = st.columns([3, 3, 1])
            cols[0].write(f"📅 Date: **{row['availableDate']}**")
            cols[1].write(f"🕒 Time: **{row['availableTimeslot']}**")
            if cols[2].button("❌ Delete", key=f"delete_slot_{idx}"):
                from google_sheets import remove_schedule_slot
                remove_schedule_slot(row['availableDate'], row['availableTimeslot'])
                st.success(f"Slot on {row['availableDate']} at {row['availableTimeslot']} deleted.")
                st.rerun()




# --------------------------------------------
# Add Report
elif choice == "Add Report":
    st.subheader("📝 Add Appointment Report")

    # --- Report Submission ---
    customer_id = st.text_input("Customer ID")
    appt_id = st.text_input("Appointment ID")
    report_date = st.date_input("Report Date")
    content = st.text_area("Report Content")

    if st.button("Save Report"):
        if not all([customer_id, appt_id, content]):
            st.error("Please complete all fields.")
        else:
            # Generate numeric reportID with no prefix
            reports = get_all_reports()
            existing_ids = [
            int(r.get("reportID", 0)) for r in reports
            if str(r.get("reportID", "")).isdigit()
        ]
            next_id = max(existing_ids, default=0) + 1
            report_id = next_id

            # Save to sheet
            save_report([report_id, customer_id, appt_id, str(report_date), content])
            st.success("✅ Report saved.")

    # --- Interactive Report Viewer ---
    st.markdown("### 📂 View Submitted Reports")

    reports = get_all_reports()

    # Defensive check for empty or malformed data
    if not reports or not isinstance(reports, list) or not isinstance(reports[0], dict):
        st.warning("⚠️ No valid reports found or data is not structured correctly.")
    else:
        # Extract dropdown options safely
        customer_ids = sorted(set(str(r.get("customerID", "")) for r in reports if "customerID" in r))
        appointment_ids = sorted(set(str(r.get("appointmentID", "")) for r in reports if "appointmentID" in r))

        selected_cust_id = st.selectbox("Filter by Customer ID", ["All"] + customer_ids)
        selected_appt_id = st.selectbox("Filter by Appointment ID", ["All"] + appointment_ids)

        # Apply filters
        filtered_reports = reports
        if selected_cust_id != "All":
            filtered_reports = [r for r in filtered_reports if str(r.get("customerID", "")) == selected_cust_id]
        if selected_appt_id != "All":
            filtered_reports = [r for r in filtered_reports if str(r.get("appointmentID", "")) == selected_appt_id]

        # Display
        if not filtered_reports:
            st.info("No matching reports found.")
        else:
            for rep in filtered_reports:
                st.markdown(f"""
                    <div style="
                        border: 1px solid rgba(120, 120, 120, 0.3);
                        padding: 10px;
                        margin-bottom: 10px;
                        border-radius: 8px;
                        background-color: rgba(255, 255, 255, 0.05);
                        backdrop-filter: blur(2px);
                        color: inherit;
                    ">
                        <strong>📋 Report ID:</strong> {rep.get('reportID', '')}<br>
                        <strong>👤 Customer ID:</strong> {rep.get('customerID', '')}<br>
                        <strong>📎 Appointment ID:</strong> {rep.get('appointmentID', '')}<br>
                        <strong>📅 Date:</strong> {rep.get('reportDate', '')}<br>
                        <strong>📝 Content:</strong><br>
                        <div style="margin-left: 15px;">{rep.get('reportContent', '')}</div>
                    </div>
                """, unsafe_allow_html=True)

# --------------------------------------------
# Logout
elif choice == "Logout":
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

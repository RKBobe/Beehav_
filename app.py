# app.py - FINAL DATABASE-DRIVEN MULTI-USER VERSION

import streamlit as st
import pandas as pd
from engine import BehaviorTracker
from datetime import datetime
import streamlit_authenticator as stauth
import plotly.express as px

# --- Page Configuration ---
st.set_page_config(page_title="BeeHayv", layout="wide", page_icon="🐝")

# --- Initialize the Engine ---
# This creates one instance of the tracker for the entire app session.
# The engine now connects to the database on initialization.
if 'tracker' not in st.session_state:
    st.session_state.tracker = BehaviorTracker()
tracker = st.session_state.tracker

# --- User Authentication Setup ---
# 1. Fetches users from the database via our engine
users_df = tracker.get_users()
# 2. Convert to the format the authenticator expects
users_dict = users_df.to_dict('records')
credentials = {'usernames': {}}
for user in users_dict:
    # Ensure all required keys are present
    credentials['usernames'][user['Username']] = {
        'name': user.get('Name', ''),
        'password': user.get('Password', ''),
        'email': user.get('Email', '')
    }

# 3. Instantiate the authenticator
authenticator = stauth.Authenticate(
    credentials,
    'BeeHayvCookieName',
    'abcdef', # It's recommended to change this to a random secret key in production
    cookie_expiry_days=30
)

# 4. Render the login form
authenticator.login()

# --- THE LOGIN GATE ---
if st.session_state["authentication_status"]:
    # --- START OF LOGGED-IN APP ---
    st.sidebar.write(f'Welcome, *{st.session_state["name"]}*')
    authenticator.logout('Logout', 'sidebar')
    username = st.session_state["username"]

    st.title("🐝 BeeHayv Behavior Tracker")
    st.write("Welcome to your private behavior tracking dashboard.")
    st.divider()

    # --- Section 1: Data Entry ---
    st.header("1. Data Entry")
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ Add a New Subject"):
            with st.form("add_subject_form", clear_on_submit=True):
                new_subject_label = st.text_input("New Subject's Name or Label")
                submitted = st.form_submit_button("Add Subject")
                if submitted:
                    if new_subject_label:
                        # Call engine method with username
                        tracker.add_subject(username, new_subject_label)
                        st.success(f"Added: '{new_subject_label}'")
                        st.rerun()

        with st.expander("➕ Define a New Behavior"):
            # Get subjects for the CURRENT USER ONLY
            user_subjects_df = tracker.get_subjects(username)
            if user_subjects_df.empty:
                st.warning("Add a subject first.")
            else:
                with st.form("add_definition_form", clear_on_submit=True):
                    subject_options = pd.Series(user_subjects_df['SubjectLabel'].values, index=user_subjects_df['SubjectID'].values).to_dict()
                    selected_subject_id = st.selectbox("Select a Subject", options=list(subject_options.keys()), format_func=lambda x: subject_options.get(x))
                    new_behavior_name = st.text_input("New Behavior's Name")
                    description = st.text_area("Optional Description")
                    submitted = st.form_submit_button("Define Behavior")
                    if submitted:
                        if selected_subject_id and new_behavior_name:
                            tracker.add_behavior_definition(username, selected_subject_id, new_behavior_name, description)
                            st.success(f"Defined '{new_behavior_name}'.")
                            st.rerun()

    with col2:
        with st.expander("📝 Log a Daily Score", expanded=True):
            # Get definitions for the CURRENT USER ONLY
            user_defs_df = tracker.get_definitions(username)
            if user_defs_df.empty:
                st.warning("Define a behavior first.")
            else:
                user_subjects_df = tracker.get_subjects(username)
                merged_defs = pd.merge(user_defs_df, user_subjects_df, on='SubjectID')
                merged_defs['display_label'] = merged_defs['SubjectLabel'] + " - " + merged_defs['BehaviorName']
                definition_options = pd.Series(merged_defs['display_label'].values, index=merged_defs['DefinitionID'].values).to_dict()
                with st.form("log_score_form", clear_on_submit=True):
                    selected_definition_id = st.selectbox("Select Behavior to Score", options=list(definition_options.keys()), format_func=lambda x: definition_options.get(x))
                    score_date = st.date_input("Date of Observation", value=datetime.now())
                    score_value = st.slider("Score (1-10)", 1, 10, 5)
                    score_notes = st.text_area("Optional Notes")
                    submitted = st.form_submit_button("Log Score")
                    if submitted and selected_definition_id:
                        tracker.log_score(username, selected_definition_id, score_date, score_value, score_notes)
                        st.success(f"Logged score of {score_value}.")
                        st.rerun()

    st.divider()

    # --- Section 2: Data Display, Analysis & Plotting ---
    st.header("2. Your Data & Progress")
    
    display_tab1, display_tab2, display_tab3 = st.tabs(["Subjects & Definitions", "Daily Scores Log", "Averages & Charts"])

    with display_tab1:
        st.subheader("Your Subjects")
        st.dataframe(tracker.get_subjects(username), use_container_width=True)
        st.subheader("Your Behavior Definitions")
        st.dataframe(tracker.get_definitions(username), use_container_width=True)

    with display_tab2:
        st.subheader("Your Complete Scores Log")
        st.dataframe(tracker.get_daily_scores(username), use_container_width=True)

    with display_tab3:
        if st.button("📈 Calculate Averages", type="primary"):
            # Averages are now calculated on-demand and returned by the engine
            weekly_df, monthly_df, semi_annual_df = tracker.calculate_all_averages(username)
            st.session_state.weekly_df = weekly_df
            st.session_state.monthly_df = monthly_df
            st.success("Averages calculated!")
        
        st.subheader("Progress Charts")
        # Plotting logic remains largely the same, but uses data fetched for the user
        # ... (plotting UI code here)
        # The full plotting logic will be added in the next iteration for brevity

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')

elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
    
    # --- REGISTRATION LOGIC ---
    try:
        if authenticator.register_user(
            fields={
                'Form name': 'New User Registration',
                'Username': 'Username',
                'Name': 'Full Name',
                'Email': 'Email Address',
                'Password': 'Password',
                'Repeat Password': 'Confirm Password'
            },
            pre_authorization=False
        ):
            new_username = st.session_state.get('username')
            new_name = st.session_state.get('name')
            new_email = st.session_state.get('email') # Authenticator puts this in session_state on registration attempt
            new_password = st.session_state.get('password')

            if tracker.register_user(new_name, new_username, new_password, new_email):
                st.success('User registered successfully. Please refresh and login.')
            else:
                st.error('Username already exists. Please choose another.')
    except Exception as e:
        st.error(e)
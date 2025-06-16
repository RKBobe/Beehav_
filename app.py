# app.py - FINAL GOOGLE SHEETS VERSION

import streamlit as st
import pandas as pd
from engine import BehaviorTracker
from datetime import datetime
import streamlit_authenticator as stauth
import plotly.express as px

st.set_page_config(page_title="BeeHayv", layout="wide", page_icon="🐝")

# Initialize the Engine. It will connect to Google Sheets using secrets.
if 'tracker' not in st.session_state:
    st.session_state.tracker = BehaviorTracker()
tracker = st.session_state.tracker

# --- User Authentication Setup ---
# Fetches users from the Google Sheet via our engine
users_df = tracker.get_users().dropna(subset=['Username'])
users_dict = users_df.to_dict('records')
credentials = {'usernames': {}}
for user in users_dict:
    if user.get("Username"):
        credentials['usernames'][user['Username']] = {
            'name': user.get('Name', ''),
            'password': user.get('Password', ''),
            'email': user.get('Email', '')
        }

# Instantiate the authenticator
authenticator = stauth.Authenticate(
    credentials,
    'BeeHayvCookieName',
    'abcdefg', # Change this to a random secret key
    cookie_expiry_days=30
)

# Render the login form
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

    st.header("1. Data Entry")
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("➕ Add a New Subject"):
            with st.form("add_subject_form", clear_on_submit=True):
                new_subject_label = st.text_input("New Subject's Name or Label")
                submitted = st.form_submit_button("Add Subject")
                if submitted and new_subject_label:
                    tracker.add_subject(username, new_subject_label)
                    st.success(f"Added: '{new_subject_label}'")
                    st.rerun()

        with st.expander("➕ Define a New Behavior"):
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
                    if submitted and selected_subject_id and new_behavior_name:
                        tracker.add_behavior_definition(username, selected_subject_id, new_behavior_name, description)
                        st.success(f"Defined '{new_behavior_name}'.")
                        st.rerun()
    with col2:
        with st.expander("📝 Log a Daily Score", expanded=True):
            user_defs_df = tracker.get_definitions(username)
            if user_defs_df.empty:
                st.warning("Define a behavior first.")
            else:
                user_subjects_df = tracker.get_subjects(username)
                if not user_subjects_df.empty:
                    merged_defs = pd.merge(user_defs_df, user_subjects_df, on='SubjectID')
                    merged_defs['display_label'] = merged_defs['SubjectLabel'] + " - " + merged_defs['BehaviorName']
                    definition_options = pd.Series(merged_defs['display_label'].values, index=merged_defs['DefinitionID'].values).to_dict()
                    with st.form("log_score__form", clear_on_submit=True):
                        selected_definition_id = st.selectbox("Select Behavior to Score", options=list(definition_options.keys()), format_func=lambda x: definition_options.get(x))
                        score_date = st.date_input("Date of Observation", value=datetime.now())
                        score_value = st.slider("Score (1-10)", 1, 10, 5)
                        score_notes = st.text_area("Optional Notes")
                        submitted = st.form_submit_button("Log Score")
                        if submitted and selected_definition_id:
                            tracker.log_score(username, selected_definition_id, score_date, score_value, score_notes)
                            st.success(f"Logged score of {score_value}.")
                            st.rerun()

    # --- Analysis section would go here ---

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')

elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password. Contact an administrator to create an account.')
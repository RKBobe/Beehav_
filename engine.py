# engine.py - FINAL GOOGLE SHEETS VERSION

import pandas as pd
from datetime import datetime
import streamlit as st
import bcrypt
from streamlit_gsheets import GSheetsConnection

class BehaviorTracker:
    def __init__(self):
        """Initializes the engine by creating a connection to Google Sheets."""
        print("--- Instantiating Google Sheets-Driven BehaviorTracker Engine ---")
        self.conn = st.connection("gsheets", type=GSheetsConnection)
        print("--- Engine is ready and connected to Google Sheets. ---")

    def _get_next_id(self, df, id_column):
        """Helper function to get the next available unique ID."""
        if df.empty or df[id_column].dropna().empty: return 1
        return int(df[id_column].max()) + 1

    # --- USER MANAGEMENT ---
    def get_users(self):
        """Fetches all users from the 'users' worksheet."""
        return self.conn.read(worksheet="users", use_headers=True, ttl=5)

    # --- DATA READING METHODS ---
    def get_subjects(self, username):
        """Fetches all subjects for a specific user."""
        all_subjects = self.conn.read(worksheet="subjects", use_headers=True, ttl=5)
        if not all_subjects.empty and 'Username' in all_subjects.columns:
            # Filter rows where Username is not NaN before comparison
            return all_subjects[all_subjects['Username'].fillna('').str.lower() == username.lower()]
        return pd.DataFrame()

    def get_definitions(self, username):
        """Fetches all definitions for a specific user."""
        all_definitions = self.conn.read(worksheet="definitions", use_headers=True, ttl=5)
        if not all_definitions.empty and 'Username' in all_definitions.columns:
            return all_definitions[all_definitions['Username'].fillna('').str.lower() == username.lower()]
        return pd.DataFrame()

    def get_daily_scores(self, username):
        """Fetches all daily scores for a specific user."""
        all_scores = self.conn.read(worksheet="daily_scores", use_headers=True, ttl=5)
        if not all_scores.empty and 'Username' in all_scores.columns:
            return all_scores[all_scores['Username'].fillna('').str.lower() == username.lower()]
        return pd.DataFrame()

    # --- DATA WRITING METHODS ---
    def add_subject(self, username, subject_label):
        """Appends a new subject for a user to the 'subjects' worksheet."""
        all_subjects = self.conn.read(worksheet="subjects", use_headers=True, ttl=0)
        new_id = self._get_next_id(all_subjects, 'SubjectID')
        new_subject = pd.DataFrame([{'SubjectID': new_id, 'Username': username, 'SubjectLabel': subject_label.strip(), 'DateCreated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}])
        self.conn.append(worksheet="subjects", data=new_subject)

    def add_behavior_definition(self, username, subject_id, behavior_name, description=""):
        all_definitions = self.conn.read(worksheet="definitions", use_headers=True, ttl=0)
        new_id = self._get_next_id(all_definitions, 'DefinitionID')
        new_definition = pd.DataFrame([{'DefinitionID': new_id, 'SubjectID': subject_id, 'Username': username, 'BehaviorName': behavior_name.strip(), 'Description': description.strip()}])
        self.conn.append(worksheet="definitions", data=new_definition)

    def log_score(self, username, definition_id, date, score, notes=""):
        all_scores = self.conn.read(worksheet="daily_scores", use_headers=True, ttl=0)
        new_id = self._get_next_id(all_scores, 'LogID')
        new_log_entry = pd.DataFrame([{'LogID': new_id, 'DefinitionID': definition_id, 'Username': username, 'Date': pd.to_datetime(date).strftime("%Y-%m-%d"), 'Score': score, 'Notes': notes.strip()}])
        self.conn.append(worksheet="daily_scores", data=new_log_entry)
        
    def calculate_all_averages(self, username):
        scores_df = self.get_daily_scores(username)
        if scores_df.empty or scores_df['Score'].isnull().all():
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        scores_df['Date'] = pd.to_datetime(scores_df['Date'])
        scores_df['Score'] = pd.to_numeric(scores_df['Score'])
        scores_df['Year'] = scores_df['Date'].dt.isocalendar().year
        scores_df['WeekOfYear'] = scores_df['Date'].dt.isocalendar().week
        weekly_avg = scores_df.groupby(['DefinitionID', 'Year', 'WeekOfYear'])['Score'].agg(['mean', 'count']).reset_index()
        weekly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        scores_df['Month'] = scores_df['Date'].dt.month
        monthly_avg = scores_df.groupby(['DefinitionID', 'Year', 'Month'])['Score'].agg(['mean', 'count']).reset_index()
        monthly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        return weekly_avg, monthly_avg, pd.DataFrame() # Removed semi-annual for simplicity
# engine.py - FINAL DATABASE-DRIVEN VERSION

import os
import pandas as pd
from datetime import datetime
import streamlit as st # To access secrets
from sqlalchemy import create_engine, text
import streamlit_authenticator as stauth

class BehaviorTracker:
    def __init__(self):
        """
        Initializes the BehaviorTracker engine by connecting to the Turso cloud database.
        """
        print("--- Instantiating Database-Driven BehaviorTracker Engine ---")
        try:
            # --- 1. ESTABLISH DATABASE CONNECTION ---
            # Build the full database URL from Streamlit secrets
            db_url = st.secrets["TURSO_DATABASE_URL"]
            auth_token = st.secrets["TURSO_AUTH_TOKEN"]
            full_db_url = f"sqlite+{db_url}/?authToken={auth_token}&secure=true"

            # Create a SQLAlchemy engine. This object manages connections to the DB.
            self.engine = create_engine(full_db_url, connect_args={'check_same_thread': False}, echo=False)
            
            # --- 2. ENSURE DATABASE TABLES EXIST ---
            self._initialize_database()

            print("--- Engine is ready and connected to Turso DB. ---")

        except Exception as e:
            print(f"🔥 DATABASE CONNECTION FAILED: {e}")
            # If connection fails, stop the app with a helpful message.
            st.error(f"Database connection failed. Please check your Turso credentials in Streamlit Secrets. Error: {e}")
            st.stop()
    
    def _initialize_database(self):
        """
        Ensures all necessary tables exist in the database.
        Uses "CREATE TABLE IF NOT EXISTS" to be safe to run every time.
        """
        # SQL statements to create our tables
        # Using TEXT for password to store the long hash.
        # Using PRIMARY KEY and AUTOINCREMENT for IDs where appropriate.
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            Username TEXT PRIMARY KEY,
            Name TEXT,
            Password TEXT,
            Email TEXT
        );
        """
        create_subjects_table = """
        CREATE TABLE IF NOT EXISTS subjects (
            SubjectID INTEGER PRIMARY KEY,
            Username TEXT,
            SubjectLabel TEXT,
            DateCreated TEXT,
            FOREIGN KEY(Username) REFERENCES users(Username)
        );
        """
        create_definitions_table = """
        CREATE TABLE IF NOT EXISTS definitions (
            DefinitionID INTEGER PRIMARY KEY,
            SubjectID INTEGER,
            Username TEXT,
            BehaviorName TEXT,
            Description TEXT,
            FOREIGN KEY(SubjectID) REFERENCES subjects(SubjectID),
            FOREIGN KEY(Username) REFERENCES users(Username)
        );
        """
        create_scores_table = """
        CREATE TABLE IF NOT EXISTS daily_scores (
            LogID INTEGER PRIMARY KEY,
            DefinitionID INTEGER,
            Username TEXT,
            Date TEXT,
            Score INTEGER,
            Notes TEXT,
            FOREIGN KEY(DefinitionID) REFERENCES definitions(DefinitionID),
            FOREIGN KEY(Username) REFERENCES users(Username)
        );
        """
        # Execute all table creation statements
        with self.engine.connect() as connection:
            connection.execute(text(create_users_table))
            connection.execute(text(create_subjects_table))
            connection.execute(text(create_definitions_table))
            connection.execute(text(create_scores_table))
            connection.commit() # Commit the changes
        print("Database tables verified.")

    # --- USER MANAGEMENT ---
    def register_user(self, name, username, password, email):
        """Hashes password and INSERTS a new user into the database."""
        hashed_password = stauth.Hasher(passwords=[password]).generate()[0]
        sql = text("INSERT INTO users (Name, Username, Password, Email) VALUES (:name, :username, :password, :email)")
        params = {"name": name, "username": username, "password": hashed_password, "email": email}
        try:
            with self.engine.connect() as connection:
                connection.execute(sql, params)
                connection.commit()
            return True
        except Exception as e:
            print(f"Error registering user: {e}")
            return False

    # --- DATA READING METHODS ---
    def get_users(self):
        """Fetches all users to configure the authenticator."""
        return pd.read_sql("SELECT * FROM users", self.engine)

    def get_subjects(self, username):
        """Fetches all subjects for a specific user."""
        sql = text("SELECT * FROM subjects WHERE Username = :username")
        return pd.read_sql(sql, self.engine, params={"username": username})

    def get_definitions(self, username):
        """Fetches all definitions for a specific user."""
        sql = text("SELECT * FROM definitions WHERE Username = :username")
        return pd.read_sql(sql, self.engine, params={"username": username})
    
    def get_daily_scores(self, username):
        """Fetches all daily scores for a specific user."""
        sql = text("SELECT * FROM daily_scores WHERE Username = :username")
        return pd.read_sql(sql, self.engine, params={"username": username})

    # --- DATA WRITING METHODS ---
    def add_subject(self, username, subject_label):
        """INSERTS a new subject for a user into the database."""
        sql = text("INSERT INTO subjects (Username, SubjectLabel, DateCreated) VALUES (:username, :label, :date)")
        params = {
            "username": username,
            "label": subject_label.strip(),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with self.engine.connect() as connection:
            connection.execute(sql, params)
            connection.commit()

    def add_behavior_definition(self, username, subject_id, behavior_name, description=""):
        """INSERTS a new behavior definition for a user."""
        sql = text("INSERT INTO definitions (SubjectID, Username, BehaviorName, Description) VALUES (:sid, :user, :bname, :desc)")
        params = {
            "sid": subject_id, "user": username,
            "bname": behavior_name.strip(), "desc": description.strip()
        }
        with self.engine.connect() as connection:
            connection.execute(sql, params)
            connection.commit()

    def log_score(self, username, definition_id, date, score, notes=""):
        """INSERTS a new daily score for a user."""
        sql = text("INSERT INTO daily_scores (DefinitionID, Username, Date, Score, Notes) VALUES (:did, :user, :date, :score, :notes)")
        params = {
            "did": definition_id, "user": username,
            "date": pd.to_datetime(date).strftime("%Y-%m-%d"),
            "score": score, "notes": notes.strip()
        }
        with self.engine.connect() as connection:
            connection.execute(sql, params)
            connection.commit()

    # --- DATA PROCESSING ---
    def calculate_all_averages(self, username):
        """Fetches a user's scores and calculates averages in memory."""
        scores_df = self.get_daily_scores(username)
        if scores_df.empty:
            print("No daily scores for this user to calculate.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame() # Return empty dataframes

        scores_df['Date'] = pd.to_datetime(scores_df['Date'])
        scores_df['Year'] = scores_df['Date'].dt.isocalendar().year
        
        # Weekly
        scores_df['WeekOfYear'] = scores_df['Date'].dt.isocalendar().week
        weekly_avg = scores_df.groupby(['DefinitionID', 'Year', 'WeekOfYear'])['Score'].agg(['mean', 'count']).reset_index()
        weekly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        
        # Monthly
        scores_df['Month'] = scores_df['Date'].dt.month
        monthly_avg = scores_df.groupby(['DefinitionID', 'Year', 'Month'])['Score'].agg(['mean', 'count']).reset_index()
        monthly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)

        # Semi-Annual
        scores_df['Half'] = (scores_df['Date'].dt.month - 1) // 6 + 1
        semi_annual_avg = scores_df.groupby(['DefinitionID', 'Year', 'Half'])['Score'].agg(['mean', 'count']).reset_index()
        semi_annual_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)

        return weekly_avg, monthly_avg, semi_annual_avg
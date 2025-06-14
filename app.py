# app.py - FINAL SIMPLIFIED SINGLE-USER VERSION

import streamlit as st
import pandas as pd
from engine import BehaviorTracker
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="BeeHayv", layout="wide", page_icon="🐝")

if 'tracker' not in st.session_state:
    st.session_state.tracker = BehaviorTracker()
tracker = st.session_state.tracker

st.title("🐝 BeeHayv Behavior Tracker")
st.write("A tool for tracking behavioral data and visualizing progress over time.")
st.divider()

st.header("1. Data Entry")
col1, col2 = st.columns(2)

with col1:
    with st.expander("➕ Add a New Subject"):
        with st.form("add_subject_form", clear_on_submit=True):
            new_subject_label = st.text_input("New Subject's Name or Label")
            submitted = st.form_submit_button("Add Subject")
            if submitted:
                if new_subject_label:
                    tracker.add_subject(new_subject_label)
                    st.success(f"Added: '{new_subject_label}'")
                    st.rerun()
                else:
                    st.error("Subject label cannot be empty.")

    with st.expander("➕ Define a New Behavior"):
        subjects_df = tracker.dataframes['subjects']
        if subjects_df.empty:
            st.warning("Add a subject first.")
        else:
            with st.form("add_definition_form", clear_on_submit=True):
                subject_options = pd.Series(subjects_df['SubjectLabel'].values, index=subjects_df['SubjectID'].values).to_dict()
                selected_subject_id = st.selectbox("Select a Subject", options=list(subject_options.keys()), format_func=lambda x: subject_options[x])
                new_behavior_name = st.text_input("New Behavior's Name")
                description = st.text_area("Optional Description")
                submitted = st.form_submit_button("Define Behavior")
                if submitted:
                    if selected_subject_id and new_behavior_name:
                        tracker.add_behavior_definition(selected_subject_id, new_behavior_name, description)
                        st.success(f"Defined '{new_behavior_name}'.")
                        st.rerun()
                    else:
                        st.error("Select a subject and provide a name.")

with col2:
    with st.expander("📝 Log a Daily Score", expanded=True):
        defs_df = tracker.dataframes['definitions']
        if defs_df.empty:
            st.warning("Define a behavior first.")
        else:
            subjects_df = tracker.dataframes['subjects']
            merged_defs = pd.merge(defs_df, subjects_df, on='SubjectID')
            merged_defs['display_label'] = merged_defs['SubjectLabel'] + " - " + merged_defs['BehaviorName']
            definition_options = pd.Series(merged_defs['display_label'].values, index=merged_defs['DefinitionID'].values).to_dict()
            with st.form("log_score_form", clear_on_submit=True):
                selected_definition_id = st.selectbox("Select Behavior to Score", options=list(definition_options.keys()), format_func=lambda x: definition_options.get(x))
                score_date = st.date_input("Date of Observation", value=datetime.now())
                score_value = st.slider("Score (1-10)", 1, 10, 5)
                score_notes = st.text_area("Optional Notes")
                submitted = st.form_submit_button("Log Score")
                if submitted:
                    if selected_definition_id:
                        tracker.log_score(selected_definition_id, score_date, score_value, score_notes)
                        st.success(f"Logged score of {score_value}.")
                        st.rerun()
                    else:
                        st.warning("No behavior selected to score.")
st.divider()

st.header("2. Analysis & Plotting")
if st.button("📈 Calculate All Averages", type="primary"):
    tracker.calculate_all_averages()
    st.success("Averages have been calculated!")

st.subheader("Calculated Averages")
avg_tab1, avg_tab2, avg_tab3 = st.tabs(["Weekly", "Monthly", "Semi-Annual"])
with avg_tab1: st.dataframe(tracker.dataframes['weekly_averages'], use_container_width=True)
with avg_tab2: st.dataframe(tracker.dataframes['monthly_averages'], use_container_width=True)
with avg_tab3: st.dataframe(tracker.dataframes['semi_annual_averages'], use_container_width=True)

st.subheader("Progress Charts")
defs_df = tracker.dataframes['definitions']
if not defs_df.empty:
    plot_col1, plot_col2 = st.columns([1, 2])
    with plot_col1:
        subjects_df = tracker.dataframes['subjects']
        merged_defs = pd.merge(defs_df, subjects_df, on='SubjectID')
        merged_defs['display_label'] = merged_defs['SubjectLabel'] + " - " + merged_defs['BehaviorName']
        definition_options = pd.Series(merged_defs['display_label'].values, index=merged_defs['DefinitionID'].values).to_dict()
        
        if not definition_options:
            st.warning("No behaviors defined yet.")
        else:
            behavior_to_plot = st.selectbox("Select Behavior to Plot", options=list(definition_options.keys()), format_func=lambda x: definition_options.get(x))
            period_to_plot = st.radio("Select Period", ["Weekly", "Monthly"], horizontal=True)

    with plot_col2:
        if 'behavior_to_plot' in locals():
            if period_to_plot == "Weekly":
                avg_df = tracker.dataframes['weekly_averages']
                if not avg_df.empty:
                    avg_df['Time Period'] = avg_df['Year'].astype(str) + "-W" + avg_df['WeekOfYear'].astype(str)
                x_axis, y_axis = 'Time Period', 'AverageScore'
            else:
                avg_df = tracker.dataframes['monthly_averages']
                if not avg_df.empty:
                    avg_df['Time Period'] = pd.to_datetime(avg_df[['Year', 'Month']].assign(DAY=1)).dt.strftime('%Y-%b')
                x_axis, y_axis = 'Time Period', 'AverageScore'

            if not avg_df.empty:
                plot_data = avg_df[avg_df['DefinitionID'] == behavior_to_plot].sort_values(by='Time Period')
                if not plot_data.empty:
                    fig = px.line(plot_data, x=x_axis, y=y_axis, title=f"{period_to_plot} Progress for {definition_options.get(behavior_to_plot, 'N/A')}", markers=True)
                    fig.update_yaxes(range=[0, 11])
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No calculated averages to plot for this behavior yet.")
            else:
                st.info("Averages have not been calculated yet.")
else:
    st.info("Define a behavior to start plotting progress.")
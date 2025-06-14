# engine.py - FINAL SIMPLIFIED SINGLE-USER VERSION

import os
import pandas as pd
from datetime import datetime

DATA_PATH = "data"
DATABASE_SCHEMA = {
    'subjects': {
        'file': os.path.join(DATA_PATH, 'subjects.csv'),
        'cols': ['SubjectID', 'SubjectLabel', 'DateCreated']
    },
    'definitions': {
        'file': os.path.join(DATA_PATH, 'behavior_definitions.csv'),
        'cols': ['DefinitionID', 'SubjectID', 'BehaviorName', 'Description']
    },
    'daily_scores': {
        'file': os.path.join(DATA_PATH, 'daily_scores_log.csv'),
        'cols': ['LogID', 'DefinitionID', 'Date', 'Score', 'Notes']
    },
    'weekly_averages': {
        'file': os.path.join(DATA_PATH, 'weekly_averages.csv'),
        'cols': ['AverageID', 'DefinitionID', 'Year', 'WeekOfYear', 'AverageScore', 'DataPointsCount']
    },
    'monthly_averages': {
        'file': os.path.join(DATA_PATH, 'monthly_averages.csv'),
        'cols': ['AverageID', 'DefinitionID', 'Year', 'Month', 'AverageScore', 'DataPointsCount']
    },
    'semi_annual_averages': {
        'file': os.path.join(DATA_PATH, 'semi_annual_averages.csv'),
        'cols': ['AverageID', 'DefinitionID', 'Year', 'Half', 'AverageScore', 'DataPointsCount']
    }
}

def initialize_database():
    """Checks for all necessary data files and creates them if they don't exist."""
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
    for table_name, table_info in DATABASE_SCHEMA.items():
        file_path = table_info['file']
        if not os.path.exists(file_path):
            df = pd.DataFrame(columns=table_info['cols'])
            df.to_csv(file_path, index=False)

class BehaviorTracker:
    def __init__(self):
        initialize_database()
        self.dataframes = {}
        for table_name, table_info in DATABASE_SCHEMA.items():
            file_path = table_info['file']
            self.dataframes[table_name] = pd.read_csv(file_path)

    def _get_next_id(self, df, id_column):
        if df.empty or df[id_column].isnull().all(): return 1
        return int(df[id_column].max()) + 1
    
    def _save_df(self, df_name):
        file_path = DATABASE_SCHEMA[df_name]['file']
        self.dataframes[df_name].to_csv(file_path, index=False)

    def add_subject(self, subject_label):
        subject_label = subject_label.strip()
        if not subject_label: return
        subjects_df = self.dataframes['subjects']
        if not subjects_df[subjects_df['SubjectLabel'].str.lower() == subject_label.lower()].empty: return
        new_id = self._get_next_id(subjects_df, 'SubjectID')
        new_subject = {
            'SubjectID': new_id,
            'SubjectLabel': subject_label,
            'DateCreated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.dataframes['subjects'] = pd.concat([subjects_df, pd.DataFrame([new_subject])], ignore_index=True)
        self._save_df('subjects')

    def add_behavior_definition(self, subject_id, behavior_name, description=""):
        if not behavior_name or not behavior_name.strip(): return
        try: subject_id = int(subject_id)
        except (ValueError, TypeError): return
        
        subjects_df = self.dataframes['subjects']
        if subjects_df[subjects_df['SubjectID'] == subject_id].empty: return
            
        new_id = self._get_next_id(self.dataframes['definitions'], 'DefinitionID')
        new_definition = {
            'DefinitionID': new_id, 'SubjectID': subject_id,
            'BehaviorName': behavior_name.strip(), 'Description': description.strip()
        }
        self.dataframes['definitions'] = pd.concat([self.dataframes['definitions'], pd.DataFrame([new_definition])], ignore_index=True)
        self._save_df('definitions')

    def log_score(self, definition_id, date, score, notes=""):
        try:
            definition_id, score = int(definition_id), int(score)
        except (ValueError, TypeError): return
        if not (1 <= score <= 10): return
            
        if self.dataframes['definitions'][self.dataframes['definitions']['DefinitionID'] == definition_id].empty: return
        
        new_id = self._get_next_id(self.dataframes['daily_scores'], 'LogID')
        new_log_entry = {
            'LogID': new_id, 'DefinitionID': definition_id,
            'Date': pd.to_datetime(date).strftime("%Y-%m-%d"), 'Score': score, 'Notes': notes.strip()
        }
        self.dataframes['daily_scores'] = pd.concat([self.dataframes['daily_scores'], pd.DataFrame([new_log_entry])], ignore_index=True)
        self._save_df('daily_scores')

    def calculate_all_averages(self):
        scores_df = self.dataframes['daily_scores']
        if scores_df.empty: return

        scores_df['Date'] = pd.to_datetime(scores_df['Date'])
        
        scores_df['Year'] = scores_df['Date'].dt.isocalendar().year
        scores_df['WeekOfYear'] = scores_df['Date'].dt.isocalendar().week
        weekly_avg = scores_df.groupby(['DefinitionID', 'Year', 'WeekOfYear'])['Score'].agg(['mean', 'count']).reset_index()
        weekly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        weekly_avg['AverageID'] = range(1, len(weekly_avg) + 1)
        self.dataframes['weekly_averages'] = weekly_avg[DATABASE_SCHEMA['weekly_averages']['cols']]
        
        scores_df['Month'] = scores_df['Date'].dt.month
        monthly_avg = scores_df.groupby(['DefinitionID', 'Year', 'Month'])['Score'].agg(['mean', 'count']).reset_index()
        monthly_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        monthly_avg['AverageID'] = range(1, len(monthly_avg) + 1)
        self.dataframes['monthly_averages'] = monthly_avg[DATABASE_SCHEMA['monthly_averages']['cols']]

        scores_df['Half'] = (scores_df['Date'].dt.month - 1) // 6 + 1
        semi_annual_avg = scores_df.groupby(['DefinitionID', 'Year', 'Half'])['Score'].agg(['mean', 'count']).reset_index()
        semi_annual_avg.rename(columns={'mean': 'AverageScore', 'count': 'DataPointsCount'}, inplace=True)
        semi_annual_avg['AverageID'] = range(1, len(semi_annual_avg) + 1)
        self.dataframes['semi_annual_averages'] = semi_annual_avg[DATABASE_SCHEMA['semi_annual_averages']['cols']]
        
        for avg_type in ['weekly_averages', 'monthly_averages', 'semi_annual_averages']:
            self._save_df(avg_type)
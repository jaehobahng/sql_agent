import os
import pandas as pd
from sqlalchemy import create_engine

# Database connection details from environment variables
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# Connect to PostgreSQL
engine = create_engine(f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# Path to the folder containing CSV files
data_folder = 'data'

# Iterate through all files in the folder
for file_name in os.listdir(data_folder):
    if file_name.endswith('.csv'):  # Process only CSV files
        file_path = os.path.join(data_folder, file_name)
        table_name = os.path.splitext(file_name)[0]  # Table name is file name without extension

        # Load CSV into a DataFrame
        data = pd.read_csv(file_path)

        # Insert data into the database
        print(f"Inserting data from {file_name} into table {table_name}...")
        data.to_sql(table_name, engine, if_exists='replace', index=False)

# Confirm completion
print("All CSV files have been processed and loaded into the database.")

# with open('data_loaded.flag', 'w') as flag_file:
#     flag_file.write('Data loading completed')
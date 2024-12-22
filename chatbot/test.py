import getpass
import os
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv


load_dotenv('.env')
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


# Database connection details
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "your_database_name")
DB_USER = os.getenv("DB_USER", "your_username")
DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

engine = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'

db = SQLDatabase.from_uri(engine)
print(db.dialect)
print(db.get_usable_table_names())
print(db.run("SELECT * FROM PURCHASE_DATA LIMIT 10;"))


# import psycopg2
# import os

# # Database connection details
# DB_HOST = os.getenv("DB_HOST", "localhost")
# DB_PORT = os.getenv("DB_PORT", "5432")
# DB_NAME = os.getenv("DB_NAME", "your_database_name")
# DB_USER = os.getenv("DB_USER", "your_username")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "your_password")

# def get_db_connection():
#     """Establish a connection to the PostgreSQL database."""
#     return psycopg2.connect(
#         host=DB_HOST,
#         port=DB_PORT,
#         dbname=DB_NAME,
#         user=DB_USER,
#         password=DB_PASSWORD
#     )

# conn = get_db_connection()
# cursor = conn.cursor()
# cursor.execute("SELECT * FROM PURCHASE_DATA;")

# column_names = [desc[0] for desc in cursor.description]
# rows = cursor.fetchall()

# cursor.close()
# conn.close()

# single_row = rows[0]
# row_with_columns = dict(zip(column_names, single_row))

# print(row_with_columns)
# # print(rows)
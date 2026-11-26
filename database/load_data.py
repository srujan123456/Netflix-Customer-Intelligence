
# Import required libraries
import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Locate the project root and load the .env file
project_root = Path(__file__).resolve().parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Read PostgreSQL credentials
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Locate the folder containing cleaned CSV files
data_folder = project_root / "data" / "processed" / "final"

# Map each PostgreSQL table to its selected cleaned CSV
csv_files = {
    "customers": "customers_final.csv",
    "subscription_plans": "subscription_plans_final.csv",
    "content": "content_final.csv",
    "subscriptions": "subscriptions_final1.csv",
    "viewing_activity": "viewing_activity_final.csv",
    "payments": "payments_final1.csv",
    "support_tickets": "support_tickets_final1.csv",
    "customer_feedback": "customer_feedback_final1.csv",
    "churn_labels": "churn_labels_final.csv"
}

# Check that all database credentials are available
if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("Missing database credentials. Check your .env file.")

# Initialize database connection and cursor
connection = None
cursor = None

try:
    # Connect to PostgreSQL
    connection = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    cursor = connection.cursor()

    print("PostgreSQL connection successful!")
    print("\nSTARTING CSV AND DATABASE VALIDATION")

    # Check every selected CSV against its database table
    for table_name, file_name in csv_files.items():

        file_path = data_folder / file_name

        print("\n" + "=" * 60)
        print("TABLE:", table_name)
        print("CSV FILE:", file_name)

        # Check whether the CSV file exists
        if not file_path.exists():
            print("STATUS: CSV FILE NOT FOUND")
            continue

        # Read the cleaned CSV file
        df = pd.read_csv(file_path)

        # Get the number of CSV records
        csv_count = len(df)

        # Get the number of records in PostgreSQL
        count_query = sql.SQL(
            "SELECT COUNT(*) FROM public.{}"
        ).format(sql.Identifier(table_name))

        cursor.execute(count_query)
        db_count = cursor.fetchone()[0]

        # Retrieve the PostgreSQL table column names
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = %s
            ORDER BY ordinal_position;
            """,
            ("public", table_name)
        )

        db_columns = [row[0] for row in cursor.fetchall()]
        csv_columns = list(df.columns)

        # Compare CSV and database columns
        columns_match = set(csv_columns) == set(db_columns)

        # Display validation results
        print("CSV ROW COUNT:", csv_count)
        print("DATABASE ROW COUNT:", db_count)
        print("ROW COUNTS MATCH:", csv_count == db_count)
        print("CSV COLUMN COUNT:", len(csv_columns))
        print("DATABASE COLUMN COUNT:", len(db_columns))
        print("COLUMNS MATCH:", columns_match)

        # Display any column differences
        if not columns_match:
            print("CSV-ONLY COLUMNS:", sorted(set(csv_columns) - set(db_columns)))
            print("DATABASE-ONLY COLUMNS:", sorted(set(db_columns) - set(csv_columns)))

    print("\nVALIDATION COMPLETED")
    print("No database records were inserted, updated, or deleted.")

except Exception as error:
    # Display any validation or connection errors
    print("\nVALIDATION FAILED")
    print("Error:", error)

finally:
    # Close the cursor and database connection
    if cursor is not None:
        cursor.close()

    if connection is not None:
        connection.close()
        print("\nDatabase connection closed.")

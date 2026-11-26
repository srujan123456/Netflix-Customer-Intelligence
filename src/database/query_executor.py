
import json
import os
import sys

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from time import perf_counter

import psycopg2
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

load_dotenv(PROJECT_ROOT / ".env")
print("PROJECT_ROOT:", PROJECT_ROOT)
print("SRC_DIR:", SRC_DIR)
print("SRC_DIR exists:", SRC_DIR.exists())
print("LLM folder exists:", (SRC_DIR / "llm").is_dir())
print("SQL validator exists:", (SRC_DIR / "llm" / "sql_validator.py").is_file())
print("Python path:", sys.path[0])

from llm.sql_validator import validate_sql
from llm.text_to_sql import generate_sql
from llm.response_generator import generate_answer


AUDIT_LOG_PATH = PROJECT_ROOT / "reports" / "sql_audit_log.jsonl"


def get_db_connection():

    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise ValueError(
            f"Missing database configuration: {', '.join(missing_variables)}"
        )

    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=10
    )


@lru_cache(maxsize=1)
def get_database_schema():

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position
            """)

            schema = {}

            for table_name, column_name in cursor.fetchall():
                schema.setdefault(table_name, []).append(column_name)

        return schema

    finally:
        connection.close()


def write_audit_log(question, generated_sql, status, error=None):

    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "generated_sql": generated_sql,
        "execution_status": status,
        "error": error
    }

    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(log_entry) + "\n")


def execute_query(question, generated_sql, schema, timeout_ms=10000):

    if (
        not isinstance(timeout_ms, int)
        or isinstance(timeout_ms, bool)
        or timeout_ms < 1
    ):
        raise ValueError("timeout_ms must be a positive integer.")

    validated_sql = None
    connection = None
    status = "FAILED"
    error_message = None

    try:
        validated_sql = validate_sql(generated_sql, schema)

        connection = get_db_connection()

        with connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (f"{timeout_ms}ms",)
                )

                cursor.execute(validated_sql)

                if cursor.description is None:
                    raise ValueError("Query did not return a result set.")

                columns = [
                    description[0]
                    for description in cursor.description
                ]

                rows = cursor.fetchall()

                results = [
                    dict(zip(columns, row))
                    for row in rows
                ]

        status = "SUCCESS"

        return {
            "columns": columns,
            "rows": results,
            "row_count": len(results),
            "execution_status": status
        }

    except Exception as error:
        error_message = str(error)
        raise

    finally:
        if connection is not None:
            connection.close()

        write_audit_log(
            question,
            validated_sql or generated_sql,
            status,
            error_message
        )


def ask_database(question):

    if not question or not question.strip():
        raise ValueError("Please enter a question.")

    total_start = perf_counter()

    schema_start = perf_counter()
    schema = get_database_schema()
    schema_time = perf_counter() - schema_start

    generation_start = perf_counter()
    generated_sql = generate_sql(question, schema)
    sql_generation_time = perf_counter() - generation_start

    execution_start = perf_counter()

    query_result = execute_query(
        question=question,
        generated_sql=generated_sql,
        schema=schema
    )

    execution_time = perf_counter() - execution_start

    response_start = perf_counter()

    answer = generate_answer(
        question=question,
        results=query_result["rows"],
        row_count=query_result["row_count"]
    )

    response_generation_time = perf_counter() - response_start

    total_time = perf_counter() - total_start

    print("\n========== AI COPILOT PERFORMANCE ==========")
    print(f"Schema retrieval: {schema_time:.2f} seconds")
    print(f"SQL generation: {sql_generation_time:.2f} seconds")
    print(f"Query execution: {execution_time:.2f} seconds")
    print(f"Answer generation: {response_generation_time:.2f} seconds")
    print(f"Total backend time: {total_time:.2f} seconds")
    print("============================================\n")

    return {
        "execution_status": query_result["execution_status"],
        "results": query_result["rows"],
        "row_count": query_result["row_count"],
        "answer": answer
    }

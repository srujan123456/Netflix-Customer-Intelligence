
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


def generate_sql(question, schema):

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    schema_text = "\n".join(
        f"{table}({', '.join(columns)})"
        for table, columns in schema.items()
    )

    prompt = f"""You are a PostgreSQL SQL query generator.

Generate one valid SELECT query using only the supplied database schema.

Rules:
- Only SELECT statements are allowed.
- Never generate INSERT, UPDATE, DELETE, DROP, ALTER or TRUNCATE.
- Use only existing tables and columns.
- Use correct PostgreSQL syntax.
- Use table aliases when joining multiple tables.
- Return SQL only, without Markdown or explanations.
- Add a reasonable LIMIT when appropriate.
- Never invent table names or column names.
- When the user asks for churn reasons or top churn reasons, use the churn_labels table.
- For churn reason analysis, filter records using churned = TRUE.
- For top or common churn reason questions, exclude missing reasons using churn_reason IS NOT NULL.
- If the user explicitly asks about missing or unknown churn reasons, include NULL values.
- For top N questions, sort by the relevant count in descending order and apply LIMIT N.
- Use COUNT(DISTINCT customer_id) when counting customers.

Database schema:
{schema_text}

User question:
{question}

SQL:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0,
                "num_ctx": 4096,
                "num_predict": 200
            }
        },
        timeout=120
    )

    response.raise_for_status()

    generated_sql = response.json().get("response", "").strip()

    generated_sql = (
        generated_sql
        .removeprefix("```sql")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )

    if not generated_sql:
        raise ValueError("The language model returned empty SQL.")

    return generated_sql

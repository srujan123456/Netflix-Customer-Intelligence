
import json
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"


def generate_answer(question, results, row_count):

    if not question or not question.strip():
        raise ValueError("Question cannot be empty.")

    if not results:
        return "The analysis completed, but no matching records were found."

    if row_count == 1 and len(results) == 1:
        result = results[0]

        if len(result) == 1:
            column, value = next(iter(result.items()))

            if isinstance(value, (int, float)):
                return f"The answer is **{value:,}**."

    result_data = json.dumps(
        results,
        ensure_ascii=False,
        default=str
    )

    prompt = f"""You are a Netflix Customer Intelligence business analytics assistant.

Answer the user's question using only the SQL results provided below.

User question:
{question}

Number of result rows:
{row_count}

SQL results:
{result_data}

Instructions:
1. Explain the results in simple, professional business language.
2. Give a direct answer to the user's question.
3. Mention important numbers and patterns present in the results.
4. Do not invent numbers, causes, or conclusions.
5. If the results do not provide enough information, clearly say so.
6. Do not generate SQL.
7. Keep the answer concise and useful.
8. Do not repeat the entire result table.

Business answer:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0.1,
                "num_ctx": 4096,
                "num_predict": 180
            }
        },
        timeout=120
    )

    response.raise_for_status()

    answer = response.json().get("response", "").strip()

    if not answer:
        raise ValueError("The language model returned an empty answer.")

    return answer


import requests
import chromadb

from pathlib import Path

from database.query_executor import get_db_connection


BASE_DIR = Path(__file__).resolve().parents[2]
CHROMA_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b"

COLLECTION_NAME = "netflix_support_feedback"

BATCH_SIZE = 500
TOP_K = 8


client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"}
)


def load_support_and_feedback():

    connection = get_db_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                ticket_id,
                ticket_date,
                issue_category,
                issue_subcategory,
                priority,
                ticket_description
            FROM support_tickets
            WHERE ticket_description IS NOT NULL
              AND TRIM(ticket_description) <> ''
        """)

        support_records = cursor.fetchall()

        cursor.execute("""
            SELECT
                feedback_id,
                feedback_date,
                rating,
                sentiment_label,
                feedback_text
            FROM customer_feedback
            WHERE feedback_text IS NOT NULL
              AND TRIM(feedback_text) <> ''
        """)

        feedback_records = cursor.fetchall()

        support_columns = [
            "ticket_id",
            "ticket_date",
            "issue_category",
            "issue_subcategory",
            "priority",
            "ticket_description"
        ]

        feedback_columns = [
            "feedback_id",
            "feedback_date",
            "rating",
            "sentiment_label",
            "feedback_text"
        ]

        support_data = [
            dict(zip(support_columns, row))
            for row in support_records
        ]

        feedback_data = [
            dict(zip(feedback_columns, row))
            for row in feedback_records
        ]

        return support_data, feedback_data

    finally:
        connection.close()


def prepare_documents(support_records, feedback_records):

    documents = []
    metadatas = []
    ids = []

    for record in support_records:

        description = str(record["ticket_description"]).strip()

        if not description:
            continue

        record_id = str(record["ticket_id"])

        documents.append(
            f"""
Source: Support Ticket
Issue Category: {record["issue_category"]}
Issue Subcategory: {record["issue_subcategory"]}
Priority: {record["priority"]}
Description: {description}
"""
        )

        metadatas.append({
            "source": "support_tickets",
            "record_id": record_id,
            "date": str(record["ticket_date"] or ""),
            "category": str(record["issue_category"] or ""),
            "priority": str(record["priority"] or "")
        })

        ids.append(f"ticket_{record_id}")

    for record in feedback_records:

        feedback_text = str(record["feedback_text"]).strip()

        if not feedback_text:
            continue

        record_id = str(record["feedback_id"])

        documents.append(
            f"""
Source: Customer Feedback
Rating: {record["rating"]}
Sentiment: {record["sentiment_label"]}
Feedback: {feedback_text}
"""
        )

        metadatas.append({
            "source": "customer_feedback",
            "record_id": record_id,
            "date": str(record["feedback_date"] or ""),
            "rating": str(record["rating"] or ""),
            "sentiment": str(record["sentiment_label"] or "")
        })

        ids.append(f"feedback_{record_id}")

    return documents, metadatas, ids


def build_rag_index():

    support_records, feedback_records = load_support_and_feedback()

    documents, metadatas, ids = prepare_documents(
        support_records,
        feedback_records
    )

    if not documents:
        raise ValueError("No support or feedback records were found.")

    for start in range(0, len(documents), BATCH_SIZE):

        end = start + BATCH_SIZE

        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end]
        )

    return {
        "support_records": len(support_records),
        "feedback_records": len(feedback_records),
        "indexed_records": len(documents),
        "collection_count": collection.count(),
        "status": "SUCCESS"
    }


def retrieve_relevant_records(question, top_k=TOP_K):

    if not question or not question.strip():
        raise ValueError("Please provide a question.")

    total_records = collection.count()

    if total_records == 0:
        raise ValueError(
            "The RAG index is empty. Run build_rag_index() first."
        )

    results = collection.query(
        query_texts=[question],
        n_results=min(top_k, total_records),
        include=["documents", "metadatas", "distances"]
    )

    retrieved_records = []

    for index, document in enumerate(results["documents"][0]):

        metadata = results["metadatas"][0][index]

        retrieved_records.append({
            "document": document,
            "source": metadata["source"],
            "record_id": metadata["record_id"],
            "date": metadata.get("date", ""),
            "distance": results["distances"][0][index]
        })

    return retrieved_records


def generate_rag_answer(question, retrieved_records):

    if not retrieved_records:
        return "No relevant customer records were found."

    context = "\n\n".join(
        [
            f"Record {index + 1}:\n{record['document']}"
            for index, record in enumerate(retrieved_records)
        ]
    )

    prompt = f"""
You are a Netflix Customer Intelligence Analyst.

Answer the user's question using ONLY the customer records provided below.

Rules:
1. Do not invent customer complaints, feedback, or statistics.
2. Do not use outside knowledge.
3. Identify recurring complaint themes when supported by the records.
4. Clearly distinguish support tickets from customer feedback.
5. If the evidence is insufficient, say so.
6. Mention the number of retrieved records used.
7. Include source references using the supplied record IDs.

Customer Records:
{context}

User Question:
{question}

Provide:
1. Summary
2. Key Findings
3. Common Themes
4. Supporting Evidence
5. Number of Records Used
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        },
        timeout=180
    )

    response.raise_for_status()

    return response.json()["response"].strip()


def ask_support_question(question, top_k=TOP_K):

    retrieved_records = retrieve_relevant_records(
        question,
        top_k=top_k
    )

    answer = generate_rag_answer(
        question,
        retrieved_records
    )

    source_references = [
        {
            "source": record["source"],
            "record_id": record["record_id"]
        }
        for record in retrieved_records
    ]

    return {
        "question": question,
        "answer": answer,
        "records_retrieved": len(retrieved_records),
        "source_references": source_references,
        "execution_status": "SUCCESS"
    }


import json
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

from database.query_executor import get_db_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
REQUEST_TIMEOUT = 180

SUCCESS_PAYMENT_STATUSES = {
    "success",
    "successful",
    "completed",
    "paid"
}


def execute_query(query, params=()):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT set_config('statement_timeout', %s, true)",
                ("15000ms",)
            )
            cursor.execute(query, params)

            if cursor.description is None:
                return []

            columns = [
                description[0]
                for description in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]

    finally:
        connection.close()


def get_latest_common_data_date():
    query = """
        SELECT LEAST(
            (SELECT MAX(payment_date) FROM payments),
            (SELECT MAX(registration_date) FROM customers),
            (SELECT MAX(churn_date) FROM churn_labels),
            (SELECT MAX(viewing_date) FROM viewing_activity),
            (SELECT MAX(ticket_date) FROM support_tickets),
            (SELECT MAX(feedback_date) FROM customer_feedback)
        ) AS data_as_of_date
    """

    records = execute_query(query)

    data_as_of_date = records[0]["data_as_of_date"]

    if data_as_of_date is None:
        raise ValueError(
            "No common reporting date found in the database."
        )

    if isinstance(data_as_of_date, datetime):
        return data_as_of_date.date()

    return data_as_of_date


def get_report_period(period):
    today = get_latest_common_data_date()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())

    elif period == "monthly":
        start = today.replace(day=1)

    elif period == "quarterly":
        start_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, start_month, 1)

    else:
        raise ValueError(
            "Period must be weekly, monthly, or quarterly."
        )

    end_exclusive = today + timedelta(days=1)

    duration = (end_exclusive - start).days
    previous_start = start - timedelta(days=duration)

    return {
        "period": period,
        "start_date": start,
        "end_date": today,
        "end_exclusive": end_exclusive,
        "previous_start": previous_start,
        "previous_end": start - timedelta(days=1),
        "previous_end_exclusive": start
    }


def normalize_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if hasattr(value, "item"):
        return value.item()

    return value


def normalize_records(records):
    return [
        {
            key: normalize_value(value)
            for key, value in record.items()
        }
        for record in records
    ]


def get_revenue_metrics(start_date, end_exclusive):
    query = """
        SELECT
            payment_status,
            COUNT(*) AS payment_count,
            COALESCE(SUM(amount), 0) AS total_amount
        FROM payments
        WHERE payment_date >= %s
          AND payment_date < %s
        GROUP BY payment_status
        ORDER BY payment_count DESC
    """

    records = execute_query(
        query,
        (start_date, end_exclusive)
    )

    successful_revenue = 0.0
    successful_payments = 0
    total_payments = 0

    for record in records:
        status = str(
            record["payment_status"] or ""
        ).strip().lower()

        count = int(record["payment_count"] or 0)
        amount = float(record["total_amount"] or 0)

        total_payments += count

        if status in SUCCESS_PAYMENT_STATUSES:
            successful_revenue += amount
            successful_payments += count

    return {
        "successful_revenue": round(successful_revenue, 2),
        "successful_payments": successful_payments,
        "total_payments": total_payments,
        "payment_status_breakdown": normalize_records(records)
    }


def get_churn_metrics(start_date, end_exclusive):
    query = """
        SELECT
            COUNT(*) FILTER (
                WHERE LOWER(CAST(churned AS TEXT))
                IN ('true', '1', 'yes', 'churned')
            ) AS churned_customers,
            COUNT(*) AS labeled_customers
        FROM churn_labels
        WHERE churn_date >= %s
          AND churn_date < %s
    """

    records = execute_query(
        query,
        (start_date, end_exclusive)
    )

    record = records[0]

    churned = int(record["churned_customers"] or 0)
    labeled = int(record["labeled_customers"] or 0)

    churn_rate = (
        churned / labeled * 100
        if labeled > 0
        else None
    )

    return {
        "churned_customers": churned,
        "labeled_customers": labeled,
        "churn_rate_percent": (
            round(churn_rate, 2)
            if churn_rate is not None
            else None
        )
    }


def get_customer_growth_metrics(start_date, end_exclusive):
    query = """
        SELECT
            COUNT(*) AS new_customers
        FROM customers
        WHERE registration_date >= %s
          AND registration_date < %s
    """

    records = execute_query(
        query,
        (start_date, end_exclusive)
    )

    return {
        "new_customers": int(
            records[0]["new_customers"] or 0
        )
    }


def get_engagement_metrics(start_date, end_exclusive):
    query = """
        SELECT
            COUNT(*) AS total_views,
            COUNT(DISTINCT customer_id) AS active_customers,
            COALESCE(
                SUM(watch_duration_minutes), 0
            ) AS total_watch_minutes,
            AVG(completion_percentage)
                AS average_completion_percentage,
            AVG(session_duration_minutes)
                AS average_session_duration_minutes
        FROM viewing_activity
        WHERE viewing_date >= %s
          AND viewing_date < %s
    """

    record = execute_query(
        query,
        (start_date, end_exclusive)
    )[0]

    completion = record["average_completion_percentage"]
    session_duration = record["average_session_duration_minutes"]

    return {
        "total_views": int(record["total_views"] or 0),
        "active_customers": int(
            record["active_customers"] or 0
        ),
        "total_watch_minutes": round(
            float(record["total_watch_minutes"] or 0), 2
        ),
        "average_completion_percentage": (
            round(float(completion), 2)
            if completion is not None
            else None
        ),
        "average_session_duration_minutes": (
            round(float(session_duration), 2)
            if session_duration is not None
            else None
        )
    }


def get_support_metrics(start_date, end_exclusive):
    summary_query = """
        SELECT
            COUNT(*) AS total_tickets,
            COUNT(*) FILTER (
                WHERE LOWER(priority) = 'high'
            ) AS high_priority_tickets,
            COUNT(*) FILTER (
                WHERE LOWER(ticket_status) = 'open'
            ) AS open_tickets,
            AVG(resolution_time_hours)
                AS average_resolution_hours,
            AVG(customer_satisfaction_score)
                AS average_satisfaction_score
        FROM support_tickets
        WHERE ticket_date >= %s
          AND ticket_date < %s
    """

    category_query = """
        SELECT
            issue_category,
            COUNT(*) AS ticket_count
        FROM support_tickets
        WHERE ticket_date >= %s
          AND ticket_date < %s
        GROUP BY issue_category
        ORDER BY ticket_count DESC
        LIMIT 10
    """

    summary = execute_query(
        summary_query,
        (start_date, end_exclusive)
    )[0]

    categories = execute_query(
        category_query,
        (start_date, end_exclusive)
    )

    resolution = summary["average_resolution_hours"]
    satisfaction = summary["average_satisfaction_score"]

    return {
        "total_tickets": int(summary["total_tickets"] or 0),
        "high_priority_tickets": int(
            summary["high_priority_tickets"] or 0
        ),
        "open_tickets": int(summary["open_tickets"] or 0),
        "average_resolution_hours": (
            round(float(resolution), 2)
            if resolution is not None
            else None
        ),
        "average_satisfaction_score": (
            round(float(satisfaction), 2)
            if satisfaction is not None
            else None
        ),
        "top_complaint_categories": normalize_records(categories)
    }


def get_feedback_metrics(start_date, end_exclusive):
    summary_query = """
        SELECT
            COUNT(*) AS total_feedback,
            AVG(rating) AS average_rating
        FROM customer_feedback
        WHERE feedback_date >= %s
          AND feedback_date < %s
    """

    sentiment_query = """
        SELECT
            sentiment_label,
            COUNT(*) AS feedback_count
        FROM customer_feedback
        WHERE feedback_date >= %s
          AND feedback_date < %s
          AND sentiment_label IS NOT NULL
        GROUP BY sentiment_label
        ORDER BY feedback_count DESC
    """

    summary = execute_query(
        summary_query,
        (start_date, end_exclusive)
    )[0]

    sentiments = execute_query(
        sentiment_query,
        (start_date, end_exclusive)
    )

    rating = summary["average_rating"]

    return {
        "total_feedback": int(
            summary["total_feedback"] or 0
        ),
        "average_rating": (
            round(float(rating), 2)
            if rating is not None
            else None
        ),
        "sentiment_breakdown": normalize_records(sentiments)
    }


def collect_period_metrics(start_date, end_exclusive):
    return {
        "revenue": get_revenue_metrics(
            start_date, end_exclusive
        ),
        "churn": get_churn_metrics(
            start_date, end_exclusive
        ),
        "customer_growth": get_customer_growth_metrics(
            start_date, end_exclusive
        ),
        "engagement": get_engagement_metrics(
            start_date, end_exclusive
        ),
        "support": get_support_metrics(
            start_date, end_exclusive
        ),
        "feedback": get_feedback_metrics(
            start_date, end_exclusive
        )
    }


def calculate_change(current, previous):
    if current is None or previous is None:
        return {
            "change": None,
            "change_percent": None,
            "note": "Comparison unavailable because a value is missing."
        }

    change = current - previous

    if previous == 0:
        return {
            "change": round(change, 2),
            "change_percent": None,
            "note": "Previous period value was zero."
        }

    return {
        "change": round(change, 2),
        "change_percent": round(
            change / abs(previous) * 100, 2
        ),
        "note": None
    }


def compare_periods(current, previous):
    metric_pairs = {
        "successful_revenue": (
            current["revenue"]["successful_revenue"],
            previous["revenue"]["successful_revenue"]
        ),
        "churned_customers": (
            current["churn"]["churned_customers"],
            previous["churn"]["churned_customers"]
        ),
        "new_customers": (
            current["customer_growth"]["new_customers"],
            previous["customer_growth"]["new_customers"]
        ),
        "active_customers": (
            current["engagement"]["active_customers"],
            previous["engagement"]["active_customers"]
        ),
        "total_watch_minutes": (
            current["engagement"]["total_watch_minutes"],
            previous["engagement"]["total_watch_minutes"]
        ),
        "support_tickets": (
            current["support"]["total_tickets"],
            previous["support"]["total_tickets"]
        ),
        "average_rating": (
            current["feedback"]["average_rating"],
            previous["feedback"]["average_rating"]
        )
    }

    return {
        metric: calculate_change(current_value, previous_value)
        for metric, (current_value, previous_value)
        in metric_pairs.items()
    }


def generate_ai_interpretation(report_data):
    prompt = f"""
You are a business intelligence analyst preparing a Netflix
Customer Intelligence business report.

Use only the calculated database metrics supplied below.

Separate the report into two clear parts:

PART A — CALCULATED FACTS
Summarize the actual metrics and period comparisons.
Do not change, estimate, or invent any numerical values.

PART B — AI INTERPRETATION
Provide:
1. Executive Summary
2. Key Findings
3. Business Risks
4. Recommendations

Rules:
- Never invent metrics, percentages, causes, or events.
- Use only values present in the supplied data.
- If a metric is null or unavailable, state that it is unavailable.
- Do not claim a trend if the comparison is unavailable.
- Distinguish observed facts from possible explanations.
- Recommendations must be based on observed findings.
- Do not present recommendations as proven outcomes.
- Mention when the data volume is zero or insufficient.

DATABASE REPORT DATA:
{json.dumps(report_data, indent=2, default=str)}

Write a clear professional report in Markdown.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 500
            }
        },
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    answer = response.json().get("response", "").strip()

    if not answer:
        raise ValueError("The LLM returned an empty report.")

    return answer


def generate_report(period):
    period_info = get_report_period(period)

    current_metrics = collect_period_metrics(
        period_info["start_date"],
        period_info["end_exclusive"]
    )

    previous_metrics = collect_period_metrics(
        period_info["previous_start"],
        period_info["previous_end_exclusive"]
    )

    comparisons = compare_periods(
        current_metrics,
        previous_metrics
    )

    report_data = {
        "report_title": (
            f"Netflix Customer Intelligence - "
            f"{period.capitalize()} Report"
        ),
        "report_period": {
            "type": period,
            "start_date": period_info["start_date"].isoformat(),
            "end_date": period_info["end_date"].isoformat()
        },
        "previous_period": {
            "start_date": period_info["previous_start"].isoformat(),
            "end_date": period_info["previous_end"].isoformat()
        },
        "data_as_of_date": period_info["end_date"].isoformat(),
        "generated_at": datetime.now().isoformat(),
        "current_metrics": current_metrics,
        "previous_metrics": previous_metrics,
        "period_comparisons": comparisons
    }

    ai_interpretation = generate_ai_interpretation(report_data)

    return {
        "execution_status": "SUCCESS",
        "report_data": report_data,
        "ai_interpretation": ai_interpretation
    }

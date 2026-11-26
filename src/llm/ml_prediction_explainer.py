
import joblib
import requests
import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "models" / "churn_prediction_model.pkl"
DATA_PATH = PROJECT_ROOT / "data" / "processed" / "customer_churn_features.csv"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"

churn_model = joblib.load(MODEL_PATH)


def load_customer_data():

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Customer dataset not found: {DATA_PATH}"
        )

    return pd.read_csv(DATA_PATH)


def get_customer_features(customer_id):

    df = load_customer_data()

    if "customer_id" not in df.columns:
        raise ValueError("customer_id column not found in dataset.")

    customer = df[
        df["customer_id"].astype(str).str.strip()
        == str(customer_id).strip()
    ]

    if customer.empty:
        raise ValueError(
            f"Customer ID {customer_id} was not found."
        )

    if len(customer) > 1:
        raise ValueError(
            f"Multiple records found for customer {customer_id}."
        )

    expected_features = list(churn_model.feature_names_in_)

    missing_features = [
        feature for feature in expected_features
        if feature not in customer.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    customer_features = customer[expected_features].copy()

    evidence_columns = [
        "age",
        "gender",
        "country",
        "customer_segment",
        "tenure_days",
        "total_viewing_sessions",
        "days_since_last_viewing",
        "total_support_tickets",
        "failed_payment_count",
        "payment_success_rate",
        "negative_feedback_rate",
        "average_feedback_rating",
        "viewing_sessions_change",
        "watch_duration_change",
        "customer_engagement_score",
        "monthly_price_asof"
    ]

    evidence = {
        column: customer.iloc[0][column]
        for column in evidence_columns
        if column in customer.columns
    }

    evidence = {
        key: value.item() if hasattr(value, "item") else value
        for key, value in evidence.items()
    }

    return customer_features, evidence


def predict_churn(customer_features):

    if not isinstance(customer_features, pd.DataFrame):
        raise TypeError(
            "Customer features must be a pandas DataFrame."
        )

    expected_features = list(churn_model.feature_names_in_)

    missing_features = [
        feature for feature in expected_features
        if feature not in customer_features.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    customer_features = customer_features[expected_features]

    predictions = churn_model.predict(customer_features)
    probabilities = churn_model.predict_proba(customer_features)

    classes = list(churn_model.classes_)

    if 1 not in classes:
        raise ValueError("Churn class 1 was not found in the model.")

    churn_index = classes.index(1)

    results = []

    for prediction, probability in zip(predictions, probabilities):

        churn_probability = float(
            probability[churn_index] * 100
        )

        status = "Churn" if prediction == 1 else "No Churn"

        results.append({
            "prediction": status,
            "churn_probability": round(churn_probability, 2),
            "retention_probability": round(
                100 - churn_probability, 2
            )
        })

    return results


def generate_prediction_explanation(
    customer_id,
    prediction_result,
    customer_evidence=None
):

    evidence = customer_evidence or {}

    prompt = f"""
You are a Netflix customer retention analyst.

Explain the following machine learning prediction
in simple business language.

Customer ID: {customer_id}

Prediction: {prediction_result['prediction']}

Churn Probability: {prediction_result['churn_probability']}%

Retention Probability: {prediction_result['retention_probability']}%

Customer Evidence:
{evidence}

Provide:
1. Prediction summary.
2. What the churn probability means.
3. Customer behavior that may explain the prediction.
4. A practical retention recommendation.

Use only the supplied customer evidence.
Do not invent customer behavior or statistics.
Clearly distinguish model predictions from confirmed facts.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 250
            }
        },
        timeout=120
    )

    response.raise_for_status()

    return response.json()["response"].strip()


def explain_customer_churn(customer_id):

    customer_features, customer_evidence = get_customer_features(
        customer_id
    )

    prediction_results = predict_churn(customer_features)

    prediction_result = prediction_results[0]

    explanation = generate_prediction_explanation(
        customer_id,
        prediction_result,
        customer_evidence
    )

    return {
        "customer_id": customer_id,
        "prediction": prediction_result["prediction"],
        "churn_probability": prediction_result["churn_probability"],
        "retention_probability": prediction_result["retention_probability"],
        "explanation": explanation
    }

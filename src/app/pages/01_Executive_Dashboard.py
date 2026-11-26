
import sys
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

SRC_DIR = Path(__file__).resolve().parents[2]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database.query_executor import get_db_connection


st.set_page_config(
    page_title="Netflix Intelligence | Executive Dashboard",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #0B1120;
    color: #FFFFFF;
}

header[data-testid="stHeader"] {
    background: #0B1120;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1600px;
}

h1, h2, h3 {
    color: #FFFFFF !important;
}

[data-testid="stMetric"] {
    background: linear-gradient(145deg, #17263E, #111D31);
    border: 1px solid #293B56;
    border-radius: 14px;
    padding: 20px 18px;
    min-height: 145px;
    overflow: hidden;
}

[data-testid="stMetricLabel"] {
    color: #91A8C5 !important;
    font-size: 13px !important;
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-size: clamp(16px, 1.45vw, 25px) !important;
    font-weight: 750 !important;
    white-space: nowrap !important;
    overflow: visible !important;
    text-overflow: clip !important;
    letter-spacing: -0.4px;
}

[data-testid="stMetricDelta"] {
    font-size: 12px;
}

.section-card {
    background: #111D31;
    border: 1px solid #263851;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 15px;
}

.dashboard-header {
    background: linear-gradient(110deg, #15243B, #101B2D);
    border-left: 6px solid #E50914;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 25px;
}

.netflix-title {
    font-size: 37px;
    font-weight: 850;
    letter-spacing: 1px;
}

.netflix-red {
    color: #E50914;
}

.dashboard-subtitle {
    color: #91A8C5;
    font-size: 14px;
    letter-spacing: 1px;
    margin-top: 10px;
}

.stSelectbox label {
    color: #A9BBD2 !important;
}

div[data-testid="stDataFrame"] {
    border: 1px solid #263851;
    border-radius: 10px;
}

div[data-testid="stAlert"] {
    border-radius: 10px;
}

hr {
    border-color: #263851;
}

footer {
    visibility: hidden;
}

</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="dashboard-header">
    <div class="netflix-title">
        <span class="netflix-red">NETFLIX</span> INTELLIGENCE
    </div>
    <div class="dashboard-subtitle">
        EXECUTIVE BUSINESS INTELLIGENCE
        &nbsp; | &nbsp;
        CUSTOMER ANALYTICS PLATFORM
    </div>
</div>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def load_dashboard_data():

    conn = get_db_connection()

    try:
        customers = pd.read_sql_query("""
            SELECT
                customer_id,
                age,
                gender,
                country,
                customer_segment,
                acquisition_channel,
                registration_date
            FROM customers
        """, conn)

        subscriptions = pd.read_sql_query("""
            SELECT
                subscription_id,
                customer_id,
                plan_id,
                subscription_status,
                subscription_start_date,
                subscription_end_date,
                monthly_price,
                cancellation_date,
                cancellation_reason
            FROM subscriptions
        """, conn)

        payments = pd.read_sql_query("""
            SELECT
                payment_id,
                customer_id,
                subscription_id,
                payment_date,
                amount,
                payment_status,
                payment_method
            FROM payments
        """, conn)

        plans = pd.read_sql_query("""
            SELECT
                plan_id,
                plan_name,
                monthly_price
            FROM subscription_plans
        """, conn)

        feedback = pd.read_sql_query("""
            SELECT
                feedback_id,
                customer_id,
                rating,
                sentiment_label,
                feedback_date
            FROM customer_feedback
        """, conn)

        tickets = pd.read_sql_query("""
            SELECT
                ticket_id,
                customer_id,
                issue_category,
                customer_satisfaction_score,
                ticket_date
            FROM support_tickets
        """, conn)

        churn = pd.read_sql_query("""
            SELECT
                customer_id,
                churned,
                churn_date,
                churn_reason
            FROM churn_labels
        """, conn)

        return (
            customers,
            subscriptions,
            payments,
            plans,
            feedback,
            tickets,
            churn
        )

    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_churn_predictions():

    from llm.ml_prediction_explainer import (
        load_customer_data,
        predict_churn
    )

    model_data = load_customer_data()

    if "customer_id" not in model_data.columns:
        raise ValueError(
            "customer_id column is missing from customer_churn_features.csv."
        )

    feature_columns = [
        feature
        for feature in model_data.columns
        if feature != "customer_id"
    ]

    feature_data = model_data[feature_columns].copy()

    prediction_results = predict_churn(feature_data)

    if len(prediction_results) != len(model_data):
        raise ValueError(
            "The churn model returned a different number of predictions "
            "than the number of customer records."
        )

    predictions = model_data[["customer_id"]].copy()

    predictions["churn_probability"] = [
        result["churn_probability"]
        for result in prediction_results
    ]

    predictions["prediction"] = [
        result["prediction"]
        for result in prediction_results
    ]

    return predictions


def money(value):

    value = float(value or 0)

    if abs(value) >= 10000000:
        return f"₹{value / 10000000:.2f}Cr"

    if abs(value) >= 100000:
        return f"₹{value / 100000:.2f}L"

    if abs(value) >= 1000:
        return f"₹{value / 1000:.1f}K"

    return f"₹{value:,.2f}"


def number(value):
    return f"{int(value):,}"


def style_chart(fig, height=370):

    fig.update_layout(
        height=height,
        paper_bgcolor="#0B1120",
        plot_bgcolor="#111D31",
        font=dict(
            color="#A9BBD2",
            family="Arial"
        ),
        margin=dict(l=20, r=20, t=35, b=25),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#A9BBD2")
        ),
        xaxis=dict(
            gridcolor="#263851",
            zerolinecolor="#263851"
        ),
        yaxis=dict(
            gridcolor="#263851",
            zerolinecolor="#263851"
        )
    )

    return fig


try:

    (
        customers,
        subscriptions,
        payments,
        plans,
        feedback,
        tickets,
        churn
    ) = load_dashboard_data()

except Exception as e:

    st.error(f"Dashboard database error: {e}")

    st.info(
        "Please verify your PostgreSQL connection, "
        "database configuration and table structure."
    )

    st.stop()


if customers.empty:

    st.warning("No customer records found.")

    st.stop()


payments["amount"] = pd.to_numeric(
    payments["amount"],
    errors="coerce"
).fillna(0)

successful_payments = payments[
    payments["payment_status"].astype(str).str.strip().str.lower() == "success"
].copy()

total_customers = customers["customer_id"].nunique()

active_customers = subscriptions.loc[
    subscriptions["subscription_status"].astype(str).str.lower() == "active",
    "customer_id"
].nunique()

total_revenue = successful_payments["amount"].sum()

total_churn = churn["customer_id"].nunique()

churn_rate = (
    total_churn / total_customers * 100
    if total_customers else 0
)

avg_satisfaction = pd.to_numeric(
    tickets.loc[
        tickets["customer_id"].isin(customers["customer_id"]),
        "customer_satisfaction_score"
    ],
    errors="coerce"
).mean()

if pd.isna(avg_satisfaction):
    avg_satisfaction = 0


try:
    churn_predictions = load_churn_predictions()

    if churn_predictions is not None:

        churn_predictions["churn_probability"] = pd.to_numeric(
            churn_predictions["churn_probability"],
            errors="coerce"
        )

        high_risk_customers = churn_predictions.loc[
            churn_predictions["churn_probability"] >= 70,
            "customer_id"
        ].nunique()

        high_risk_available = True

    else:

        high_risk_customers = None
        high_risk_available = False

except Exception:

    high_risk_customers = None
    high_risk_available = False
    st.error(f"Churn prediction error: {type(e).__name__}: {e}")


st.subheader("📊 Business Overview")

st.caption(
    "A consolidated view of customer growth, revenue, "
    "subscription health and customer experience."
)


filter1, filter2, filter3 = st.columns(3)

country_options = ["All Countries"] + sorted(
    customers["country"].dropna().astype(str).unique().tolist()
)

segment_options = ["All Segments"] + sorted(
    customers["customer_segment"].dropna().astype(str).unique().tolist()
)

with filter1:
    selected_country = st.selectbox(
        "🌍 Country",
        country_options
    )

with filter2:
    selected_segment = st.selectbox(
        "👥 Customer Segment",
        segment_options
    )

with filter3:

    payment_dates = pd.to_datetime(
        successful_payments["payment_date"],
        errors="coerce"
    )

    available_years = sorted(
        payment_dates.dropna().dt.year.unique().tolist()
    )

    year_options = ["All Years"] + available_years

    selected_year = st.selectbox(
        "📅 Revenue Year",
        year_options
    )


filtered_customers = customers.copy()

if selected_country != "All Countries":
    filtered_customers = filtered_customers[
        filtered_customers["country"] == selected_country
    ]

if selected_segment != "All Segments":
    filtered_customers = filtered_customers[
        filtered_customers["customer_segment"] == selected_segment
    ]


filtered_ids = filtered_customers["customer_id"].unique()

filtered_tickets = tickets[
    tickets["customer_id"].isin(filtered_ids)
].copy()

filtered_avg_satisfaction = pd.to_numeric(
    filtered_tickets["customer_satisfaction_score"],
    errors="coerce"
).mean()

if pd.isna(filtered_avg_satisfaction):
    filtered_avg_satisfaction = 0

filtered_subscriptions = subscriptions[
    subscriptions["customer_id"].isin(filtered_ids)
]

filtered_payments = successful_payments[
    successful_payments["customer_id"].isin(filtered_ids)
]

if selected_year != "All Years":

    filtered_payments = filtered_payments[
        pd.to_datetime(
            filtered_payments["payment_date"],
            errors="coerce"
        ).dt.year == selected_year
    ]


filtered_revenue = filtered_payments["amount"].sum()

filtered_active = filtered_subscriptions.loc[
    filtered_subscriptions["subscription_status"].astype(str).str.lower() == "active",
    "customer_id"
].nunique()

filtered_churn_data = churn[
    churn["customer_id"].isin(filtered_ids)
].copy()

churned_flag = (
    filtered_churn_data["churned"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(["true", "1", "yes", "t"])
)

filtered_churn = filtered_churn_data.loc[
    churned_flag, "customer_id"
].nunique()

filtered_churn_rate = (
    filtered_churn / len(filtered_ids) * 100
    if len(filtered_ids) else 0
)


st.markdown("### Key Performance Indicators")

k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.metric(
        "TOTAL CUSTOMERS",
        number(len(filtered_ids))
    )

with k2:
    st.metric(
        "ACTIVE CUSTOMERS",
        number(filtered_active)
    )

with k3:
    st.metric(
        "CHURN RATE",
        f"{filtered_churn_rate:.2f}%"
    )

with k4:
    st.metric(
        "TOTAL REVENUE",
        money(filtered_revenue),
        help=f"Exact revenue: ₹{filtered_revenue:,.2f}"
    )

with k5:

    if high_risk_available:

        filtered_high_risk = churn_predictions[
            (churn_predictions["customer_id"].isin(filtered_ids))
            & (churn_predictions["churn_probability"] >= 70)
        ]["customer_id"].nunique()

        st.metric(
            "HIGH-RISK CUSTOMERS",
            number(filtered_high_risk),
            help="Customers with a model-predicted churn probability of at least 70%."
        )

    else:

        st.metric(
            "HIGH-RISK CUSTOMERS",
            "N/A",
            help="The trained churn model or its processed feature dataset could not be loaded."
        )

with k6:
    st.metric(
        "AVG SATISFACTION",
        f"{filtered_avg_satisfaction:.2f}/5"
    )


if not high_risk_available:
    st.caption(
        "High-risk predictions are unavailable. Check that the trained "
        "churn model and processed customer feature dataset can be loaded."
    )


st.divider()


st.subheader("💰 Revenue Analytics")

left, right = st.columns([1.5, 1])

with left:

    st.markdown("#### Revenue Performance")

    revenue_trend = filtered_payments.copy()

    revenue_trend["payment_date"] = pd.to_datetime(
        revenue_trend["payment_date"],
        errors="coerce"
    )

    revenue_trend = revenue_trend.dropna(
        subset=["payment_date"]
    )

    if not revenue_trend.empty:

        revenue_trend["Month"] = (
            revenue_trend["payment_date"].dt.to_period("M").astype(str)
        )

        monthly_revenue = (
            revenue_trend.groupby("Month")["amount"]
            .sum()
            .reset_index()
        )

        fig = px.area(
            monthly_revenue,
            x="Month",
            y="amount",
            markers=True,
            color_discrete_sequence=["#E50914"]
        )

        fig.update_traces(
            fill="tozeroy",
            line=dict(width=3)
        )

        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)"
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("Revenue trend data is unavailable.")


with right:

    st.markdown("#### Payment Performance")

    filtered_all_payments = payments[
        payments["customer_id"].isin(filtered_ids)
    ].copy()

    if selected_year != "All Years":
        filtered_all_payments["payment_date"] = pd.to_datetime(
            filtered_all_payments["payment_date"],
            errors="coerce"
        )

        filtered_all_payments = filtered_all_payments[
            filtered_all_payments["payment_date"].dt.year == selected_year
        ]

    payment_summary = (
        filtered_all_payments.groupby("payment_status")["amount"]
        .sum()
        .reset_index()
    )

    if not payment_summary.empty:

        fig = px.pie(
            payment_summary,
            names="payment_status",
            values="amount",
            hole=0.65,
            color="payment_status",
            color_discrete_map={
                "Success": "#10B981",
                "Failed": "#E50914"
            }
        )

        fig.update_traces(
            textinfo="percent+label",
            textfont_size=13
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("Payment status data is unavailable for the selected filters.")


st.divider()


st.subheader("📦 Revenue by Subscription Plan")

plan_data = successful_payments.merge(
    subscriptions[["subscription_id", "plan_id"]],
    on="subscription_id",
    how="left"
)

plan_data = plan_data.merge(
    plans[["plan_id", "plan_name"]],
    on="plan_id",
    how="left"
)

revenue_by_plan = (
    plan_data.groupby("plan_name", dropna=False)
    .agg(
        total_payments=("payment_id", "count"),
        total_revenue=("amount", "sum")
    )
    .reset_index()
)

if not revenue_by_plan.empty:

    left, right = st.columns([1.5, 1])

    with left:

        fig = px.bar(
            revenue_by_plan.sort_values("total_revenue"),
            x="total_revenue",
            y="plan_name",
            orientation="h",
            text="total_revenue",
            color="total_revenue",
            color_continuous_scale=["#7F1D1D", "#E50914", "#F87171"]
        )

        fig.update_traces(
            texttemplate="₹%{x:,.0f}",
            textposition="outside",
            cliponaxis=False
        )

        fig.update_layout(
            xaxis_title="Revenue (₹)",
            yaxis_title="Subscription Plan",
            coloraxis_showscale=False
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    with right:

        st.markdown("#### Plan Revenue Details")

        display_plan = revenue_by_plan.copy()

        display_plan["total_revenue"] = display_plan[
            "total_revenue"
        ].apply(lambda x: f"₹{x:,.2f}")

        st.dataframe(
            display_plan,
            hide_index=True,
            use_container_width=True
        )

else:

    st.info("Plan-level payment data is not available.")


st.divider()


st.subheader("🌍 Global Revenue Intelligence")

country_revenue = filtered_payments.merge(
    filtered_customers[["customer_id", "country"]],
    on="customer_id",
    how="inner"
)

country_summary = (
    country_revenue.groupby("country")
    .agg(
        total_revenue=("amount", "sum"),
        transactions=("payment_id", "count"),
        customers=("customer_id", "nunique")
    )
    .reset_index()
    .sort_values("total_revenue", ascending=False)
)

left, right = st.columns([1.6, 1])

with left:

    st.markdown("#### Revenue by Country — World Map")

    if not country_summary.empty:

        fig = px.choropleth(
            country_summary,
            locations="country",
            locationmode="country names",
            color="total_revenue",
            hover_name="country",
            hover_data={
                "total_revenue": ":,.2f",
                "transactions": True,
                "customers": True
            },
            color_continuous_scale=[
                "#172554",
                "#2563EB",
                "#E50914"
            ],
            projection="natural earth"
        )

        fig.update_geos(
            bgcolor="#111D31",
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#42546C",
            showland=True,
            landcolor="#25364D",
            showocean=True,
            oceancolor="#111D31"
        )

        fig.update_layout(
            height=470,
            paper_bgcolor="#0B1120",
            font=dict(color="#A9BBD2"),
            margin=dict(l=0, r=0, t=15, b=0)
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    else:
        st.info("Country revenue data is unavailable.")


with right:

    st.markdown("#### Customer Segmentation")

    segment_data = filtered_customers[
        "customer_segment"
    ].fillna("Unknown").value_counts().reset_index()

    segment_data.columns = ["Segment", "Customers"]

    if not segment_data.empty:

        fig = px.pie(
            segment_data,
            names="Segment",
            values="Customers",
            hole=0.62,
            color_discrete_sequence=[
                "#3B82F6",
                "#10B981",
                "#F59E0B",
                "#E50914",
                "#8B5CF6"
            ]
        )

        fig.update_traces(
            textinfo="label+percent"
        )

        st.plotly_chart(
            style_chart(fig, 470),
            use_container_width=True
        )

    else:
        st.info("Customer segment data is unavailable for the selected filters.")


st.markdown("#### Country Revenue Details")

if not country_summary.empty:

    country_display = country_summary.copy()

    country_display["total_revenue"] = country_display[
        "total_revenue"
    ].apply(lambda x: f"₹{x:,.2f}")

    st.dataframe(
        country_display,
        hide_index=True,
        use_container_width=True
    )


st.divider()


st.subheader("👥 Customer Health & Subscription Overview")

left, right = st.columns(2)

with left:

    st.markdown("#### Subscription Status")

    subscription_summary = (
        filtered_subscriptions["subscription_status"]
        .value_counts()
        .reset_index()
    )

    subscription_summary.columns = [
        "Subscription Status",
        "Customers"
    ]

    if not subscription_summary.empty:

        fig = px.bar(
            subscription_summary,
            x="Subscription Status",
            y="Customers",
            color="Subscription Status",
            color_discrete_sequence=[
                "#10B981",
                "#E50914",
                "#3B82F6"
            ]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("Subscription data is unavailable.")


with right:

    st.markdown("#### Churn Reasons")

    churn_data = churn[
        churn["customer_id"].isin(filtered_ids)
    ].copy()

    churn_data["churn_reason"] = (
        churn_data["churn_reason"]
        .fillna("Not Specified")
    )

    churn_reasons = (
        churn_data["churn_reason"]
        .value_counts()
        .reset_index()
    )

    churn_reasons.columns = ["Reason", "Customers"]

    if not churn_reasons.empty:

        fig = px.bar(
            churn_reasons.sort_values("Customers"),
            x="Customers",
            y="Reason",
            orientation="h",
            color_discrete_sequence=["#E50914"]
        )

        st.plotly_chart(
            style_chart(fig),
            use_container_width=True
        )

    else:
        st.info("Churn reason data is unavailable.")


st.divider()


st.subheader("⭐ Customer Satisfaction")

satisfaction = tickets.copy()

satisfaction["customer_satisfaction_score"] = pd.to_numeric(
    satisfaction["customer_satisfaction_score"],
    errors="coerce"
)

satisfaction = satisfaction[
    satisfaction["customer_id"].isin(filtered_ids)
]

satisfaction_summary = (
    satisfaction.groupby("issue_category")
    ["customer_satisfaction_score"]
    .mean()
    .reset_index()
    .sort_values("customer_satisfaction_score")
)

if not satisfaction_summary.empty:

    fig = px.bar(
        satisfaction_summary,
        x="customer_satisfaction_score",
        y="issue_category",
        orientation="h",
        text="customer_satisfaction_score",
        color_discrete_sequence=["#3B82F6"]
    )

    fig.update_traces(
        texttemplate="%{x:.2f}",
        textposition="outside"
    )

    fig.update_layout(
        xaxis_title="Average Satisfaction Score",
        yaxis_title="Issue Category"
    )

    st.plotly_chart(
        style_chart(fig, 400),
        use_container_width=True
    )

else:
    st.info("Customer satisfaction data is unavailable.")


st.divider()


st.markdown("""
<div style="
    text-align:center;
    color:#7186A2;
    padding:20px;
    font-size:13px;
">
    NETFLIX INTELLIGENCE |
    EXECUTIVE BUSINESS INTELLIGENCE |
    CUSTOMER ANALYTICS PLATFORM
</div>
""", unsafe_allow_html=True)

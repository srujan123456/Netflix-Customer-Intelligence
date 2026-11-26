
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Customer Segmentation | Netflix Intelligence",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #0e1117;
    color: #f5f5f5;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
}
.dashboard-title {
    font-size: 36px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 4px;
}
.dashboard-subtitle {
    color: #9ca3af;
    font-size: 15px;
    margin-bottom: 28px;
}
.kpi-card {
    background: linear-gradient(135deg, #1c2333, #151a27);
    border: 1px solid #30394d;
    border-radius: 14px;
    padding: 20px;
    min-height: 125px;
}
.kpi-label {
    color: #aab3c5;
    font-size: 14px;
}
.kpi-value {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
    margin-top: 9px;
}
.kpi-note {
    color: #7d8ba5;
    font-size: 12px;
    margin-top: 5px;
}
.section-heading {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    margin-top: 20px;
    margin-bottom: 15px;
}
.insight-card {
    background: #171e2d;
    border: 1px solid #30394d;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
}
.insight-title {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
}
.insight-text {
    color: #b8c1d1;
    font-size: 14px;
    line-height: 1.6;
}
div[data-testid="stDataFrame"] {
    border: 1px solid #30394d;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

ROOT_DIR = Path(__file__).resolve().parents[3]

CSV_PATHS = [
    ROOT_DIR / "data" / "processed" / "final" / "customer_segments.csv",
    ROOT_DIR / "data" / "processed" / "customer_segments.csv",
    ROOT_DIR / "customer_segments.csv",
    ROOT_DIR / "notebooks" / "customer_segments.csv"
]

csv_path = next((p for p in CSV_PATHS if p.exists()), None)

st.markdown(
    '<div class="dashboard-title">🎯 Customer Segmentation</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="dashboard-subtitle">K-Means customer clusters, segment distribution and business insights</div>',
    unsafe_allow_html=True
)

if csv_path is None:
    st.error("customer_segments.csv was not found.")
    st.info("Place the file in data/processed/final/customer_segments.csv.")
    st.stop()

try:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
except Exception as e:
    st.error(f"Unable to read the segmentation file: {e}")
    st.stop()

df.columns = df.columns.astype(str).str.strip()

if "customer_id" not in df.columns:
    st.error("The dataset does not contain customer_id.")
    st.stop()

if "cluster" in df.columns:
    cluster_values = pd.to_numeric(df["cluster"], errors="coerce")
    if cluster_values.notna().any():
        df["customer_cluster"] = cluster_values
    elif "customer_cluster" in df.columns:
        df["customer_cluster"] = pd.to_numeric(
            df["customer_cluster"], errors="coerce"
        )
    else:
        st.error("No valid cluster assignments were found.")
        st.stop()
elif "customer_cluster" in df.columns:
    df["customer_cluster"] = pd.to_numeric(
        df["customer_cluster"], errors="coerce"
    )
else:
    st.error("The dataset must contain a cluster or customer_cluster column.")
    st.stop()

df = df.dropna(subset=["customer_id", "customer_cluster"]).copy()
df["customer_id"] = df["customer_id"].astype(str).str.strip()
df["customer_cluster"] = df["customer_cluster"].astype(int)
df = df[df["customer_id"] != ""]
df = df.drop_duplicates(subset=["customer_id"])

if df.empty:
    st.error("No valid customer records were found.")
    st.stop()

CLUSTER_NAMES = {
    0: "High Historical Spend - Inactive",
    1: "Recently Active Customers",
    2: "Low Spend - Inactive",
    3: "Multi-Subscription - Inactive"
}

CLUSTER_DESCRIPTIONS = {
    0: (
        "Customers identified as having high historical spending but inactive behavior.",
        "Consider personalized win-back campaigns and targeted retention offers."
    ),
    1: (
        "Customers identified as recently active.",
        "Focus on retention, continued engagement and subscription continuity."
    ),
    2: (
        "Customers identified as having low historical spending and inactive behavior.",
        "Consider suitable reactivation campaigns and relevant subscription offers."
    ),
    3: (
        "Customers identified as having multiple subscriptions but inactive behavior.",
        "Consider personalized win-back campaigns based on subscription history."
    )
}

df["segment_name"] = df["customer_cluster"].map(
    CLUSTER_NAMES
).fillna(
    "Cluster " + df["customer_cluster"].astype(str)
)

total_customers = len(df)
total_clusters = df["customer_cluster"].nunique()

summary = (
    df.groupby(["customer_cluster", "segment_name"])
    .agg(customer_count=("customer_id", "count"))
    .reset_index()
    .sort_values("customer_cluster")
)

summary["percentage"] = (
    summary["customer_count"] / total_customers * 100
)

largest_segment = summary.loc[summary["customer_count"].idxmax()]
largest_segment_name = largest_segment["segment_name"]

st.markdown('<div class="section-heading">Executive Overview</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Total Customers</div>
        <div class="kpi-value">{total_customers:,}</div>
        <div class="kpi-note">Customers in segmentation data</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Customer Segments</div>
        <div class="kpi-value">{total_clusters}</div>
        <div class="kpi-note">Distinct K-Means clusters</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Largest Segment</div>
        <div class="kpi-value">{largest_segment['percentage']:.1f}%</div>
        <div class="kpi-note">{largest_segment_name}</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">Customer Records</div>
        <div class="kpi-value">{df['customer_id'].nunique():,}</div>
        <div class="kpi-note">Unique customer IDs</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

st.markdown('<div class="section-heading">Customer Distribution Analytics</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    fig = px.pie(
        summary,
        names="segment_name",
        values="customer_count",
        hole=0.58,
        title="Customer Share by Segment",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        marker=dict(line=dict(color="#0e1117", width=3))
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="Customer Segment",
        margin=dict(t=60, b=20, l=20, r=20)
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.bar(
        summary,
        x="segment_name",
        y="customer_count",
        color="segment_name",
        text="customer_count",
        title="Customers Across Clusters",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis_title="Customer Segment",
        yaxis_title="Number of Customers",
        xaxis_tickangle=-20,
        margin=dict(t=60, b=70, l=20, r=20)
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.markdown('<div class="section-heading">Cluster Performance</div>', unsafe_allow_html=True)

display_summary = summary[
    ["customer_cluster", "segment_name", "customer_count", "percentage"]
].rename(columns={
    "customer_cluster": "Cluster ID",
    "segment_name": "Segment",
    "customer_count": "Customers",
    "percentage": "Customer Share (%)"
})

display_summary["Customer Share (%)"] = (
    display_summary["Customer Share (%)"].round(2)
)

st.dataframe(
    display_summary,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

st.markdown('<div class="section-heading">Business Insights</div>', unsafe_allow_html=True)

insight_cols = st.columns(2)

for index, row in summary.iterrows():
    cluster_id = int(row["customer_cluster"])
    segment_name = row["segment_name"]
    count = int(row["customer_count"])
    percentage = float(row["percentage"])

    profile, strategy = CLUSTER_DESCRIPTIONS.get(
        cluster_id,
        (
            "A separate customer cluster identified by the K-Means model.",
            "Review this segment's underlying customer behavior before designing a campaign."
        )
    )

    with insight_cols[index % 2]:
        st.markdown(f"""
        <div class="insight-card">
            <div class="insight-title">{segment_name}</div>
            <div class="insight-text">
                <br>
                <b>Cluster:</b> {cluster_id}<br>
                <b>Customers:</b> {count:,}<br>
                <b>Customer share:</b> {percentage:.2f}%<br><br>
                <b>Profile:</b> {profile}<br><br>
                <b>Suggested strategy:</b> {strategy}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

st.markdown('<div class="section-heading">Customer Explorer</div>', unsafe_allow_html=True)

filter_col1, filter_col2 = st.columns(2)

with filter_col1:
    selected_segment = st.selectbox(
        "Filter by customer segment",
        ["All Segments"] + summary["segment_name"].tolist()
    )

with filter_col2:
    customer_search = st.text_input(
        "Search Customer ID",
        placeholder="Example: CUST000744"
    )

filtered_df = df.copy()

if selected_segment != "All Segments":
    filtered_df = filtered_df[
        filtered_df["segment_name"] == selected_segment
    ]

if customer_search.strip():
    filtered_df = filtered_df[
        filtered_df["customer_id"].str.contains(
            customer_search.strip(),
            case=False,
            na=False
        )
    ]

st.write(f"**Matching customers:** {len(filtered_df):,}")

st.dataframe(
    filtered_df[
        ["customer_id", "customer_cluster", "segment_name"]
    ].rename(columns={
        "customer_id": "Customer ID",
        "customer_cluster": "Cluster",
        "segment_name": "Segment"
    }),
    use_container_width=True,
    hide_index=True
)

download_data = filtered_df[
    ["customer_id", "customer_cluster", "segment_name"]
].to_csv(index=False).encode("utf-8")

st.download_button(
    "📥 Download Customer Segmentation CSV",
    data=download_data,
    file_name="customer_segmentation_report.csv",
    mime="text/csv"
)

st.markdown("---")

st.caption(
    "Netflix Customer Intelligence | Customer Segmentation | "
    "Existing K-Means assignments | No model retraining performed"
)

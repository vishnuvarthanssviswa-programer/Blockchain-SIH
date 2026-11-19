import streamlit as st
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objects as go
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import hashlib
import os


# ============================================================
# TRINETRA - AI Powered Bitcoin Transaction Intelligence
# ============================================================

st.set_page_config(
    page_title="TRINETRA | Bitcoin Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# FILES
# ============================================================

RISK_FILE = "data/risk_results.csv"
TX_FILE = "data/bitcoin_transactions.csv"


# ============================================================
# LOAD DATA
# ============================================================

@st.cache_data
def load_data():

    risk = pd.read_csv(RISK_FILE)

    tx = pd.read_csv(TX_FILE)

    tx["timestamp"] = pd.to_datetime(
        tx["timestamp"]
    )

    return risk, tx


risk_df, tx_df = load_data()


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        letter-spacing: 3px;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 15px;
        opacity: 0.7;
        margin-bottom: 25px;
    }

    .risk-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        background: rgba(128,128,128,0.06);
    }

    .small-label {
        font-size: 12px;
        opacity: 0.65;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .big-number {
        font-size: 30px;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True
)


st.markdown(
    '<div class="main-title">TRINETRA</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'AI-Powered Bitcoin Transaction Monitoring & Forensic Intelligence'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("TRINETRA")

st.sidebar.caption(
    "Transaction Intelligence Platform"
)

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Risk Overview",
        "Investigation Queue",
        "Wallet Investigation",
        "Transaction Graph"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    f"Transactions: {len(tx_df):,}"
)

st.sidebar.caption(
    f"Wallets: {risk_df['wallet'].nunique():,}"
)

st.sidebar.caption(
    "MODE: OFFLINE"
)


# ============================================================
# COMMON FUNCTIONS
# ============================================================

def risk_badge(level):

    if level == "CRITICAL":
        return "🔴 CRITICAL"

    if level == "HIGH":
        return "🟠 HIGH"

    if level == "MEDIUM":
        return "🟡 MEDIUM"

    return "🟢 LOW"


def create_pdf(wallet_row, wallet_tx):

    filename = (
        f"reports/TRINETRA_{wallet_row['wallet']}_report.pdf"
    )

    os.makedirs(
        "reports",
        exist_ok=True
    )

    c = canvas.Canvas(
        filename,
        pagesize=A4
    )

    width, height = A4

    y = height - 50

    c.setFont(
        "Helvetica-Bold",
        20
    )

    c.drawString(
        50,
        y,
        "TRINETRA INVESTIGATION REPORT"
    )

    y -= 35

    c.setFont(
        "Helvetica",
        10
    )

    c.drawString(
        50,
        y,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    y -= 30

    c.setFont(
        "Helvetica-Bold",
        13
    )

    c.drawString(
        50,
        y,
        f"Wallet: {wallet_row['wallet']}"
    )

    y -= 25

    c.setFont(
        "Helvetica",
        11
    )

    details = [
        f"Risk Score: {wallet_row['risk_score']}/100",
        f"Risk Level: {wallet_row['risk_level']}",
        f"Anomaly Score: {wallet_row['anomaly_score']}",
        f"Behavior Cluster: {wallet_row['cluster_id']}",
        f"Cluster Probability: {wallet_row['cluster_probability']}",
        f"Graph Risk: {wallet_row['graph_risk']:.2f}",
        f"PageRank: {wallet_row['pagerank']:.6f}",
        f"Betweenness: {wallet_row['betweenness_centrality']:.6f}",
        f"Transaction Count: {len(wallet_tx)}",
        f"Total Volume: {wallet_tx['amount_btc'].sum():.6f} BTC",
    ]

    for line in details:

        c.drawString(
            60,
            y,
            line
        )

        y -= 20

    y -= 10

    c.setFont(
        "Helvetica-Bold",
        12
    )

    c.drawString(
        50,
        y,
        "WHY FLAGGED"
    )

    y -= 20

    c.setFont(
        "Helvetica",
        10
    )

    evidence = str(
        wallet_row["risk_evidence"]
    )

    for chunk in evidence.split(";"):

        c.drawString(
            60,
            y,
            "• " + chunk.strip()
        )

        y -= 18

    y -= 15

    c.setFont(
        "Helvetica-Bold",
        12
    )

    c.drawString(
        50,
        y,
        "INTEGRITY HASH"
    )

    y -= 18

    c.setFont(
        "Helvetica",
        8
    )

    with open(
        TX_FILE,
        "rb"
    ) as f:

        file_hash = hashlib.sha256(
            f.read()
        ).hexdigest()

    c.drawString(
        60,
        y,
        file_hash
    )

    c.save()

    return filename


def make_graph(wallet, transactions):

    G = nx.DiGraph()

    selected = transactions[
        (transactions["src_wallet"] == wallet)
        |
        (transactions["dst_wallet"] == wallet)
    ]

    # Keep graph readable
    selected = selected.head(150)

    for _, row in selected.iterrows():

        src = row["src_wallet"]
        dst = row["dst_wallet"]

        G.add_edge(
            src,
            dst,
            amount=float(row["amount_btc"])
        )

    if wallet not in G:
        G.add_node(wallet)

    positions = nx.spring_layout(
        G,
        seed=42,
        k=1.2
    )

    edge_x = []
    edge_y = []

    for source, target in G.edges():

        x0, y0 = positions[source]
        x1, y1 = positions[target]

        edge_x += [
            x0,
            x1,
            None
        ]

        edge_y += [
            y0,
            y1,
            None
        ]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        hoverinfo="none",
        line=dict(
            width=1
        )
    )

    node_x = []
    node_y = []
    node_text = []

    for node in G.nodes():

        x, y = positions[node]

        node_x.append(x)
        node_y.append(y)

        node_text.append(
            f"Wallet: {node}"
        )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=list(G.nodes()),
        textposition="top center",
        hovertext=node_text,
        hoverinfo="text",
        marker=dict(
            size=12
        )
    )

    figure = go.Figure(
        data=[
            edge_trace,
            node_trace
        ]
    )

    figure.update_layout(
        height=650,
        showlegend=False,
        margin=dict(
            l=0,
            r=0,
            t=20,
            b=0
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        )
    )

    return figure


# ============================================================
# PAGE 1 - RISK OVERVIEW
# ============================================================

if page == "Risk Overview":

    st.header(
        "Risk Overview"
    )

    total_wallets = len(risk_df)

    critical = (
        risk_df["risk_level"] == "CRITICAL"
    ).sum()

    high = (
        risk_df["risk_level"] == "HIGH"
    ).sum()

    medium = (
        risk_df["risk_level"] == "MEDIUM"
    ).sum()

    anomalies = (
        risk_df["anomaly_label"] == "ANOMALY"
    ).sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "Wallets",
            f"{total_wallets:,}"
        )

    with col2:

        st.metric(
            "Anomalies",
            f"{anomalies:,}"
        )

    with col3:

        st.metric(
            "Critical",
            f"{critical:,}"
        )

    with col4:

        st.metric(
            "High Risk",
            f"{high:,}"
        )

    with col5:

        st.metric(
            "Transactions",
            f"{len(tx_df):,}"
        )

    st.divider()

    left, right = st.columns(
        [1, 1]
    )

    with left:

        st.subheader(
            "Risk Distribution"
        )

        distribution = (
            risk_df["risk_level"]
            .value_counts()
        )

        fig = go.Figure(
            data=[
                go.Bar(
                    x=distribution.index,
                    y=distribution.values,
                    text=distribution.values,
                    textposition="auto"
                )
            ]
        )

        fig.update_layout(
            height=400,
            xaxis_title="Risk Level",
            yaxis_title="Wallet Count"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with right:

        st.subheader(
            "Top Investigation Leads"
        )

        top = risk_df[
            [
                "wallet",
                "risk_score",
                "risk_level",
                "anomaly_score",
                "cluster_id"
            ]
        ].head(10)

        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.subheader(
        "Highest-Risk Wallets"
    )

    display_df = risk_df[
        [
            "wallet",
            "risk_score",
            "risk_level",
            "anomaly_score",
            "cluster_id",
            "graph_risk",
            "risk_evidence"
        ]
    ].head(20)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# PAGE 2 - INVESTIGATION QUEUE
# ============================================================

elif page == "Investigation Queue":

    st.header(
        "Investigation Queue"
    )

    st.caption(
        "Prioritized behavioral leads generated by the TRINETRA risk engine."
    )

    selected_level = st.multiselect(
        "Risk Level",
        [
            "CRITICAL",
            "HIGH",
            "MEDIUM",
            "LOW"
        ],
        default=[
            "CRITICAL",
            "HIGH"
        ]
    )

    filtered = risk_df[
        risk_df["risk_level"].isin(
            selected_level
        )
    ].copy()

    filtered["priority"] = range(
        1,
        len(filtered) + 1
    )

    st.dataframe(
        filtered[
            [
                "priority",
                "wallet",
                "risk_score",
                "risk_level",
                "anomaly_score",
                "cluster_id",
                "graph_risk",
                "risk_evidence"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "Risk scores prioritize behavioral investigation. "
        "They do not by themselves establish ownership, identity, "
        "or criminal activity."
    )


# ============================================================
# PAGE 3 - WALLET INVESTIGATION
# ============================================================

elif page == "Wallet Investigation":

    st.header(
        "Wallet Investigation"
    )

    wallet_options = risk_df[
        "wallet"
    ].tolist()

    selected_wallet = st.selectbox(
        "Select Wallet",
        wallet_options
    )

    wallet_row = risk_df[
        risk_df["wallet"] == selected_wallet
    ].iloc[0]

    wallet_tx = tx_df[
        (tx_df["src_wallet"] == selected_wallet)
        |
        (tx_df["dst_wallet"] == selected_wallet)
    ].copy()

    st.divider()

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Risk Score",
            f"{wallet_row['risk_score']:.2f}"
        )

    with col2:

        st.metric(
            "Risk Level",
            risk_badge(
                wallet_row["risk_level"]
            )
        )

    with col3:

        st.metric(
            "Anomaly Score",
            f"{wallet_row['anomaly_score']:.2f}"
        )

    with col4:

        st.metric(
            "Transactions",
            f"{len(wallet_tx):,}"
        )

    st.divider()

    left, right = st.columns(
        [1, 1]
    )

    with left:

        st.subheader(
            "Behavioral Intelligence"
        )

        st.write(
            f"**Behavior Cluster:** "
            f"{wallet_row['cluster_id']}"
        )

        st.write(
            f"**Cluster Probability:** "
            f"{wallet_row['cluster_probability']}"
        )

        st.write(
            f"**Graph Risk:** "
            f"{wallet_row['graph_risk']:.2f}"
        )

        st.write(
            f"**PageRank:** "
            f"{wallet_row['pagerank']:.6f}"
        )

        st.write(
            f"**Betweenness:** "
            f"{wallet_row['betweenness_centrality']:.6f}"
        )

        st.write(
            f"**Connectivity:** "
            f"{wallet_row['graph_total_degree']}"
        )

    with right:

        st.subheader(
            "WHY FLAGGED"
        )

        evidence = str(
            wallet_row["risk_evidence"]
        ).split(";")

        for item in evidence:

            st.write(
                "• " + item.strip()
            )

    st.divider()

    st.subheader(
        "Wallet Transaction Timeline"
    )

    timeline = wallet_tx[
        [
            "timestamp",
            "txid",
            "src_wallet",
            "dst_wallet",
            "amount_btc",
            "fee_btc",
            "src_ip",
            "dst_ip",
            "scenario"
        ]
    ].sort_values(
        "timestamp",
        ascending=False
    )

    st.dataframe(
        timeline.head(100),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    if st.button(
        "Generate Investigation PDF",
        type="primary"
    ):

        path = create_pdf(
            wallet_row,
            wallet_tx
        )

        with open(
            path,
            "rb"
        ) as f:

            st.download_button(
                "Download Report",
                f,
                file_name=os.path.basename(path),
                mime="application/pdf"
            )


# ============================================================
# PAGE 4 - TRANSACTION GRAPH
# ============================================================

elif page == "Transaction Graph":

    st.header(
        "Transaction Network Graph"
    )

    wallet_options = risk_df[
        "wallet"
    ].tolist()

    selected_wallet = st.selectbox(
        "Central Wallet",
        wallet_options
    )

    wallet_tx = tx_df[
        (tx_df["src_wallet"] == selected_wallet)
        |
        (tx_df["dst_wallet"] == selected_wallet)
    ]

    st.caption(
        f"Showing transaction relationships for {selected_wallet}"
    )

    figure = make_graph(
        selected_wallet,
        wallet_tx
    )

    st.plotly_chart(
        figure,
        use_container_width=True
    )

    st.subheader(
        "Related Transactions"
    )

    st.dataframe(
        wallet_tx[
            [
                "timestamp",
                "txid",
                "src_wallet",
                "dst_wallet",
                "amount_btc",
                "scenario"
            ]
        ].head(100),
        use_container_width=True,
        hide_index=True
    )
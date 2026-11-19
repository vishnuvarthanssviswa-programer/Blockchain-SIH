import pandas as pd
import numpy as np

ANOMALY_FILE = "data/anomaly_results.csv"
CLUSTER_FILE = "data/cluster_results.csv"
GRAPH_FILE = "data/graph_features.csv"

OUTPUT_FILE = "data/risk_results.csv"


def min_max_normalize(series):

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            np.zeros(len(series)),
            index=series.index
        )

    return (
        (series - minimum) /
        (maximum - minimum)
    )


def run_risk_engine():

    print("=" * 60)
    print("TRINETRA - Multi-Layer Risk Fusion Engine")
    print("=" * 60)

    # ---------------------------------------------------------
    # Load analytical results
    # ---------------------------------------------------------

    anomaly = pd.read_csv(
        ANOMALY_FILE
    )

    cluster = pd.read_csv(
        CLUSTER_FILE
    )

    graph = pd.read_csv(
        GRAPH_FILE
    )

    print(
        f"\nAnomaly records : {len(anomaly)}"
    )

    print(
        f"Cluster records : {len(cluster)}"
    )

    print(
        f"Graph records   : {len(graph)}"
    )

    # ---------------------------------------------------------
    # Select required columns
    # ---------------------------------------------------------

    anomaly = anomaly[
        [
            "wallet",
            "anomaly_label",
            "anomaly_score",
            "anomaly_rank"
        ]
    ]

    cluster = cluster[
        [
            "wallet",
            "cluster_id",
            "cluster_probability",
            "cluster_type"
        ]
    ]

    graph = graph[
        [
            "wallet",
            "graph_in_degree",
            "graph_out_degree",
            "graph_total_degree",
            "incoming_volume",
            "outgoing_volume",
            "pagerank",
            "betweenness_centrality",
            "clustering_coefficient"
        ]
    ]

    # ---------------------------------------------------------
    # Merge all analytical layers
    # ---------------------------------------------------------

    df = anomaly.merge(
        cluster,
        on="wallet",
        how="left"
    )

    df = df.merge(
        graph,
        on="wallet",
        how="left"
    )

    print(
        f"\nCombined wallet records: {len(df)}"
    )

    # ---------------------------------------------------------
    # Clean numerical values
    # ---------------------------------------------------------

    numeric_columns = df.select_dtypes(
        include=np.number
    ).columns

    df[numeric_columns] = (
        df[numeric_columns]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )

    # ---------------------------------------------------------
    # Normalize graph indicators
    # ---------------------------------------------------------

    df["pagerank_norm"] = min_max_normalize(
        df["pagerank"]
    )

    df["betweenness_norm"] = min_max_normalize(
        df["betweenness_centrality"]
    )

    df["degree_norm"] = min_max_normalize(
        df["graph_total_degree"]
    )

    # ---------------------------------------------------------
    # Behavioral isolation score
    # ---------------------------------------------------------

    df["cluster_risk"] = np.where(
        df["cluster_id"] == -1,
        100.0,
        (1 - df["cluster_probability"]) * 50
    )

    # ---------------------------------------------------------
    # Graph risk score
    # ---------------------------------------------------------

    df["graph_risk"] = (
        0.40 * df["pagerank_norm"] * 100
        +
        0.35 * df["betweenness_norm"] * 100
        +
        0.25 * df["degree_norm"] * 100
    )

    # ---------------------------------------------------------
    # Multi-layer risk fusion
    # ---------------------------------------------------------

    df["risk_score"] = (
        0.50 * df["anomaly_score"]
        +
        0.20 * df["cluster_risk"]
        +
        0.30 * df["graph_risk"]
    )

    df["risk_score"] = (
        df["risk_score"]
        .clip(0, 100)
        .round(2)
    )

    # ---------------------------------------------------------
    # Risk classification
    # ---------------------------------------------------------

    def classify_risk(score):

        if score >= 80:
            return "CRITICAL"

        elif score >= 60:
            return "HIGH"

        elif score >= 40:
            return "MEDIUM"

        else:
            return "LOW"

    df["risk_level"] = (
        df["risk_score"]
        .apply(classify_risk)
    )

    # ---------------------------------------------------------
    # Evidence generation
    # ---------------------------------------------------------

    def generate_evidence(row):

        evidence = []

        if row["anomaly_score"] >= 70:

            evidence.append(
                "Strong behavioral anomaly"
            )

        elif row["anomaly_score"] >= 40:

            evidence.append(
                "Moderate behavioral anomaly"
            )

        if row["cluster_id"] == -1:

            evidence.append(
                "Behavioral outlier / isolated cluster"
            )

        if row["pagerank_norm"] >= 0.75:

            evidence.append(
                "High network influence"
            )

        if row["betweenness_norm"] >= 0.75:

            evidence.append(
                "High network intermediary position"
            )

        if row["degree_norm"] >= 0.75:

            evidence.append(
                "High transaction connectivity"
            )

        if not evidence:

            evidence.append(
                "No strong risk indicators"
            )

        return "; ".join(evidence)

    df["risk_evidence"] = (
        df.apply(
            generate_evidence,
            axis=1
        )
    )

    # ---------------------------------------------------------
    # Investigation priority
    # ---------------------------------------------------------

    df["investigation_priority"] = (
        df["risk_score"]
        .rank(
            ascending=False,
            method="first"
        )
        .astype(int)
    )

    # ---------------------------------------------------------
    # Sort by risk
    # ---------------------------------------------------------

    df = df.sort_values(
        "risk_score",
        ascending=False
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\nRisk fusion complete.")

    print(
        "\nRisk distribution:"
    )

    print(
        df["risk_level"]
        .value_counts()
        .to_string()
    )

    print(
        "\nTop 20 investigation priorities:"
    )

    print(
        df[
            [
                "wallet",
                "risk_score",
                "risk_level",
                "anomaly_score",
                "cluster_id",
                "graph_risk",
                "risk_evidence"
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

    print(
        "\nResults saved to:"
    )

    print(
        OUTPUT_FILE
    )

    return df


if __name__ == "__main__":
    run_risk_engine()
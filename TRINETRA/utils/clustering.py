import pandas as pd
import numpy as np
import joblib
import hdbscan
from sklearn.preprocessing import StandardScaler

INPUT_FILE = "data/anomaly_results.csv"
OUTPUT_FILE = "data/cluster_results.csv"
SCALER_FILE = "models/cluster_scaler.pkl"
MODEL_FILE = "models/hdbscan_model.pkl"


def run_clustering():

    print("=" * 60)
    print("TRINETRA - HDBSCAN Behavioral Clustering")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    print(f"\nWallets loaded: {len(df)}")

    excluded_columns = [
        "wallet",
        "first_seen",
        "last_seen",
        "anomaly_label",
        "anomaly_score",
        "anomaly_rank",
        "scenario_BURST",
        "scenario_FAN_IN",
        "scenario_FAN_OUT",
        "scenario_LAYERING",
        "scenario_NETWORK_LINKED",
        "scenario_NORMAL",
    ]

    feature_columns = [
        column
        for column in df.columns
        if column not in excluded_columns
        and pd.api.types.is_numeric_dtype(df[column])
    ]

    print(f"Clustering features used: {len(feature_columns)}")

    X = df[feature_columns].copy()

    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    ).fillna(0)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # HDBSCAN clustering
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=8,
        min_samples=5,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True
    )

    cluster_labels = clusterer.fit_predict(X_scaled)

    # Add cluster information
    df["cluster_id"] = cluster_labels

    # HDBSCAN membership probability
    df["cluster_probability"] = np.round(
        clusterer.probabilities_,
        3
    )

    # -1 means noise / isolated behavioral pattern
    df["cluster_type"] = np.where(
        df["cluster_id"] == -1,
        "NOISE",
        "BEHAVIOR_CLUSTER"
    )

    # Save model and scaler
    joblib.dump(clusterer, MODEL_FILE)
    joblib.dump(scaler, SCALER_FILE)

    # Save results
    df.to_csv(OUTPUT_FILE, index=False)

    # Statistics
    total_clusters = len(
        set(cluster_labels)
        - {-1}
    )

    noise_count = (
        df["cluster_id"] == -1
    ).sum()

    print("\nClustering complete.")

    print(
        f"Behavioral clusters found: {total_clusters}"
    )

    print(
        f"Noise / isolated wallets: {noise_count}"
    )

    print("\nCluster distribution:")

    print(
        df["cluster_id"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nTop wallets with cluster information:")

    print(
        df[
            [
                "wallet",
                "anomaly_label",
                "anomaly_score",
                "cluster_id",
                "cluster_probability",
                "cluster_type"
            ]
        ]
        .sort_values(
            "anomaly_score",
            ascending=False
        )
        .head(15)
        .to_string(index=False)
    )

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    print("\nModel saved to:")
    print(MODEL_FILE)

    return df


if __name__ == "__main__":
    run_clustering()
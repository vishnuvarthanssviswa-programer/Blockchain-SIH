import pandas as pd
import numpy as np
import joblib

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


INPUT_FILE = "data/wallet_features.csv"
OUTPUT_FILE = "data/anomaly_results.csv"

MODEL_FILE = "models/isolation_forest.pkl"
SCALER_FILE = "models/feature_scaler.pkl"


def run_anomaly_detection():

    print("=" * 60)
    print("TRINETRA - Isolation Forest Anomaly Detection")
    print("=" * 60)

    # ---------------------------------------------
    # Load features
    # ---------------------------------------------

    df = pd.read_csv(INPUT_FILE)

    print(f"\nWallets loaded: {len(df)}")

    # ---------------------------------------------
    # Select numerical ML features
    # ---------------------------------------------

    excluded_columns = [
        "wallet",
        "first_seen",
        "last_seen",

        # Ground-truth scenario columns
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

    X = df[feature_columns].copy()

    print(f"ML features used: {len(feature_columns)}")

    # ---------------------------------------------
    # Clean data
    # ---------------------------------------------

    X = X.replace(
        [np.inf, -np.inf],
        np.nan
    )

    X = X.fillna(0)

    # ---------------------------------------------
    # Scale features
    # ---------------------------------------------

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    # ---------------------------------------------
    # Isolation Forest
    # ---------------------------------------------

    model = IsolationForest(
        n_estimators=300,
        contamination=0.10,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_scaled)

    # ---------------------------------------------
    # Predictions
    # ---------------------------------------------

    predictions = model.predict(X_scaled)

    raw_scores = model.decision_function(X_scaled)

    # sklearn:
    # -1 = anomaly
    # +1 = normal

    df["anomaly_label"] = np.where(
        predictions == -1,
        "ANOMALY",
        "NORMAL"
    )

    # Convert score so larger = more suspicious
    anomaly_score = -raw_scores

    # Normalize to 0-100
    min_score = anomaly_score.min()
    max_score = anomaly_score.max()

    if max_score != min_score:
        anomaly_score = (
            (anomaly_score - min_score)
            / (max_score - min_score)
        ) * 100
    else:
        anomaly_score = np.zeros(len(df))

    df["anomaly_score"] = np.round(
        anomaly_score,
        2
    )

    # ---------------------------------------------
    # Rank wallets
    # ---------------------------------------------

    df["anomaly_rank"] = (
        df["anomaly_score"]
        .rank(
            ascending=False,
            method="first"
        )
        .astype(int)
    )

    df = df.sort_values(
        "anomaly_score",
        ascending=False
    )

    # ---------------------------------------------
    # Save model
    # ---------------------------------------------

    joblib.dump(
        model,
        MODEL_FILE
    )

    joblib.dump(
        scaler,
        SCALER_FILE
    )

    # ---------------------------------------------
    # Save results
    # ---------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------
    # Display results
    # ---------------------------------------------

    print("\nAnomaly detection complete.")

    print(
        f"Anomalies detected: "
        f"{(df['anomaly_label'] == 'ANOMALY').sum()}"
    )

    print(
        f"Normal wallets: "
        f"{(df['anomaly_label'] == 'NORMAL').sum()}"
    )

    print("\nTop 15 suspicious wallets:")

    print(
        df[
            [
                "wallet",
                "anomaly_label",
                "anomaly_score",
                "anomaly_rank"
            ]
        ].head(15).to_string(index=False)
    )

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    print("\nModel saved to:")
    print(MODEL_FILE)

    return df


if __name__ == "__main__":

    run_anomaly_detection()
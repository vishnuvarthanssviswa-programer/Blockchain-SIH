import pandas as pd
import numpy as np


def build_wallet_features(input_file="data/bitcoin_transactions.csv"):

    print("Loading transaction dataset...")

    df = pd.read_csv(input_file)

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # -------------------------------------------------
    # Create wallet-level transaction records
    # -------------------------------------------------

    sent = df[
        [
            "timestamp",
            "src_wallet",
            "dst_wallet",
            "amount_btc",
            "fee_btc",
            "src_ip",
            "scenario",
        ]
    ].copy()

    sent = sent.rename(
        columns={
            "src_wallet": "wallet",
            "dst_wallet": "counterparty",
            "src_ip": "ip",
        }
    )

    sent["direction"] = "OUT"

    received = df[
        [
            "timestamp",
            "src_wallet",
            "dst_wallet",
            "amount_btc",
            "fee_btc",
            "dst_ip",
            "scenario",
        ]
    ].copy()

    received = received.rename(
        columns={
            "dst_wallet": "wallet",
            "src_wallet": "counterparty",
            "dst_ip": "ip",
        }
    )

    received["direction"] = "IN"

    wallet_tx = pd.concat(
        [sent, received],
        ignore_index=True
    )

    # -------------------------------------------------
    # Basic transaction features
    # -------------------------------------------------

    grouped = wallet_tx.groupby("wallet")

    features = grouped.agg(
        transaction_count=("wallet", "count"),
        total_volume=("amount_btc", "sum"),
        avg_amount=("amount_btc", "mean"),
        amount_std=("amount_btc", "std"),
        avg_fee=("fee_btc", "mean"),
        unique_counterparties=("counterparty", "nunique"),
        unique_ips=("ip", "nunique"),
    ).reset_index()

    # -------------------------------------------------
    # Incoming / outgoing counts
    # -------------------------------------------------

    incoming = (
        wallet_tx[wallet_tx["direction"] == "IN"]
        .groupby("wallet")
        .size()
        .rename("fan_in")
    )

    outgoing = (
        wallet_tx[wallet_tx["direction"] == "OUT"]
        .groupby("wallet")
        .size()
        .rename("fan_out")
    )

    features = features.merge(
        incoming,
        on="wallet",
        how="left"
    )

    features = features.merge(
        outgoing,
        on="wallet",
        how="left"
    )

    features[["fan_in", "fan_out"]] = (
        features[["fan_in", "fan_out"]]
        .fillna(0)
    )

    # -------------------------------------------------
    # Temporal features
    # -------------------------------------------------

    temporal = grouped["timestamp"].agg(
        first_seen="min",
        last_seen="max"
    ).reset_index()

    features = features.merge(
        temporal,
        on="wallet",
        how="left"
    )

    features["active_duration_hours"] = (
        (
            features["last_seen"]
            - features["first_seen"]
        ).dt.total_seconds()
        / 3600
    )

    features["active_duration_hours"] = (
        features["active_duration_hours"]
        .fillna(0)
    )

    # Transaction velocity

    features["transaction_velocity"] = (
        features["transaction_count"]
        / (features["active_duration_hours"] + 1)
    )

    # -------------------------------------------------
    # IP repetition
    # -------------------------------------------------

    ip_counts = (
        wallet_tx.groupby(["wallet", "ip"])
        .size()
        .reset_index(name="ip_count")
    )

    ip_repetition = (
        ip_counts.groupby("wallet")["ip_count"]
        .max()
        .rename("max_ip_repetition")
    )

    features = features.merge(
        ip_repetition,
        on="wallet",
        how="left"
    )

    # -------------------------------------------------
    # Burstiness
    # -------------------------------------------------

    def calculate_burstiness(group):

        if len(group) < 2:
            return 0.0

        times = (
            group["timestamp"]
            .sort_values()
            .astype("int64")
            / 1e9
        )

        intervals = np.diff(times)

        if len(intervals) == 0:
            return 0.0

        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)

        if mean_interval == 0:
            return 0.0

        return float(std_interval / mean_interval)

    burst_values = (
        wallet_tx.groupby("wallet")
        .apply(calculate_burstiness, include_groups=False)
        .rename("burstiness")
    )

    features = features.merge(
        burst_values,
        on="wallet",
        how="left"
    )

    # -------------------------------------------------
    # Scenario indicators
    # -------------------------------------------------

    scenario_counts = pd.crosstab(
        wallet_tx["wallet"],
        wallet_tx["scenario"]
    )

    scenario_counts = scenario_counts.add_prefix(
        "scenario_"
    ).reset_index()

    features = features.merge(
        scenario_counts,
        on="wallet",
        how="left"
    )

    # -------------------------------------------------
    # Clean missing values
    # -------------------------------------------------

    numeric_columns = features.select_dtypes(
        include=np.number
    ).columns

    features[numeric_columns] = (
        features[numeric_columns]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    # -------------------------------------------------
    # Save
    # -------------------------------------------------

    output_file = "data/wallet_features.csv"

    features.to_csv(
        output_file,
        index=False
    )

    print()
    print("Feature engineering complete.")
    print(f"Wallets analyzed : {len(features)}")
    print(f"Features created : {len(features.columns)}")
    print(f"Saved to         : {output_file}")

    print()
    print("Feature columns:")
    print(list(features.columns))

    return features


if __name__ == "__main__":

    build_wallet_features()
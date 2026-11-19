import random
import string
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


NUM_TRANSACTIONS = 10000
NUM_WALLETS = 500


def generate_txid():
    return "".join(
        random.choices(string.hexdigits.lower(), k=64)
    )


def create_wallets():
    return [f"W{i:04d}" for i in range(1, NUM_WALLETS + 1)]


def normal_transaction(wallets, timestamp):
    src = random.choice(wallets)
    dst = random.choice(wallets)

    while dst == src:
        dst = random.choice(wallets)

    return {
        "timestamp": timestamp,
        "txid": generate_txid(),
        "src_wallet": src,
        "dst_wallet": dst,
        "amount_btc": round(np.random.lognormal(2.0, 1.0), 6),
        "fee_btc": round(random.uniform(0.00001, 0.005), 6),
        "src_ip": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
        "dst_ip": f"10.0.{random.randint(1,20)}.{random.randint(1,254)}",
        "src_port": random.choice([8333, 80, 443, 8080]),
        "dst_port": random.choice([8333, 80, 443]),
        "scenario": "NORMAL"
    }


def fan_out(wallets, timestamp, count=10):
    src = random.choice(wallets)

    destinations = random.sample(
        [w for w in wallets if w != src],
        count
    )

    rows = []

    for dst in destinations:
        rows.append({
            "timestamp": timestamp + timedelta(seconds=random.randint(1,120)),
            "txid": generate_txid(),
            "src_wallet": src,
            "dst_wallet": dst,
            "amount_btc": round(random.uniform(0.5,5.0),6),
            "fee_btc": round(random.uniform(0.0001,0.003),6),
            "src_ip": f"172.16.1.{random.randint(1,20)}",
            "dst_ip": f"10.10.{random.randint(1,10)}.{random.randint(1,254)}",
            "src_port": 8333,
            "dst_port": 8333,
            "scenario": "FAN_OUT"
        })

    return rows


def fan_in(wallets, timestamp, count=10):
    dst = random.choice(wallets)

    sources = random.sample(
        [w for w in wallets if w != dst],
        count
    )

    rows = []

    for src in sources:
        rows.append({
            "timestamp": timestamp + timedelta(seconds=random.randint(1,120)),
            "txid": generate_txid(),
            "src_wallet": src,
            "dst_wallet": dst,
            "amount_btc": round(random.uniform(0.5,5.0),6),
            "fee_btc": round(random.uniform(0.0001,0.003),6),
            "src_ip": f"172.20.{random.randint(1,10)}.{random.randint(1,254)}",
            "dst_ip": f"10.20.1.{random.randint(1,20)}",
            "src_port": 8333,
            "dst_port": 8333,
            "scenario": "FAN_IN"
        })

    return rows


def layering(wallets, timestamp, count=8):
    chain = random.sample(wallets, count)

    rows = []

    for i in range(len(chain)-1):
        rows.append({
            "timestamp": timestamp + timedelta(seconds=i*random.randint(20,90)),
            "txid": generate_txid(),
            "src_wallet": chain[i],
            "dst_wallet": chain[i+1],
            "amount_btc": round(random.uniform(0.2,3.0),6),
            "fee_btc": round(random.uniform(0.0001,0.002),6),
            "src_ip": f"100.64.{random.randint(1,20)}.{random.randint(1,254)}",
            "dst_ip": f"100.65.{random.randint(1,20)}.{random.randint(1,254)}",
            "src_port": 8333,
            "dst_port": 8333,
            "scenario": "LAYERING"
        })

    return rows


def burst(wallets, timestamp, count=20):
    src = random.choice(wallets)

    destinations = random.sample(
        [w for w in wallets if w != src],
        count
    )

    rows = []

    for dst in destinations:
        rows.append({
            "timestamp": timestamp + timedelta(milliseconds=random.randint(1,999)),
            "txid": generate_txid(),
            "src_wallet": src,
            "dst_wallet": dst,
            "amount_btc": round(random.uniform(0.1,2.0),6),
            "fee_btc": round(random.uniform(0.0001,0.002),6),
            "src_ip": f"203.0.113.{random.randint(1,20)}",
            "dst_ip": f"198.51.100.{random.randint(1,254)}",
            "src_port": random.choice([80,443,8333]),
            "dst_port": 8333,
            "scenario": "BURST"
        })

    return rows


def network_linked(wallets, timestamp, count=12):
    src = random.choice(wallets)

    shared_ip = f"45.67.89.{random.randint(1,20)}"

    rows = []

    for _ in range(count):
        dst = random.choice(wallets)

        while dst == src:
            dst = random.choice(wallets)

        rows.append({
            "timestamp": timestamp + timedelta(seconds=random.randint(1,300)),
            "txid": generate_txid(),
            "src_wallet": src,
            "dst_wallet": dst,
            "amount_btc": round(random.uniform(0.2,4.0),6),
            "fee_btc": round(random.uniform(0.0001,0.003),6),
            "src_ip": shared_ip,
            "dst_ip": f"10.30.{random.randint(1,20)}.{random.randint(1,254)}",
            "src_port": 8333,
            "dst_port": 8333,
            "scenario": "NETWORK_LINKED"
        })

    return rows


def generate_dataset():

    wallets = create_wallets()

    start_time = datetime.now() - timedelta(days=30)

    transactions = []

    while len(transactions) < NUM_TRANSACTIONS:

        timestamp = start_time + timedelta(
            seconds=random.randint(0, 30 * 24 * 60 * 60)
        )

        scenario = random.choice([
            "NORMAL",
            "FAN_OUT",
            "FAN_IN",
            "LAYERING",
            "BURST",
            "NETWORK_LINKED"
        ])

        if scenario == "NORMAL":
            transactions.append(
                normal_transaction(wallets, timestamp)
            )

        elif scenario == "FAN_OUT":
            transactions.extend(
                fan_out(wallets, timestamp)
            )

        elif scenario == "FAN_IN":
            transactions.extend(
                fan_in(wallets, timestamp)
            )

        elif scenario == "LAYERING":
            transactions.extend(
                layering(wallets, timestamp)
            )

        elif scenario == "BURST":
            transactions.extend(
                burst(wallets, timestamp)
            )

        elif scenario == "NETWORK_LINKED":
            transactions.extend(
                network_linked(wallets, timestamp)
            )

    df = pd.DataFrame(transactions)

    df = df.head(NUM_TRANSACTIONS)

    df = df.sort_values("timestamp")

    df = df.reset_index(drop=True)

    return df


if __name__ == "__main__":

    print("=" * 50)
    print("TRINETRA - Synthetic Bitcoin Dataset Generator")
    print("=" * 50)

    df = generate_dataset()

    output_file = "data/bitcoin_transactions.csv"

    df.to_csv(output_file, index=False)

    print(f"\nTransactions generated : {len(df):,}")
    print(f"Dataset saved           : {output_file}")

    print("\nScenario distribution:")
    print(df["scenario"].value_counts())

    print("\nFirst 5 transactions:")
    print(df.head())
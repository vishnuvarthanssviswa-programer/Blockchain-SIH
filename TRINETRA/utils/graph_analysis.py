import pandas as pd
import numpy as np
import networkx as nx

INPUT_FILE = "data/bitcoin_transactions.csv"
OUTPUT_FILE = "data/graph_features.csv"


def build_transaction_graph():

    print("=" * 60)
    print("TRINETRA - Bitcoin Transaction Graph Analysis")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    print(f"\nTransactions loaded: {len(df):,}")

    # ---------------------------------------------------------
    # Create directed transaction graph
    # ---------------------------------------------------------

    G = nx.DiGraph()

    for _, row in df.iterrows():

        src = row["src_wallet"]
        dst = row["dst_wallet"]

        amount = float(row["amount_btc"])

        if G.has_edge(src, dst):

            G[src][dst]["transaction_count"] += 1
            G[src][dst]["total_volume"] += amount

        else:

            G.add_edge(
                src,
                dst,
                transaction_count=1,
                total_volume=amount
            )

    print(f"Wallet nodes: {G.number_of_nodes():,}")
    print(f"Transaction edges: {G.number_of_edges():,}")

    # ---------------------------------------------------------
    # Basic degree features
    # ---------------------------------------------------------

    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    total_degree = {
        node: in_degree.get(node, 0) +
        out_degree.get(node, 0)
        for node in G.nodes()
    }

    # ---------------------------------------------------------
    # Weighted transaction volume
    # ---------------------------------------------------------

    incoming_volume = {}

    outgoing_volume = {}

    for node in G.nodes():

        outgoing_volume[node] = sum(
            data.get("total_volume", 0)
            for _, _, data in G.out_edges(
                node,
                data=True
            )
        )

        incoming_volume[node] = sum(
            data.get("total_volume", 0)
            for _, _, data in G.in_edges(
                node,
                data=True
            )
        )

    # ---------------------------------------------------------
    # PageRank
    # ---------------------------------------------------------

    print("\nCalculating PageRank...")

    try:

        pagerank = nx.pagerank(
            G,
            alpha=0.85
        )

    except Exception:

        pagerank = {
            node: 0.0
            for node in G.nodes()
        }

    # ---------------------------------------------------------
    # Betweenness centrality
    # ---------------------------------------------------------

    print("Calculating betweenness centrality...")

    try:

        betweenness = nx.betweenness_centrality(
            G,
            normalized=True
        )

    except Exception:

        betweenness = {
            node: 0.0
            for node in G.nodes()
        }

    # ---------------------------------------------------------
    # Clustering coefficient
    # ---------------------------------------------------------

    print("Calculating clustering coefficient...")

    undirected_graph = G.to_undirected()

    clustering = nx.clustering(
        undirected_graph
    )

    # ---------------------------------------------------------
    # Build feature table
    # ---------------------------------------------------------

    wallets = sorted(G.nodes())

    features = pd.DataFrame({
        "wallet": wallets,

        "graph_in_degree": [
            in_degree.get(w, 0)
            for w in wallets
        ],

        "graph_out_degree": [
            out_degree.get(w, 0)
            for w in wallets
        ],

        "graph_total_degree": [
            total_degree.get(w, 0)
            for w in wallets
        ],

        "incoming_volume": [
            incoming_volume.get(w, 0)
            for w in wallets
        ],

        "outgoing_volume": [
            outgoing_volume.get(w, 0)
            for w in wallets
        ],

        "pagerank": [
            pagerank.get(w, 0)
            for w in wallets
        ],

        "betweenness_centrality": [
            betweenness.get(w, 0)
            for w in wallets
        ],

        "clustering_coefficient": [
            clustering.get(w, 0)
            for w in wallets
        ]
    })

    # ---------------------------------------------------------
    # Numerical cleanup
    # ---------------------------------------------------------

    numeric_columns = features.select_dtypes(
        include=np.number
    ).columns

    features[numeric_columns] = (
        features[numeric_columns]
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    features.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nGraph analysis complete.")

    print(
        f"Wallets analyzed: {len(features)}"
    )

    print(
        f"Graph features created: "
        f"{len(features.columns) - 1}"
    )

    print("\nTop PageRank wallets:")

    print(
        features[
            [
                "wallet",
                "pagerank",
                "graph_in_degree",
                "graph_out_degree"
            ]
        ]
        .sort_values(
            "pagerank",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )

    print("\nTop betweenness wallets:")

    print(
        features[
            [
                "wallet",
                "betweenness_centrality",
                "graph_total_degree"
            ]
        ]
        .sort_values(
            "betweenness_centrality",
            ascending=False
        )
        .head(10)
        .to_string(index=False)
    )

    print("\nResults saved to:")
    print(OUTPUT_FILE)

    return features


if __name__ == "__main__":
    build_transaction_graph()
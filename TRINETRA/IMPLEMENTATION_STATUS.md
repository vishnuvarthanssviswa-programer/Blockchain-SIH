# TRINETRA executable technical-flow status

## Implemented end to end

- CSV, JSON and XML validation and ingestion
- SHA-256 input evidence fingerprinting
- Network and blockchain record correlation
- Isolation Forest anomaly detection
- HDBSCAN clustering with DBSCAN fallback
- NetworkX graph features and interactive transaction graph
- XGBoost pattern-risk fusion and feature-contribution explanations
- Risk-ranked investigation queue and transaction timeline
- Confidence-scored IP-to-wallet evidence with shared-IP safeguards
- Persistent SQLite cases, selected leads, notes and audit events
- PDF investigation reports and CSV/manifest exports
- Fully local Streamlit interface
- Optional FastAPI endpoints and interactive API documentation
- Secure local login gate and logout
- Unified Wallet / TXID / IP search
- Visible seven-stage pipeline runner with per-stage output inspection
- Polars CSV ingestion with Pandas fallback
- One-click Windows launcher with dependency and startup checks

## Deployment adapters, not duplicated in the demo

- SQLite is the working offline database. PostgreSQL is a production alternative.
- NetworkX is the working graph engine. Neo4j is a scale-out alternative.
- GraphSAGE/GAT remains an explicitly labelled future enhancement, matching the PPT.
- Automatic GeoIP requires a licensed/downloaded local GeoLite2 database. Supplied geo_country and ASN fields are retained without making network calls.

## Responsible-use boundary

All scores and associations are investigation leads. They do not prove wallet ownership, identity, or criminal activity. Human review and corroborating evidence are required.

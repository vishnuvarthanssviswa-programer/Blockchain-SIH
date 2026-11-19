# TRINETRA - complete executable technical-flow prototype

This version extends your existing Streamlit project. It uses the included 10,000 synthetic transactions and 500 stored wallet risk results. The original analysis scripts, datasets and models are preserved. `app_original.py` is your previous interface.

## Run on Windows

1. Install **64-bit Python 3.11** from Python.org. Keep the Python Launcher selected during installation.
2. Extract this ZIP fully.
3. Double-click `START_WINDOWS.bat`.
4. Keep the server window open and use `http://localhost:8501`.
5. Login with `investigator` / `Trinetra@2026`.

The first run downloads the required open-source Python packages. Later runs remain local.

If you previously ran an older package, delete its `.venv` folder before starting this corrected edition. The launcher intentionally refuses Python 3.12/3.13/3.14 and 32-bit Python so pip cannot fall back to compiling NumPy from source.

Manual alternative:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dashboard.txt
.venv\Scripts\python -m streamlit run app.py
```

The terminal displays a local address, normally http://localhost:8501. Keep the terminal open while using the dashboard. Python 3.11 or newer is recommended. Installation needs internet; the dashboard needs no cloud API or external graph assets after installation.

## Execute the complete architecture flow

Open **Technical pipeline** and select **Run complete 7-stage pipeline**. The prototype executes and exposes:

1. Validated CSV/JSON/XML network and blockchain ingestion.
2. Cleaning, normalization and wallet-level feature extraction.
3. Isolation Forest anomaly detection and HDBSCAN clustering.
4. NetworkX wallet/transaction/IP knowledge graph.
5. XGBoost pattern-risk fusion and feature-contribution explanations.
6. Offline geo-country and ASN evidence context.
7. ReportLab PDF creation and SHA-256 integrity verification.

Use the stage selector to inspect the actual input and output of each stage. **Unified search** searches wallet addresses, transaction IDs and IP observations from the active dataset.

If your existing Python environment already has the dashboard dependencies, run `python -m streamlit run app.py`, or double-click START_WINDOWS.bat. The batch file uses your default Python, not a newly created virtual environment.

On Linux/macOS, replace `.venv\Scripts\python` with `.venv/bin/python` in the commands above.

## Quick graph preview

Double-click GRAPH_PREVIEW.html to inspect an interactive graph of W0240 without installing anything. This is a fixed graph sample, not the complete dashboard. It supports zoom, node dragging, link/node details and neighbour highlighting. The full app lets you change wallets and tracing settings.

## Demo flow

1. Dashboard: show transaction counts, observed activity, priorities and the network.
2. Investigation queue: filter priorities, search wallet IDs or evidence and export matching rows. Select a row, then open Wallet investigation.
3. Wallet investigation: explain the actual score contributions, inspect the timeline and export a PDF.
4. Transaction graph: choose Incoming, Outgoing or Both; try two hops; optionally include IP observations. Click a link to see aggregated BTC, transaction count and observation dates.

## What changed

- Dark navy and teal dashboard with consistently coloured priorities.
- Interactive offline graph with directed links, node dragging, zoom and details.
- Repeated transfers aggregate amounts and counts instead of overwriting each other.
- Bounded one-/two-hop exploration, with neighbours ranked by transaction volume.
- Clear IP observation links without an ownership claim.
- Searchable priority queue, CSV exports, transaction activity and wallet timeline.
- Actual weighted score contributions and a wrapped, single-page PDF report.
- Absolute data paths relative to app.py, so launching from another directory works.
- Refresh button reloads updated on-disk analysis results.
- Original requirements.txt converted from UTF-16 to UTF-8 without changing its package list.
- Separate small dashboard requirements: no ML training dependencies needed for viewing results.

## What the prototype does and does not calculate

Uploaded datasets run Isolation Forest anomaly detection, behavioural clustering, graph analytics and XGBoost pattern-risk fusion. XGBoost contribution values explain why a score moved up or down. The target is derived from transparent risk heuristics because the prototype has no verified criminal labels; it is a triage score, never proof of wrongdoing.

The local SQLite case workspace preserves cases, selected wallet leads, notes, dataset fingerprints and an audit trail. The IP ↔ Wallet page calculates evidence confidence from repetition, time diversity and IP specificity. It explicitly accounts for shared infrastructure and never claims ownership. Optional geo_country/ASN fields are retained for offline datasets.

An optional FastAPI service is included. Run `python -m uvicorn api:app --port 8000` and open `http://127.0.0.1:8000/docs`.

Demo scores and scenario labels come from the supplied synthetic dataset. Uploaded scores come from the active upload and locally fitted models. IP links represent network observations alongside transactions, not verified owners. The graph deliberately limits wallet count for readability; visible graph totals are labelled separately from full-dataset scores. Its exports contain exactly the transaction rows represented by the view.

The SHA-256 report field fingerprints the input CSV; it is not proof of provenance or a digital signature. The included model pickle files are preserved but are not loaded by this dashboard.

## Validation

Streamlit AppTest exercised all four pages and filtering/settings flows without application exceptions. Graph checks verified wallet limits, edge endpoints, exact row counts and BTC aggregation across both depths and all directions. JavaScript syntax was checked. The generated PDF was rendered and inspected. No interactive browser visual test was performed.


## Offline upload update

Open **Upload dataset**, select CSV/JSON/XML, then click **Validate and run offline analysis**. The active upload updates Dashboard, Investigation queue, Wallet investigation and Transaction graph. Downloads and PDFs use the active upload. Use **Return to included demo dataset** to reset.

To download a PDF: **Wallet investigation -> choose a wallet -> Behaviour & report -> Download investigation PDF**. The report includes source filename, exact input SHA-256, score contributions, evidence and limitations. Uploaded files stay in local server session memory; they are not sent to external APIs or saved automatically. Export results before closing the session.

Initial dependency installation requires internet. After installation the processing works offline on Linux or Windows. Reinstall `requirements-dashboard.txt` after this update to obtain scikit-learn and NetworkX.

Required common fields: timestamp, txid, src_ip, dst_ip, src_port, dst_port.
Choose either flat fields (src_wallet, dst_wallet, amount_btc), or arrays (input_addresses, output_addresses, input_amounts, output_amounts). CSV arrays are JSON lists in quoted cells. JSON supports a list or a transactions/records wrapper; XML supports transaction records beneath a root, with item children for arrays. BTC is the expected amount unit. Optional fee, script_type, geo_country/asn are preserved.

Multiple inputs/outputs connect through a TX: transaction node, without inventing an input-output mapping. Each graph hop is an entity edge: for Bitcoin arrays, wallet -> transaction -> wallet takes two hops. The node limit includes transaction nodes. Recorded amounts are observed flow-leg volumes; summing both input and output legs is not a unique amount of money transferred. Distinct repeated network observations can also repeat a flow amount. Interpret volume totals in this observation context.

The samples folder includes matching synthetic CSV, JSON and XML files (36 transactions, 12 wallets) to test the workflow. Limits: 25 MB, 50,000 input records, 100,000 expanded legs, 5,000 entities, minimum 5 wallets. Invalid data is rejected rather than silently skipped.

### Model approach and explainability

Uploaded datasets use log-transformed transaction count, amount mean/variation, transaction velocity, observed IP count, graph degree, incoming and outgoing volume. RobustScaler prepares these features. Isolation Forest (160 trees, seed 42) produces a fitted anomaly score, displayed as a percentile relative to the uploaded dataset. DBSCAN clusters behaviour; outliers receive a cluster risk component. This baseline differs from the original precomputed demo's HDBSCAN results.

Risk remains an explicit weighted ranking (50% anomaly percentile + 20% cluster risk + 30% graph risk). Graph risk weights normalized PageRank, sampled betweenness and degree. Explanations report arithmetic contributions and two features most distant from the dataset median; these are descriptive feature deviations, not SHAP attribution or model causality. DBSCAN does not produce calibrated membership probabilities, so the UI reports these as unavailable.

No score is presented as a probability of criminality. Network metadata contributes observed IP diversity and visual associations, but full temporal network-to-blockchain correlation and calibrated association confidence remain future work. Geo/ASN values are retained, not independently enriched. No accuracy or validation metrics are claimed without a labelled held-out evaluation.

Validation: matched normalized graphs across CSV/JSON/XML, rejected malformed samples, exercised all five pages with uploaded state, verified multi-input/output transaction nodes, graph count aggregation, and report filename/hash. PDF rendered and inspected. Upload parsing and analysis were tested programmatically; native browser file-picker interactions were not browser-tested.

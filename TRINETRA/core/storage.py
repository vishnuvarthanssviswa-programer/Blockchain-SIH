import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "trinetra.db"

def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS datasets(
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, sha256 TEXT UNIQUE NOT NULL,
      imported_at TEXT NOT NULL, record_count INTEGER NOT NULL, wallet_count INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS cases(
      id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'OPEN',
      priority TEXT NOT NULL DEFAULT 'MEDIUM', notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS case_wallets(
      case_id INTEGER NOT NULL, wallet TEXT NOT NULL, risk_score REAL,
      rationale TEXT NOT NULL DEFAULT '', added_at TEXT NOT NULL,
      PRIMARY KEY(case_id,wallet), FOREIGN KEY(case_id) REFERENCES cases(id));
    CREATE TABLE IF NOT EXISTS audit_log(
      id INTEGER PRIMARY KEY, action TEXT NOT NULL, details TEXT NOT NULL,
      created_at TEXT NOT NULL);
    """)
    return con

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def register_dataset(name, digest, records, wallets):
    with connect() as con:
        con.execute("INSERT OR IGNORE INTO datasets(name,sha256,imported_at,record_count,wallet_count) VALUES(?,?,?,?,?)",
                    (name,digest,now(),records,wallets))
        con.execute("INSERT INTO audit_log(action,details,created_at) VALUES(?,?,?)",
                    ("DATASET_ANALYSED",json.dumps({"name":name,"sha256":digest}),now()))

def create_case(title, priority="MEDIUM", notes=""):
    stamp=now()
    with connect() as con:
        cur=con.execute("INSERT INTO cases(title,status,priority,notes,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                        (title,"OPEN",priority,notes,stamp,stamp))
        case_id=cur.lastrowid
        con.execute("INSERT INTO audit_log(action,details,created_at) VALUES(?,?,?)",
                    ("CASE_CREATED",json.dumps({"case_id":case_id,"title":title}),stamp))
    return case_id

def list_cases():
    with connect() as con:
        return [dict(x) for x in con.execute("SELECT c.*,COUNT(w.wallet) wallet_count FROM cases c LEFT JOIN case_wallets w ON c.id=w.case_id GROUP BY c.id ORDER BY c.updated_at DESC")]

def add_wallet(case_id,wallet,risk_score,rationale):
    stamp=now()
    with connect() as con:
        con.execute("INSERT OR REPLACE INTO case_wallets(case_id,wallet,risk_score,rationale,added_at) VALUES(?,?,?,?,?)",
                    (case_id,wallet,float(risk_score),rationale,stamp))
        con.execute("UPDATE cases SET updated_at=? WHERE id=?",(stamp,case_id))
        con.execute("INSERT INTO audit_log(action,details,created_at) VALUES(?,?,?)",
                    ("WALLET_ADDED",json.dumps({"case_id":case_id,"wallet":wallet}),stamp))

def case_wallets(case_id):
    with connect() as con:
        return [dict(x) for x in con.execute("SELECT * FROM case_wallets WHERE case_id=? ORDER BY risk_score DESC",(case_id,))]


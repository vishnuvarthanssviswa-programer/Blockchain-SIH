from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException
from core.storage import list_cases, case_wallets

BASE=Path(__file__).resolve().parent
app=FastAPI(title="TRINETRA Offline API",version="1.0")

@app.get('/health')
def health(): return {'status':'ok','mode':'offline'}

@app.get('/leads')
def leads(limit:int=25):
    df=pd.read_csv(BASE/'data/risk_results.csv').sort_values('risk_score',ascending=False)
    return df.head(max(1,min(limit,250))).fillna('').to_dict('records')

@app.get('/wallets/{wallet}')
def wallet(wallet:str):
    df=pd.read_csv(BASE/'data/risk_results.csv')
    row=df[df.wallet.eq(wallet)]
    if row.empty:raise HTTPException(404,'Wallet not found')
    return row.fillna('').iloc[0].to_dict()

@app.get('/cases')
def cases(): return list_cases()

@app.get('/cases/{case_id}/wallets')
def wallets(case_id:int): return case_wallets(case_id)

"""Local validated ingestion and reproducible, unsupervised ML analysis."""
import hashlib
import io
import json
import ipaddress
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN, HDBSCAN
from sklearn.preprocessing import RobustScaler
import networkx as nx


def parse_dataset(raw, filename):
    if len(raw)>25*1024*1024:raise ValueError('Maximum upload size is 25 MB.')
    suffix=filename.rsplit('.',1)[-1].lower()
    try:
        if suffix=='csv':
            try:
                import polars as pl
                frame=pl.read_csv(io.BytesIO(raw),infer_schema_length=10000).to_pandas()
                frame=frame.fillna('')
            except ImportError:
                frame=pd.read_csv(io.BytesIO(raw),dtype=str,keep_default_na=False)
        elif suffix=='json':
            obj=json.loads(raw)
            if isinstance(obj,dict):obj=obj.get('transactions',obj.get('records'))
            if not isinstance(obj,list):raise ValueError('JSON must be a list, or an object with a transactions/records list.')
            frame=pd.DataFrame(obj)
        elif suffix=='xml':
            content=raw.decode('utf-8-sig')
            if '<!DOCTYPE' in content.upper() or '<!ENTITY' in content.upper():raise ValueError('XML DTDs and entities are not supported.')
            root=ET.fromstring(content)
            frame=pd.DataFrame([{e.tag:([c.text for c in e] if len(e) else e.text) for e in record} for record in root])
        else:raise ValueError('Choose CSV, JSON or XML.')
    except (ET.ParseError,json.JSONDecodeError,UnicodeDecodeError,pd.errors.ParserError) as exc:raise ValueError('Could not parse file: '+str(exc)) from exc
    frame.columns=[str(c).strip().replace('[]','') for c in frame.columns]
    required=['timestamp','txid','src_ip','dst_ip','src_port','dst_port']
    missing=[x for x in required if x not in frame]
    if missing:raise ValueError('Missing columns: '+', '.join(missing))
    if frame.empty:raise ValueError('Dataset has no records.')
    if len(frame)>50000:raise ValueError('Prototype limit: 50,000 input records.')
    def array(value):
        if isinstance(value,list):return value
        if isinstance(value,str) and value.strip().startswith('['):return json.loads(value)
        return [value]
    records=[]
    for index,row in frame.iterrows():
        try:
            common=row.to_dict()
            for key in required:
                if pd.isna(common[key]) or not str(common[key]).strip():raise ValueError(key+' is empty')
            for key in ['src_ip','dst_ip']:ipaddress.ip_address(str(common[key]))
            for key in ['src_port','dst_port']:
                port=float(common[key])
                if not port.is_integer() or not 0<=port<=65535:raise ValueError('invalid '+key)
                common[key]=int(port)
            common['timestamp']=pd.to_datetime(common['timestamp'],utc=True).tz_convert(None)
            if pd.isna(common['timestamp']):raise ValueError('invalid timestamp')
            common['fee_btc']=float(common.get('fee_btc',common.get('fee',0)) or 0)
            if not np.isfinite(common['fee_btc']) or common['fee_btc']<0:raise ValueError('fee must be finite and nonnegative')
            if all(k in common for k in ['src_wallet','dst_wallet','amount_btc']):
                legs=[(common['src_wallet'],common['dst_wallet'],common['amount_btc'])]
            else:
                inputs=array(common.get('input_addresses',[]));outputs=array(common.get('output_addresses',[]))
                ina=array(common.get('input_amounts',[]));outa=array(common.get('output_amounts',[]))
                if not inputs or not outputs or len(inputs)!=len(ina) or len(outputs)!=len(outa):raise ValueError('Provide matching input_addresses/input_amounts and output_addresses/output_amounts arrays')
                hub='TX:'+str(common['txid'])
                legs=[(w,hub,a) for w,a in zip(inputs,ina)]+[(hub,w,a) for w,a in zip(outputs,outa)]
            for src,dst,amount in legs:
                amount=float(amount)
                if not np.isfinite(amount) or amount<0:raise ValueError('amount must be finite and nonnegative')
                if src is None or dst is None or not str(src).strip() or not str(dst).strip():raise ValueError('empty wallet address')
                if len(str(src))>160 or len(str(dst))>160:raise ValueError('identifier longer than 160 characters')
                records.append({**common,'src_wallet':str(src),'dst_wallet':str(dst),'amount_btc':amount})
        except (ValueError,TypeError,OverflowError) as exc:raise ValueError(f'Record {index+1}: {exc}') from exc
    tx=pd.DataFrame(records)
    # Keep distinct network observations; collapse only identical normalized records.
    tx=tx.drop_duplicates(subset=['txid','timestamp','src_ip','dst_ip','src_port','dst_port','src_wallet','dst_wallet','amount_btc']).reset_index(drop=True)
    if len(tx)>100000:raise ValueError('Expanded graph exceeds the prototype limit of 100,000 records.')
    ids=set(tx.src_wallet)|set(tx.dst_wallet)
    if len(ids)>5000:raise ValueError('Prototype limit: 5,000 graph entities.')
    return tx,hashlib.sha256(raw).hexdigest()


def analyse(tx):
    g=nx.DiGraph()
    for r in tx.itertuples():
        if g.has_edge(r.src_wallet,r.dst_wallet):g[r.src_wallet][r.dst_wallet]['weight']+=r.amount_btc
        else:g.add_edge(r.src_wallet,r.dst_wallet,weight=r.amount_btc)
    pr=nx.pagerank(g,weight='weight')
    central=nx.betweenness_centrality(g,k=min(50,len(g)),seed=42)
    rows=[]
    for wallet in sorted(g.nodes):
        if wallet.startswith('TX:'):continue
        outgoing=tx[tx.src_wallet.eq(wallet)];incoming=tx[tx.dst_wallet.eq(wallet)]
        records=tx[tx.src_wallet.eq(wallet)|tx.dst_wallet.eq(wallet)]
        hours=max((records.timestamp.max()-records.timestamp.min()).total_seconds()/3600,1)
        ips=set(outgoing.src_ip.astype(str))|set(incoming.dst_ip.astype(str))
        rows.append(dict(wallet=wallet,tx_count=records.txid.nunique(),mean_amount=records.amount_btc.mean(),std_amount=records.amount_btc.std(ddof=0),velocity=records.txid.nunique()/hours,unique_ips=len(ips),graph_in_degree=g.in_degree(wallet),graph_out_degree=g.out_degree(wallet),graph_total_degree=g.degree(wallet),incoming_volume=incoming.amount_btc.sum(),outgoing_volume=outgoing.amount_btc.sum(),pagerank=pr[wallet],betweenness_centrality=central[wallet]))
    df=pd.DataFrame(rows)
    if len(df)<5:raise ValueError('Analysis needs at least 5 distinct wallets. Upload a larger dataset.')
    features=['tx_count','mean_amount','std_amount','velocity','unique_ips','graph_total_degree','incoming_volume','outgoing_volume']
    x=RobustScaler().fit_transform(np.log1p(df[features].to_numpy(dtype=float)))
    model=IsolationForest(n_estimators=160,contamination='auto',random_state=42,n_jobs=-1).fit(x)
    raw=-model.score_samples(x)
    # Dataset-relative anomaly percentile; no calibrated criminality probability.
    df['anomaly_score']=pd.Series(raw).rank(pct=True,method='average').to_numpy()*100
    df['anomaly_label']=np.where(model.predict(x)==-1,'ANOMALY','NORMAL')
    try:
        clusterer=HDBSCAN(min_cluster_size=max(3,min(12,len(df)//8))).fit(x)
        df['cluster_id']=clusterer.labels_
        df['cluster_probability']=clusterer.probabilities_
        cluster_name='HDBSCAN'
    except (ValueError,AttributeError):
        df['cluster_id']=DBSCAN(eps=1.8,min_samples=3).fit_predict(x)
        df['cluster_probability']=np.nan
        cluster_name='DBSCAN fallback'
    df['cluster_risk']=np.where(df.cluster_id.eq(-1),100.,0.)
    for src,dst in [('pagerank','pagerank_norm'),('betweenness_centrality','betweenness_norm'),('graph_total_degree','degree_norm')]:
        span=df[src].max()-df[src].min();df[dst]=(df[src]-df[src].min())/span if span else 0.
    df['graph_risk']=100*(.4*df.pagerank_norm+.35*df.betweenness_norm+.25*df.degree_norm)
    # Pattern-derived training target lets XGBoost learn nonlinear fusion without
    # pretending that synthetic heuristics are verified criminal labels.
    base=(.5*df.anomaly_score+.2*df.cluster_risk+.3*df.graph_risk).clip(0,100)
    model_features=features+['pagerank','betweenness_centrality','cluster_risk','graph_risk']
    try:
        from xgboost import XGBRegressor
        model=XGBRegressor(n_estimators=120,max_depth=3,learning_rate=.05,subsample=.85,colsample_bytree=.85,random_state=42,n_jobs=1)
        model.fit(df[model_features],base)
        df['risk_score']=model.predict(df[model_features]).clip(0,100).round(2)
        booster=model.get_booster()
        contrib=booster.predict(__import__('xgboost').DMatrix(df[model_features]),pred_contribs=True)
        for j,name in enumerate(model_features):df['shap_'+name]=contrib[:,j]
        df['model_type']='XGBoost pattern-risk fusion'
    except (ImportError,ValueError):
        df['risk_score']=base.round(2)
        for name in model_features:df['shap_'+name]=0.
        df['model_type']='weighted risk fusion (XGBoost unavailable)'
    df['risk_level']=pd.cut(df.risk_score,[-1,39.999,59.999,79.999,101],labels=['LOW','MEDIUM','HIGH','CRITICAL']).astype(str)
    z=np.abs(x-np.median(x,axis=0))
    evidence=[]
    for i,r in df.iterrows():
        unusual=[features[j].replace('_',' ') for j in np.argsort(z[i])[-2:][::-1]]
        evidence.append('Isolation Forest anomaly percentile '+f'{r.anomaly_score:.1f}'+ '; Most unusual measured features: '+', '.join(unusual)+(f'; {cluster_name} behavioural outlier' if r.cluster_id==-1 else f'; {cluster_name} cluster '+str(r.cluster_id)))
    df['risk_evidence']=evidence
    shap_cols=['shap_'+x for x in model_features]
    df['top_explanation']=df.apply(lambda r:'; '.join(f"{c[5:].replace('_',' ')} {r[c]:+.2f}" for c in sorted(shap_cols,key=lambda c:abs(r[c]),reverse=True)[:3]),axis=1)
    return df.sort_values('risk_score',ascending=False).reset_index(drop=True)

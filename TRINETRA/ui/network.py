"""Bounded, deterministic graph views with exact transfer aggregation."""
import json
import math
from pathlib import Path
import pandas as pd


def build_graph(tx, risk, center, hops=1, direction='Both', max_wallets=24, show_ips=False):
    selected = {center}
    frontier = {center}
    for depth in range(hops):
        incoming = tx[tx.dst_wallet.isin(frontier)] if direction != 'Outgoing' else tx.iloc[:0]
        outgoing = tx[tx.src_wallet.isin(frontier)] if direction != 'Incoming' else tx.iloc[:0]
        candidates = pd.concat([incoming, outgoing]).drop_duplicates(subset=['txid','timestamp','src_wallet','dst_wallet','amount_btc','src_ip','dst_ip'])
        totals = {}
        for row in candidates.itertuples():
            for wallet in (row.src_wallet, row.dst_wallet):
                if wallet not in selected:
                    totals[wallet] = totals.get(wallet, 0) + float(row.amount_btc)
        next_nodes = sorted(totals, key=lambda w: (-totals[w], w))[:max(0, math.ceil((max_wallets-len(selected))/(hops-depth)))]
        frontier = set(next_nodes)
        selected.update(frontier)
        if not frontier:
            break
    related = tx[tx.src_wallet.isin(selected) & tx.dst_wallet.isin(selected)].copy()
    if direction == 'Incoming':
        related = related[related.src_wallet.ne(center)]
    elif direction == 'Outgoing':
        related = related[related.dst_wallet.ne(center)]
    lookup = risk.set_index('wallet').to_dict('index')
    nodes = []
    for i, wallet in enumerate([center] + sorted(selected-{center})):
        records = related[(related.src_wallet == wallet) | (related.dst_wallet == wallet)]
        r = lookup.get(wallet, {})
        angle = (i-1)*2*math.pi/max(1,len(selected)-1)
        nodes.append(dict(id=wallet,kind=('transaction' if wallet.startswith('TX:') else 'wallet'),x=400 if i==0 else 400+295*math.cos(angle),y=240 if i==0 else 240+175*math.sin(angle),risk=r.get('risk_score'),level=r.get('risk_level','UNKNOWN'),evidence=r.get('risk_evidence',''),count=len(records),volume=float(records.amount_btc.sum())))
    edges = []
    for (src,dst), records in related.groupby(['src_wallet','dst_wallet']):
        edges.append(dict(source=src,target=dst,kind='transfer',amount=float(records.amount_btc.sum()),count=len(records),first=str(records.timestamp.min()),last=str(records.timestamp.max())))
    if show_ips:
        observations = []
        for row in related.itertuples():
            if row.src_wallet == center: observations.append((str(row.src_ip),row.timestamp))
            if row.dst_wallet == center: observations.append((str(row.dst_ip),row.timestamp))
        ips = pd.DataFrame(observations,columns=['ip','timestamp'])
        for i,ip in enumerate(ips.ip.value_counts().head(4).index):
            records=ips[ips.ip==ip]
            node_id='IP '+ip
            nodes.append(dict(id=node_id,kind='ip',x=160+i*160,y=445,level='OBSERVATION',count=len(records)))
            edges.append(dict(source=node_id,target=center,kind='observation',count=len(records),first=str(records.timestamp.min()),last=str(records.timestamp.max())))
    return dict(center=center,nodes=nodes,edges=edges),related


def graph_html(data):
    template=(Path(__file__).parent/'graph.html').read_text(encoding='utf-8')
    payload=json.dumps(data,ensure_ascii=True,allow_nan=False).replace('<','\\u003c')
    return template.replace('__GRAPH_DATA__',payload)

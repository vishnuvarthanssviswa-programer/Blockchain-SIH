import math
import pandas as pd

def ip_wallet_associations(tx):
    """Evidence confidence, never an ownership probability."""
    observations=[]
    for r in tx.itertuples():
        observations.extend([(str(r.src_ip),str(r.src_wallet),r.timestamp,str(r.txid)),
                             (str(r.dst_ip),str(r.dst_wallet),r.timestamp,str(r.txid))])
    df=pd.DataFrame(observations,columns=['ip','wallet','timestamp','txid'])
    if df.empty:return pd.DataFrame(columns=['ip','wallet','confidence','observations','distinct_days','specificity','reason'])
    pair=df.groupby(['ip','wallet']).agg(observations=('txid','nunique'),distinct_days=('timestamp',lambda x:pd.Series(x).dt.date.nunique())).reset_index()
    counts=df.groupby('ip').wallet.nunique().rename('wallets_on_ip')
    pair=pair.join(counts,on='ip')
    pair['specificity']=1/pair.wallets_on_ip.clip(lower=1)
    repeat=pair.observations.map(lambda n:1-math.exp(-n/3))
    days=pair.distinct_days.map(lambda n:1-math.exp(-n/2))
    pair['confidence']=(100*(.45*repeat+.25*days+.30*pair.specificity)).clip(0,95).round(1)
    pair['reason']=pair.apply(lambda r:f"{r.observations} observations across {r.distinct_days} day(s); IP shared by {r.wallets_on_ip} wallet(s)",axis=1)
    return pair.sort_values('confidence',ascending=False).reset_index(drop=True)


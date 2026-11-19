from pathlib import Path
import hashlib
import html
import io
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from ui.network import build_graph, graph_html
from ui.reports import create_pdf
from ui.ingestion import parse_dataset, analyse
from core.associations import ip_wallet_associations
from core.storage import register_dataset, create_case, list_cases, add_wallet, case_wallets

BASE = Path(__file__).resolve().parent
st.set_page_config(page_title='TRINETRA | Investigation workspace',page_icon='◈',layout='wide')
COLORS={'CRITICAL':'#f87889','HIGH':'#f39a6c','MEDIUM':'#f6c66a','LOW':'#6e9ed9'}

def login_gate():
    if st.session_state.get('authenticated'):return
    st.markdown('<div style="max-width:460px;margin:8vh auto 20px;text-align:center;padding:30px;border:1px solid #29425c;border-radius:18px;background:#102036"><div style="font-size:34px;color:#55dfc8;font-weight:800;letter-spacing:5px">◈ TRINETRA</div><div style="color:#9ab0c9;margin-top:10px">SECURE OFFLINE INVESTIGATION WORKSPACE</div></div>',unsafe_allow_html=True)
    _,mid,_=st.columns([1,1.1,1])
    with mid:
        with st.form('login'):
            username=st.text_input('Investigator ID',value='investigator')
            password=st.text_input('Password',type='password',value='Trinetra@2026')
            submitted=st.form_submit_button('Secure login',type='primary',use_container_width=True)
        if submitted:
            valid_user=username.strip()=='investigator'
            valid_password=hashlib.sha256(password.encode()).hexdigest()==hashlib.sha256(b'Trinetra@2026').hexdigest()
            if valid_user and valid_password:st.session_state['authenticated']=True;st.rerun()
            else:st.error('Incorrect investigator ID or password.')
        st.caption('Demo login: investigator / Trinetra@2026')
    st.stop()

login_gate()

@st.cache_data
def load_data(signature):
    risk=pd.read_csv(BASE/'data/risk_results.csv').sort_values('risk_score',ascending=False).reset_index(drop=True)
    tx=pd.read_csv(BASE/'data/bitcoin_transactions.csv')
    tx['timestamp']=pd.to_datetime(tx.timestamp)
    return risk,tx

try:
    signature=tuple((BASE/p).stat().st_mtime_ns for p in ['data/risk_results.csv','data/bitcoin_transactions.csv'])
    risk,tx=load_data(signature)
except (OSError,ValueError) as exc:
    st.error(f'Unable to load the analysis files: {exc}');st.stop()

source_bytes=(BASE/'data/bitcoin_transactions.csv').read_bytes()
source_name='bitcoin_transactions.csv (included synthetic data)'
model_note='Stored analysis: Isolation Forest, HDBSCAN and weighted fusion.'
if 'uploaded_analysis' in st.session_state:
    active=st.session_state['uploaded_analysis']
    risk,tx=active['risk'],active['tx']
    source_bytes,source_name=active['raw'],active['name']
    model_note='Active analysis: Isolation Forest, HDBSCAN/DBSCAN fallback and XGBoost pattern-risk fusion.'

st.markdown('''<style>
[data-testid="stAppViewContainer"]{background:#091221;color:#e5edf9}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:#101b2c;border-right:1px solid #233247}
.block-container{padding-top:2rem;max-width:1650px;padding-bottom:3rem}
h1{font-size:2rem!important;letter-spacing:-.7px}h2{font-size:1.45rem!important}h3{font-size:1.12rem!important}
[data-testid="stMetric"]{background:linear-gradient(120deg,#13243a,#101c2d);border:1px solid #2b3b50;border-radius:12px;padding:18px 20px;min-height:115px}
[data-testid="stMetricValue"]{font-size:2rem;color:#edf5ff}
[data-testid="stMetricLabel"]{color:#a9bdd5}
[data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#293a51!important;border-radius:12px}
.brand{font-size:26px;font-weight:800;letter-spacing:4px;color:#e7f1fc}.brand span{color:#55dfc8}
.kicker{font-size:12px;letter-spacing:2px;color:#55dfc8;margin-bottom:8px}.muted{color:#9ab0c9;font-size:14px}.tag{display:inline-block;border:1px solid #305166;padding:5px 10px;border-radius:5px;color:#8be7d7;font-size:12px;letter-spacing:1px}
.evidence{border-left:2px solid #56d7c4;background:#122337;padding:10px 14px;margin:8px 0;color:#dbe7f8;font-size:14px;line-height:1.5}
.flow{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:16px 0 25px}.flow div{padding:14px 7px;border:1px solid #2e4964;border-top:4px solid #55dfc8;border-radius:10px;background:#112238;text-align:center;font-size:12px;min-height:70px}.flow b{display:block;color:#55dfc8;font-size:17px;margin-bottom:5px}@media(max-width:900px){.flow{grid-template-columns:1fr 1fr}}
[data-testid="stSidebar"] .block-container{padding-top:1rem}
</style>''',unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="brand"><span>◈</span> TRINETRA</div>',unsafe_allow_html=True)
    st.caption('BITCOIN INVESTIGATION WORKSPACE')
    st.divider()
    page=st.radio('WORKSPACE',['Dashboard','Technical pipeline','Unified search','Upload dataset','Investigation queue','Wallet investigation','Transaction graph','IP ↔ Wallet evidence','Case workspace','Integrity & audit'])
    st.divider()
    st.markdown('<span class="tag">LOCAL DATA · OFFLINE</span>',unsafe_allow_html=True)
    st.caption(f'{tx.txid.nunique():,} transactions · {len(risk):,} wallets')
    st.caption(f"{tx.timestamp.min():%d %b %Y} — {tx.timestamp.max():%d %b %Y}")
    st.caption('Active dataset: '+source_name)
    st.caption(model_note)
    if st.button('Refresh analysis files',use_container_width=True):
        st.cache_data.clear();st.rerun()
    if st.button('Logout',use_container_width=True):
        st.session_state.clear();st.rerun()

st.markdown('<div class="kicker">SLYTHERINS / SIH26146</div>',unsafe_allow_html=True)
st.title(page)
st.caption('Network and blockchain evidence, in one investigation workspace.')

def chart(fig,height=270):
    fig.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',font=dict(color='#adc0d8',size=14),height=height,margin=dict(l=10,r=10,t=20,b=10),colorway=['#55dfc8','#759fe1','#f87889'])
    fig.update_xaxes(gridcolor='#223249');fig.update_yaxes(gridcolor='#223249')
    st.plotly_chart(fig,use_container_width=True,config={'displaylogo':False})

def risk_table(df,key):
    fields=['wallet','risk_score','risk_level','anomaly_score','cluster_id','risk_evidence']
    event=st.dataframe(df[fields],hide_index=True,use_container_width=True,on_select='rerun',selection_mode='single-row',key=key,column_config={'wallet':'Wallet','risk_score':st.column_config.ProgressColumn('Risk / 100',min_value=0,max_value=100,format='%.2f'),'risk_level':'Priority','anomaly_score':st.column_config.NumberColumn('Anomaly / 100',format='%.2f'),'cluster_id':'Cluster','risk_evidence':'Evidence'})
    if event.selection.rows:
        st.session_state['wallet']=df.iloc[event.selection.rows[0]].wallet
        st.caption('Selected '+st.session_state['wallet']+' — open Wallet investigation or Transaction graph in the sidebar.')

def select_wallet(label='Investigate wallet'):
    wallets=risk.wallet.tolist()
    if st.session_state.get('wallet') not in wallets:st.session_state['wallet']=wallets[0]
    return st.selectbox(label,wallets,key='wallet')

def graph_view(wallet,compact=False):
    c1,c2,c3,c4=st.columns([1,1,1,1])
    direction=c1.selectbox('Trace direction',['Both','Outgoing','Incoming'],key='direction')
    hops=c2.selectbox('Trace depth',[1,2],key='hops',format_func=lambda x:f'{x} hop'+('s' if x>1 else ''))
    limit=c3.selectbox('Entity limit',[8,16,24],index=2,key='limit')
    ips=c4.checkbox('Show IP observations',key='ips')
    data,related=build_graph(tx,risk,wallet,hops,direction,limit,ips)
    components.html(graph_html(data),height=620,scrolling=False)
    st.caption(f"{len(related):,} transactions represented · {len(data['nodes'])} displayed nodes · Neighbours selected by BTC volume, limited to {limit} entities. Scores use the full dataset. Dashed IP links show observations, not ownership.")
    return related

if page=='Technical pipeline':
    st.markdown('''<div class="flow"><div><b>1</b>Data Ingestion</div><div><b>2</b>Data Processing</div><div><b>3</b>AI Analysis</div><div><b>4</b>Knowledge Graph</div><div><b>5</b>Risk + XAI</div><div><b>6</b>Enrichment</div><div><b>7</b>Report + Integrity</div></div>''',unsafe_allow_html=True)
    st.info('Run all seven stages for the active dataset. The new scores automatically update every investigation page.')
    if st.button('Run complete 7-stage pipeline',type='primary'):
        try:
            progress=st.progress(8,text='Stage 1/7 · Validating ingestion')
            progress.progress(22,text='Stage 2/7 · Cleaning, normalising and extracting features')
            progress.progress(36,text='Stage 3/7 · Isolation Forest and HDBSCAN analysis')
            computed=analyse(tx.copy())
            progress.progress(58,text='Stage 4/7 · Building the knowledge graph')
            progress.progress(72,text='Stage 5/7 · XGBoost fusion and explanations')
            progress.progress(86,text='Stage 6/7 · Applying offline geo and ASN context')
            st.session_state['uploaded_analysis']={'risk':computed,'tx':tx.copy(),'raw':source_bytes,'name':source_name}
            progress.progress(100,text='Stage 7/7 · PDF and SHA-256 integrity ready')
            st.session_state['pipeline_success']=True;st.rerun()
        except Exception as exc:st.error('Pipeline stopped: '+str(exc))
    if st.session_state.pop('pipeline_success',False):st.success('All seven stages completed. Dashboard, search, graphs and reports now use the new analysis.')
    stage=st.selectbox('Inspect technical stage',['1 · Data Ingestion','2 · Data Processing','3 · AI Analysis','4 · Knowledge Graph','5 · Risk Fusion & Explainability','6 · Offline Enrichment','7 · Report & Integrity'])
    if stage.startswith('1'):
        a,b,c=st.columns(3);a.metric('Validated rows',f'{len(tx):,}');b.metric('Unique TXIDs',f'{tx.txid.nunique():,}');c.metric('Supported formats','CSV · JSON · XML')
        st.dataframe(tx.head(100),hide_index=True,use_container_width=True)
    elif stage.startswith('2'):
        cols=[x for x in ['wallet','tx_count','mean_amount','std_amount','velocity','unique_ips','incoming_volume','outgoing_volume','graph_total_degree'] if x in risk]
        st.write('Cleaned and normalised wallet-level features:')
        st.dataframe(risk[cols].head(150),hide_index=True,use_container_width=True)
    elif stage.startswith('3'):
        a,b,c=st.columns(3);a.metric('Anomalous wallets',int(risk.anomaly_label.eq('ANOMALY').sum()));b.metric('Clusters',risk[risk.cluster_id.ge(0)].cluster_id.nunique());c.metric('Behaviour outliers',int(risk.cluster_id.eq(-1).sum()))
        st.dataframe(risk[['wallet','anomaly_score','anomaly_label','cluster_id','cluster_probability']].head(150),hide_index=True,use_container_width=True)
        st.caption('Isolation Forest detects unusual behaviour. HDBSCAN groups similar behaviour and marks noise as cluster -1.')
    elif stage.startswith('4'):
        wallet=select_wallet('Graph centre');graph_view(wallet)
        st.caption('NetworkX builds the entity graph; wallet transfers and network observations are correlated from the same evidence rows.')
    elif stage.startswith('5'):
        wallet=select_wallet('Explain wallet');row=risk[risk.wallet.eq(wallet)].iloc[0]
        st.metric('Fused risk score',f'{row.risk_score:.2f} · {row.risk_level}')
        shap_cols=[c for c in risk if c.startswith('shap_')]
        if shap_cols:
            values=sorted([(c[5:].replace('_',' '),float(row[c])) for c in shap_cols],key=lambda x:abs(x[1]),reverse=True)[:8]
            chart(go.Figure(go.Bar(x=[v for _,v in values],y=[n for n,_ in values],orientation='h',marker_color=['#55dfc8' if v>=0 else '#f87889' for _,v in values])),320)
            st.write(row.top_explanation)
        else:st.warning('Click “Run complete 7-stage pipeline” to fit XGBoost and generate feature-contribution explanations for this active dataset.')
    elif stage.startswith('6'):
        cols=[x for x in ['timestamp','txid','src_ip','dst_ip','geo_country','asn','src_wallet','dst_wallet'] if x in tx]
        st.dataframe(tx[cols].head(150),hide_index=True,use_container_width=True)
        st.caption('Geo and ASN evidence supplied in the dataset is retained locally. No IP evidence is sent to an online service.')
    else:
        wallet=select_wallet('Report subject');row=risk[risk.wallet.eq(wallet)].iloc[0];wallet_tx=tx[tx.src_wallet.eq(wallet)|tx.dst_wallet.eq(wallet)]
        st.code(hashlib.sha256(source_bytes).hexdigest(),language=None)
        pdf=create_pdf(row,wallet_tx,source_bytes,source_name,model_note)
        st.download_button('Generate verified PDF report',pdf,file_name=f'TRINETRA_{wallet}_report.pdf',mime='application/pdf',type='primary')
        st.caption('The PDF contains model evidence, transaction context, dataset fingerprint and responsible-use limitations.')

elif page=='Unified search':
    query=st.text_input('Search wallet address, transaction ID or IP address',placeholder='W0240, transaction hash, or 100.64.10.65')
    if query.strip():
        q=query.strip();wallet_hits=risk[risk.wallet.astype(str).str.contains(q,case=False,regex=False)]
        tx_hits=tx[tx.txid.astype(str).str.contains(q,case=False,regex=False)|tx.src_wallet.astype(str).str.contains(q,case=False,regex=False)|tx.dst_wallet.astype(str).str.contains(q,case=False,regex=False)|tx.src_ip.astype(str).str.contains(q,case=False,regex=False)|tx.dst_ip.astype(str).str.contains(q,case=False,regex=False)]
        a,b=st.columns(2);a.metric('Wallet matches',len(wallet_hits));b.metric('TX/IP matches',len(tx_hits))
        if not wallet_hits.empty:risk_table(wallet_hits.head(100),'search_wallets')
        if not tx_hits.empty:st.dataframe(tx_hits.head(500),hide_index=True,use_container_width=True)
        if wallet_hits.empty and tx_hits.empty:st.info('No matching wallet, transaction or IP observation found.')
    else:st.caption('Searches only the active offline evidence dataset.')

elif page=='Upload dataset':
    st.write('Choose a file on this computer. Processing runs in this local application without a cloud API.')
    uploaded=st.file_uploader('Bitcoin transaction / network metadata',type=['csv','json','xml'])
    st.caption('Maximum 25 MB, 50,000 input records and 5,000 graph entities. At least five wallets are needed for analysis. Invalid records are rejected with an explanation.')
    with st.expander('Supported columns and formats'):
        st.write('Required: timestamp, txid, src_ip, dst_ip, src_port, dst_port.')
        st.write('Flat format: src_wallet, dst_wallet, amount_btc. Or Bitcoin format: input_addresses, output_addresses, input_amounts, output_amounts arrays. Amounts and fees must be in BTC.')
        st.write('CSV arrays are JSON lists inside quoted cells. JSON accepts a record list or a transactions/records wrapper. XML uses a root containing transaction elements; array elements contain item children. Optional fee, script_type, geo_country and asn are retained.')
    for ext in ['csv','json','xml']:
        sample=BASE/'samples'/('sample_transactions.'+ext)
        if sample.exists():st.download_button('Download '+ext.upper()+' sample',sample.read_bytes(),file_name=sample.name,key='sample_'+ext)
    if uploaded is not None:
        if st.button('Validate and run offline analysis',type='primary'):
            try:
                with st.spinner('Validating records and fitting local models…'):
                    raw=uploaded.getvalue()
                    parsed,digest=parse_dataset(raw,uploaded.name)
                    computed=analyse(parsed)
                    register_dataset(uploaded.name,digest,len(parsed),len(computed))
                st.session_state['uploaded_analysis']={'risk':computed,'tx':parsed,'raw':raw,'name':uploaded.name}
                for key in ['wallet','dashboard_queue','queue']:st.session_state.pop(key,None)
                st.session_state['upload_success']=True
                st.rerun()
            except (ValueError,TypeError,KeyError) as exc:st.error(str(exc))
    if st.session_state.pop('upload_success',False):st.success('Analysis complete. Dashboard, queue, graphs and PDF reports now use your uploaded dataset.')
    if 'uploaded_analysis' in st.session_state:
        st.write(f'Active: {source_name} · {tx.txid.nunique():,} transactions · {len(risk):,} scored wallets')
        st.dataframe(risk[['wallet','risk_score','risk_level','risk_evidence']].head(10),hide_index=True,use_container_width=True)
        st.download_button('Download analysed wallet scores',risk.to_csv(index=False).encode(),file_name='TRINETRA_uploaded_analysis.csv',mime='text/csv')
        if st.button('Return to included demo dataset'):
            del st.session_state['uploaded_analysis']
            st.session_state.pop('wallet',None)
            st.rerun()
    st.caption('Uploaded data stays in this local browser session’s server memory until the session ends or the app stops. Download results and reports before closing.')
elif page=='Dashboard':
    cols=st.columns(5)
    for col,label,value in zip(cols,['Transactions','Wallets analysed','Anomalous wallets','Critical leads','High-priority leads'],[tx.txid.nunique(),len(risk),int(risk.anomaly_label.eq('ANOMALY').sum()),int(risk.risk_level.eq('CRITICAL').sum()),int(risk.risk_level.eq('HIGH').sum())]):col.metric(label,f'{value:,}')
    st.write('')
    left,right=st.columns([2,1])
    with left:
        with st.container(border=True):
            st.subheader('Transaction activity')
            daily=tx.set_index('timestamp').resample('D').agg(transactions=('txid','nunique'),volume=('amount_btc','sum'))
            chart(go.Figure(go.Scatter(x=daily.index,y=daily.transactions,mode='lines',line=dict(color='#55dfc8',width=3),fill='tozeroy',fillcolor='rgba(85,223,200,.10)',hovertemplate='%{x|%d %b}<br>%{y:,} transactions<extra></extra>')),230)
    with right:
        with st.container(border=True):
            st.subheader('Lead distribution')
            counts=risk.risk_level.value_counts().reindex(COLORS,fill_value=0)
            chart(go.Figure(go.Bar(x=counts.values,y=counts.index,orientation='h',marker_color=list(COLORS.values()),text=counts.values,textposition='auto')),230)
    st.subheader('Investigation network')
    wallet=select_wallet()
    graph_view(wallet,True)
    st.subheader('Priority queue')
    risk_table(risk.head(10),'dashboard_queue')

elif page=='Investigation queue':
    a,b,c=st.columns([2,1,1])
    query=a.text_input('Find wallet or evidence',placeholder='Search W0240, connectivity, outlier…')
    levels=b.multiselect('Priority',list(COLORS),default=['CRITICAL','HIGH'])
    minimum=c.slider('Minimum risk score',0,100,0)
    filtered=risk[risk.risk_level.isin(levels)&risk.risk_score.ge(minimum)]
    if query.strip():filtered=filtered[filtered.wallet.str.contains(query.strip(),case=False,regex=False)|filtered.risk_evidence.str.contains(query.strip(),case=False,regex=False)]
    st.caption(f'{len(filtered)} matching wallets · Highest risk first')
    if filtered.empty:st.info('No leads match these filters. Try another priority or search term.')
    else:risk_table(filtered,'queue')
    st.download_button('Export filtered queue CSV',filtered.to_csv(index=False).encode(),file_name='TRINETRA_investigation_queue.csv',mime='text/csv')
    st.info('Risk scores help prioritize review; they do not establish criminal activity or wallet ownership.')

elif page=='Wallet investigation':
    wallet=select_wallet()
    row=risk[risk.wallet.eq(wallet)].iloc[0]
    wallet_tx=tx[tx.src_wallet.eq(wallet)|tx.dst_wallet.eq(wallet)].sort_values('timestamp')
    cols=st.columns(4)
    for col,label,value in zip(cols,['Risk / 100','Priority','Transactions','Observed volume (BTC)'],[f'{row.risk_score:.2f}',row.risk_level,f'{len(wallet_tx):,}',f'{wallet_tx.amount_btc.sum():,.4f}']):col.metric(label,value)
    st.write('')
    left,right=st.columns([1,1])
    with left:
        with st.container(border=True):
            st.subheader('Why this wallet was flagged')
            for evidence in str(row.risk_evidence).split(';'):
                st.markdown('<div class="evidence">'+html.escape(evidence.strip())+'</div>',unsafe_allow_html=True)
            st.caption('Model evidence for prioritisation. It is not a probability of wrongdoing.')
    with right:
        with st.container(border=True):
            st.subheader('Risk score contributions')
            shap_cols=[c for c in risk.columns if c.startswith('shap_')]
            if shap_cols:
                vals=sorted([(c[5:].replace('_',' '),float(row[c])) for c in shap_cols],key=lambda x:abs(x[1]),reverse=True)[:6]
                chart(go.Figure(go.Bar(x=[v for _,v in vals],y=[n for n,_ in vals],orientation='h',marker_color=['#55dfc8' if v>=0 else '#f87889' for _,v in vals],text=[f'{v:+.2f}' for _,v in vals],textposition='auto')),250)
                st.caption('XGBoost feature contributions: positive values raise the pattern-risk score; negative values lower it. These explain the model, not criminal intent.')
            else:
                values=[.5*row.anomaly_score,.2*row.cluster_risk,.3*row.graph_risk]
                chart(go.Figure(go.Bar(x=values,y=['Anomaly × 50%','Cluster risk × 20%','Graph risk × 30%'],orientation='h')),230)
                st.caption('Stored demo uses weighted contributions. Analyse an upload to generate XGBoost explanations.')
    tabs=st.tabs(['Transaction timeline','Network graph','Behaviour & report'])
    with tabs[0]:
        st.subheader('Funds over time')
        fig=go.Figure()
        for label,mask,color in [('Incoming',wallet_tx.dst_wallet.eq(wallet),'#55dfc8'),('Outgoing',wallet_tx.src_wallet.eq(wallet),'#f6bb62')]:
            d=wallet_tx[mask];fig.add_trace(go.Scatter(x=d.timestamp,y=d.amount_btc,mode='markers',name=label,marker=dict(size=8,color=color),text=d.txid,hovertemplate='%{x}<br>%{y:.6f} BTC<br>%{text}<extra></extra>'))
        fig.update_layout(yaxis_title='BTC');chart(fig)
        st.dataframe(wallet_tx.sort_values('timestamp',ascending=False),hide_index=True,use_container_width=True)
        st.download_button('Export wallet transactions',wallet_tx.to_csv(index=False).encode(),file_name=f'{wallet}_transactions.csv',mime='text/csv')
    with tabs[1]:graph_view(wallet)
    with tabs[2]:
        st.write('**Behaviour cluster:** '+('Noise / outlier' if row.cluster_id==-1 else str(row.cluster_id)))
        st.write(f'**Graph degree:** {int(row.graph_total_degree)} · **PageRank:** {row.pagerank:.6f} · **Betweenness:** {row.betweenness_centrality:.6f}')
        st.caption(model_note)
        st.caption('IP association confidence is available in the IP ↔ Wallet evidence page. It measures repeated observations and specificity, never ownership.')
        pdf=create_pdf(row,wallet_tx,source_bytes,source_name,model_note)
        st.download_button('Download investigation PDF',pdf,file_name=f'TRINETRA_{wallet}_report.pdf',mime='application/pdf',type='primary')
        st.code(hashlib.sha256(source_bytes).hexdigest(),language=None)
        st.caption('SHA-256 of the active input file. This fingerprint detects byte changes; it does not independently verify the source.')

elif page=='Transaction graph':
    wallet=select_wallet('Central wallet')
    related=graph_view(wallet)
    st.subheader('Transactions represented in this graph')
    st.dataframe(related.sort_values('timestamp',ascending=False),hide_index=True,use_container_width=True)
    st.download_button('Export displayed transactions',related.to_csv(index=False).encode(),file_name=f'{wallet}_graph_transactions.csv',mime='text/csv')

elif page=='IP ↔ Wallet evidence':
    st.info('Association confidence ranks repeated network observations. NAT, VPNs, proxies, reassigned addresses and shared infrastructure mean it must never be treated as wallet ownership.')
    assoc=ip_wallet_associations(tx)
    a,b=st.columns([2,1])
    query=a.text_input('Search IP or wallet')
    minimum=b.slider('Minimum evidence confidence',0,95,40)
    view=assoc[assoc.confidence.ge(minimum)]
    if query.strip():view=view[view.ip.str.contains(query,case=False,regex=False)|view.wallet.str.contains(query,case=False,regex=False)]
    st.dataframe(view,hide_index=True,use_container_width=True,column_config={'confidence':st.column_config.ProgressColumn('Evidence confidence',min_value=0,max_value=100,format='%.1f%%')})
    st.download_button('Export association evidence',view.to_csv(index=False).encode(),file_name='TRINETRA_ip_wallet_evidence.csv',mime='text/csv')

elif page=='Case workspace':
    with st.expander('Create investigation case',expanded=not bool(list_cases())):
        title=st.text_input('Case title')
        priority=st.selectbox('Case priority',['LOW','MEDIUM','HIGH','CRITICAL'],index=1)
        notes=st.text_area('Investigator notes')
        if st.button('Create case',type='primary',disabled=not title.strip()):
            create_case(title.strip(),priority,notes.strip());st.success('Case created.');st.rerun()
    cases=list_cases()
    if not cases:st.info('Create a case to preserve selected leads and notes in the local database.')
    else:
        labels={f"#{c['id']} · {c['title']}":c for c in cases}
        selected=labels[st.selectbox('Open case',list(labels))]
        c1,c2,c3=st.columns(3);c1.metric('Status',selected['status']);c2.metric('Priority',selected['priority']);c3.metric('Wallet leads',selected['wallet_count'])
        st.write(selected['notes'] or '_No case notes_')
        wallet=select_wallet('Add wallet lead')
        row=risk[risk.wallet.eq(wallet)].iloc[0]
        rationale=st.text_area('Rationale',value=str(row.risk_evidence),key='case_rationale')
        if st.button('Add selected wallet to case'):
            add_wallet(selected['id'],wallet,row.risk_score,rationale);st.success('Lead saved to case.');st.rerun()
        saved=pd.DataFrame(case_wallets(selected['id']))
        if not saved.empty:
            st.dataframe(saved,hide_index=True,use_container_width=True)
            st.download_button('Export case leads',saved.to_csv(index=False).encode(),file_name=f"TRINETRA_case_{selected['id']}.csv",mime='text/csv')

else:
    st.subheader('Evidence integrity')
    digest=hashlib.sha256(source_bytes).hexdigest()
    st.code(digest,language=None)
    st.caption('SHA-256 fingerprints the exact input bytes. A changed file produces a different fingerprint.')
    st.subheader('Active processing manifest')
    manifest=pd.DataFrame([
      ['Dataset',source_name],['Transactions',tx.txid.nunique()],['Wallets',len(risk)],
      ['Analysis model',str(risk.model_type.iloc[0]) if 'model_type' in risk else model_note],
      ['Processing mode','Local / offline'],['Generated',pd.Timestamp.utcnow().isoformat()] ],columns=['Field','Value'])
    st.dataframe(manifest,hide_index=True,use_container_width=True)
    st.download_button('Download integrity manifest',manifest.to_csv(index=False).encode(),file_name='TRINETRA_integrity_manifest.csv',mime='text/csv')

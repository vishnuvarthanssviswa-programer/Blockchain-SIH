"""In-memory case reports; no shared output-file collisions."""
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def create_pdf(row, transactions, dataset_source, source_name="bitcoin_transactions.csv (synthetic data)", model_note="Stored analysis results"):
    raw=dataset_source if isinstance(dataset_source,bytes) else dataset_source.read_bytes()
    output=BytesIO()
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallText',fontName='Helvetica',fontSize=9,leading=14,textColor=colors.HexColor('#40536b')))
    styles['Title'].textColor=colors.HexColor('#11253c')
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=45,leftMargin=45,topMargin=40,bottomMargin=40)
    story=[Paragraph('TRINETRA',styles['Title']),Paragraph('INVESTIGATION BRIEF',styles['Heading2']),Paragraph('Generated '+datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC'),styles['SmallText']),Spacer(1,16)]
    rows=[['Subject wallet',Paragraph(escape(str(row.wallet)),styles['BodyText'])],['Risk score / priority',f'{row.risk_score:.2f} / 100 | {row.risk_level}'],['Transaction records',str(len(transactions))],['Observed volume',f'{transactions.amount_btc.sum():.6f} BTC'],['Behaviour cluster','Noise / outlier' if row.cluster_id==-1 else str(row.cluster_id)],['Cluster membership strength',('Unavailable (DBSCAN)' if row.cluster_probability!=row.cluster_probability else f'{row.cluster_probability:.3f}')]]
    table=Table(rows,colWidths=[190,315]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#edf3f8')),('TEXTCOLOR',(0,0),(-1,-1),colors.HexColor('#13263d')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9)]));story.extend([table,Spacer(1,18),Paragraph('Evidence for review',styles['Heading2'])])
    for item in str(row.risk_evidence).split(';'):story.append(Paragraph(escape(item.strip()),styles['BodyText']));story.append(Spacer(1,6))
    explanation=getattr(row,'top_explanation','Weighted contributions: anomaly, cluster and graph behaviour')
    story.extend([Spacer(1,10),Paragraph('Score explanation',styles['Heading2']),Paragraph(escape(str(explanation)),styles['BodyText']),Spacer(1,12),Paragraph('Scope and limitations',styles['Heading2']),Paragraph('This report uses the active input dataset and its analysis results. Scores prioritize investigation; they do not establish identity, wallet ownership or criminal activity. IP association confidence measures evidence strength, not ownership.',styles['BodyText']),Spacer(1,12),Paragraph('Dataset integrity',styles['Heading2']),Paragraph('Source: '+escape(source_name),styles['SmallText']),Paragraph(escape(model_note),styles['SmallText']),Paragraph('SHA-256: '+sha256(raw).hexdigest(),styles['SmallText'])])
    def footer(canvas,doc):
        canvas.setFont('Helvetica',9);canvas.setFillColor(colors.HexColor('#52657b'));canvas.drawString(45,24,'TRINETRA | Investigator review required');canvas.drawRightString(A4[0]-45,24,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()

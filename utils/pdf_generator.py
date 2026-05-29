# ============================================================
# utils/pdf_generator.py — PDF Report Generator
# Uses reportlab to produce professional PDF reports
# ============================================================
import io
from datetime import date
from reportlab.lib            import colors
from reportlab.lib.pagesizes  import A4, landscape
from reportlab.lib.styles     import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units      import cm
from reportlab.platypus       import (SimpleDocTemplate, Table, TableStyle,
                                       Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums      import TA_CENTER, TA_LEFT

# ── Brand colours ────────────────────────────────────────────
NAVY   = colors.HexColor('#1E3A5F')
BLUE   = colors.HexColor('#2563EB')
GREEN  = colors.HexColor('#16A34A')
RED    = colors.HexColor('#DC2626')
AMBER  = colors.HexColor('#D97706')
LGRAY  = colors.HexColor('#F3F4F6')
DGRAY  = colors.HexColor('#374151')


def _base_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('Title2',   parent=styles['Title'],   textColor=NAVY,  fontSize=18, spaceAfter=4))
    styles.add(ParagraphStyle('SubTitle2',parent=styles['Normal'],  textColor=DGRAY, fontSize=11, spaceAfter=2, alignment=TA_CENTER))
    styles.add(ParagraphStyle('Section',  parent=styles['Heading2'],textColor=NAVY,  fontSize=13, spaceBefore=12, spaceAfter=4))
    styles.add(ParagraphStyle('Cell',     parent=styles['Normal'],  fontSize=9,  leading=12))
    return styles


def _table_style(header_color=NAVY):
    return TableStyle([
        ('BACKGROUND',  (0, 0), (-1, 0),  header_color),
        ('TEXTCOLOR',   (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',    (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0),  10),
        ('ALIGN',       (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LGRAY]),
        ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#CBD5E1')),
        ('TOPPADDING',  (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING',(0,0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',(0, 0), (-1, -1), 6),
    ])


def generate_attendance_pdf(subject, records) -> bytes:
    """
    Generate a PDF attendance report for a subject.
    Returns bytes — the complete PDF file.
    """
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_styles()
    story  = []

    # ── Header ───────────────────────────────────────────────
    story.append(Paragraph('Smart Campus — Attendance Report', styles['Title2']))
    story.append(Paragraph(f'{subject.name} ({subject.code})  ·  Semester {subject.semester}', styles['SubTitle2']))
    story.append(Paragraph(f'Generated: {date.today().strftime("%d %B %Y")}', styles['SubTitle2']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=12))

    # ── Summary stats ─────────────────────────────────────────
    total   = len(records)
    present = sum(1 for r in records if r.status.value in ('Present', 'Late'))
    absent  = total - present
    pct     = round(present / total * 100, 1) if total else 0

    summary_data = [
        ['Total Classes', 'Present', 'Absent', 'Attendance %'],
        [str(total), str(present), str(absent), f'{pct}%'],
    ]
    summary_table = Table(summary_data, colWidths=[4*cm]*4)
    summary_table.setStyle(_table_style())
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Detail table ─────────────────────────────────────────
    story.append(Paragraph('Detailed Records', styles['Section']))
    table_data = [['#', 'Reg Number', 'Student Name', 'Date', 'Time In', 'Status']]
    for idx, rec in enumerate(records, 1):
        status_color = {'Present': GREEN, 'Late': AMBER, 'Absent': RED}.get(rec.status.value, DGRAY)
        table_data.append([
            str(idx),
            rec.student.reg_number,
            rec.student.name,
            str(rec.date),
            rec.time_in.strftime('%H:%M') if rec.time_in else '—',
            Paragraph(f'<font color="#{status_color.hexval()[1:] if hasattr(status_color,"hexval") else "000000"}">'
                      f'<b>{rec.status.value}</b></font>', styles['Cell']),
        ])

    detail_table = Table(table_data, colWidths=[1*cm, 3*cm, 5*cm, 3*cm, 2.5*cm, 2.5*cm], repeatRows=1)
    detail_table.setStyle(_table_style())
    story.append(detail_table)

    doc.build(story)
    return buf.getvalue()


def generate_risk_report_pdf(predictions) -> bytes:
    """Generate a risk prediction summary PDF."""
    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=landscape(A4),
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = _base_styles()
    story  = []

    story.append(Paragraph('Smart Campus — Academic Risk Report', styles['Title2']))
    story.append(Paragraph(f'Generated: {date.today().strftime("%d %B %Y")}', styles['SubTitle2']))
    story.append(HRFlowable(width='100%', thickness=1.5, color=NAVY, spaceAfter=12))

    # ── Risk distribution ─────────────────────────────────────
    safe     = sum(1 for p in predictions if p.risk_level.value == 'Safe')
    moderate = sum(1 for p in predictions if p.risk_level.value == 'Moderate')
    high     = sum(1 for p in predictions if p.risk_level.value == 'High')

    dist_data = [['Safe', 'Moderate Risk', 'High Risk', 'Total'],
                 [str(safe), str(moderate), str(high), str(len(predictions))]]
    dist_table = Table(dist_data, colWidths=[5*cm]*4)
    dist_table.setStyle(_table_style())
    story.append(dist_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Detail table ─────────────────────────────────────────
    story.append(Paragraph('Student Risk Details', styles['Section']))
    table_data = [['#', 'Reg Number', 'Name', 'Attend %', 'Avg Marks', 'Assign %', 'GPA', 'Risk Level', 'Model']]
    for idx, p in enumerate(predictions, 1):
        table_data.append([
            str(idx),
            p.student.reg_number,
            p.student.name,
            f'{p.attend_pct}%',
            str(p.avg_marks),
            f'{p.assign_pct}%' if p.assign_pct else '—',
            str(p.prev_gpa) if p.prev_gpa else '—',
            p.risk_level.value,
            p.model_used or '—',
        ])

    detail_table = Table(table_data,
                         colWidths=[1*cm,3*cm,5*cm,2.5*cm,3*cm,2.5*cm,2*cm,3*cm,3*cm],
                         repeatRows=1)
    detail_table.setStyle(_table_style())
    story.append(detail_table)

    doc.build(story)
    return buf.getvalue()

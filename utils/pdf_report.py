"""Professional PDF health report generation using ReportLab."""

import io
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Image,
)
from reportlab.graphics.shapes import Drawing, String as GString, Rect
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

BRAND = "#0f4c81"
TEAL = "#0e7c86"
SOFT = "#e8f1f8"
WARN = "#d35400"
DANGER = "#c0392b"
OK = "#1e8449"
GREY = "#555555"

STATUS_COLORS = {
    "HIGH": colors.HexColor(DANGER),
    "LOW": colors.HexColor(DANGER),
    "BORDERLINE": colors.HexColor(WARN),
    "NORMAL": colors.HexColor(OK),
    "UNKNOWN": colors.HexColor(GREY),
}

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
PDF_FONT = "Helvetica"
if os.path.exists(FONT_PATH):
    try:
        pdfmetrics.registerFont(TTFont("DiaUnicode", FONT_PATH))
        PDF_FONT = "DiaUnicode"
    except Exception:
        pass

PDF_LABELS = {
    "en": {"report": "AI HEALTH & WELLNESS REPORT", "report_date": "Report date", "patient": "Patient Overview", "score": "Dia Wellness Score", "summary": "AI Quick Summary", "key": "Key Findings", "priority": "Priority Findings", "complete": "Complete Lab Results", "explanation": "Explanation of Abnormal Results", "recommendations": "Recommendations", "diet": "Diet Guidance", "trends": "Health Trends", "questions": "Questions for Your Doctor", "privacy": "Privacy Note", "disclaimer": "Medical Disclaimer", "unknown": "Unknown", "not_available": "Not available", "name": "Patient Name", "age": "Age", "sex": "Sex", "date": "Report Date", "test": "Test", "value": "Value", "range": "Reference Range", "status": "Status"},
    "kn": {"report": "AI ಆರೋಗ್ಯ ಮತ್ತು ಕ್ಷೇಮ ವರದಿ", "report_date": "ವರದಿ ದಿನಾಂಕ", "patient": "ರೋಗಿಯ ವಿವರ", "score": "ಡಿಯಾ ಆರೋಗ್ಯ ಕ್ಷೇಮ ಸ್ಕೋರ್", "summary": "AI ತ್ವರಿತ ಸಾರಾಂಶ", "key": "ಪ್ರಮುಖ ಕಂಡುಬಂದ ಅಂಶಗಳು", "priority": "ತಕ್ಷಣ ಗಮನಿಸಬೇಕಾದ ಫಲಿತಾಂಶಗಳು", "complete": "ಸಂಪೂರ್ಣ ಪ್ರಯೋಗಾಲಯ ಫಲಿತಾಂಶಗಳು", "explanation": "ಅಸಾಮಾನ್ಯ ಫಲಿತಾಂಶಗಳ ವಿವರಣೆ", "recommendations": "ಶಿಫಾರಸುಗಳು", "diet": "ಆಹಾರ ಮಾರ್ಗದರ್ಶನ", "trends": "ಆರೋಗ್ಯ ಪ್ರವೃತ್ತಿಗಳು", "questions": "ವೈದ್ಯರಿಗಾಗಿ ಪ್ರಶ್ನೆಗಳು", "privacy": "ಗೌಪ್ಯತೆ ಸೂಚನೆ", "disclaimer": "ವೈದ್ಯಕೀಯ ನಿರಾಕರಣೆ", "unknown": "ತಿಳಿದಿಲ್ಲ", "not_available": "ಲಭ್ಯವಿಲ್ಲ", "name": "ರೋಗಿಯ ಹೆಸರು", "age": "ವಯಸ್ಸು", "sex": "ಲಿಂಗ", "date": "ವರದಿ ದಿನಾಂಕ", "test": "ಪರೀಕ್ಷೆ", "value": "ಮೌಲ್ಯ", "range": "ಉಲ್ಲೇಖ ಮಿತಿ", "status": "ಸ್ಥಿತಿ"},
    "te": {"report": "AI ఆరోగ్య మరియు వెల్‌నెస్ నివేదిక", "report_date": "నివేదిక తేదీ", "patient": "రోగి వివరాలు", "score": "డియా ఆరోగ్య స్కోర్", "summary": "AI త్వరిత సారాంశం", "key": "ముఖ్యమైన ఫలితాలు", "priority": "ప్రాధాన్య ఫలితాలు", "complete": "పూర్తి ప్రయోగశాల ఫలితాలు", "explanation": "అసాధారణ ఫలితాల వివరణ", "recommendations": "సిఫార్సులు", "diet": "ఆహార మార్గదర్శకం", "trends": "ఆరోగ్య ధోరణులు", "questions": "డాక్టర్ కోసం ప్రశ్నలు", "privacy": "గోప్యతా గమనిక", "disclaimer": "వైద్య నిరాకరణ", "unknown": "తెలియదు", "not_available": "అందుబాటులో లేదు", "name": "రోగి పేరు", "age": "వయస్సు", "sex": "లింగం", "date": "నివేదిక తేదీ", "test": "పరీక్ష", "value": "విలువ", "range": "రిఫరెన్స్ పరిధి", "status": "స్థితి"},
    "hi": {"report": "AI स्वास्थ्य और वेलनेस रिपोर्ट", "report_date": "रिपोर्ट की तारीख", "patient": "मरीज का विवरण", "score": "डिया वेलनेस स्कोर", "summary": "AI त्वरित सारांश", "key": "मुख्य निष्कर्ष", "priority": "प्राथमिक परिणाम", "complete": "सभी लैब परिणाम", "explanation": "असामान्य परिणामों की व्याख्या", "recommendations": "सुझाव", "diet": "डाइट मार्गदर्शन", "trends": "स्वास्थ्य रुझान", "questions": "डॉक्टर के लिए सवाल", "privacy": "गोपनीयता नोट", "disclaimer": "चिकित्सा अस्वीकरण", "unknown": "अज्ञात", "not_available": "उपलब्ध नहीं", "name": "मरीज का नाम", "age": "उम्र", "sex": "लिंग", "date": "रिपोर्ट की तारीख", "test": "जांच", "value": "मान", "range": "संदर्भ सीमा", "status": "स्थिति"}
}


def _label(extra, key):
    language = extra.get("language", "en")
    return PDF_LABELS.get(language, PDF_LABELS["en"]).get(key, PDF_LABELS["en"].get(key, key))


def _styles():
    ss = getSampleStyleSheet()
    st = {
        "title": ParagraphStyle("title", parent=ss["Title"], fontName=PDF_FONT, fontSize=22, leading=26,
                                textColor=colors.HexColor(BRAND), alignment=1, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", parent=ss["Normal"], fontName=PDF_FONT, fontSize=10, alignment=1,
                                   textColor=colors.HexColor(TEAL), spaceAfter=12),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=PDF_FONT, fontSize=13, textColor=colors.HexColor(BRAND),
                             spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", parent=ss["BodyText"], fontName=PDF_FONT, fontSize=9.5, leading=13.5,
                               textColor=colors.HexColor("#222222")),
        "small": ParagraphStyle("small", parent=ss["Normal"], fontName=PDF_FONT, fontSize=8, textColor=colors.HexColor("#777")),
        "cell": ParagraphStyle("cell", parent=ss["Normal"], fontName=PDF_FONT, fontSize=8.5, leading=11),
        "badge": ParagraphStyle("badge", parent=ss["Normal"], fontName=PDF_FONT, fontSize=7.5, leading=10,
                                alignment=1, textColor=colors.white),
    }
    return ss, st


def _status_badge(status):
    color = STATUS_COLORS.get(status, colors.HexColor(GREY))
    return Paragraph(f"<font color='white'><b>{status}</b></font>", ParagraphStyle(
        "badge", fontName=PDF_FONT, fontSize=7.5, leading=10, alignment=1,
        backColor=color, borderPadding=4, borderRadius=6))


def _bar_chart(title, data):
    """Simple horizontal bar chart as ReportLab drawing."""
    if not data:
        return None
    # filter out non-numeric
    rows = []
    for item in data:
        val = item.get("value")
        if isinstance(val, (int, float)) and item.get("is_bp") is not True:
            rows.append((item["test"], float(val), item.get("unit", "")))
        elif item.get("is_bp") and isinstance(item.get("value_sys"), (int, float)):
            rows.append((item["test"] + " (systolic)", float(item["value_sys"]), "mmHg"))
    if not rows:
        return None
    rows = rows[:8]

    width = 170 * mm
    bar_area = width - 30 * mm
    height = 20 + len(rows) * 11
    d = Drawing(width, height)
    max_val = max(r[1] for r in rows) or 1

    y = height - 15
    for label, val, unit in rows:
        bar_w = max(3, (val / max_val) * (bar_area - 35 * mm))
        d.add(Rect(30 * mm, y - 6, bar_w, 6, fillColor=colors.HexColor(BRAND), strokeColor=None))
        d.add(GString(30 * mm + bar_w + 3, y - 5, f"{val:g} {unit}".strip(), fontSize=7))
        t = GString(2, y - 4.5, label, fontSize=7.5, fontName="Helvetica-Bold")
        d.add(t)
        y -= 11

    d.add(GString(2, int(height) - 3, title, fontSize=9, fillColor=colors.HexColor(BRAND)))
    return d



def _fmt_brief(a):
    v = a.get("value")
    if isinstance(v, (int, float)):
        return f"{a['test']} — {a['status']} ({v:g} {a.get('unit', '')})".strip()
    return f"{a['test']} — {a['status']} ({v} {a.get('unit', '')})".strip()


def _fmt_val(a, unit):
    v = a.get("value")
    if v is None:
        return "Unknown"
    if isinstance(v, (int, float)):
        return f"{v:g} {unit}".strip()
    return f"{v} {unit}".strip()
def _header_footer(canvas, doc):
    footer_label = {
        "en": "Generated by Dia Assist — educational tool, not medical advice.",
        "kn": "ಡಿಯಾ ಅಸಿಸ್ಟ್ ರಚಿಸಿದೆ — ಶೈಕ್ಷಣಿಕ ಸಾಧನ, ವೈದ್ಯಕೀಯ ಸಲಹೆಯಲ್ಲ.",
        "te": "డియా అసిస్ట్ రూపొందించింది — విద్యా సాధనం, వైద్య సలహా కాదు.",
        "hi": "डिया असिस्ट द्वारा बनाया गया — शैक्षणिक टूल, चिकित्सा सलाह नहीं।",
    }.get(getattr(doc, "language", "en"), "Generated by Dia Assist — educational tool, not medical advice.")
    canvas.saveState()
    canvas.setFont(PDF_FONT, 9)
    canvas.setFillColor(colors.HexColor(BRAND))
    canvas.drawString(15 * mm, A4[1] - 12 * mm, "DIA ASSIST")
    canvas.setFont(PDF_FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.drawString(60 * mm, A4[1] - 12 * mm, "AI Health & Wellness Report")

    canvas.setFont(PDF_FONT, 7.5)
    canvas.setFillColor(colors.HexColor("#888"))
    canvas.drawString(15 * mm, 10 * mm, footer_label)
    canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 13 * mm, A4[0] - 15 * mm, 13 * mm)
    canvas.restoreState()


def generate_pdf(patient, analysis, report_date, extra=None):
    """Return PDF bytes."""
    extra = extra or {}
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15 * mm, leftMargin=15 * mm, topMargin=18 * mm, bottomMargin=16 * mm,
        title="DIA ASSIST — AI Health & Wellness Report",
        author="Dia Assist",
    )
    doc.language = extra.get("language", "en")
    ss, st = _styles()
    story = []

    # Title block
    story.append(Paragraph("DIA ASSIST", st["title"]))
    story.append(Paragraph(_label(extra, "report"), st["subtitle"]))
    story.append(HRFlowable(color=colors.HexColor(TEAL), thickness=1.5, spaceAfter=10))

    # 1. Report date
    story.append(Paragraph(f"<b>{_label(extra, 'report_date')}:</b> {report_date}", st["body"]))
    story.append(Spacer(1, 6))

    # 2. Patient overview
    story.append(Paragraph(f"1. {_label(extra, 'patient')}", st["h2"]))
    ovr = [
        [_label(extra, "name"), patient.get("name") or _label(extra, "unknown")],
        [_label(extra, "age"), f"{patient.get('age')}" if patient.get("age") is not None else _label(extra, "unknown")],
        [_label(extra, "sex"), patient.get("sex") or _label(extra, "unknown")],
        [_label(extra, "date"), patient.get("date") or report_date],
    ]
    t = Table(ovr, colWidths=[45 * mm, 100 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(SOFT)),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d0d0")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (-1, -1), PDF_FONT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 4))

    intelligence = extra.get("intelligence", {})
    story.append(Paragraph(f"2. {_label(extra, 'summary')}", st["h2"]))
    story.append(Paragraph(intelligence.get("summary", "No summary available."), st["body"]))
    story.append(Spacer(1, 4))

    # 3. Key findings
    story.append(Paragraph(f"3. {_label(extra, 'key')}", st["h2"]))
    abnormal = [a for a in analysis if a["status"] in ("HIGH", "LOW", "BORDERLINE")]
    if abnormal:
        kf = [_fmt_brief(a) for a in abnormal]
        story.append(Paragraph("Values flagged as outside the reference range:<br/>" +
                               "<br/>".join(f"• {k}" for k in kf), st["body"]))
    else:
        story.append(Paragraph("All detected lab values appear within their reference ranges (where a "
                               "reference range was available).", st["body"]))
    story.append(Spacer(1, 4))

    # 4. Abnormal results table
    if abnormal:
        story.append(Paragraph(f"5. {_label(extra, 'priority')}", st["h2"]))
        rows = [[_label(extra, "test"), _label(extra, "value"), _label(extra, "range"), _label(extra, "status")]]
        for a in abnormal:
            lo, hi, unit = a.get("ref_low"), a.get("ref_high"), a.get("unit", "")
            ref = "—"
            if lo is not None and hi is not None:
                ref = f"{lo:g}–{hi:g} {unit}".strip()
            elif hi is not None:
                ref = f"< {hi:g} {unit}".strip()
            elif lo is not None:
                ref = f"> {lo:g} {unit}".strip()
            val = _fmt_val(a, unit)
            rows.append([a["test"], val, ref, _status_badge(a["status"])])
        t = Table(rows, colWidths=[40 * mm, 35 * mm, 40 * mm, 30 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), PDF_FONT),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d0d0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    # 5. Complete lab results
    story.append(Paragraph(f"6. {_label(extra, 'complete')}", st["h2"]))
    if analysis:
        rows = [[_label(extra, "test"), _label(extra, "value"), _label(extra, "range"), _label(extra, "status")]]
        for a in analysis:
            lo, hi, unit = a.get("ref_low"), a.get("ref_high"), a.get("unit", "")
            ref = "No range"
            if lo is not None and hi is not None:
                ref = f"{lo:g}–{hi:g} {unit}".strip()
            elif hi is not None:
                ref = f"< {hi:g} {unit}".strip()
            elif lo is not None:
                ref = f"> {lo:g} {unit}".strip()
            val = _fmt_val(a, unit)
            rows.append([a["test"], val, ref, _status_badge(a["status"])])
        t = Table(rows, colWidths=[40 * mm, 35 * mm, 40 * mm, 30 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), PDF_FONT),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d0d0d0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8fb")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No lab values were detected in the uploaded report.", st["body"]))
    story.append(Spacer(1, 6))

    # 6. Explanation of abnormal results
    abnormal_ex = [a for a in analysis if a.get("explanation") and a["status"] != "NORMAL"]
    if abnormal_ex:
        story.append(Paragraph(f"7. {_label(extra, 'explanation')}", st["h2"]))
        for a in abnormal_ex:
            story.append(Paragraph(f"<b>{a['test']}</b> ({a['status']}):", st["body"]))
            story.append(Paragraph(a["explanation"], st["body"]))
            story.append(Spacer(1, 4))
        if extra.get("general_notes"):
            story.append(Paragraph(f"8. {_label(extra, 'recommendations')}", st["h2"]))
            for n in extra["general_notes"]:
                story.append(Paragraph(f"• {n}", st["body"]))
    else:
        story.append(Paragraph(f"7. {_label(extra, 'explanation')}", st["h2"]))
        story.append(Paragraph("No abnormal values flagged; all detected values were within their "
                               "reference ranges.", st["body"]))

    # 7. Diet guidance
    story.append(Paragraph(f"9. {_label(extra, 'diet')}", st["h2"]))
    diet = extra.get("diet_summary")
    if diet:
        for note in diet:
            story.append(Paragraph(f"• {note}", st["body"]))
    else:
        story.append(Paragraph("• General guidance is provided in the app; see your personalized diet "
                               "plan for details.", st["body"]))
    story.append(Spacer(1, 2))

    # 8. Chart / visual summary
    chart = _bar_chart("Detected Lab Values (visual summary)", analysis)
    if chart:
        story.append(Paragraph("10. Visual Summary", st["h2"]))
        story.append(chart)
        story.append(Spacer(1, 4))

    trend_rows = [trend for trend in extra.get("trends", []) if len(trend.get("points", [])) > 1]
    if trend_rows:
        story.append(Paragraph(f"10. {_label(extra, 'trends')}", st["h2"]))
        for trend in trend_rows:
            values = " → ".join(f"{point['value']:g}" for point in trend["points"])
            story.append(Paragraph(
                f"<b>{trend['test']}</b>: {values} ({trend.get('direction', 'Stable')}). "
                "This mathematical direction is not proof of medical improvement or deterioration.", st["body"]
            ))
        story.append(Spacer(1, 4))

    # 9. Questions for doctor
    story.append(Paragraph(f"11. {_label(extra, 'questions')}", st["h2"]))
    questions = intelligence.get("questions") or ["What do the flagged values in my report mean for my health?"]
    abnormal_names = set(a["test"] for a in abnormal)
    if abnormal_names:
        questions.append(f"Please explain the results flagged as {', '.join(sorted(abnormal_names))} "
                         "and whether any follow-up testing is needed.")
    questions.append("Are there any lifestyle changes or monitoring you recommend for me?")
    for q in questions:
        story.append(Paragraph(f"• {q}", st["body"]))
    story.append(Spacer(1, 4))

    # 10. Safety disclaimer
    story.append(Paragraph(f"12. {_label(extra, 'privacy')}", st["h2"]))
    story.append(Paragraph("Your uploaded files and analysis are stored locally by this application and are not served publicly. Delete local data from the Privacy Center.", st["body"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"13. {_label(extra, 'disclaimer')}", st["h2"]))
    story.append(Paragraph(
        "This report is generated by an educational, rule-based prototype (Dia Assist). It is NOT a "
        "medical diagnosis, does not replace professional medical advice, and does not prescribe any "
        "medicine or dosage. All information is general wellness education. Discuss your results with "
        "a licensed healthcare professional before making any health decision.", st["body"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Generated by DIA ASSIST on behalf of the user. Data is stored locally.", st["small"]))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buffer.seek(0)
    return buffer.getvalue()
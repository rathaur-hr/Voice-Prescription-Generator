"""
Renders the final prescription into a letterhead-style, printable PDF using
reportlab. Layout: blue header band (clinic/doctor info + logo), patient
info fields, a watermarked "Rx" content area with three clearly separated
sections (Tests / Medicines / Notes), a signature line, and a blue footer
band with hospital contact details + copyright.
"""

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)

PAGE_W, PAGE_H = A4

DARK_BLUE = colors.HexColor("#1F4E79")
ACCENT_BLUE = colors.HexColor("#4A90C4")
LIGHT_BLUE = colors.HexColor("#EAF4FB")
WATERMARK_BLUE = colors.HexColor("#DCEBF7")
WHITE = colors.white
GREY = colors.HexColor("#6B6B6B")

HEADER_H = 34 * mm
PATIENT_H = 40 * mm
FOOTER_H = 28 * mm
MARGIN = 15 * mm


def _plus_icon(c, cx, cy, r):
    """Simple plus-in-circle medical icon (no external art / font glyphs needed)."""
    c.setFillColor(WHITE)
    c.circle(cx, cy, r, fill=1, stroke=0)
    c.setFillColor(ACCENT_BLUE)
    bar_len = r * 1.1
    bar_thick = r * 0.32
    c.rect(cx - bar_len / 2, cy - bar_thick / 2, bar_len, bar_thick, fill=1, stroke=0)
    c.rect(cx - bar_thick / 2, cy - bar_len / 2, bar_thick, bar_len, fill=1, stroke=0)


def build_prescription_pdf(
    doctor_name,
    doctor_qualification,
    doctor_reg,
    clinic_name,
    clinic_slogan,
    clinic_phone1,
    clinic_phone2,
    clinic_email,
    clinic_website,
    patient_name,
    patient_address,
    patient_age,
    presc_date,
    diagnosis,
    tests,
    medicines,
    advice_notes,
):
    buffer = io.BytesIO()

    styles = getSampleStyleSheet()
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading3"],
        textColor=DARK_BLUE,
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
    )
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)
    list_item_style = ParagraphStyle("ListItem", parent=body, textColor=colors.HexColor("#222222"))

    # ---- Static (drawn every page): header, patient box, footer, sig line ----
    def draw_static(c, doc_):
        # Header band
        c.setFillColor(ACCENT_BLUE)
        c.rect(0, PAGE_H - HEADER_H, PAGE_W, HEADER_H, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(MARGIN, PAGE_H - 13 * mm, doctor_name or "Dr.")
        c.setFont("Helvetica", 9)
        if doctor_qualification:
            c.drawString(MARGIN, PAGE_H - 19 * mm, doctor_qualification.upper())
        if doctor_reg:
            c.setFont("Helvetica", 8)
            c.drawString(MARGIN, PAGE_H - 25 * mm, f"Reg./License No: {doctor_reg}")

        _plus_icon(c, PAGE_W - MARGIN - 10 * mm, PAGE_H - 16 * mm, 9 * mm)

        # Patient info box
        py_top = PAGE_H - HEADER_H
        c.setFillColor(colors.HexColor("#333333"))
        c.setFont("Helvetica", 9)
        line_x1 = MARGIN + 26 * mm
        line_x2 = PAGE_W - MARGIN

        def field_line(label, value, y, x1=line_x1, x2=line_x2, label_x=MARGIN):
            c.setFont("Helvetica-Bold", 9)
            c.drawString(label_x, y, label)
            c.setFont("Helvetica", 9)
            if value:
                c.drawString(x1 + 2, y, str(value))
            c.setStrokeColor(colors.HexColor("#B9C6D0"))
            c.line(x1, y - 1.5, x2, y - 1.5)

        field_line("Patient Name:", patient_name, py_top - 8 * mm)
        field_line("Address:", patient_address, py_top - 16 * mm)

        half_w = (line_x2 - MARGIN) / 2
        field_line("Age:", patient_age, py_top - 24 * mm, x1=MARGIN + 14 * mm, x2=MARGIN + half_w - 4 * mm)
        field_line(
            "Date:",
            presc_date,
            py_top - 24 * mm,
            x1=MARGIN + half_w + 14 * mm,
            x2=line_x2,
            label_x=MARGIN + half_w,
        )
        field_line("Diagnosis:", diagnosis, py_top - 32 * mm)

        c.setStrokeColor(colors.HexColor("#D0D7DD"))
        c.setLineWidth(0.75)
        c.line(MARGIN, py_top - PATIENT_H, PAGE_W - MARGIN, py_top - PATIENT_H)

        # Rx watermark
        c.saveState()
        try:
            c.setFillAlpha(0.5)
        except Exception:
            pass
        c.setFillColor(WATERMARK_BLUE)
        c.setFont("Helvetica-Bold", 150)
        c.drawCentredString(PAGE_W / 2, FOOTER_H + 70 * mm, "Rx")
        c.restoreState()

        # Rx symbol marker at start of content area
        c.setFillColor(ACCENT_BLUE)
        c.setFont("Helvetica-Bold", 26)
        c.drawString(MARGIN, py_top - PATIENT_H - 12 * mm, "Rx")

        # Signature line (fixed position, just above footer)
        sig_y = FOOTER_H + 14 * mm
        c.setStrokeColor(colors.HexColor("#888888"))
        c.line(PAGE_W - MARGIN - 55 * mm, sig_y, PAGE_W - MARGIN, sig_y)
        c.setFillColor(GREY)
        c.setFont("Helvetica", 8)
        c.drawCentredString(PAGE_W - MARGIN - 27.5 * mm, sig_y - 9, "Signature")

        # Footer band
        c.setFillColor(DARK_BLUE)
        c.rect(0, 0, PAGE_W, FOOTER_H, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN, FOOTER_H - 9 * mm, (clinic_name or "").upper())
        c.setFont("Helvetica-Oblique", 8)
        if clinic_slogan:
            c.drawString(MARGIN, FOOTER_H - 15 * mm, clinic_slogan)

        c.setFont("Helvetica", 8)
        right_x = PAGE_W - MARGIN
        contact_lines = []
        if clinic_phone1:
            contact_lines.append(f"Tel: {clinic_phone1}" + (f" / {clinic_phone2}" if clinic_phone2 else ""))
        if clinic_email:
            contact_lines.append(f"Email: {clinic_email}")
        if clinic_website:
            contact_lines.append(f"Web: {clinic_website}")
        y = FOOTER_H - 9 * mm
        for line in contact_lines:
            c.drawRightString(right_x, y, line)
            y -= 5 * mm

        # Copyright / portfolio credit
        c.setFillColor(colors.HexColor("#CFE0EE"))
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(
            PAGE_W / 2,
            4 * mm,
            f"\u00a9 {date.today().year} Harshit Rathaur  |  Portfolio: contactharshit.netlify.app",
        )

    # ---- Flowable content area (Tests / Medicines / Notes) ----
    story = []

    if tests:
        story.append(Paragraph("TESTS ADVISED", section_heading))
        items = [ListItem(Paragraph(t, list_item_style), leftIndent=6) for t in tests if t.strip()]
        if items:
            story.append(ListFlowable(items, bulletType="bullet", start="circle", leftIndent=10))
        story.append(Spacer(1, 6))

    if medicines:
        story.append(Paragraph("MEDICINES", section_heading))
        table_data = [["#", "Medicine", "Dosage", "Frequency", "Duration", "Notes"]]
        for i, med in enumerate(medicines, start=1):
            table_data.append(
                [
                    str(i),
                    med.get("medicine", ""),
                    med.get("dosage", ""),
                    med.get("frequency", ""),
                    med.get("duration", ""),
                    med.get("notes", ""),
                ]
            )
        med_table = Table(
            table_data,
            colWidths=[8 * mm, 38 * mm, 26 * mm, 30 * mm, 22 * mm, 32 * mm],
            repeatRows=1,
        )
        med_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BLUE]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(med_table)
        story.append(Spacer(1, 6))

    if advice_notes:
        story.append(Paragraph("ADVICE / NOTES", section_heading))
        story.append(Paragraph(advice_notes.replace("\n", "<br/>"), body))
        story.append(Spacer(1, 6))

    if not (tests or medicines or advice_notes):
        story.append(Spacer(1, 20))
        story.append(Paragraph("<i>No prescription details recorded yet.</i>", body))

    # ---- Document / page template ----
    doc = BaseDocTemplate(buffer, pagesize=A4)
    frame_y = FOOTER_H + 20 * mm
    frame_h = PAGE_H - HEADER_H - PATIENT_H - frame_y - 6 * mm
    content_frame = Frame(
        MARGIN,
        frame_y,
        PAGE_W - 2 * MARGIN,
        frame_h,
        topPadding=6,
        leftPadding=0,
        rightPadding=0,
        bottomPadding=0,
        id="content",
    )
    template = PageTemplate(id="letterhead", frames=[content_frame], onPage=draw_static)
    doc.addPageTemplates([template])
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()

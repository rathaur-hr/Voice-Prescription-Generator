"""
Renders the final structured prescription data into a clean, printable PDF
using reportlab (pure Python, no external binaries needed).
"""

import io

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
)


def build_prescription_pdf(
    doctor_name,
    doctor_reg,
    clinic_name,
    patient_name,
    patient_age,
    patient_sex,
    presc_date,
    medicines,
    extra_notes="",
):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ClinicTitle", parent=styles["Title"], fontSize=16, spaceAfter=2
    )
    doctor_style = ParagraphStyle(
        "DoctorStyle", parent=styles["Normal"], fontSize=10, textColor=colors.grey
    )
    rx_style = ParagraphStyle(
        "Rx", parent=styles["Heading2"], fontSize=20, spaceBefore=10, spaceAfter=6
    )
    normal = styles["Normal"]

    elements = []

    if clinic_name:
        elements.append(Paragraph(clinic_name, title_style))
    elements.append(Paragraph(f"{doctor_name}", styles["Heading3"]))
    if doctor_reg:
        elements.append(Paragraph(f"Reg. No: {doctor_reg}", doctor_style))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", color=colors.HexColor("#333333")))
    elements.append(Spacer(1, 8))

    # Patient info row
    patient_info = [
        [
            Paragraph(f"<b>Patient:</b> {patient_name}", normal),
            Paragraph(f"<b>Date:</b> {presc_date}", normal),
        ],
        [
            Paragraph(f"<b>Age:</b> {patient_age or '-'}", normal),
            Paragraph(f"<b>Sex:</b> {patient_sex or '-'}", normal),
        ],
    ]
    patient_table = Table(patient_info, colWidths=[90 * mm, 80 * mm])
    patient_table.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(patient_table)
    elements.append(Spacer(1, 10))

    # Rx symbol + medicine table
    elements.append(Paragraph("℞", rx_style))

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
        colWidths=[8 * mm, 42 * mm, 28 * mm, 32 * mm, 24 * mm, 36 * mm],
        repeatRows=1,
    )
    med_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2b6777")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7f8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(med_table)
    elements.append(Spacer(1, 12))

    if extra_notes:
        elements.append(Paragraph("<b>Advice / Notes:</b>", normal))
        elements.append(Paragraph(extra_notes.replace("\n", "<br/>"), normal))
        elements.append(Spacer(1, 20))

    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="40%", color=colors.HexColor("#333333")))
    elements.append(Paragraph("Doctor's Signature", doctor_style))

    elements.append(Spacer(1, 16))
    elements.append(
        Paragraph(
            "<i>Generated with the assistance of a voice-transcription tool. "
            "Please verify all details before dispensing.</i>",
            ParagraphStyle("Disclaimer", parent=normal, fontSize=7, textColor=colors.grey),
        )
    )

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


from io import BytesIO
from decimal import Decimal

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet


def generate_wholesale_invoice_pdf(order) -> BytesIO:
    """
    Generate wholesale invoice PDF for an order.
    This is the CANONICAL implementation — called by both:
      - orders/admin.py (admin action)
      - users/views.py download_invoice view (wholesale user self-service)

    Requires order.user to have company requisites set.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>СЧЁТ НА ОПЛАТУ</b>", styles["Title"]))
    story.append(Paragraph(f"№ {order.pk} от {order.created_at.strftime('%d.%m.%Y')}", styles["Normal"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("<b>Продавец:</b> ООО «Aspect Coffee»", styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))

    user = order.user
    if user:
        buyer_lines = [
            f"<b>Покупатель:</b> {user.company_name or user.get_full_name()}",
        ]
        if user.company_inn:
            buyer_lines.append(f"ИНН: {user.company_inn}")
        if user.company_kpp:
            buyer_lines.append(f"КПП: {user.company_kpp}")
        if user.company_bank_account:
            buyer_lines.append(f"Р/с: {user.company_bank_account}")
        for line in buyer_lines:
            story.append(Paragraph(line, styles["Normal"]))
    story.append(Spacer(1, 0.4*cm))

    table_data = [["№", "Наименование", "Кол-во", "Цена", "Сумма"]]
    total = Decimal("0")
    for i, item in enumerate(order.items.all(), start=1):
        line_total = item.price_at_order * item.qty
        total += line_total
        table_data.append([
            str(i),
            item.product_name,
            str(item.qty),
            f"{item.price_at_order:.2f} ₽",
            f"{line_total:.2f} ₽",
        ])

    table_data.append(["", "", "", "<b>ИТОГО:</b>", f"<b>{order.total_amount:.2f} ₽</b>"])

    col_widths = [0.8*cm, 9*cm, 1.8*cm, 3*cm, 3*cm]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F5F5F5")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F0F0F0")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -2), 0.5, colors.HexColor("#CCCCCC")),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    if order.discount_amount:
        story.append(Paragraph(f"Скидка: {order.discount_amount:.2f} ₽", styles["Normal"]))

    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Подпись продавца: _____________________", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

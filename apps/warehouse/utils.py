
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
import os


def _get_styles():
    styles = getSampleStyleSheet()
    return styles


def generate_packing_slip_pdf(order) -> BytesIO:
    """
    Generate warehouse packing slip PDF for an order.
    Returns BytesIO buffer ready for FileResponse.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    styles = _get_styles()
    story = []

    story.append(Paragraph(f"<b>Лист комплектации — Заказ #{order.pk}</b>", styles["Title"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Получатель: {order.contact_name}", styles["Normal"]))
    story.append(Paragraph(f"Телефон: {order.contact_phone}", styles["Normal"]))

    if order.delivery_type == 'cdek_pvz' and order.cdek_pvz_address:
        address_str = f"ПВЗ СДЭК: {order.cdek_pvz_address}"
    else:
        addr = order.delivery_address
        if isinstance(addr, dict):
            city = addr.get("city", "")
            street = addr.get("street", "")
            house = addr.get("house", "")
            apt = addr.get("apartment", "")
            address_str = f"{city}, {street}, д.{house}, кв.{apt}".strip(", ")
        else:
            address_str = str(addr)
    story.append(Paragraph(f"Адрес: {address_str}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    table_data = [["№", "Товар", "Артикул", "Кол-во"]]
    for i, item in enumerate(order.items.select_related("variant__product").all(), start=1):
        sku = getattr(item.variant, "sku", "") or "—"
        table_data.append([
            str(i),
            item.product_name,
            sku,
            str(item.qty),
        ])

    table = Table(table_data, colWidths=[1*cm, 10*cm, 4*cm, 2*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(f"Итого позиций: {order.items.count()}", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer

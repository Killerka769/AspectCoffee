
from django.urls import path
from apps.warehouse import views

app_name = "warehouse"

urlpatterns = [
    path("", views.assembly_queue, name="queue"),
    path("order/<int:pk>/", views.order_detail, name="order_detail"),
    path("order/<int:pk>/assembled/", views.mark_assembled, name="mark_assembled"),
    path("order/<int:pk>/packing-slip/", views.packing_slip_pdf, name="packing_slip"),
    path("stock/", views.stock_table, name="stock"),
]

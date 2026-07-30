from django.urls import path
from . import views

app_name = "delivery"

urlpatterns = [
    path("cities/", views.cdek_cities, name="cdek_cities"),
    path("offices/", views.cdek_offices, name="cdek_offices"),
    path("pvz-count/", views.cdek_pvz_count, name="cdek_pvz_count"),
    path("calc/", views.cdek_calc, name="cdek_calc"),
]

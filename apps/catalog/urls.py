
from django.urls import path
from . import views
app_name = "catalog"
urlpatterns = [
    path("", views.index, name="index"),
    # /coffee/ — раздел «Кофе» (ЧПУ 1.4.7); /coffee/<slug>/ — категория или товар.
    path("coffee/", views.section_catalog, {"section": "coffee"}, name="coffee"),
    path("coffee/<slug:slug>/", views.coffee_node, name="coffee_detail"),
    path("catalog/", views.catalog, name="catalog"),
    path("catalog/compare/", views.compare_view, name="compare"),
    path("search/suggest/", views.search_suggest, name="search_suggest"),
    path("product/<slug:slug>/", views.product_detail, name="detail"),
    path("product/<slug:slug>/recipe/add/", views.recipe_add, name="recipe_add"),
    path("recipes/<slug:slug>/", views.recipe_detail, name="recipe_detail"),
    path("dismiss-povodyr/", views.dismiss_povodyr, name="dismiss_povodyr"),
    path("api/cafes/", views.cafe_list_api, name="cafe_list_api"),
]

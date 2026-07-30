from django.urls import path, re_path
from . import views

app_name = "blog"

urlpatterns = [
    path("", views.index, name="index"),
    path("category/<slug:slug>/", views.category, name="category"),
    re_path(r"^(?P<slug>[-\w]+)/bookmark/$", views.toggle_bookmark, name="toggle_bookmark"),
    re_path(r"^(?P<slug>[-\w]+)/like/$", views.toggle_like, name="toggle_like"),
    re_path(r"^(?P<slug>[-\w]+)/comment/$", views.add_comment, name="add_comment"),
    re_path(r"^(?P<slug>[-\w]+)/$", views.detail, name="detail"),
]

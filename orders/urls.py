from django.urls import path

from . import views

app_name = "orders"
urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:number>/", views.success, name="success"),
    path("track/", views.track, name="track"),
]

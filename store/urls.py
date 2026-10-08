from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("toy/<slug:slug>/", views.product_detail, name="product"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("delivery-and-returns/", views.delivery_info, name="delivery"),
    path("api/chat/", views.chat_api, name="chat_api"),
]

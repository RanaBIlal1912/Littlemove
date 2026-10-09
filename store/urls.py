from django.urls import path

from . import views

app_name = "store"
urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.shop, name="shop"),
    path("gallery/", views.gallery, name="gallery"),
    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("toy/<slug:slug>/quickview/", views.product_quickview, name="product_quickview"),
    path("toy/<slug:slug>/", views.product_detail, name="product"),
    path("cart/", views.cart_view, name="cart"),
    path("api/search/", views.search_suggest, name="search_suggest"),
    path("api/wishlist/<int:product_id>/", views.wishlist_toggle, name="wishlist_toggle"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("delivery-and-returns/", views.delivery_info, name="delivery"),
    path("api/chat/", views.chat_api, name="chat_api"),
    path("api/mila/guide/", views.mila_guide, name="mila_guide"),
    path("bundles/<slug:slug>/", views.bundle_detail, name="bundle_detail"),
    path("bundles/<int:bundle_id>/add/", views.bundle_add_to_cart, name="bundle_add_to_cart"),
]

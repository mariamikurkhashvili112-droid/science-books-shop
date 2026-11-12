from django.urls import path

from . import web_views as v

urlpatterns = [
    path("", v.home, name="home"),
    path("books/<int:pk>/", v.book_detail, name="book_detail"),
    path("books/<int:pk>/review/", v.add_review, name="add_review"),
    path("cart/", v.cart_view, name="cart"),
    path("cart/add/<int:pk>/", v.cart_add, name="cart_add"),
    path("cart/item/<int:item_id>/update/", v.cart_update, name="cart_update"),
    path("cart/item/<int:item_id>/delete/", v.cart_delete, name="cart_delete"),
    path("checkout/", v.checkout, name="checkout"),
    path("order/<int:pk>/", v.order_done, name="order_done"),
]
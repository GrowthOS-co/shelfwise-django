from django.urls import path

from . import views

urlpatterns = [
    path("", views.catalogue, name="catalogue"),
    path("books/<int:pk>", views.book_detail, name="book"),
    path("cart", views.cart_detail, name="cart"),
    path("cart/add/<int:book_id>", views.cart_add, name="cart_add"),
    path("cart/update/<int:book_id>", views.cart_update, name="cart_update"),
    path("cart/remove/<int:book_id>", views.cart_remove, name="cart_remove"),
    path("checkout", views.checkout, name="checkout"),
    path("orders", views.order_list, name="order_list"),
    path("orders/<int:pk>", views.order_detail, name="order"),
    path("orders/<int:pk>/ship", views.order_ship, name="order_ship"),
]

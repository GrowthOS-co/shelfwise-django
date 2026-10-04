from .views import current_cart


def cart(request):
    """The number of books in this browser's cart, for the nav bar."""
    cart = current_cart(request)
    return {"cart_count": 0 if cart is None else cart.book_count()}

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AddToCartForm, CartLineForm, CheckoutForm
from .models import Book, Cart, CartItem, Order, ShopError

# The browser keeps its cart's token in this cookie.
CART_COOKIE = "cart_token"


def current_cart(request):
    """This browser's cart, or None before its first add to cart."""
    token = request.COOKIES.get(CART_COOKIE)
    if token is None:
        return None
    return Cart.objects.filter(token=token).first()


def _form_errors(form):
    return " ".join(error for errors in form.errors.values() for error in errors)


def catalogue(request):
    genre = request.GET.get("genre")
    if genre not in Book.Genre.values:
        genre = None
    books = Book.objects.all()
    if genre is not None:
        books = books.filter(genre=genre)
    return render(
        request,
        "books/catalogue.html",
        {"books": books, "genres": Book.Genre.values, "genre": genre},
    )


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(
        request, "books/detail.html", {"book": book, "form": AddToCartForm()}
    )


@require_POST
def cart_add(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    form = AddToCartForm(request.POST)
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return redirect(book)
    cart = current_cart(request) or Cart()
    try:
        cart.add(book, form.cleaned_data["quantity"])
    except ShopError as error:
        messages.error(request, str(error))
        return redirect(book)
    response = redirect("cart")
    response.set_cookie(
        CART_COOKIE, cart.token, httponly=True, samesite="Lax", path="/"
    )
    return response


def cart_detail(request):
    cart = current_cart(request)
    lines = [] if cart is None else cart.lines()
    rows = [(line, CartLineForm(initial={"quantity": line.quantity})) for line in lines]
    return render(
        request,
        "cart/detail.html",
        {"rows": rows, "total": 0 if cart is None else cart.total_cents()},
    )


def _cart_line(request, book_id):
    return get_object_or_404(
        CartItem.objects.select_related("book"),
        cart=current_cart(request),
        book_id=book_id,
    )


@require_POST
def cart_update(request, book_id):
    line = _cart_line(request, book_id)
    form = CartLineForm(request.POST)
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return redirect("cart")
    try:
        line.change_quantity(form.cleaned_data["quantity"])
    except ShopError as error:
        messages.error(request, str(error))
    return redirect("cart")


@require_POST
def cart_remove(request, book_id):
    _cart_line(request, book_id).delete()
    return redirect("cart")


def checkout(request):
    cart = current_cart(request)
    form = CheckoutForm(request.POST or None)
    if form.is_valid():
        try:
            order = Order.place(cart, **form.cleaned_data)
        except ShopError as error:
            form.add_error(None, str(error))
        else:
            return redirect(order)
    lines = [] if cart is None else list(cart.lines())
    if request.method == "GET" and not lines:
        return redirect("cart")
    return render(
        request,
        "cart/checkout.html",
        {
            "form": form,
            "lines": lines,
            "total": 0 if cart is None else cart.total_cents(),
        },
    )


def order_list(request):
    orders = Order.objects.with_totals().order_by("-created_at", "-id")
    return render(request, "orders/list.html", {"orders": orders})


def order_detail(request, pk):
    order = get_object_or_404(Order.objects.with_totals(), pk=pk)
    return render(request, "orders/detail.html", {"order": order})


@require_POST
def order_ship(request, pk):
    order = get_object_or_404(Order, pk=pk)
    try:
        order.mark_shipped(timezone.now())
    except ShopError as error:
        messages.error(request, str(error))
    return redirect(order)

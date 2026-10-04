from django.test import TestCase

from .models import Book, Cart, Order, ShopError


def create_book(title, price_cents, stock):
    return Book.objects.create(
        title=title,
        author="Clara Whitlow",
        isbn=f"isbn-{title}",
        genre=Book.Genre.FICTION,
        published_year=2021,
        description="",
        price_cents=price_cents,
        stock=stock,
    )


CHECKOUT_DETAILS = {
    "customer_name": "Ben Turner",
    "email": "ben.turner@example.com",
    "shipping_address": "14 Elm Street\nSpringfield, IL 62704",
}


class CartTests(TestCase):
    def test_total_is_quantity_times_current_price(self):
        cart = Cart()
        cart.add(create_book("Lantern", 1699, 10), 2)
        cart.add(create_book("Locker", 1399, 10), 1)

        self.assertEqual(cart.total_cents(), 4797)

    def test_adding_more_than_the_stock_is_refused(self):
        book = create_book("Fern Hollow", 1299, 2)
        cart = Cart()
        cart.add(book, 2)

        with self.assertRaisesMessage(ShopError, "Only 2 left in stock"):
            cart.add(book, 1)
        self.assertEqual(cart.items.get(book=book).quantity, 2)


class PlaceOrderTests(TestCase):
    def test_copies_titles_and_prices_takes_stock_and_empties_the_cart(self):
        lantern = create_book("Lantern", 1699, 12)
        locker = create_book("Locker", 1399, 15)
        cart = Cart()
        cart.add(lantern, 2)
        cart.add(locker, 1)

        order = Order.place(cart, **CHECKOUT_DETAILS)

        self.assertEqual(
            list(order.items.values_list("title", "unit_price_cents", "quantity")),
            [("Lantern", 1699, 2), ("Locker", 1399, 1)],
        )
        lantern.refresh_from_db()
        locker.refresh_from_db()
        self.assertEqual((lantern.stock, locker.stock), (10, 14))
        self.assertFalse(cart.items.exists())

        lantern.price_cents = 9999
        lantern.save()
        self.assertEqual(Order.objects.with_totals().get(pk=order.pk).total, 4797)

    def test_an_empty_cart_is_refused(self):
        cart = Cart.objects.create()

        with self.assertRaisesMessage(ShopError, "Your cart is empty."):
            Order.place(cart, **CHECKOUT_DETAILS)
        self.assertFalse(Order.objects.exists())

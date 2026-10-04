import secrets

from django.db import models, transaction
from django.db.models import F, Max, Q, Sum
from django.db.models.functions import Now
from django.urls import reverse


class ShopError(Exception):
    """A shop rule refused the request. The message is written for the customer
    and is shown on the page they were on."""

    @classmethod
    def out_of_stock(cls, book):
        return cls(f"Only {book.stock} left in stock of {book.title}.")


class Book(models.Model):
    class Genre(models.TextChoices):
        FICTION = "Fiction"
        MYSTERY = "Mystery"
        SCIENCE = "Science"
        HISTORY = "History"

    title = models.CharField()
    author = models.CharField()
    isbn = models.CharField(unique=True)
    genre = models.CharField(choices=Genre)
    published_year = models.PositiveIntegerField()
    description = models.TextField()
    price_cents = models.PositiveIntegerField()
    stock = models.PositiveIntegerField()

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("book", args=[self.pk])


def new_cart_token():
    return secrets.token_hex(16)


class Cart(models.Model):
    token = models.CharField(unique=True, default=new_cart_token)
    created_at = models.DateTimeField(db_default=Now())

    def __str__(self):
        return self.token

    def lines(self):
        return self.items.select_related("book")

    # Priced at each book's current price: a cart is not an order yet.
    def total_cents(self):
        return self.items.aggregate(
            total=Sum(F("quantity") * F("book__price_cents"), default=0)
        )["total"]

    def book_count(self):
        return self.items.aggregate(count=Sum("quantity", default=0))["count"]

    # A new cart (not saved yet) is saved only once the book is in stock.
    def add(self, book, quantity):
        item = None if self.pk is None else self.items.filter(book=book).first()
        in_cart = 0 if item is None else item.quantity
        if in_cart + quantity > book.stock:
            raise ShopError.out_of_stock(book)
        with transaction.atomic():
            if self.pk is None:
                self.save()
            if item is None:
                self.items.create(book=book, quantity=quantity)
            else:
                item.quantity = in_cart + quantity
                item.save(update_fields=["quantity"])


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="+")
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["cart", "book"], name="one_line_per_book"),
            models.CheckConstraint(
                condition=Q(quantity__gte=1), name="cart_quantity_at_least_one"
            ),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.book}"

    @property
    def amount_cents(self):
        return self.quantity * self.book.price_cents

    # A quantity of 0 removes the line.
    def change_quantity(self, quantity):
        if quantity == 0:
            self.delete()
            return
        if quantity > self.book.stock:
            raise ShopError.out_of_stock(self.book)
        self.quantity = quantity
        self.save(update_fields=["quantity"])


class OrderQuerySet(models.QuerySet):
    def with_totals(self):
        """Annotates each order with `total` (quantity x copied unit price) and
        `book_count` (the sum of quantities)."""
        return self.annotate(
            total=Sum(F("items__quantity") * F("items__unit_price_cents")),
            book_count=Sum("items__quantity"),
        )


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed"
        SHIPPED = "shipped"

    number = models.CharField(unique=True)
    customer_name = models.CharField()
    email = models.EmailField()
    shipping_address = models.TextField()
    status = models.CharField(choices=Status, default=Status.PLACED)
    created_at = models.DateTimeField(db_default=Now())
    shipped_at = models.DateTimeField(null=True, blank=True)

    objects = OrderQuerySet.as_manager()

    def __str__(self):
        return self.number

    def get_absolute_url(self):
        return reverse("order", args=[self.pk])

    # Copies each book's title and current price, takes the quantities out of
    # stock and empties the cart, all or nothing. `cart` is None when this
    # browser has never added a book.
    @classmethod
    def place(cls, cart, *, customer_name, email, shipping_address):
        with transaction.atomic():
            lines = [] if cart is None else list(cart.lines())
            if not lines:
                raise ShopError("Your cart is empty.")
            for line in lines:
                if line.quantity > line.book.stock:
                    raise ShopError.out_of_stock(line.book)

            last_id = cls.objects.aggregate(last=Max("id"))["last"] or 0
            order = cls.objects.create(
                number=f"ORD-{last_id + 1:04d}",
                customer_name=customer_name,
                email=email,
                shipping_address=shipping_address,
            )
            OrderItem.objects.bulk_create(
                OrderItem(
                    order=order,
                    book=line.book,
                    title=line.book.title,
                    unit_price_cents=line.book.price_cents,
                    quantity=line.quantity,
                )
                for line in lines
            )
            for line in lines:
                Book.objects.filter(pk=line.book.pk).update(
                    stock=F("stock") - line.quantity
                )
            cart.items.all().delete()
        return order

    def mark_shipped(self, now):
        if self.status != self.Status.PLACED:
            raise ShopError(f"Order {self.number} is {self.status} and cannot be shipped.")
        self.status = self.Status.SHIPPED
        self.shipped_at = now
        self.save(update_fields=["status", "shipped_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="+")
    title = models.CharField()
    unit_price_cents = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.quantity} × {self.title}"

    @property
    def amount_cents(self):
        return self.quantity * self.unit_price_cents

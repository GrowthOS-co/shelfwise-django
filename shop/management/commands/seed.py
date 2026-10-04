"""Replaces everything in the database with the sample shop below. Order times
are relative to now, so the newest order was always placed a few hours ago."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from shop.models import Book, Cart, CartItem, Order, OrderItem

# (title, author, genre, year, price in cents, stock, isbn, description).
# Stock is what is left after the sample orders below.
SAMPLE_BOOKS = [
    ("The Lantern Keeper's Daughter", "Clara Whitlow", "Fiction", 2021, 1699, 12, "9781999900014", "A lighthouse keeper's daughter inherits the light and a box of unsent letters."),
    ("Salt and Saffron", "Rafael Okoye", "Fiction", 2019, 1499, 8, "9781999900021", "Two rival cooks share one small kitchen for a summer."),
    ("A Year Without Winter", "Ingrid Solberg", "Fiction", 2023, 2199, 5, "9781999900038", "A northern town waits for snow that never comes."),
    ("The Quiet Orchard", "Hannah Mercer", "Fiction", 2018, 1299, 0, "9781999900045", "Three sisters return to sell the family orchard."),
    ("Paper Boats", "Dev Malhotra", "Fiction", 2022, 1599, 20, "9781999900052", "Childhood friends reunite in the city where they grew up."),
    ("Tidewater", "June Calloway", "Fiction", 2020, 1799, 3, "9781999900069", "A ferry captain's last season on the river."),
    ("The Ninth Locker", "Marcus Hale", "Mystery", 2021, 1399, 15, "9781999900076", "A key found in a library book opens a locker no one has rented."),
    ("Death at Low Tide", "Agnes Pryor", "Mystery", 2017, 1199, 9, "9781999900083", "A body on the sandbar and only one set of footprints."),
    ("The Cartographer's Alibi", "Simone Duval", "Mystery", 2022, 1899, 6, "9781999900090", "A mapmaker swears she was somewhere that does not exist."),
    ("Cold Case at Fern Hollow", "Peter Lindqvist", "Mystery", 2019, 1299, 2, "9781999900106", "A retired detective reopens the case that ended his career."),
    ("Silent Bell", "Okonkwo Adeyemi", "Mystery", 2023, 2099, 11, "9781999900113", "The church bell stops ringing the night the organist vanishes."),
    ("The Last Train to Halden", "Ruth Ellery", "Mystery", 2020, 1499, 0, "9781999900120", "Six passengers, one stalled train, and a missing ticket."),
    ("Small Worlds: A Field Guide to Microbes", "Elena Ruiz", "Science", 2021, 2499, 7, "9781999900137", "The tiny life all around us, with photographs and simple experiments."),
    ("The Shape of Time", "Arjun Sen", "Science", 2018, 2299, 4, "9781999900144", "How clocks, planets and physics agree on what a second is."),
    ("Rivers of Air", "Molly Hargreaves", "Science", 2022, 1999, 10, "9781999900151", "The winds and currents that carry weather around the world."),
    ("Why Bridges Stand", "Tomas Novak", "Science", 2020, 2699, 5, "9781999900168", "The engineering behind ten famous bridges."),
    ("The Clever Octopus", "Fiona Banks", "Science", 2023, 1799, 14, "9781999900175", "What scientists have learned about how octopuses think."),
    ("Counting the Stars", "Kenji Mori", "Science", 2019, 2199, 1, "9781999900182", "A short history of measuring the night sky."),
    ("The Spice Roads", "Leila Nasser", "History", 2020, 2899, 6, "9781999900199", "Traders, ports and the routes that carried pepper and cinnamon."),
    ("Empire of Clay", "Victor Hume", "History", 2017, 2499, 3, "9781999900205", "The rise and fall of an ancient kingdom of potters."),
    ("Harbor Lights: A History of Lighthouses", "Grace Okafor", "History", 2021, 1999, 8, "9781999900212", "Two thousand years of keeping ships off the rocks."),
    ("The Printer's Revolution", "Samuel Wren", "History", 2018, 2299, 9, "9781999900229", "How cheap printing changed who could read and what they read."),
    ("Letters from the Front", "Anne Delacroix", "History", 2022, 1899, 12, "9781999900236", "Ordinary soldiers' letters home, collected and explained."),
    ("Cities Under Sand", "Hamid Rahimi", "History", 2023, 2699, 4, "9781999900243", "Desert cities lost and found again by archaeologists."),
]

# items are (index into SAMPLE_BOOKS, quantity); titles and prices are copied
# from the books, as placing an order does.
SAMPLE_ORDERS = [
    {"customer_name": "Ben Turner", "email": "ben.turner@example.com", "shipping_address": "14 Elm Street\nSpringfield, IL 62704", "placed_ago": timedelta(days=9), "shipped_ago": timedelta(days=7), "items": [(0, 1), (12, 1)]},
    {"customer_name": "Mira Shah", "email": "mira.shah@example.com", "shipping_address": "88 Harbor Road\nPortland, ME 04101", "placed_ago": timedelta(days=2), "items": [(6, 2)]},
    {"customer_name": "Carlos Mendes", "email": "carlos.mendes@example.com", "shipping_address": "301 Pine Avenue, Apt 4B\nAustin, TX 78701", "placed_ago": timedelta(hours=3), "items": [(18, 1), (4, 1), (16, 1)]},
]


class Command(BaseCommand):
    help = "Replaces everything in the database with a sample bookshop."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()

        models = (OrderItem, Order, CartItem, Cart, Book)
        for model in models:
            model.objects.all().delete()
        tables = [model._meta.db_table for model in models]
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM sqlite_sequence WHERE name IN (%s, %s, %s, %s, %s)",
                tables,
            )

        books = [
            Book.objects.create(
                title=title,
                author=author,
                genre=genre,
                published_year=year,
                price_cents=price_cents,
                stock=stock,
                isbn=isbn,
                description=description,
            )
            for title, author, genre, year, price_cents, stock, isbn, description in SAMPLE_BOOKS
        ]

        for index, sample in enumerate(SAMPLE_ORDERS, start=1):
            shipped = "shipped_ago" in sample
            order = Order.objects.create(
                number=f"ORD-{index:04d}",
                customer_name=sample["customer_name"],
                email=sample["email"],
                shipping_address=sample["shipping_address"],
                status=Order.Status.SHIPPED if shipped else Order.Status.PLACED,
                created_at=now - sample["placed_ago"],
                shipped_at=now - sample["shipped_ago"] if shipped else None,
            )
            OrderItem.objects.bulk_create(
                OrderItem(
                    order=order,
                    book=books[book_index],
                    title=books[book_index].title,
                    unit_price_cents=books[book_index].price_cents,
                    quantity=quantity,
                )
                for book_index, quantity in sample["items"]
            )

        self.stdout.write(
            f"Seeded {len(SAMPLE_BOOKS)} books and {len(SAMPLE_ORDERS)} orders."
        )

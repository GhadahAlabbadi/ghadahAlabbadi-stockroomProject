from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Category, Customer, Order, OrderItem, Product


class Command(BaseCommand):
    help = "Fill the database with sample data for the StockRoom project."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing inventory data before creating the sample data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Product.objects.all().delete()
            Customer.objects.all().delete()
            Category.objects.all().delete()
        elif Product.objects.exists():
            self.stdout.write(
                self.style.WARNING("Data already exists. Run with --reset to recreate it.")
            )
            return

        categories = {
            name: Category.objects.create(name=name)
            for name in ["Electronics", "Stationery", "Groceries"]
        }

        product_rows = [
            ("Wireless Mouse", "E001", "24.99", 40, True, "Electronics"),
            ("USB-C Cable", "E002", "8.50", 120, True, "Electronics"),
            ("Bluetooth Speaker", "E003", "59.90", 4, True, "Electronics"),
            ("Webcam HD", "E004", "45.00", 30, True, "Electronics"),
            ("Notebook A5", "S001", "3.75", 200, True, "Stationery"),
            ("Gel Pen Pack", "S002", "5.20", 5, True, "Stationery"),
            ("Marker Set", "S003", "12.40", 2, False, "Stationery"),
            ("Coffee Beans 1kg", "G001", "19.99", 60, True, "Groceries"),
            ("Green Tea Box", "G002", "6.50", 3, True, "Groceries"),
            ("Honey Jar", "G003", "14.75", 25, False, "Groceries"),
        ]
        products = {}
        for name, sku, price, stock, is_active, category in product_rows:
            products[sku] = Product.objects.create(
                name=name,
                sku=sku,
                price=Decimal(price),
                stock=stock,
                is_active=is_active,
                category=categories[category],
            )

        customers = {
            "aisha": Customer.objects.create(name="Aisha Khan", email="aisha@example.com"),
            "omar": Customer.objects.create(name="Omar Saleh", email="omar@example.com"),
            "lina": Customer.objects.create(name="Lina Haddad", email="lina@example.com"),
        }

        order_rows = [
            ("aisha", Order.Status.PAID, [("E001", 2, "24.99"), ("E002", 3, "8.50")]),
            ("aisha", Order.Status.SHIPPED, [("S001", 10, "3.75"), ("S002", 4, "5.20")]),
            ("omar", Order.Status.PENDING, [("E003", 1, "59.90"), ("G001", 2, "19.99")]),
            ("omar", Order.Status.CANCELLED, [("G002", 5, "6.50")]),
            ("lina", Order.Status.PAID, [("E004", 1, "45.00"), ("E001", 1, "22.00"), ("G001", 1, "19.99")]),
            ("aisha", Order.Status.PENDING, [("G003", 2, "14.75"), ("S003", 3, "12.40")]),
        ]
        for customer_key, status, items in order_rows:
            order = Order.objects.create(customer=customers[customer_key], status=status)
            for sku, quantity, unit_price in items:
                OrderItem.objects.create(
                    order=order,
                    product=products[sku],
                    quantity=quantity,
                    unit_price=Decimal(unit_price),
                )

        self.stdout.write(self.style.SUCCESS(
            f"Created {Category.objects.count()} categories, {Product.objects.count()} products, "
            f"{Customer.objects.count()} customers, {Order.objects.count()} orders, "
            f"{OrderItem.objects.count()} order items."
        ))
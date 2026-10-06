from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from inventory.models import Category, Customer, Order, OrderItem, Product


class Command(BaseCommand):
    help = "Show that the database constraints reject invalid data (nothing is saved)."

    def handle(self, *args, **options):
        print("=" * 70)
        print("CONSTRAINT CHECKS (every attempt is rolled back at the end)")
        print("=" * 70)

        with transaction.atomic():
            self.run()
            transaction.set_rollback(True)

        print()
        print("Question : Is the sample data unchanged after these attempts?")
        print(f"Result   : products = {Product.objects.count()}, "
              f"order items = {OrderItem.objects.count()}, "
              f"categories = {Category.objects.count()}, "
              f"customers = {Customer.objects.count()}")

    def attempt(self, question, statement):
        print(f"\nQuestion : {question}")
        print(f"Statement: {statement}")
        try:
            with transaction.atomic():
                exec(statement, dict(globals()))
        except IntegrityError as exc:
            print(f"Result   : REJECTED by the database (IntegrityError): {exc}")
        else:
            print("Result   : ACCEPTED (row saved inside the demo transaction)")

    def run(self):
        self.attempt(
            "Control: is a valid product with price 0.00 and stock 0 accepted? (boundary values)",
            'Product.objects.create(name="Control", sku="OK-1", price=Decimal("0.00"), '
            'stock=0, category=Category.objects.first())',
        )
        self.attempt(
            "Is a negative price rejected? (CheckConstraint price >= 0)",
            'Product.objects.create(name="Bad", sku="BAD-1", price=Decimal("-1.00"), '
            'stock=1, category=Category.objects.first())',
        )
        self.attempt(
            "Is a negative stock rejected? (CheckConstraint stock >= 0)",
            'Product.objects.create(name="Bad", sku="BAD-2", price=Decimal("1.00"), '
            'stock=-1, category=Category.objects.first())',
        )
        self.attempt(
            "Is a duplicate SKU rejected? (unique sku)",
            'Product.objects.create(name="Copy", sku="E001", price=Decimal("1.00"), '
            'stock=1, category=Category.objects.first())',
        )
        self.attempt(
            "Is a duplicate category name rejected? (unique name)",
            'Category.objects.create(name="Electronics")',
        )
        self.attempt(
            "Is a duplicate customer email rejected? (unique email)",
            'Customer.objects.create(name="Copy", email="aisha@example.com")',
        )
        self.attempt(
            "Is an order item with quantity 0 rejected? (CheckConstraint quantity >= 1)",
            'OrderItem.objects.create(order_id=1, product=Product.objects.get(sku="G003"), '
            'quantity=0, unit_price=Decimal("1.00"))',
        )
        self.attempt(
            "Is a negative unit_price rejected? (CheckConstraint unit_price >= 0)",
            'OrderItem.objects.create(order_id=1, product=Product.objects.get(sku="G003"), '
            'quantity=1, unit_price=Decimal("-1.00"))',
        )
        self.attempt(
            "Is the same product twice in one order rejected? (unique order + product)",
            'OrderItem.objects.create(order_id=1, product=Product.objects.get(sku="E001"), '
            'quantity=1, unit_price=Decimal("24.99"))',
        )
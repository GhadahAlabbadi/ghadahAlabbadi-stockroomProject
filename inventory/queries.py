from decimal import Decimal

from django.db import transaction
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    Sum,
)
from django.db.models.deletion import ProtectedError

from .models import Category, Customer, Order, OrderItem, Product

def heading(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def show_result(result):
    if isinstance(result, QuerySet):
        rows = list(result)
        print(f"Result   : {len(rows)} row(s)")
        for row in rows:
            print("           ", row)
    else:
        print("Result   :", result)


def ask(question, statement, ns=None):
    """Evaluate one ORM expression and print question, statement and result."""
    print(f"\nQuestion : {question}")
    print(f"Statement: {statement}")
    result = eval(statement, ns if ns is not None else globals())
    show_result(result)
    return result


def do(question, statement, ns):
    """Execute one ORM statement (for example an assignment) and print it."""
    print(f"\nQuestion : {question}")
    print(f"Statement: {statement}")
    exec(statement, ns)


def try_delete(obj):
    """Delete an object and report the PROTECT error instead of crashing."""
    try:
        return obj.delete()
    except ProtectedError as error:
        return (
            f"ProtectedError raised, nothing deleted "
            f"({len(error.protected_objects)} protected object(s))"
        )


def run_crud():
    heading("CRUD OPERATIONS (all changes are rolled back at the end)")
    ns = dict(globals())

    with transaction.atomic():
        # CREATE
        do("Create a category", 'category = Category.objects.create(name="Demo Category")', ns)
        do(
            "Create a product",
            'product = Product.objects.create(name="Demo Product", sku="DEMO-001", '
            'price=Decimal("10.00"), stock=7, category=category)',
            ns,
        )
        do(
            "Create a customer",
            'customer = Customer.objects.create(name="Demo Customer", email="demo@example.com")',
            ns,
        )
        do("Create an order", "order = Order.objects.create(customer=customer)", ns)
        do(
            "Create an order item",
            'item = OrderItem.objects.create(order=order, product=product, '
            'quantity=2, unit_price=Decimal("10.00"))',
            ns,
        )
        ask("What was created?", "[category, product, customer, order, item]", ns)

        # RETRIEVE
        ask("Retrieve one product by primary key", "Product.objects.get(pk=product.pk)", ns)
        ask("List several products (first three, default ordering by name)",
            "Product.objects.all()[:3]", ns)

        # UPDATE
        do(
            "Update the product price and stock",
            'product.price = Decimal("12.50"); product.stock = 20; '
            'product.save(update_fields=["price", "stock"])',
            ns,
        )
        ask(
            "Confirm the change by reading the row from the database",
            "Product.objects.filter(pk=product.pk).values('name', 'price', 'stock')",
            ns,
        )

        # DELETE
        ask(
            "Delete a category that still has products (on_delete=PROTECT)",
            "try_delete(category)",
            ns,
        )
        do("Create an unreferenced category", 'unused = Category.objects.create(name="Unused Category")', ns)
        ask("Delete the unreferenced category", "unused.delete()", ns)
        ask(
            "Delete an order that has items (on_delete=CASCADE on OrderItem.order)",
            "order.delete()",
            ns,
        )
        ask(
            "Is the product still there after its order was deleted?",
            "Product.objects.filter(pk=product.pk).exists()",
            ns,
        )

        transaction.set_rollback(True)

    ask("Is the sample data unchanged after the demo? (products stored)",
        "Product.objects.count()", ns)

# ---------------------------------------------------------------------------
# Section 8: QuerySets and field lookups
# ---------------------------------------------------------------------------

def run_querysets():
    heading("QUERYSETS AND FIELD LOOKUPS")

    ask("Which products are active?",
        "Product.objects.filter(is_active=True)")

    ask("Which products have stock less than or equal to 5?",
        "Product.objects.filter(stock__lte=5)")

    ask("Which products cost between 10.00 and 30.00 (inclusive)?",
        'Product.objects.filter(price__range=(Decimal("10.00"), Decimal("30.00")))')

    ask("Which product names contain 'CABLE' (case-insensitive search)?",
        'Product.objects.filter(name__icontains="CABLE")')

    ask("Which products remain after excluding the inactive ones?",
        "Product.objects.exclude(is_active=False)")

    ask("List products ordered by category name, then product name",
        'Product.objects.order_by("category__name", "name").values_list("category__name", "name")')

    ask("What are the five most recently created orders (newest first)?",
        'Order.objects.order_by("-created_at", "-pk")[:5]')

    ask("Q object, matching on the NAME: search 'mouse' in name OR sku",
        'Product.objects.filter(Q(name__icontains="mouse") | Q(sku__icontains="mouse"))')

    ask("Q object, matching on the SKU: search 'g00' in name OR sku",
        'Product.objects.filter(Q(name__icontains="g00") | Q(sku__icontains="g00"))')

    ask("F expression (comparison): which order items were sold at a price "
        "different from the product's current price?",
        'OrderItem.objects.exclude(unit_price=F("product__price"))')

    with transaction.atomic():
        ask("Stock of product E001 before the update",
            'Product.objects.filter(sku="E001").values_list("sku", "stock")')
        ask("F expression (update): sell 5 units of E001 using a database-side update "
            "(number of rows updated)",
            'Product.objects.filter(sku="E001").update(stock=F("stock") - 5)')
        ask("Stock of product E001 after the update",
            'Product.objects.filter(sku="E001").values_list("sku", "stock")')
        transaction.set_rollback(True)

    ask("Stock of product E001 after the rollback (back to the original value)",
        'Product.objects.filter(sku="E001").values_list("sku", "stock")')
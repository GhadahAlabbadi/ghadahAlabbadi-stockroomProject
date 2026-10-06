from decimal import Decimal

from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
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

# ---------------------------------------------------------------------------
# Section 9: Relationship queries and required explanations
# ---------------------------------------------------------------------------

def try_get(**kwargs):
    """Call get() on Product and report the two errors it can raise."""
    try:
        return Product.objects.get(**kwargs)
    except Product.DoesNotExist:
        return "Product.DoesNotExist raised (get() found no match)"
    except Product.MultipleObjectsReturned:
        return "Product.MultipleObjectsReturned raised (get() found several matches)"


def show_lazy_evaluation():
    print("\nQuestion : When does a QuerySet actually touch the database?")
    with CaptureQueriesContext(connection) as log:
        print("Statement: queryset = Product.objects.filter(is_active=True).order_by('name')")
        queryset = Product.objects.filter(is_active=True).order_by("name")
        print("Result   : database queries so far =", len(log))

        print("Statement: rows = list(queryset)")
        rows = list(queryset)
        print(f"Result   : database queries so far = {len(log)} ({len(rows)} rows loaded)")

        print("Statement: list(queryset)   (same QuerySet again, rows are cached)")
        list(queryset)
        print("Result   : database queries so far =", len(log))

        print("Statement: Product.objects.filter(is_active=True).count()   (a new QuerySet)")
        Product.objects.filter(is_active=True).count()
        print("Result   : database queries so far =", len(log))


def explain(title, text):
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)
    print(text)


def run_relationships():
    heading("RELATIONSHIP QUERIES")

    print("\n--- Forward traversal (from the model that holds the ForeignKey) ---")
    ask("From a Product, access its Category",
        'Product.objects.get(sku="E001").category')
    ask("From an OrderItem, access the related Product",
        "OrderItem.objects.filter(order__pk=5).first().product")
    ask("From an Order, access its Customer",
        "Order.objects.get(pk=5).customer")

    print("\n--- Reverse traversal (through the related_name) ---")
    ask("From a Category, return all related Products",
        'Category.objects.get(name="Electronics").products.all()')
    ask("From a Customer, return all related Orders",
        'Customer.objects.get(email="aisha@example.com").orders.all()')
    ask("From an Order, return its OrderItems",
        "Order.objects.get(pk=5).items.all()")

    print("\n--- Many-to-many through OrderItem ---")
    ask("Return all products contained in one selected order (order 5)",
        "Order.objects.get(pk=5).products.all()")
    ask("Return all orders that contain one selected product (SKU E001)",
        'Product.objects.get(sku="E001").orders.all()')

    print("\n--- The same two questions written as lookups across relationships ---")
    ask("Products in order 5, using a lookup across OrderItem",
        "Product.objects.filter(order_items__order__pk=5)")
    ask("Orders containing SKU E001, using a lookup across OrderItem",
        'Order.objects.filter(items__product__sku="E001")')

    print("\n--- get() compared with filter() ---")
    ask("get(): exactly one match returns one object",
        'Product.objects.get(sku="E001")')
    ask("filter(): the same condition returns a QuerySet",
        'Product.objects.filter(sku="E001")')
    ask("get() when nothing matches", 'try_get(sku="NOPE")')
    ask("filter() when nothing matches", 'Product.objects.filter(sku="NOPE")')
    ask("get() when several rows match", "try_get(is_active=True)")

    print("\n--- Lazy evaluation ---")
    show_lazy_evaluation()

    heading("REQUIRED EXPLANATIONS")

    explain(
        "1. Forward versus reverse relationship traversal",
        "Forward traversal follows a ForeignKey from the model that declares it to the\n"
        "model it points to, and returns one object: product.category,\n"
        "order_item.product, order.customer.\n"
        "Reverse traversal goes the other way, from the referenced model back to the\n"
        "many side, through the related_name, and returns a related manager that gives\n"
        "a QuerySet: category.products, customer.orders, order.items,\n"
        "product.order_items.\n"
        "Both directions use the same foreign key column (for example\n"
        "inventory_product.category_id); only the direction of the lookup differs.",
    )

    explain(
        "2. Why OrderItem is a model and not only an automatic many-to-many table",
        "An automatic many-to-many table holds only two foreign keys. An order line\n"
        "needs more: the quantity, the unit_price at the time of sale, and the rule\n"
        "that the same product cannot appear twice in one order. These need their own\n"
        "columns and constraints, so OrderItem is a real model. Order.products still\n"
        "works as a many-to-many shortcut because it is declared with\n"
        "through='OrderItem'. The model also makes quantity * unit_price available\n"
        "for the order totals in the aggregation section.",
    )

    explain(
        "3. The difference between get() and filter()",
        "get() returns exactly one object. It raises DoesNotExist when nothing matches\n"
        "and MultipleObjectsReturned when several rows match. filter() always returns\n"
        "a QuerySet, which may be empty, hold one row or hold many rows, and it never\n"
        "raises for a missing row. Use get() when exactly one row is expected (a\n"
        "primary key or unique field) and filter() when zero or more rows are fine.",
    )

    explain(
        "4. When a QuerySet is evaluated, and why it is called lazy",
        "A QuerySet is lazy: building it and chaining filter(), exclude() or\n"
        "order_by() only describes the SQL and does not run it. The database is\n"
        "queried when the QuerySet is evaluated: by iterating over it, list(), len(),\n"
        "bool(), printing it, indexing one item, or calling count(), exists() or\n"
        "first(). After the first evaluation the rows are cached inside that QuerySet,\n"
        "so using it again does not query again. Laziness lets Django combine all the\n"
        "chained conditions into one SQL statement and avoids queries whose results\n"
        "are never used.",
    )
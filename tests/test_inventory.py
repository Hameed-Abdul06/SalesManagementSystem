"""Unit and integration tests for inventory management, stock deductions, and transactional integrity."""
import pytest
import config
from database.schema import init_db
from database.connection import get_connection
from services import product_service, customer_service, order_service


@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path, monkeypatch):
    """Use a temporary SQLite database for each test to ensure complete isolation."""
    test_db_file = tmp_path / "test_sales_system.db"
    monkeypatch.setattr(config, "DATABASE_PATH", test_db_file)
    init_db(test_db_file)
    yield test_db_file


def test_create_and_fetch_product():
    """Verify product insertion and retrieval."""
    prod = product_service.create_product(
        sku="TEST-001",
        name="Test Item 1",
        category="Electronics",
        cost_price=10.0,
        selling_price=20.0,
        stock_quantity=50,
        low_stock_threshold=5,
        description="A test product"
    )
    assert prod["sku"] == "TEST-001"
    assert prod["stock_quantity"] == 50
    
    fetched = product_service.get_product_by_id(prod["id"])
    assert fetched["name"] == "Test Item 1"


def test_duplicate_sku_rejection():
    """Verify that creating two products with identical SKU raises ValueError."""
    product_service.create_product(
        sku="UNIQUE-SKU",
        name="Original",
        category="Other",
        cost_price=5.0,
        selling_price=10.0,
        stock_quantity=10
    )
    with pytest.raises(ValueError, match="already exists"):
        product_service.create_product(
            sku="unique-sku",  # Case-insensitive duplicate check
            name="Copycat",
            category="Other",
            cost_price=5.0,
            selling_price=10.0,
            stock_quantity=5
        )


def test_order_reduces_stock_automatically():
    """Verify stock decrements correctly upon placing an order."""
    p = product_service.create_product(
        sku="STOCK-001",
        name="Stock Item",
        category="Electronics",
        cost_price=15.0,
        selling_price=30.0,
        stock_quantity=20
    )
    c = customer_service.create_customer(name="Alice Walker", phone="1234567890")

    items = [{
        "product_id": p["id"],
        "name": p["name"],
        "cost_price": p["cost_price"],
        "unit_price": p["selling_price"],
        "quantity": 5
    }]

    order = order_service.create_order(
        customer_id=c["id"],
        items=items,
        payment_method="Cash",
        payment_status="Paid",
        order_status="Completed"
    )
    assert order["total_amount"] > 0

    # Verify inventory was decremented from 20 to 15
    updated_p = product_service.get_product_by_id(p["id"])
    assert updated_p["stock_quantity"] == 15


def test_overselling_prevention():
    """Verify that attempting to order more than available stock raises an error and preserves stock."""
    p = product_service.create_product(
        sku="LOW-001",
        name="Scarce Item",
        category="Electronics",
        cost_price=5.0,
        selling_price=10.0,
        stock_quantity=3
    )

    items = [{
        "product_id": p["id"],
        "name": p["name"],
        "cost_price": p["cost_price"],
        "unit_price": p["selling_price"],
        "quantity": 5  # Requested 5, only 3 available
    }]

    with pytest.raises(ValueError, match="Insufficient stock"):
        order_service.create_order(
            customer_id=None,
            items=items,
            payment_method="Cash"
        )

    # Stock must remain unchanged
    unchanged_p = product_service.get_product_by_id(p["id"])
    assert unchanged_p["stock_quantity"] == 3


def test_order_cancellation_restores_stock():
    """Verify that cancelling an order restores the previously deducted stock."""
    p = product_service.create_product(
        sku="RESTORE-001",
        name="Restorable Item",
        category="Electronics",
        cost_price=10.0,
        selling_price=25.0,
        stock_quantity=10
    )

    items = [{
        "product_id": p["id"],
        "name": p["name"],
        "cost_price": p["cost_price"],
        "unit_price": p["selling_price"],
        "quantity": 4
    }]

    order = order_service.create_order(
        customer_id=None,
        items=items,
        payment_method="Cash",
        order_status="Completed"
    )
    # Check intermediate stock
    assert product_service.get_product_by_id(p["id"])["stock_quantity"] == 6

    # Cancel order
    order_service.update_order_status(order["id"], "Cancelled")

    # Stock must be restored back to 10
    assert product_service.get_product_by_id(p["id"])["stock_quantity"] == 10


def test_manual_stock_adjustment():
    """Verify manual stock adjustments for restocking and shrinkage."""
    p = product_service.create_product(
        sku="ADJ-001",
        name="Adjustable",
        category="Other",
        cost_price=5.0,
        selling_price=10.0,
        stock_quantity=10
    )

    # Restock +15
    res1 = product_service.adjust_stock(p["id"], 15, "Supplier Delivery")
    assert res1["new_stock"] == 25

    # Shrinkage -5
    res2 = product_service.adjust_stock(p["id"], -5, "Damaged in transit")
    assert res2["new_stock"] == 20

    # Attempt to reduce beyond zero
    with pytest.raises(ValueError, match="Cannot reduce stock"):
        product_service.adjust_stock(p["id"], -25, "Impossible reduction")

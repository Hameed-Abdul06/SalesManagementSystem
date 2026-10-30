"""Unit tests for financial calculations, order totals, discounts, taxes, and profit."""
import pytest
from services.order_service import calculate_order_totals


def test_basic_subtotal_calculation():
    """Verify subtotal without discounts or tax."""
    items = [
        {"name": "Mouse", "unit_price": 25.0, "cost_price": 10.0, "quantity": 2},
        {"name": "Keyboard", "unit_price": 50.0, "cost_price": 20.0, "quantity": 1},
    ]
    # 25*2 + 50*1 = 100.0
    res = calculate_order_totals(items, discount_type="Percentage", discount_value=0.0, tax_rate=0.0)
    assert res["subtotal"] == 100.0
    assert res["discount_amount"] == 0.0
    assert res["tax_amount"] == 0.0
    assert res["total_amount"] == 100.0
    assert res["total_cost"] == 40.0  # 10*2 + 20*1
    assert res["estimated_profit"] == 60.0  # 100 - 40


def test_percentage_discount():
    """Verify percentage discount calculation."""
    items = [
        {"name": "Item A", "unit_price": 200.0, "cost_price": 100.0, "quantity": 1}
    ]
    # 10% discount on 200 = 20.0, tax 5% on 180 = 9.0, total = 189.0
    res = calculate_order_totals(items, discount_type="Percentage", discount_value=10.0, tax_rate=5.0)
    assert res["subtotal"] == 200.0
    assert res["discount_amount"] == 20.0
    assert res["tax_amount"] == 9.0
    assert res["total_amount"] == 189.0
    assert res["total_cost"] == 100.0
    assert res["estimated_profit"] == 80.0  # 189 - 100 - 9 = 80.0


def test_fixed_amount_discount():
    """Verify flat amount discount calculation."""
    items = [
        {"name": "Item A", "unit_price": 50.0, "cost_price": 20.0, "quantity": 2}
    ]
    # Subtotal 100, Fixed discount 15, taxable = 85, tax 10% on 85 = 8.5, total = 93.5
    res = calculate_order_totals(items, discount_type="Fixed", discount_value=15.0, tax_rate=10.0)
    assert res["subtotal"] == 100.0
    assert res["discount_amount"] == 15.0
    assert res["tax_amount"] == 8.5
    assert res["total_amount"] == 93.5
    assert res["estimated_profit"] == 45.0  # 93.5 - 40 - 8.5 = 45.0


def test_discount_greater_than_subtotal():
    """Fixed discount cannot exceed subtotal."""
    items = [
        {"name": "Item", "unit_price": 30.0, "cost_price": 15.0, "quantity": 1}
    ]
    res = calculate_order_totals(items, discount_type="Fixed", discount_value=50.0, tax_rate=5.0)
    assert res["discount_amount"] == 30.0  # Capped at subtotal
    assert res["total_amount"] == 0.0


def test_negative_values_raise_error():
    """Negative inputs must raise ValueError."""
    items = [{"name": "Item", "unit_price": 10.0, "cost_price": 5.0, "quantity": 1}]
    with pytest.raises(ValueError):
        calculate_order_totals(items, discount_value=-5.0)

    with pytest.raises(ValueError):
        calculate_order_totals(items, tax_rate=-1.0)

    with pytest.raises(ValueError):
        calculate_order_totals([{"name": "Item", "unit_price": 10.0, "cost_price": 5.0, "quantity": 0}])

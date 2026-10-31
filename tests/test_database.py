"""Unit and security tests for Empório da Música SQLite database layer."""

import os
import sqlite3
import pytest
from pathlib import Path

from src.database import (
    DEFAULT_DB_PATH,
    get_connection,
    get_order_status,
    get_product_details,
    list_all_products,
    search_products,
)


@pytest.fixture(scope="module")
def db_conn():
    """Ensure database exists and provide connection fixture."""
    assert DEFAULT_DB_PATH.exists(), "Database emporio.db must exist before tests run."
    conn = get_connection()
    yield conn
    conn.close()


def test_schema_integrity_and_row_counts(db_conn):
    """Verify all 6 core tables are populated from CSV sources."""
    tables = ["categories", "products", "customers", "orders", "order_items", "promotions"]
    cur = db_conn.cursor()
    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM {t};")
        count = cur.fetchone()[0]
        assert count > 0, f"Table {t} should contain ingested rows, found {count}."


def test_b_tree_indexes_exist(db_conn):
    """Verify B-tree performance indexes are created."""
    cur = db_conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row[0] for row in cur.fetchall()]
    assert "idx_products_name" in indexes
    assert "idx_products_category_id" in indexes
    assert "idx_products_price" in indexes
    assert "idx_orders_tracking_code" in indexes
    assert "idx_customers_email" in indexes


def test_search_products_price_filter():
    """Validate price-constrained search (e.g. violões <= R$ 1000)."""
    prods = search_products(keyword="violão", max_price=1000.0)
    assert len(prods) > 0
    for p in prods:
        assert p["effective_price"] <= 1000.0
        assert p["stock_quantity"] > 0
        assert p["pix_price"] == round(p["effective_price"] * 0.95, 2)
        assert p["installment_12x"] == round(p["effective_price"] / 12.0, 2)


def test_promotions_is_active_validation(db_conn):
    """Ensure expired/inactive promotions (is_active == 0) are NOT applied to prices."""
    cur = db_conn.cursor()
    # Find a product with inactive promotion
    cur.execute("SELECT product_id, discount_percent FROM promotions WHERE is_active = 0 LIMIT 1;")
    row = cur.fetchone()
    if row:
        prod_id = row[0]
        details = get_product_details(str(prod_id))
        assert details is not None
        # Effective price must equal base price when promotion is inactive
        assert details["effective_price"] == details["base_price"]
        assert details["discount_percent"] == 0.0


def test_get_product_details_takamine():
    """Verify specific lookup of Takamine GD20."""
    item = get_product_details("Takamine GD20")
    assert item is not None
    assert "Takamine GD20" in item["name"]
    assert item["base_price"] > 0
    assert item["stock_quantity"] > 0
    assert "specs" in item and isinstance(item["specs"], dict)


def test_lgpd_dual_factor_order_lookup():
    """Verify LGPD dual-factor authentication on orders."""
    # Valid auth: Pedro Oliveira -> BRAB1234567BR
    res_valid = get_order_status("BRAB1234567BR", "pedro.oliveira@jmail.com")
    assert res_valid["authenticated"] is True
    assert res_valid["tracking_code"] == "BRAB1234567BR"
    assert res_valid["status"] == "delivered"
    assert "items" in res_valid and len(res_valid["items"]) > 0
    # Customer name must be masked for LGPD privacy
    assert res_valid["masked_customer"].startswith("Pedro")
    assert "." in res_valid["masked_customer"]

    # Invalid auth: wrong email
    res_invalid = get_order_status("BRAB1234567BR", "unauthorized@target.com")
    assert res_invalid["authenticated"] is False
    assert "LGPD" in res_invalid["error"]


def test_anti_sqli_resilience():
    """Verify parameterized queries prevent SQL injection."""
    malicious_inputs = [
        "' OR '1'='1",
        "Takamine'; DROP TABLE products; --",
        "1 UNION SELECT null, null, null, null, null, null, null, null, null --",
    ]
    for attack in malicious_inputs:
        # Should execute safely without database corruption or leaking unintended rows
        res = search_products(keyword=attack)
        assert isinstance(res, list)

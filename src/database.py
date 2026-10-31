"""Database module for Empório da Música.

Handles SQLite ingestion of store CSV datasets, encoding sanitization,
relational indexing, and parameterized queries with strict anti-SQLi protection
and LGPD customer privacy compliance.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Default filesystem paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "emporio.db"


def sanitize_text(value: Optional[str]) -> str:
    """Sanitize strings by normalizing spaces and fixing known encoding artifacts."""
    if not value:
        return ""
    text = value.strip()
    # Normalize common mojibake or replacement artifacts if present
    replacements = {
        "\ufffd": "",
        "elǸtricas": "elétricas",
        "eltricas": "elétricas",
        "acsticos": "acústicos",
        "formaes": "formações",
        "Percusso": "Percussão",
        "projeo": "projeção",
        "clssico": "clássico",
        "slido": "sólido",
        "Slido": "Sólido",
        "intermedirio": "intermediário",
        "Liquidao": "Liquidação",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def get_connection(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return an active SQLite database connection with row factory configured."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(data_dir: Path | str = DATA_DIR, db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create relational schema, ingest sanitized CSV data, and create B-tree indexes."""
    data_path = Path(data_dir)
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Recreate clean database
    if db_file.exists():
        db_file.unlink()

    conn = get_connection(db_file)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            price_brl REAL NOT NULL,
            name TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            description TEXT,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            specs TEXT,
            created_at TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (category_id)
        );

        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            status TEXT NOT NULL,
            total_brl REAL NOT NULL,
            payment_method TEXT,
            tracking_code TEXT,
            estimated_delivery TEXT,
            notes TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
        );

        CREATE TABLE order_items (
            order_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            product_id INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        );

        CREATE TABLE promotions (
            promotion_id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            discount_percent REAL NOT NULL,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        );

        -- Performance & query indexes
        CREATE INDEX idx_products_name ON products(name);
        CREATE INDEX idx_products_category_id ON products(category_id);
        CREATE INDEX idx_products_price ON products(price_brl);
        CREATE INDEX idx_orders_tracking_code ON orders(tracking_code);
        CREATE INDEX idx_orders_customer_id ON orders(customer_id);
        CREATE INDEX idx_customers_email ON customers(email);
        CREATE INDEX idx_customers_phone ON customers(phone);
        CREATE INDEX idx_promotions_product ON promotions(product_id);
        """
    )

    # Ingestion mapping: table -> matching filename substring
    csv_mappings = [
        ("categories", "categories.csv"),
        ("customers", "customers.csv"),
        ("products", "products.csv"),
        ("orders", "orders.csv"),
        ("order_items", "order_items.csv"),
        ("promotions", "promotions.csv"),
    ]

    for table_name, pattern in csv_mappings:
        matches = list(data_path.glob(f"*{pattern}"))
        if not matches:
            continue
        csv_file = matches[0]

        # Read CSV with UTF-8 encoding
        with open(csv_file, mode="r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                cleaned_row = {k.strip(): sanitize_text(v) for k, v in row.items() if k}
                rows.append(cleaned_row)

            if rows:
                columns = list(rows[0].keys())
                placeholders = ", ".join(["?"] * len(columns))
                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                val_tuples = [tuple(r[col] for col in columns) for r in rows]
                cur.executemany(sql, val_tuples)

    conn.commit()
    conn.close()


def search_products(
    keyword: Optional[str] = None,
    max_price: Optional[float] = None,
    category_name: Optional[str] = None,
    in_stock_only: bool = True,
    limit: int = 10,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """Search products with parameterized SQL, filtering active promotions and calculating financing terms."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = """
        SELECT 
            p.product_id,
            p.name,
            p.price_brl,
            p.stock_quantity,
            p.status,
            p.description,
            p.specs,
            c.name AS category_name,
            pr.discount_percent,
            pr.description AS promo_description
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN promotions pr ON p.product_id = pr.product_id AND pr.is_active = 1
        WHERE p.status = 'active'
    """
    params: List[Any] = []

    if in_stock_only:
        query += " AND p.stock_quantity > 0"

    if keyword:
        # Match against name or description
        query += " AND (p.name LIKE ? OR p.description LIKE ?)"
        kw_param = f"%{keyword.strip()}%"
        params.extend([kw_param, kw_param])

    if category_name:
        query += " AND c.name LIKE ?"
        params.append(f"%{category_name.strip()}%")

    if max_price is not None:
        query += " AND p.price_brl <= ?"
        params.append(float(max_price))

    query += " ORDER BY p.price_brl ASC LIMIT ?"
    params.append(int(limit))

    cur.execute(query, params)
    rows = cur.fetchall()

    results = []
    for r in rows:
        base_price = float(r["price_brl"])
        discount = float(r["discount_percent"]) if r["discount_percent"] is not None else 0.0
        effective_price = round(base_price * (1.0 - (discount / 100.0)), 2)
        pix_price = round(effective_price * 0.95, 2)  # 5% cash discount on PIX
        installment_12x = round(effective_price / 12.0, 2)

        try:
            specs_obj = json.loads(r["specs"]) if r["specs"] else {}
        except Exception:
            specs_obj = {}

        results.append({
            "product_id": r["product_id"],
            "name": r["name"],
            "category": r["category_name"],
            "base_price": base_price,
            "effective_price": effective_price,
            "pix_price": pix_price,
            "installment_12x": installment_12x,
            "discount_percent": discount,
            "promo_description": r["promo_description"],
            "stock_quantity": r["stock_quantity"],
            "description": r["description"],
            "specs": specs_obj,
        })

    conn.close()
    return results


def get_product_details(
    product_identifier: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Retrieve exhaustive product details by numeric ID or matching name."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = """
        SELECT 
            p.product_id,
            p.name,
            p.price_brl,
            p.stock_quantity,
            p.status,
            p.description,
            p.specs,
            c.name AS category_name,
            pr.discount_percent,
            pr.description AS promo_description
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN promotions pr ON p.product_id = pr.product_id AND pr.is_active = 1
        WHERE (p.product_id = ? OR p.name LIKE ?)
        LIMIT 1
    """
    ident = str(product_identifier).strip()
    prod_id = int(ident) if ident.isdigit() else -1
    name_like = f"%{ident}%"

    cur.execute(query, (prod_id, name_like))
    r = cur.fetchone()
    conn.close()

    if not r:
        return None

    base_price = float(r["price_brl"])
    discount = float(r["discount_percent"]) if r["discount_percent"] is not None else 0.0
    effective_price = round(base_price * (1.0 - (discount / 100.0)), 2)
    pix_price = round(effective_price * 0.95, 2)
    installment_12x = round(effective_price / 12.0, 2)

    try:
        specs_obj = json.loads(r["specs"]) if r["specs"] else {}
    except Exception:
        specs_obj = {}

    return {
        "product_id": r["product_id"],
        "name": r["name"],
        "category": r["category_name"],
        "base_price": base_price,
        "effective_price": effective_price,
        "pix_price": pix_price,
        "installment_12x": installment_12x,
        "discount_percent": discount,
        "promo_description": r["promo_description"],
        "stock_quantity": r["stock_quantity"],
        "description": r["description"],
        "specs": specs_obj,
    }


def get_order_status(
    tracking_code: str,
    customer_identifier: str,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Verify order status with LGPD dual-factor verification (tracking code + email or phone)."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    code_clean = tracking_code.strip().upper()
    ident_clean = customer_identifier.strip().lower()
    # Normalize phone digits for resilient matching
    phone_digits = re.sub(r"\D", "", ident_clean)

    query = """
        SELECT 
            o.order_id,
            o.order_date,
            o.status,
            o.total_brl,
            o.payment_method,
            o.tracking_code,
            o.estimated_delivery,
            o.notes,
            c.name AS customer_name,
            c.email AS customer_email,
            c.phone AS customer_phone,
            c.city AS customer_city
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE UPPER(o.tracking_code) = ?
    """
    cur.execute(query, (code_clean,))
    order = cur.fetchone()

    if not order:
        conn.close()
        return {
            "authenticated": False,
            "error": "Código de rastreamento não encontrado no sistema.",
        }

    # Verify identity against email or phone digits
    stored_email = (order["customer_email"] or "").strip().lower()
    stored_phone_digits = re.sub(r"\D", "", order["customer_phone"] or "")

    email_matched = ident_clean and (ident_clean in stored_email or stored_email in ident_clean)
    phone_matched = phone_digits and (phone_digits in stored_phone_digits or stored_phone_digits in phone_digits)

    if not (email_matched or phone_matched):
        conn.close()
        return {
            "authenticated": False,
            "error": "Por conformidade com a LGPD, o e-mail ou telefone informado não confere com o titular deste pedido.",
        }

    # Fetch order items
    items_query = """
        SELECT 
            oi.quantity,
            p.name AS product_name,
            p.price_brl
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
    """
    cur.execute(items_query, (order["order_id"],))
    items_rows = cur.fetchall()
    items = [
        {"quantity": it["quantity"], "product": it["product_name"]}
        for it in items_rows
    ]

    conn.close()

    # Mask name for privacy (e.g. Lucas M. da S.)
    name_parts = order["customer_name"].split()
    masked_name = name_parts[0] + " " + " ".join(f"{p[0]}." for p in name_parts[1:]) if len(name_parts) > 1 else order["customer_name"]

    return {
        "authenticated": True,
        "order_id": order["order_id"],
        "tracking_code": order["tracking_code"],
        "status": order["status"],
        "order_date": order["order_date"],
        "estimated_delivery": order["estimated_delivery"],
        "notes": order["notes"],
        "payment_method": order["payment_method"],
        "masked_customer": masked_name,
        "destination_city": order["customer_city"],
        "items": items,
    }


def list_all_products(
    category_id: Optional[int] = None,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> List[Dict[str, Any]]:
    """List active products for storefront feed."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    query = """
        SELECT 
            p.product_id,
            p.name,
            p.price_brl,
            p.stock_quantity,
            p.description,
            p.specs,
            c.name AS category_name,
            pr.discount_percent
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        LEFT JOIN promotions pr ON p.product_id = pr.product_id AND pr.is_active = 1
        WHERE p.status = 'active'
    """
    params: List[Any] = []
    if category_id is not None:
        query += " AND p.category_id = ?"
        params.append(category_id)

    query += " ORDER BY p.product_id ASC"
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        base_price = float(r["price_brl"])
        discount = float(r["discount_percent"]) if r["discount_percent"] is not None else 0.0
        effective_price = round(base_price * (1.0 - (discount / 100.0)), 2)
        pix_price = round(effective_price * 0.95, 2)
        installment_12x = round(effective_price / 12.0, 2)
        try:
            specs_obj = json.loads(r["specs"]) if r["specs"] else {}
        except Exception:
            specs_obj = {}

        results.append({
            "product_id": r["product_id"],
            "name": r["name"],
            "category": r["category_name"],
            "base_price": base_price,
            "effective_price": effective_price,
            "pix_price": pix_price,
            "installment_12x": installment_12x,
            "discount_percent": discount,
            "stock_quantity": r["stock_quantity"],
            "description": r["description"],
            "specs": specs_obj,
        })
    return results


if __name__ == "__main__":
    init_db()
    print("Database initialization completed at:", DEFAULT_DB_PATH)
    sample_prods = search_products(keyword="violão", max_price=1000)
    print(f"Found {len(sample_prods)} violões up to R$1000:")
    for p in sample_prods:
        print(f" - {p['name']}: R$ {p['effective_price']} (PIX: R$ {p['pix_price']}), Stock: {p['stock_quantity']}")

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_SQLITE_PATH = PROJECT_ROOT / "backend" / "loan_management_local.db"
DEFAULT_DATABASE_URL = f"sqlite:///{str(LOCAL_SQLITE_PATH).replace(os.sep, '/')}"


def using_sqlite(database_url: str) -> bool:
    return str(database_url or "").strip().lower().startswith("sqlite:")


def get_database_url(explicit_url: str | None) -> str:
    if explicit_url:
        return explicit_url
    configured = str(os.environ.get("DATABASE_URL", "") or "").strip()
    return configured or DEFAULT_DATABASE_URL


def column_exists(conn, table_name: str, column_name: str, is_sqlite: bool) -> bool:
    if is_sqlite:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).mappings().all()
        return any(str(row.get("name") or "").lower() == column_name.lower() for row in rows)
    query = text(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :table_name AND column_name = :column_name
        LIMIT 1
        """
    )
    return conn.execute(query, {"table_name": table_name, "column_name": column_name}).first() is not None


def add_column_if_missing(conn, table_name: str, column_name: str, definition: str, is_sqlite: bool) -> None:
    if not column_exists(conn, table_name, column_name, is_sqlite):
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def normalize_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:10]).date()


def normalize_amount(value) -> float:
    return round(float(value or 0), 2)


def ensure_schema(conn, is_sqlite: bool) -> None:
    add_column_if_missing(conn, "payment_transactions", "is_virtual", "BOOLEAN DEFAULT FALSE", is_sqlite)
    add_column_if_missing(conn, "payment_transactions", "linked_successor_loan_id", "VARCHAR(20)", is_sqlite)
    add_column_if_missing(conn, "loan_master", "parent_loan_id", "VARCHAR(20)", is_sqlite)
    add_column_if_missing(conn, "loan_master", "loan_chain_id", "VARCHAR(36)", is_sqlite)
    add_column_if_missing(conn, "loan_master", "fresh_principal", "DECIMAL(15,2)", is_sqlite)
    add_column_if_missing(conn, "loan_master", "chain_start_date", "DATE", is_sqlite)


def backfill_virtual_flags(conn) -> None:
    conn.execute(
        text(
            """
            UPDATE payment_transactions
            SET is_virtual = TRUE
            WHERE UPPER(COALESCE(payment_type, '')) = 'BALANCE'
            """
        )
    )
    conn.execute(
        text(
            """
            UPDATE loan_master
            SET fresh_principal = ROUND(principal_amount - COALESCE(add_on_principal, 0), 2)
            WHERE fresh_principal IS NULL
            """
        )
    )


def backfill_parent_links(conn) -> int:
    loans = [
        dict(row)
        for row in conn.execute(
        text(
            """
            SELECT loan_id, customer_id, add_on_principal, start_date
            FROM loan_master
            WHERE COALESCE(add_on_principal, 0) > 0
            ORDER BY start_date, loan_id
            """
        )
    ).mappings().all()
    ]
    balance_payments = [
        dict(row)
        for row in conn.execute(
        text(
            """
            SELECT payment_id, loan_id, customer_id, payment_date, amount, linked_successor_loan_id
            FROM payment_transactions
            WHERE UPPER(COALESCE(payment_type, '')) = 'BALANCE'
            ORDER BY payment_date, payment_id
            """
        )
    ).mappings().all()
    ]
    matched = 0

    for loan in loans:
        add_on_principal = normalize_amount(loan.get("add_on_principal"))
        loan_start = normalize_date(loan.get("start_date"))
        if add_on_principal <= 0 or not loan_start:
            continue
        candidates = [
            payment for payment in balance_payments
            if payment.get("customer_id") == loan.get("customer_id")
            and normalize_amount(payment.get("amount")) == add_on_principal
            and normalize_date(payment.get("payment_date"))
            and normalize_date(payment.get("payment_date")) <= loan_start
            and (not payment.get("linked_successor_loan_id") or payment.get("linked_successor_loan_id") == loan.get("loan_id"))
        ]
        if not candidates:
            continue
        parent_payment = max(
            candidates,
            key=lambda payment: (
                normalize_date(payment.get("payment_date")) or date.min,
                str(payment.get("payment_id") or "")
            )
        )
        conn.execute(
            text(
                """
                UPDATE payment_transactions
                SET linked_successor_loan_id = :successor_loan_id, is_virtual = TRUE
                WHERE payment_id = :payment_id
                """
            ),
            {"successor_loan_id": loan.get("loan_id"), "payment_id": parent_payment.get("payment_id")},
        )
        parent_payment["linked_successor_loan_id"] = loan.get("loan_id")
        conn.execute(
            text(
                """
                UPDATE loan_master
                SET parent_loan_id = :parent_loan_id
                WHERE loan_id = :loan_id
                """
            ),
            {"parent_loan_id": parent_payment.get("loan_id"), "loan_id": loan.get("loan_id")},
        )
        matched += 1
    return matched


def backfill_chain_metadata(conn) -> int:
    loan_rows = conn.execute(
        text(
            """
            SELECT loan_id, parent_loan_id, start_date, loan_chain_id, chain_start_date
            FROM loan_master
            """
        )
    ).mappings().all()
    loan_map = {row["loan_id"]: dict(row) for row in loan_rows}

    def resolve_root(loan_id: str) -> str:
        seen = set()
        current_id = loan_id
        while current_id and current_id not in seen:
            seen.add(current_id)
            parent_id = str(loan_map.get(current_id, {}).get("parent_loan_id") or "").strip()
            if not parent_id or parent_id not in loan_map:
                return current_id
            current_id = parent_id
        return loan_id

    updates = []
    for loan_id, loan in loan_map.items():
        root_id = resolve_root(loan_id)
        root = loan_map.get(root_id, {})
        chain_id = str(root.get("loan_chain_id") or "").strip() or str(uuid4())
        chain_start = normalize_date(root.get("chain_start_date")) or normalize_date(root.get("start_date"))
        updates.append(
            {
                "loan_id": loan_id,
                "loan_chain_id": chain_id,
                "chain_start_date": chain_start,
            }
        )
        if not root.get("loan_chain_id"):
            root["loan_chain_id"] = chain_id
        if not root.get("chain_start_date"):
            root["chain_start_date"] = chain_start

    for update in updates:
        conn.execute(
            text(
                """
                UPDATE loan_master
                SET loan_chain_id = :loan_chain_id,
                    chain_start_date = :chain_start_date
                WHERE loan_id = :loan_id
                """
            ),
            update,
        )
    return len(updates)


def validate_rollover_totals(conn) -> dict:
    virtual_total = conn.execute(
        text("SELECT COALESCE(SUM(amount), 0) FROM payment_transactions WHERE COALESCE(is_virtual, FALSE) = TRUE")
    ).scalar_one()
    add_on_total = conn.execute(
        text("SELECT COALESCE(SUM(add_on_principal), 0) FROM loan_master WHERE add_on_principal IS NOT NULL")
    ).scalar_one()

    loan_totals = {
        row["customer_id"]: normalize_amount(row["total_add_on"])
        for row in conn.execute(
            text(
                """
                SELECT customer_id, COALESCE(SUM(add_on_principal), 0) AS total_add_on
                FROM loan_master
                GROUP BY customer_id
                """
            )
        ).mappings().all()
    }
    payment_totals = {
        row["customer_id"]: normalize_amount(row["total_virtual"])
        for row in conn.execute(
            text(
                """
                SELECT customer_id, COALESCE(SUM(amount), 0) AS total_virtual
                FROM payment_transactions
                WHERE COALESCE(is_virtual, FALSE) = TRUE
                GROUP BY customer_id
                """
            )
        ).mappings().all()
    }
    discrepancies = []
    for customer_id in sorted(set(loan_totals) | set(payment_totals)):
        add_on_amount = loan_totals.get(customer_id, 0.0)
        virtual_amount = payment_totals.get(customer_id, 0.0)
        if round(add_on_amount - virtual_amount, 2) != 0:
            discrepancies.append(
                {
                    "customer_id": customer_id,
                    "add_on_principal_total": add_on_amount,
                    "virtual_balance_total": virtual_amount,
                    "difference": round(add_on_amount - virtual_amount, 2),
                }
            )
    return {
        "virtual_payment_total": normalize_amount(virtual_total),
        "add_on_principal_total": normalize_amount(add_on_total),
        "matches": round(normalize_amount(virtual_total) - normalize_amount(add_on_total), 2) == 0,
        "discrepancies": discrepancies,
    }


def run_migration(database_url: str) -> dict:
    engine = create_engine(database_url, connect_args={"check_same_thread": False} if using_sqlite(database_url) else {})
    with engine.begin() as conn:
        is_sqlite = using_sqlite(database_url)
        ensure_schema(conn, is_sqlite)
        backfill_virtual_flags(conn)
        parent_matches = backfill_parent_links(conn)
        chain_updates = backfill_chain_metadata(conn)
        validation = validate_rollover_totals(conn)
    return {
        "database_url": database_url,
        "parent_links_backfilled": parent_matches,
        "chain_rows_updated": chain_updates,
        "validation": validation,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill loan rollover metadata and virtual payment flags.")
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL / local SQLite fallback.")
    args = parser.parse_args()
    report = run_migration(get_database_url(args.database_url))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()

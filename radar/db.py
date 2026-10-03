from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from datetime import datetime, timezone
from typing import Any

from radar.config import DATA_DIR, DB_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS source_status (
                source TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                message TEXT NOT NULL,
                last_attempt TEXT,
                last_success TEXT
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                country TEXT NOT NULL DEFAULT '',
                currency TEXT NOT NULL DEFAULT 'EUR',
                provider TEXT NOT NULL DEFAULT '',
                provider_url TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                product_cost REAL NOT NULL DEFAULT 0,
                shipping_cost REAL NOT NULL DEFAULT 0,
                ad_cost REAL NOT NULL DEFAULT 0,
                platform_fee_pct REAL NOT NULL DEFAULT 0,
                tax_pct REAL NOT NULL DEFAULT 0,
                refund_pct REAL NOT NULL DEFAULT 0,
                sale_price REAL NOT NULL DEFAULT 0,
                launch_budget REAL NOT NULL DEFAULT 0,
                delivery_days INTEGER,
                supplier_quality REAL,
                demand_score REAL,
                demand_source TEXT NOT NULL DEFAULT '',
                demand_updated TEXT NOT NULL DEFAULT '',
                competition_score REAL,
                competitor_price REAL,
                competition_source TEXT NOT NULL DEFAULT '',
                fragile INTEGER NOT NULL DEFAULT 0,
                return_risk INTEGER NOT NULL DEFAULT 0,
                legal_risk INTEGER NOT NULL DEFAULT 0,
                brand_risk INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                is_favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                currency TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(symbol, asset_type)
            );
            CREATE TABLE IF NOT EXISTS asset_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                price REAL NOT NULL,
                currency TEXT NOT NULL DEFAULT '',
                change_pct REAL,
                volume REAL,
                market_cap REAL,
                volatility_pct REAL,
                avg_volume REAL,
                avg_value REAL,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL DEFAULT '',
                as_of TEXT NOT NULL DEFAULT '',
                fetched_at TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS product_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                sale_price REAL NOT NULL,
                demand_score REAL,
                competition_score REAL,
                competitor_price REAL,
                product_cost REAL NOT NULL DEFAULT 0,
                shipping_cost REAL NOT NULL DEFAULT 0,
                margin_pct REAL,
                observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                target TEXT NOT NULL,
                operator TEXT NOT NULL,
                threshold REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pendiente',
                created_at TEXT NOT NULL,
                triggered_at TEXT,
                last_checked TEXT,
                details TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                currency TEXT NOT NULL,
                initial_cash REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sim_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS portfolio_marks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                cash REAL NOT NULL,
                market_value REAL NOT NULL,
                total_value REAL NOT NULL,
                benchmark_symbol TEXT NOT NULL DEFAULT '',
                benchmark_price REAL,
                valuation_source TEXT NOT NULL DEFAULT 'manual',
                details TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS lesson_progress (
                lesson_id TEXT PRIMARY KEY,
                completed INTEGER NOT NULL DEFAULT 0,
                quiz_score REAL,
                updated_at TEXT NOT NULL
            );
            """
        )


def get_setting(key: str, default: str = "") -> str:
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return str(row["value"]) if row else default


def set_setting(key: str, value: Any) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def get_all_settings() -> dict[str, str]:
    with connect() as con:
        rows = con.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: row["value"] for row in rows}


def save_source_status(source: str, state: str, message: str, succeeded: bool = False) -> None:
    stamp = now_iso()
    with connect() as con:
        con.execute(
            """INSERT INTO source_status(source,state,message,last_attempt,last_success)
               VALUES(?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET
               state=excluded.state,message=excluded.message,last_attempt=excluded.last_attempt,
               last_success=CASE WHEN ? THEN excluded.last_success ELSE source_status.last_success END""",
            (source, state, message[:500], stamp, stamp if succeeded else None, int(succeeded)),
        )


def source_statuses() -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM source_status ORDER BY source").fetchall()]


def add_product(values: dict[str, Any]) -> int:
    fields = [
        "name", "category", "country", "currency", "provider", "provider_url", "source_url",
        "product_cost", "shipping_cost", "ad_cost", "platform_fee_pct", "tax_pct", "refund_pct",
        "sale_price", "launch_budget", "delivery_days", "supplier_quality", "demand_score",
        "demand_source", "demand_updated", "competition_score", "fragile", "brand_risk", "notes",
        "competitor_price", "competition_source", "return_risk", "legal_risk",
    ]
    record = {key: values.get(key) for key in fields}
    record["created_at"] = now_iso()
    record["updated_at"] = record["created_at"]
    with connect() as con:
        cur = con.execute(
            f"INSERT INTO products({','.join(fields)},created_at,updated_at) VALUES({','.join('?' for _ in fields)},?,?)",
            [record[key] for key in fields] + [record["created_at"], record["updated_at"]],
        )
        product_id = int(cur.lastrowid)
        _observe_product(con, product_id, record)
        return product_id


def _observe_product(con: sqlite3.Connection, product_id: int, values: dict[str, Any]) -> None:
    from radar.scoring import product_economics

    economics = product_economics(values)
    con.execute(
        "INSERT INTO product_observations(product_id,sale_price,demand_score,competition_score,competitor_price,product_cost,shipping_cost,margin_pct,observed_at) VALUES(?,?,?,?,?,?,?,?,?)",
        (product_id, float(values.get("sale_price") or 0), values.get("demand_score"), values.get("competition_score"),
         values.get("competitor_price"), float(values.get("product_cost") or 0), float(values.get("shipping_cost") or 0),
         economics["margin_pct"], now_iso()),
    )


def update_product(product_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
    fields = [
        "name", "category", "country", "currency", "provider", "provider_url", "source_url",
        "product_cost", "shipping_cost", "ad_cost", "platform_fee_pct", "tax_pct", "refund_pct",
        "sale_price", "launch_budget", "delivery_days", "supplier_quality", "demand_score",
        "demand_source", "demand_updated", "competition_score", "fragile", "brand_risk", "notes",
        "competitor_price", "competition_source", "return_risk", "legal_risk",
    ]
    with connect() as con:
        old_row = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if old_row is None:
            return None
        old = dict(old_row)
        values = {field: values.get(field) for field in fields}
        assignments = ",".join(f"{field}=?" for field in fields)
        con.execute(f"UPDATE products SET {assignments},updated_at=? WHERE id=?",
                    [values[field] for field in fields] + [now_iso(), product_id])
        _observe_product(con, product_id, values)
        return old


def list_products(favorites_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM products"
    if favorites_only:
        query += " WHERE is_favorite=1"
    query += " ORDER BY created_at DESC"
    with connect() as con:
        return [dict(r) for r in con.execute(query).fetchall()]


def toggle_product_favorite(product_id: int, favorite: bool) -> None:
    with connect() as con:
        con.execute("UPDATE products SET is_favorite=? WHERE id=?", (int(favorite), product_id))


def delete_product(product_id: int) -> None:
    with connect() as con:
        con.execute("DELETE FROM products WHERE id=?", (product_id,))


def product_history(product_id: int) -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(row) for row in con.execute(
            "SELECT * FROM product_observations WHERE product_id=? ORDER BY observed_at,id", (product_id,)
        ).fetchall()]


def add_watch(symbol: str, asset_type: str, name: str, currency: str) -> None:
    with connect() as con:
        con.execute(
            "INSERT OR IGNORE INTO watchlist(symbol,asset_type,name,currency,created_at) VALUES(?,?,?,?,?)",
            (symbol.upper() if asset_type != "Cripto" else symbol.lower(), asset_type, name, currency, now_iso()),
        )


def list_watchlist() -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall()]


def remove_watch(item_id: int) -> None:
    with connect() as con:
        con.execute("DELETE FROM watchlist WHERE id=?", (item_id,))


def save_asset_observation(values: dict[str, Any]) -> None:
    fields = ["symbol", "asset_type", "name", "price", "currency", "change_pct", "volume", "market_cap",
              "volatility_pct", "avg_volume", "avg_value", "source", "source_url", "as_of", "details"]
    with connect() as con:
        con.execute(
            f"INSERT INTO asset_observations({','.join(fields)},fetched_at) VALUES({','.join('?' for _ in fields)},?)",
            [values.get(field, "{}" if field == "details" else "") for field in fields] + [now_iso()],
        )


def latest_asset_observations() -> list[dict[str, Any]]:
    with connect() as con:
        rows = con.execute(
            """SELECT o.* FROM asset_observations o
               INNER JOIN (SELECT symbol,asset_type,MAX(id) AS max_id FROM asset_observations GROUP BY symbol,asset_type) latest
               ON latest.max_id=o.id ORDER BY o.fetched_at DESC"""
        ).fetchall()
        return [dict(row) for row in rows]


def create_alert(kind: str, target: str, operator: str, threshold: float, label: str = "") -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO alerts(kind,target,operator,threshold,label,created_at) VALUES(?,?,?,?,?,?)",
            (kind, target, operator, float(threshold), label, now_iso()),
        )


def list_alerts(active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM alerts"
    if active_only:
        query += " WHERE active=1"
    query += " ORDER BY created_at DESC"
    with connect() as con:
        return [dict(r) for r in con.execute(query).fetchall()]


def update_alert(alert_id: int, **values: Any) -> None:
    allowed = {"active", "status", "triggered_at", "last_checked", "details"}
    values = {k: v for k, v in values.items() if k in allowed}
    if not values:
        return
    assignments = ",".join(f"{k}=?" for k in values)
    with connect() as con:
        con.execute(f"UPDATE alerts SET {assignments} WHERE id=?", [*values.values(), alert_id])


def create_portfolio(name: str, currency: str, initial_cash: float) -> int:
    with connect() as con:
        cur = con.execute(
            "INSERT INTO portfolios(name,currency,initial_cash,created_at) VALUES(?,?,?,?)",
            (name, currency, float(initial_cash), now_iso()),
        )
        return int(cur.lastrowid)


def list_portfolios() -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM portfolios ORDER BY created_at DESC").fetchall()]


def portfolio_trades(portfolio_id: int) -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM sim_trades WHERE portfolio_id=? ORDER BY created_at,id", (portfolio_id,)
        ).fetchall()]


def add_sim_trade(portfolio_id: int, symbol: str, asset_type: str, action: str,
                  quantity: float, price: float, fee: float) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO sim_trades(portfolio_id,symbol,asset_type,action,quantity,price,fee,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (portfolio_id, symbol, asset_type, action, quantity, price, fee, now_iso()),
        )


def add_portfolio_mark(portfolio_id: int, cash: float, market_value: float, total_value: float,
                       benchmark_symbol: str = "", benchmark_price: float | None = None,
                       valuation_source: str = "manual", details: str = "") -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO portfolio_marks(portfolio_id,cash,market_value,total_value,benchmark_symbol,benchmark_price,valuation_source,details,created_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (portfolio_id, cash, market_value, total_value, benchmark_symbol, benchmark_price, valuation_source, details, now_iso()),
        )


def portfolio_history(portfolio_id: int) -> list[dict[str, Any]]:
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM portfolio_marks WHERE portfolio_id=? ORDER BY created_at,id", (portfolio_id,)
        ).fetchall()]


def save_lesson(lesson_id: str, completed: bool, quiz_score: float | None) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO lesson_progress(lesson_id,completed,quiz_score,updated_at) VALUES(?,?,?,?) "
            "ON CONFLICT(lesson_id) DO UPDATE SET completed=excluded.completed,quiz_score=excluded.quiz_score,updated_at=excluded.updated_at",
            (lesson_id, int(completed), quiz_score, now_iso()),
        )


def lessons_progress() -> dict[str, dict[str, Any]]:
    with connect() as con:
        return {r["lesson_id"]: dict(r) for r in con.execute("SELECT * FROM lesson_progress").fetchall()}


def counts() -> dict[str, int]:
    with connect() as con:
        return {
            "products": con.execute("SELECT count(*) FROM products").fetchone()[0],
            "favorites": con.execute("SELECT count(*) FROM products WHERE is_favorite=1").fetchone()[0],
            "watchlist": con.execute("SELECT count(*) FROM watchlist").fetchone()[0],
            "alerts": con.execute("SELECT count(*) FROM alerts WHERE active=1 AND status='pendiente'").fetchone()[0],
            "changes": con.execute("SELECT count(*) FROM alerts WHERE status='activada'").fetchone()[0],
        }


def clear_user_data() -> None:
    with connect() as con:
        con.executescript(
            "DELETE FROM sim_trades; DELETE FROM portfolio_marks; DELETE FROM portfolios; "
            "DELETE FROM product_observations; DELETE FROM products; DELETE FROM watchlist; DELETE FROM alerts; "
            "DELETE FROM asset_observations; DELETE FROM source_status;"
            "DELETE FROM lesson_progress; DELETE FROM settings;"
        )


def export_rows(table: str) -> list[dict[str, Any]]:
    allowed = {"products", "watchlist", "alerts", "sim_trades", "portfolios", "lesson_progress"}
    if table not in allowed:
        raise ValueError("Tabla no exportable")
    with connect() as con:
        return [dict(r) for r in con.execute(f"SELECT * FROM {table}").fetchall()]

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from radar.auth import current_user_id, get_supabase_client


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _query(table: str):
    return get_supabase_client().table(table).select("*").eq("user_id", current_user_id())


def _clean(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: value for key, value in row.items() if key != "user_id"}


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None) or []
    if isinstance(data, dict):
        data = [data]
    return [_clean(row) for row in data]


def _insert(table: str, values: dict[str, Any]) -> dict[str, Any] | None:
    payload = {**values, "user_id": current_user_id()}
    response = get_supabase_client().table(table).insert(payload).select("*").execute()
    return next(iter(_rows(response)), None)


def _upsert(table: str, values: dict[str, Any], conflict: str) -> None:
    payload = {**values, "user_id": current_user_id()}
    get_supabase_client().table(table).upsert(payload, on_conflict=conflict).execute()


def save_source_status(source: str, state: str, message: str, succeeded: bool = False) -> None:
    stamp = now_iso()
    current = next(iter(_rows(_query("source_status").eq("source", source).limit(1).execute())), None)
    _upsert(
        "source_status",
        {
            "source": source,
            "state": state,
            "message": message[:500],
            "last_attempt": stamp,
            "last_success": stamp if succeeded else (current or {}).get("last_success"),
        },
        "user_id,source",
    )


def source_statuses() -> list[dict[str, Any]]:
    return sorted(_rows(_query("source_status").execute()), key=lambda row: row["source"])


def get_setting(key: str, default: str = "") -> str:
    row = next(iter(_rows(_query("settings").eq("key", key).limit(1).execute())), None)
    return str(row["value"]) if row else default


def set_setting(key: str, value: Any) -> None:
    _upsert("settings", {"key": key, "value": str(value)}, "user_id,key")


def get_all_settings() -> dict[str, str]:
    return {row["key"]: row["value"] for row in _rows(_query("settings").execute())}


PRODUCT_FIELDS = [
    "name", "category", "country", "currency", "provider", "provider_url", "source_url",
    "product_cost", "shipping_cost", "ad_cost", "platform_fee_pct", "tax_pct", "refund_pct",
    "sale_price", "launch_budget", "delivery_days", "supplier_quality", "demand_score",
    "demand_source", "demand_updated", "competition_score", "fragile", "brand_risk", "notes",
    "competitor_price", "competition_source", "return_risk", "legal_risk",
]


def _observe_product(product_id: int, values: dict[str, Any]) -> None:
    from radar.scoring import product_economics

    economics = product_economics(values)
    _insert(
        "product_observations",
        {
            "product_id": product_id,
            "sale_price": float(values.get("sale_price") or 0),
            "demand_score": values.get("demand_score"),
            "competition_score": values.get("competition_score"),
            "competitor_price": values.get("competitor_price"),
            "product_cost": float(values.get("product_cost") or 0),
            "shipping_cost": float(values.get("shipping_cost") or 0),
            "margin_pct": economics["margin_pct"],
            "observed_at": now_iso(),
        },
    )


def add_product(values: dict[str, Any]) -> int:
    record = {key: values.get(key) for key in PRODUCT_FIELDS}
    record["created_at"] = now_iso()
    record["updated_at"] = record["created_at"]
    row = _insert("products", record)
    if row is None:
        raise RuntimeError("No se pudo guardar el producto.")
    product_id = int(row["id"])
    _observe_product(product_id, record)
    return product_id


def update_product(product_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
    old = next(iter(_rows(_query("products").eq("id", product_id).limit(1).execute())), None)
    if old is None:
        return None
    record = {key: values.get(key) for key in PRODUCT_FIELDS}
    get_supabase_client().table("products").update({**record, "updated_at": now_iso()}) \
        .eq("user_id", current_user_id()).eq("id", product_id).execute()
    _observe_product(product_id, record)
    return old


def list_products(favorites_only: bool = False) -> list[dict[str, Any]]:
    query = _query("products")
    if favorites_only:
        query = query.eq("is_favorite", 1)
    return sorted(_rows(query.execute()), key=lambda row: row["created_at"], reverse=True)


def toggle_product_favorite(product_id: int, favorite: bool) -> None:
    get_supabase_client().table("products").update({"is_favorite": int(bool(favorite))}) \
        .eq("user_id", current_user_id()).eq("id", product_id).execute()


def delete_product(product_id: int) -> None:
    get_supabase_client().table("products").delete().eq("user_id", current_user_id()).eq("id", product_id).execute()


def product_history(product_id: int) -> list[dict[str, Any]]:
    query = _query("product_observations").eq("product_id", product_id)
    return sorted(_rows(query.execute()), key=lambda row: (row["observed_at"], row["id"]))


def add_watch(symbol: str, asset_type: str, name: str, currency: str) -> None:
    normalized = symbol.upper() if asset_type != "Cripto" else symbol.lower()
    _upsert(
        "watchlist",
        {"symbol": normalized, "asset_type": asset_type, "name": name, "currency": currency, "created_at": now_iso()},
        "user_id,symbol,asset_type",
    )


def list_watchlist() -> list[dict[str, Any]]:
    return sorted(_rows(_query("watchlist").execute()), key=lambda row: row["created_at"], reverse=True)


def remove_watch(item_id: int) -> None:
    get_supabase_client().table("watchlist").delete().eq("user_id", current_user_id()).eq("id", item_id).execute()


def save_asset_observation(values: dict[str, Any]) -> None:
    fields = ["symbol", "asset_type", "name", "price", "currency", "change_pct", "volume", "market_cap",
              "volatility_pct", "avg_volume", "avg_value", "source", "source_url", "as_of", "details"]
    record = {field: values.get(field, "{}" if field == "details" else "") for field in fields}
    record["fetched_at"] = now_iso()
    _insert("asset_observations", record)


def latest_asset_observations() -> list[dict[str, Any]]:
    rows = sorted(_rows(_query("asset_observations").execute()), key=lambda row: row["fetched_at"], reverse=True)
    seen: set[tuple[str, str]] = set()
    latest = []
    for row in rows:
        key = (row["symbol"], row["asset_type"])
        if key not in seen:
            seen.add(key)
            latest.append(row)
    return latest


def create_alert(kind: str, target: str, operator: str, threshold: float, label: str = "") -> None:
    _insert("alerts", {"kind": kind, "target": target, "operator": operator, "threshold": float(threshold),
                        "label": label, "created_at": now_iso()})


def list_alerts(active_only: bool = False) -> list[dict[str, Any]]:
    query = _query("alerts")
    if active_only:
        query = query.eq("active", True)
    return sorted(_rows(query.execute()), key=lambda row: row["created_at"], reverse=True)


def update_alert(alert_id: int, **values: Any) -> None:
    allowed = {key: value for key, value in values.items()
               if key in {"active", "status", "triggered_at", "last_checked", "details"}}
    if allowed:
        get_supabase_client().table("alerts").update(allowed).eq("user_id", current_user_id()) \
            .eq("id", alert_id).execute()


def create_portfolio(name: str, currency: str, initial_cash: float) -> int:
    row = _insert("portfolios", {"name": name, "currency": currency, "initial_cash": float(initial_cash),
                                  "created_at": now_iso()})
    if row is None:
        raise RuntimeError("No se pudo crear la cartera simulada.")
    return int(row["id"])


def list_portfolios() -> list[dict[str, Any]]:
    return sorted(_rows(_query("portfolios").execute()), key=lambda row: row["created_at"], reverse=True)


def portfolio_trades(portfolio_id: int) -> list[dict[str, Any]]:
    return sorted(_rows(_query("sim_trades").eq("portfolio_id", portfolio_id).execute()),
                  key=lambda row: (row["created_at"], row["id"]))


def add_sim_trade(portfolio_id: int, symbol: str, asset_type: str, action: str,
                  quantity: float, price: float, fee: float) -> None:
    _insert("sim_trades", {"portfolio_id": portfolio_id, "symbol": symbol, "asset_type": asset_type,
                            "action": action, "quantity": quantity, "price": price, "fee": fee,
                            "created_at": now_iso()})


def add_portfolio_mark(portfolio_id: int, cash: float, market_value: float, total_value: float,
                       benchmark_symbol: str = "", benchmark_price: float | None = None,
                       valuation_source: str = "manual", details: str = "") -> None:
    _insert("portfolio_marks", {"portfolio_id": portfolio_id, "cash": cash, "market_value": market_value,
                                 "total_value": total_value, "benchmark_symbol": benchmark_symbol,
                                 "benchmark_price": benchmark_price, "valuation_source": valuation_source,
                                 "details": details, "created_at": now_iso()})


def portfolio_history(portfolio_id: int) -> list[dict[str, Any]]:
    return sorted(_rows(_query("portfolio_marks").eq("portfolio_id", portfolio_id).execute()),
                  key=lambda row: (row["created_at"], row["id"]))


def save_lesson(lesson_id: str, completed: bool, quiz_score: float | None) -> None:
    _upsert("lesson_progress", {"lesson_id": lesson_id, "completed": bool(completed),
                                "quiz_score": quiz_score, "updated_at": now_iso()}, "user_id,lesson_id")


def lessons_progress() -> dict[str, dict[str, Any]]:
    return {row["lesson_id"]: row for row in _rows(_query("lesson_progress").execute())}


def image_analysis_usage_24h() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    response = get_supabase_client().table("image_analyses").select("id") \
        .eq("user_id", current_user_id()).gte("created_at", cutoff).execute()
    return len(getattr(response, "data", None) or [])


def reserve_image_analysis(mode: str, file_name: str) -> int:
    row = _insert("image_analyses", {"mode": mode, "file_name": file_name[:255],
                                     "analysis": "", "status": "procesando", "created_at": now_iso()})
    if row is None:
        raise RuntimeError("No se pudo reservar el análisis.")
    return int(row["id"])


def complete_image_analysis(analysis_id: int, analysis: str) -> None:
    get_supabase_client().table("image_analyses").update({"analysis": analysis, "status": "completado"}) \
        .eq("user_id", current_user_id()).eq("id", analysis_id).execute()


def fail_image_analysis(analysis_id: int) -> None:
    get_supabase_client().table("image_analyses").update({"status": "error"}) \
        .eq("user_id", current_user_id()).eq("id", analysis_id).execute()


def image_analyses(limit: int = 20) -> list[dict[str, Any]]:
    rows = _rows(_query("image_analyses").eq("status", "completado").execute())
    return sorted(rows, key=lambda row: row["created_at"], reverse=True)[:limit]


def delete_image_analysis(analysis_id: int) -> None:
    get_supabase_client().table("image_analyses").delete().eq("user_id", current_user_id()) \
        .eq("id", analysis_id).execute()


def counts() -> dict[str, int]:
    products = list_products()
    alerts = list_alerts()
    return {
        "products": len(products),
        "favorites": sum(bool(row.get("is_favorite")) for row in products),
        "watchlist": len(list_watchlist()),
        "alerts": sum(bool(row.get("active")) and row.get("status") == "pendiente" for row in alerts),
        "changes": sum(row.get("status") == "activada" for row in alerts),
    }


def clear_user_data() -> None:
    client = get_supabase_client()
    user_id = current_user_id()
    for table in ("sim_trades", "portfolio_marks", "product_observations", "image_analyses",
                  "lesson_progress", "asset_observations", "watchlist", "alerts", "source_status",
                  "settings", "portfolios", "products"):
        client.table(table).delete().eq("user_id", user_id).execute()


def export_rows(table: str) -> list[dict[str, Any]]:
    allowed = {"products", "watchlist", "alerts", "sim_trades", "portfolios", "lesson_progress"}
    if table not in allowed:
        raise ValueError("Tabla no exportable")
    return _rows(_query(table).execute())

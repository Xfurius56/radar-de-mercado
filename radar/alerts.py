from __future__ import annotations

from typing import Any

from radar.db import list_alerts, now_iso, update_alert
from radar.scoring import product_economics


def _is_met(operator: str, value: float, threshold: float) -> bool:
    if operator == "por encima de":
        return value >= threshold
    if operator == "por debajo de":
        return value <= threshold
    return False


def check_asset_alerts(symbol: str, quote: dict[str, Any]) -> list[str]:
    triggered: list[str] = []
    symbol = symbol.upper()
    for alert in list_alerts(active_only=True):
        if alert["target"].upper() != symbol:
            continue
        value = None
        unit = ""
        if alert["kind"] == "precio":
            value, unit = quote.get("price"), f" {quote.get('currency', '')}"
        elif alert["kind"] == "variacion":
            raw = quote.get("change_pct")
            try:
                value = float(str(raw).replace("%", ""))
            except (TypeError, ValueError):
                value = None
            unit = "%"
        if value is None or not _is_met(alert["operator"], float(value), float(alert["threshold"])):
            update_alert(alert["id"], last_checked=now_iso())
            continue
        details = f"{symbol}: valor observado {float(value):.4g}{unit}; fuente: {quote.get('source')} ({quote.get('as_of') or quote.get('fetched_at')})."
        update_alert(alert["id"], active=0, status="activada", triggered_at=now_iso(),
                     last_checked=now_iso(), details=details)
        triggered.append(details)
    return triggered


def check_news_alerts(symbol: str, articles: list[dict[str, Any]]) -> list[str]:
    triggered: list[str] = []
    haystack = "\n".join(f"{item.get('title', '')} {item.get('summary', '')}" for item in articles).casefold()
    for alert in list_alerts(active_only=True):
        if alert["kind"] != "noticia" or alert["target"].upper() != symbol.upper():
            continue
        keyword = alert.get("label", "").strip()
        if keyword and keyword.casefold() in haystack:
            details = f"Se encontró «{keyword}» en noticias consultadas para {symbol}. Revisa los enlaces y sus fechas de publicación."
            update_alert(alert["id"], active=0, status="activada", triggered_at=now_iso(),
                         last_checked=now_iso(), details=details)
            triggered.append(details)
        else:
            update_alert(alert["id"], last_checked=now_iso())
    return triggered


def check_product_update(product_id: int, old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    triggered: list[str] = []
    old_econ = product_economics(old)
    new_econ = product_economics(new)
    old_price = float(old.get("sale_price") or 0)
    new_price = float(new.get("sale_price") or 0)
    price_change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0.0
    old_demand = old.get("demand_score")
    new_demand = new.get("demand_score")
    demand_delta = (float(new_demand) - float(old_demand)) if old_demand not in (None, "") and new_demand not in (None, "") else None
    for alert in list_alerts(active_only=True):
        if alert["target"] != str(product_id):
            continue
        met = False
        detail = ""
        if alert["kind"] == "margen_producto" and new_econ["margin_pct"] is not None:
            met = _is_met(alert["operator"], float(new_econ["margin_pct"]), float(alert["threshold"]))
            detail = f"Margen estimado de {new.get('name', 'producto')}: {new_econ['margin_pct']:.1f}% frente al umbral {alert['threshold']:.1f}%."
        elif alert["kind"] == "precio_producto":
            met = abs(price_change_pct) >= float(alert["threshold"])
            detail = f"Precio de venta de {new.get('name', 'producto')}: variación observada {price_change_pct:+.1f}% ({old_price:g} → {new_price:g} {new.get('currency', '')})."
        elif alert["kind"] == "demanda_producto" and demand_delta is not None:
            met = abs(demand_delta) >= float(alert["threshold"])
            detail = f"Señal de demanda de {new.get('name', 'producto')}: cambio de {demand_delta:+.1f} puntos introducido manualmente."
        if met:
            detail += " La revisión se activó al guardar datos actualizados; no hay vigilancia continua."
            update_alert(alert["id"], active=0, status="activada", triggered_at=now_iso(),
                         last_checked=now_iso(), details=detail)
            triggered.append(detail)
        else:
            update_alert(alert["id"], last_checked=now_iso())
    return triggered

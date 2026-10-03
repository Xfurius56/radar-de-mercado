from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from radar.config import env_value

BASE_URL = "https://www.alphavantage.co/query"


class SourceError(RuntimeError):
    pass


def _request(params: dict[str, str]) -> dict[str, Any]:
    api_key = env_value("ALPHAVANTAGE_API_KEY")
    if not api_key:
        raise SourceError("Falta ALPHAVANTAGE_API_KEY en los secretos de Streamlit o en las variables de entorno.")
    query = {**params, "apikey": api_key}
    try:
        response = requests.get(BASE_URL, params=query, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "desconocido"
        raise SourceError(f"Alpha Vantage respondió con estado HTTP {status}; revisa acceso y límites de la cuenta.") from exc
    except requests.RequestException as exc:
        raise SourceError(f"No se pudo contactar con Alpha Vantage ({type(exc).__name__}).") from exc
    except ValueError as exc:
        raise SourceError("Alpha Vantage devolvió una respuesta que no es JSON válido.") from exc
    if not isinstance(payload, dict):
        raise SourceError("Formato de respuesta no reconocido de Alpha Vantage.")
    for key in ("Error Message", "Note", "Information"):
        if key in payload:
            safe_message = str(payload[key]).replace(api_key, "[credencial oculta]")
            raise SourceError(safe_message)
    return payload


def quote(symbol: str) -> dict[str, Any]:
    payload = _request({"function": "GLOBAL_QUOTE", "symbol": symbol.strip().upper()})
    quote_data = payload.get("Global Quote", {})
    if not quote_data or not quote_data.get("05. price"):
        raise SourceError(f"No hay cotización disponible para {symbol.upper()}.")
    return {
        "symbol": quote_data.get("01. symbol", symbol.upper()),
        "price": float(quote_data["05. price"]),
        "change": float(quote_data.get("09. change", 0) or 0),
        "change_pct": str(quote_data.get("10. change percent", "")).replace("%", ""),
        "volume": int(float(quote_data.get("06. volume", 0) or 0)),
        "as_of": quote_data.get("07. latest trading day", ""),
        # GLOBAL_QUOTE no incluye divisa; no se infiere desde el símbolo.
        "currency": "",
        "source": "Alpha Vantage · GLOBAL_QUOTE",
        "source_url": "https://www.alphavantage.co/documentation/#global_quote",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def daily_history(symbol: str, compact: bool = True) -> list[dict[str, Any]]:
    params = {"function": "TIME_SERIES_DAILY", "symbol": symbol.strip().upper(), "outputsize": "compact" if compact else "full"}
    payload = _request(params)
    series = payload.get("Time Series (Daily)")
    if not isinstance(series, dict) or not series:
        raise SourceError(f"No hay histórico diario disponible para {symbol.upper()}.")
    rows = []
    for date, values in series.items():
        rows.append({
            "date": date,
            "open": float(values["1. open"]),
            "high": float(values["2. high"]),
            "low": float(values["3. low"]),
            "close": float(values["4. close"]),
            "volume": int(float(values.get("5. volume", 0) or 0)),
        })
    return sorted(rows, key=lambda row: row["date"])


def overview(symbol: str) -> dict[str, Any]:
    payload = _request({"function": "OVERVIEW", "symbol": symbol.strip().upper()})
    if not payload.get("Symbol"):
        raise SourceError(f"No hay ficha fundamental disponible para {symbol.upper()}.")
    fields = {
        "Name": "Nombre", "Exchange": "Mercado", "Currency": "Moneda reportada",
        "MarketCapitalization": "Capitalización bursátil", "PERatio": "PER",
        "PriceToBookRatio": "Precio/valor contable", "DividendYield": "Rentabilidad por dividendo",
        "52WeekHigh": "Máximo 52 semanas", "52WeekLow": "Mínimo 52 semanas",
        "Description": "Descripción",
    }
    return {label: payload.get(key) for key, label in fields.items() if payload.get(key) not in (None, "", "None")}


def news(ticker: str, limit: int = 10) -> list[dict[str, Any]]:
    payload = _request({"function": "NEWS_SENTIMENT", "tickers": ticker.strip().upper(), "sort": "LATEST", "limit": str(min(limit, 50))})
    rows = []
    for item in payload.get("feed", []):
        rows.append({
            "title": item.get("title", "Sin título"),
            "summary": item.get("summary", ""),
            "url": item.get("url", ""),
            "source": item.get("source", "Alpha Vantage"),
            "published": item.get("time_published", ""),
            "sentiment": item.get("overall_sentiment_label", "No disponible"),
        })
    return rows

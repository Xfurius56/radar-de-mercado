from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from radar.config import env_value
from radar.sources.alpha_vantage import SourceError

BASE_URL = "https://api.coingecko.com/api/v3"


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    api_key = env_value("COINGECKO_API_KEY")
    if not api_key:
        raise SourceError("Falta COINGECKO_API_KEY en el archivo .env.")
    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            params=params or {},
            headers={"x-cg-demo-api-key": api_key},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "desconocido"
        raise SourceError(f"CoinGecko respondió con estado HTTP {status}; revisa el acceso y el límite de la cuenta.") from exc
    except requests.RequestException as exc:
        raise SourceError(f"No se pudo contactar con CoinGecko ({type(exc).__name__}).") from exc
    except ValueError as exc:
        raise SourceError("CoinGecko devolvió una respuesta JSON no válida.") from exc


def market(coin_id: str, currency: str = "eur") -> dict[str, Any]:
    rows = _get("/coins/markets", {
        "vs_currency": currency.lower(), "ids": coin_id.lower().strip(),
        "order": "market_cap_desc", "per_page": 1, "page": 1, "sparkline": "false",
    })
    if not rows:
        raise SourceError(f"No se encontró el identificador de CoinGecko «{coin_id}».")
    row = rows[0]
    return {
        "symbol": row.get("symbol", "").upper(),
        "name": row.get("name", coin_id),
        "price": row.get("current_price"),
        "change_pct": row.get("price_change_percentage_24h"),
        "volume": row.get("total_volume"),
        "market_cap": row.get("market_cap"),
        "as_of": row.get("last_updated", ""),
        "currency": currency.upper(),
        "source": "CoinGecko · coins/markets",
        "source_url": f"https://www.coingecko.com/en/coins/{coin_id.lower()}",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def history(coin_id: str, currency: str = "eur", days: int = 365) -> list[dict[str, Any]]:
    payload = _get(f"/coins/{coin_id.lower().strip()}/market_chart", {
        "vs_currency": currency.lower(), "days": int(days),
    })
    prices = payload.get("prices", [])
    if not prices:
        raise SourceError(f"CoinGecko no tiene histórico para {coin_id}.")
    return [
        {"date": datetime.fromtimestamp(point[0] / 1000, timezone.utc).date().isoformat(), "close": float(point[1])}
        for point in prices
    ]

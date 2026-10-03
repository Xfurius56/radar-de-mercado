from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "radar.db"
load_dotenv(ROOT / ".env")


def env_value(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def source_keys() -> dict[str, bool]:
    return {
        "Alpha Vantage": bool(env_value("ALPHAVANTAGE_API_KEY")),
        "CoinGecko": bool(env_value("COINGECKO_API_KEY")),
        "OpenAI": bool(env_value("OPENAI_API_KEY")),
    }


def source_info() -> list[dict[str, str | bool]]:
    keys = source_keys()
    return [
        {
            "name": "Alpha Vantage",
            "configured": keys["Alpha Vantage"],
            "use": "Cotizaciones diarias, históricos, fundamentos y noticias financieras.",
            "url": "https://www.alphavantage.co/documentation/",
        },
        {
            "name": "CoinGecko",
            "configured": keys["CoinGecko"],
            "use": "Precio, volumen, capitalización e histórico de criptoactivos.",
            "url": "https://docs.coingecko.com/",
        },
        {
            "name": "OpenAI API",
            "configured": keys["OpenAI"],
            "use": "Asistente de explicación contextual basado en los datos visibles en la app.",
            "url": "https://platform.openai.com/docs/quickstart",
        },
        {
            "name": "Investigación de productos",
            "configured": True,
            "use": "Datos introducidos por ti o importados desde un CSV; no hay catálogo de proveedor conectado.",
            "url": "",
        },
    ]

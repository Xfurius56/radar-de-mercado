from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def env_value(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        value = str(__import__("streamlit").secrets.get(name, "")).strip()
    except Exception:
        value = ""
    return value or default


def source_keys() -> dict[str, bool]:
    return {
        "Alpha Vantage": bool(env_value("ALPHAVANTAGE_API_KEY")),
        "CoinGecko": bool(env_value("COINGECKO_API_KEY")),
        "OpenAI": bool(env_value("OPENAI_API_KEY")),
        "Supabase": bool(env_value("SUPABASE_URL") and env_value("SUPABASE_ANON_KEY")),
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
            "use": "Asistente contextual y análisis educativo de imágenes; la búsqueda web es opcional.",
            "url": "https://platform.openai.com/docs/quickstart",
        },
        {
            "name": "Supabase Auth + PostgreSQL",
            "configured": keys["Supabase"],
            "use": "Inicio de sesión y almacenamiento persistente con aislamiento de filas por usuario (RLS).",
            "url": "https://supabase.com/docs/guides/database/postgres/row-level-security",
        },
        {
            "name": "Investigación de productos",
            "configured": True,
            "use": "Datos introducidos por ti o importados desde un CSV; no hay catálogo de proveedor conectado.",
            "url": "",
        },
    ]

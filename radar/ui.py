from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from radar.db import save_source_status
from radar.sources.alpha_vantage import SourceError


def apply_style() -> None:
    st.markdown(
        """<style>
        .block-container{padding-top:1.5rem;padding-bottom:2rem;max-width:1250px}
        [data-testid="stMetric"]{background:#f5f8fc;border:1px solid #e3eaf3;padding:14px 16px;border-radius:12px}
        div[data-testid="stExpander"]{border:1px solid #e3eaf3;border-radius:10px}
        .source-note{font-size:.88rem;color:#526276}
        @media(max-width:640px){.block-container{padding-left:1rem;padding-right:1rem}}
        </style>""",
        unsafe_allow_html=True,
    )


def money(value: Any, currency: str = "EUR", decimals: int = 2) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):,.{decimals}f} {currency.upper()}"
    except (TypeError, ValueError):
        return "—"


def percent(value: Any, decimals: int = 1) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{float(value):+.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def date_label(value: str | None) -> str:
    if not value:
        return "sin actualizar"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    except ValueError:
        return value


def call_source(source: str, function, *args, **kwargs):
    try:
        result = function(*args, **kwargs)
    except SourceError as exc:
        save_source_status(source, "limitada", str(exc))
        return None, str(exc)
    except Exception as exc:
        safe_error = f"Error inesperado ({type(exc).__name__})."
        save_source_status(source, "error", safe_error)
        return None, f"Error al procesar la respuesta de {source}: {safe_error}"
    save_source_status(source, "conectada", "Última consulta correcta.", succeeded=True)
    return result, None


def show_external_error(error: str, feature: str) -> None:
    st.warning(f"{feature} está limitado ahora. {error} No se mostrarán datos sustitutos como si fueran reales.")


def source_link(label: str, url: str) -> None:
    if url:
        st.markdown(f"[Fuente: {label}]({url})")
    else:
        st.caption(f"Fuente: {label}")

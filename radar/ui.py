from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

from radar.db import save_source_status
from radar.sources.alpha_vantage import SourceError


def apply_style() -> None:
    st.markdown(
        """<style>
        :root{--radar-night:#000f22;--radar-navy:#1b3554;--radar-blue:#3f6593;--radar-sky:#80aad3;--radar-ice:#c0e6fd;--radar-charcoal:#1e2023;--radar-slate:#47484c}
        .stApp{background:radial-gradient(ellipse at 90% 0%,rgba(63,101,147,.25),transparent 36%),linear-gradient(145deg,#000f22 0%,#101b2b 56%,#1e2023 100%);color:var(--radar-ice)}
        [data-testid="stHeader"]{background:rgba(0,15,34,.68)}
        .block-container{padding-top:2rem;padding-bottom:3rem;max-width:1450px}
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#1e2023 0%,#151a22 52%,#000f22 100%);border-right:1px solid rgba(192,230,253,.12)}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#b9c6d6}
        [data-testid="stSidebar"] [data-testid="stRadio"] label{padding:.45rem .65rem;border-radius:10px;transition:background .18s ease,color .18s ease}
        [data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(128,170,211,.13);color:var(--radar-ice)}
        h1,h2,h3{color:#edf7ff;letter-spacing:-.035em}
        h1{font-weight:720}
        [data-testid="stMetric"]{background:linear-gradient(145deg,rgba(27,53,84,.88),rgba(30,32,35,.92));border:1px solid rgba(128,170,211,.28);padding:17px 18px;border-radius:16px;box-shadow:0 12px 34px rgba(0,0,0,.16);transition:transform .18s ease,border-color .18s ease}
        [data-testid="stMetric"]:hover{transform:translateY(-2px);border-color:rgba(192,230,253,.55)}
        [data-testid="stMetricLabel"] p{color:#c1d6e8}
        [data-testid="stMetricValue"]{color:#f4fbff}
        [data-testid="stMetricDelta"]{font-size:.86rem}
        div[data-testid="stExpander"],div[data-testid="stForm"],div[data-testid="stDataFrame"]{border:1px solid rgba(128,170,211,.2);border-radius:14px;background:rgba(17,31,48,.58)}
        div[data-testid="stTabs"] button{color:#a9bfd5;transition:color .16s ease,background .16s ease}
        div[data-testid="stTabs"] button[aria-selected="true"]{color:var(--radar-ice);border-bottom-color:var(--radar-sky)}
        div[data-testid="stButton"]>button,div[data-testid="stFormSubmitButton"]>button{border:1px solid rgba(128,170,211,.58);border-radius:11px;background:linear-gradient(135deg,#3f6593,#1b3554);color:#f1f9ff;transition:transform .16s ease,filter .16s ease,box-shadow .16s ease}
        div[data-testid="stButton"]>button:hover,div[data-testid="stFormSubmitButton"]>button:hover{transform:translateY(-1px);filter:brightness(1.13);box-shadow:0 8px 22px rgba(0,0,0,.24);border-color:#c0e6fd}
        div[data-testid="stTextInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stTextArea"] textarea,div[data-testid="stSelectbox"] [data-baseweb="select"]>div{background:rgba(7,19,34,.8);border-color:rgba(128,170,211,.3);color:#e6f5ff;border-radius:10px}
        label, [data-testid="stCaptionContainer"]{color:#b9cadb}
        a{color:#a8d8ff!important}
        .radar-hero{position:relative;overflow:hidden;margin:.25rem 0 1.4rem;padding:1.35rem 1.55rem;border:1px solid rgba(128,170,211,.28);border-radius:22px;background:linear-gradient(112deg,rgba(27,53,84,.9),rgba(30,32,35,.86) 66%,rgba(71,72,76,.56));box-shadow:0 20px 60px rgba(0,0,0,.2)}
        .radar-hero:after{content:"";position:absolute;right:-7rem;top:-10rem;width:24rem;height:24rem;border-radius:50%;background:radial-gradient(circle,rgba(128,170,211,.19),transparent 68%);pointer-events:none}
        .radar-kicker{text-transform:uppercase;letter-spacing:.16em;font-size:.72rem;font-weight:700;color:#9ecdf2;margin-bottom:.55rem}
        .radar-hero h1{font-size:clamp(2rem,4vw,3.25rem);margin:0 0 .45rem;color:#f5fbff}
        .radar-hero p{max-width:850px;margin:0;color:#cfdeeb;font-size:1.02rem;line-height:1.6}
        .radar-note{padding:.8rem 1rem;border-left:3px solid var(--radar-sky);border-radius:0 10px 10px 0;background:rgba(27,53,84,.42);color:#d3e6f5}
        .source-note{font-size:.88rem;color:#abc0d4}
        @media(max-width:640px){.block-container{padding:1rem .9rem 2rem}.radar-hero{padding:1.1rem;border-radius:16px}}
        </style>""",
        unsafe_allow_html=True,
    )


def page_header(title: str, description: str, eyebrow: str = "RADAR DE MERCADO") -> None:
    """Render a compact editorial header with the app's navy/charcoal visual system."""
    st.markdown(
        f'<section class="radar-hero"><div class="radar-kicker">{eyebrow}</div>'
        f'<h1>{title}</h1><p>{description}</p></section>',
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

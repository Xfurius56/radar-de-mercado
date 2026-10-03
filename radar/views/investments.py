from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd
import streamlit as st

from radar.alerts import check_asset_alerts, check_news_alerts
from radar.db import (add_watch, get_all_settings, get_setting, latest_asset_observations,
                      list_watchlist, remove_watch, save_asset_observation, set_setting)
from radar.sources import alpha_vantage, coingecko
from radar.ui import call_source, money, percent, show_external_error

HORIZONS = ["Menos de 1 año", "1–3 años", "3–7 años", "Más de 7 años"]
GOALS = ["Aprender y simular", "Crecimiento del capital", "Ingresos periódicos", "Preservar capital"]
RISK_LEVELS = ["Bajo", "Medio", "Alto"]
CLASSES = ["Acciones", "ETF", "Criptomonedas", "Bonos"]


def _historical_stats(rows: list[dict[str, Any]], asset_type: str) -> dict[str, Any]:
    frame = pd.DataFrame(rows).sort_values("date")
    closes = pd.to_numeric(frame["close"], errors="coerce").dropna()
    returns = closes.pct_change().dropna()
    annual_factor = 365 if asset_type == "Cripto" else 252
    volatility = float(returns.std() * math.sqrt(annual_factor) * 100) if len(returns) > 1 else None
    drawdown = float((closes / closes.cummax() - 1).min() * 100) if len(closes) > 1 else None
    pct_total = float((closes.iloc[-1] / closes.iloc[0] - 1) * 100) if len(closes) > 1 and closes.iloc[0] else None
    avg_volume = None
    avg_value = None
    if "volume" in frame.columns:
        volume = pd.to_numeric(frame["volume"], errors="coerce").dropna()
        if not volume.empty:
            avg_volume = float(volume.mean())
            common = frame.dropna(subset=["close", "volume"])
            if not common.empty:
                avg_value = float((pd.to_numeric(common["close"]) * pd.to_numeric(common["volume"])).mean())
    return {"volatility_pct": volatility, "max_drawdown_pct": drawdown, "period_return_pct": pct_total,
            "avg_volume": avg_volume, "avg_value": avg_value, "period_start": frame["date"].iloc[0],
            "period_end": frame["date"].iloc[-1], "count": len(frame), "frame": frame}


def _save_profile() -> None:
    settings = get_all_settings()
    classes = settings.get("investor_classes", "").split(",")
    with st.form("investor_profile"):
        st.markdown("Antes de ordenar candidatos, indica tu contexto. Solo sirve para orientar la investigación educativa; no genera una recomendación financiera personalizada.")
        c1, c2 = st.columns(2)
        country = c1.text_input("País", value=settings.get("investor_country", get_setting("country", "España")))
        horizon = c2.selectbox("Horizonte temporal", HORIZONS, index=HORIZONS.index(settings.get("investor_horizon", HORIZONS[1])) if settings.get("investor_horizon", HORIZONS[1]) in HORIZONS else 1)
        c1, c2 = st.columns(2)
        goal = c1.selectbox("Objetivo de aprendizaje/investigación", GOALS, index=GOALS.index(settings.get("investor_goal", GOALS[0])) if settings.get("investor_goal", GOALS[0]) in GOALS else 0)
        risk = c2.selectbox("Riesgo que aceptarías estudiar", RISK_LEVELS, index=RISK_LEVELS.index(settings.get("investor_risk", "Medio")) if settings.get("investor_risk", "Medio") in RISK_LEVELS else 1)
        selected_classes = st.multiselect("Clases de activos que te interesan", CLASSES, default=[item for item in classes if item in CLASSES])
        saved = st.form_submit_button("Guardar perfil de investigación", type="primary")
    if saved:
        for key, value in (("investor_country", country.strip()), ("investor_horizon", horizon),
                           ("investor_goal", goal), ("investor_risk", risk),
                           ("investor_classes", ",".join(selected_classes))):
            set_setting(key, value)
        st.session_state["investor_profile_complete"] = bool(country.strip() and selected_classes)
        st.success("Perfil guardado en tu cuenta. Puedes editarlo o borrarlo en Configuración.")
        st.rerun()


def _analyze(symbol: str, asset_type: str, currency: str, include_fundamentals: bool,
             include_news: bool) -> None:
    if asset_type == "Criptomonedas":
        quote, error = call_source("CoinGecko", coingecko.market, symbol, currency.lower())
        if error:
            show_external_error(error, "La consulta de criptoactivos")
            return
        history, hist_error = call_source("CoinGecko", coingecko.history, symbol, currency.lower(), 365)
        source = quote["source"]
        fundamental = None
        news_items: list[dict[str, Any]] = []
    else:
        av_symbol = symbol.strip().upper()
        quote, error = call_source("Alpha Vantage", alpha_vantage.quote, av_symbol)
        if error:
            show_external_error(error, "La cotización")
            quote = None
        history, hist_error = call_source("Alpha Vantage", alpha_vantage.daily_history, av_symbol, True)
        if quote is None and history:
            last = history[-1]
            quote = {"symbol": av_symbol, "price": last["close"], "change": None, "change_pct": None,
                     "volume": last.get("volume"), "as_of": last["date"], "currency": "",
                     "source": "Alpha Vantage · cierre diario histórico", "source_url": "https://www.alphavantage.co/documentation/",
                     "fetched_at": last["date"]}
            st.info("La cotización no respondió; se muestra el último cierre diario del histórico, identificado como tal.")
        if quote is None:
            if hist_error:
                show_external_error(hist_error, "El histórico")
            return
        fundamental = None
        news_items = []
        if include_fundamentals:
            fundamental, fundamental_error = call_source("Alpha Vantage", alpha_vantage.overview, av_symbol)
            if fundamental_error:
                st.caption(f"Fundamentales no disponibles: {fundamental_error}")
            elif fundamental and fundamental.get("Moneda reportada"):
                quote["currency"] = fundamental["Moneda reportada"]
        if include_news:
            news_items, news_error = call_source("Alpha Vantage", alpha_vantage.news, av_symbol, 10)
            if news_error:
                st.caption(f"Noticias no disponibles: {news_error}")

    if not history:
        if hist_error:
            st.caption(f"Histórico no disponible: {hist_error}")
        stats = {"volatility_pct": None, "max_drawdown_pct": None, "period_return_pct": None,
                 "avg_volume": None, "avg_value": None, "period_start": "", "period_end": "", "count": 0}
        frame = None
    else:
        stats = _historical_stats(history, "Cripto" if asset_type == "Criptomonedas" else asset_type)
        frame = stats.pop("frame")
    change_pct = quote.get("change_pct")
    try:
        change_value = float(str(change_pct).replace("%", "")) if change_pct is not None else None
    except (TypeError, ValueError):
        change_value = None
    quote["change_pct"] = change_value
    name = quote.get("name") or symbol.upper()
    result = {"symbol": symbol, "asset_type": asset_type, "quote": quote, "stats": stats,
              "history": history or [], "fundamental": fundamental, "news": news_items,
              "analyzed_at": quote.get("fetched_at", "")}
    recent = st.session_state.setdefault("market_results", [])
    st.session_state["market_results"] = [r for r in recent if not (r["symbol"].casefold() == symbol.casefold() and r["asset_type"] == asset_type)] + [result]
    watch_type = "Cripto" if asset_type == "Criptomonedas" else ("ETF" if asset_type == "ETF" else "Acción")
    add_watch(symbol, watch_type, name, quote.get("currency", ""))
    if stats.get("volatility_pct") is not None:
        save_asset_observation({
            "symbol": symbol, "asset_type": watch_type, "name": name, "price": quote["price"],
            "currency": quote.get("currency", currency.upper()), "change_pct": change_value,
            "volume": quote.get("volume"), "market_cap": quote.get("market_cap"),
            "volatility_pct": stats.get("volatility_pct"), "avg_volume": stats.get("avg_volume"),
            "avg_value": stats.get("avg_value"), "source": quote["source"],
            "source_url": quote["source_url"], "as_of": quote.get("as_of", ""),
            "details": json.dumps({"period_start": stats.get("period_start"), "period_end": stats.get("period_end"),
                                   "max_drawdown_pct": stats.get("max_drawdown_pct"), "period_return_pct": stats.get("period_return_pct")}),
        })
    fired = check_asset_alerts(symbol, quote)
    for detail in fired:
        st.warning("Alerta activada: " + detail)
    if news_items:
        for detail in check_news_alerts(symbol, news_items):
            st.warning("Alerta de noticias: " + detail)
    st.success(f"Consulta guardada en la lista de seguimiento: {name} ({symbol}).")


def render() -> None:
    st.title("Analizador de inversiones")
    st.write("Investiga activos con datos disponibles. La herramienta no ejecuta operaciones ni calcula una cartera adecuada para ti.")
    _save_profile()
    settings = get_all_settings()
    ready = bool(settings.get("investor_country", "").strip() and settings.get("investor_classes", "").strip())
    if not ready:
        st.info("Completa y guarda el perfil anterior para desbloquear el buscador de candidatos.")
        return
    classes = [value for value in settings.get("investor_classes", "").split(",") if value in CLASSES]
    st.caption(f"Contexto guardado: {settings.get('investor_country')} · {settings.get('investor_horizon')} · {settings.get('investor_goal')} · riesgo declarado: {settings.get('investor_risk')} · clases: {', '.join(classes)}. Se usa para contextualizar la investigación, no como recomendación.")
    if "Bonos" in classes:
        st.info("Bonos: esta versión no consulta precios ni fichas de bonos. Usa una fuente oficial del emisor o intermediario; la app no inventa una cotización.")
    available_classes = [item for item in classes if item != "Bonos"]
    if not available_classes:
        st.info("No hay una clase de activo seleccionada con integración de datos en esta versión.")
        return

    with st.form("asset_search"):
        selected_type = st.selectbox("Clase", available_classes)
        symbol_label = "ID de CoinGecko (por ejemplo: bitcoin)" if selected_type == "Criptomonedas" else "Símbolo bursátil (por ejemplo: IBM o SPY)"
        symbol = st.text_input(symbol_label).strip()
        supported_currencies = ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"]
        preferred_currency = get_setting("currency", "EUR")
        currency = st.selectbox("Moneda de cotización cripto", supported_currencies, index=supported_currencies.index(preferred_currency) if preferred_currency in supported_currencies else 0)
        c1, c2 = st.columns(2)
        include_fundamentals = c1.checkbox("Consultar fundamentales (acciones/ETF; consume una consulta adicional)", value=False, disabled=selected_type == "Criptomonedas")
        include_news = c2.checkbox("Consultar noticias (consume una consulta adicional)", value=False, disabled=selected_type == "Criptomonedas")
        submit = st.form_submit_button("Consultar datos actuales disponibles", type="primary")
    if submit:
        if not symbol:
            st.error("Escribe un símbolo o ID válido.")
        else:
            _analyze(symbol, selected_type, currency, include_fundamentals, include_news)

    results = st.session_state.get("market_results", [])
    for result in reversed(results):
        quote, stats = result["quote"], result["stats"]
        with st.container(border=True):
            st.subheader(f"{quote.get('name') or result['symbol']} · {result['symbol']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precio de la fuente", money(quote.get("price"), quote.get("currency") or "divisa no indicada"), percent(quote.get("change_pct")))
            c2.metric("Volatilidad histórica anualizada", percent(stats.get("volatility_pct")))
            c3.metric("Variación del periodo analizado", percent(stats.get("period_return_pct")))
            c4.metric("Retroceso máximo del periodo", percent(stats.get("max_drawdown_pct")))
            if stats.get("avg_volume") is not None:
                st.write(f"Volumen diario medio aproximado: {stats['avg_volume']:,.0f} unidades · valor negociado medio aproximado: {money(stats.get('avg_value'), quote.get('currency', ''))}.")
            elif quote.get("volume") is not None:
                st.write(f"Volumen 24 h informado por la fuente: {money(quote.get('volume'), quote.get('currency') or 'divisa no indicada')} · capitalización: {money(quote.get('market_cap'), quote.get('currency') or 'divisa no indicada')}.")
            st.caption(f"Fuente: {quote.get('source')} · fecha de la cotización: {quote.get('as_of') or 'no indicada'} · consultado: {quote.get('fetched_at', '')}")
            st.markdown(f"[Abrir fuente]({quote.get('source_url', '')})")
            st.caption(f"Histórico analizado: {stats.get('period_start') or 'sin datos'} a {stats.get('period_end') or 'sin datos'} · {stats.get('count', 0)} observaciones. La volatilidad usa desviación estándar de variaciones diarias anualizada; el volumen es una aproximación, no una medida completa de liquidez.")
            st.warning("Comisiones, diferencial compra/venta, fiscalidad y costes del intermediario dependen del instrumento y del país; no están incluidos salvo que se indiquen expresamente.")
            if result.get("fundamental"):
                with st.expander("Datos fundamentales disponibles"):
                    for label, value in result["fundamental"].items():
                        st.markdown(f"**{label}:** {value}")
                    st.caption("Fuente Alpha Vantage Overview. La cobertura y la fecha del proveedor pueden variar; las métricas no son una valoración completa.")
            if result.get("news"):
                with st.expander("Noticias consultadas"):
                    for article in result["news"]:
                        st.markdown(f"**[{article['title']}]({article['url']})** · {article['source']} · {article['published']} · sentimiento etiquetado: {article['sentiment']}")
                        st.caption(article.get("summary", ""))
                    st.caption("Las etiquetas de sentimiento del proveedor no verifican la noticia ni predicen el precio.")
            st.markdown("**Factores para investigar**")
            favorable = []
            adverse = []
            daily_change = quote.get("change_pct")
            if daily_change is not None and daily_change > 0:
                favorable.append(f"La fuente reporta una variación positiva de {daily_change:.2f}% en su periodo más reciente publicado.")
            elif daily_change is not None and daily_change < 0:
                adverse.append(f"La fuente reporta una variación negativa de {daily_change:.2f}% en su periodo más reciente publicado.")
            period_return = stats.get("period_return_pct")
            if period_return is not None and period_return > 0:
                favorable.append(f"El precio subió {period_return:.2f}% durante la ventana histórica mostrada ({stats['period_start']} a {stats['period_end']}).")
            elif period_return is not None and period_return < 0:
                adverse.append(f"El precio bajó {abs(period_return):.2f}% durante esa ventana histórica.")
            if stats.get("volatility_pct") is not None:
                adverse.append(f"La volatilidad histórica anualizada fue {stats['volatility_pct']:.1f}%; resume dispersión pasada y puede cambiar.")
            if stats.get("max_drawdown_pct") is not None and stats["max_drawdown_pct"] < 0:
                adverse.append(f"El mayor retroceso observado en la ventana fue {stats['max_drawdown_pct']:.1f}% desde un máximo previo.")
            if not quote.get("currency"):
                adverse.append("La cotización no declaró su divisa; evita comparar o sumar ese importe con otras monedas.")
            if not result.get("fundamental") and result["asset_type"] != "Criptomonedas":
                adverse.append("No se consultaron datos fundamentales en esta ficha.")
            if not result.get("news"):
                adverse.append("No se consultaron noticias para esta ficha.")
            st.markdown("**Datos que podrían apoyar una hipótesis (solo descriptivos):** " + (" ".join(favorable) if favorable else "no hay una señal favorable documentada en los datos mostrados."))
            st.markdown("**Riesgos o aspectos adversos observados:** " + (" ".join(adverse) if adverse else "no se identificó un factor adverso concreto en los datos disponibles."))
            st.caption("Estas pistas describen el periodo publicado. No explican por sí solas las causas del movimiento ni anticipan el siguiente.")

    st.subheader("Lista de seguimiento y comparación")
    watchlist = list_watchlist()
    observations = latest_asset_observations()
    if not watchlist:
        st.info("Aún no hay activos guardados. Consultar un activo lo añade a la lista.")
    else:
        by_key = {(x["symbol"].casefold(), x["asset_type"]): x for x in observations}
        joined = []
        for item in watchlist:
            latest = by_key.get((item["symbol"].casefold(), item["asset_type"]), {})
            joined.append({**item, **latest})
        c1, c2 = st.columns(2)
        criterion = c1.selectbox("Ordenar por criterio visible", ["Volatilidad histórica", "Variación de la fuente", "Volumen medio", "Capitalización"])
        descending = c2.checkbox("Orden descendente", value=False, help="Aplica al criterio elegido. La posición de una fila no implica una recomendación.")
        mapping = {"Volatilidad histórica": "volatility_pct", "Variación de la fuente": "change_pct",
                   "Volumen medio": "avg_volume", "Capitalización": "market_cap"}
        field = mapping[criterion]
        present = [row for row in joined if row.get(field) is not None]
        missing = [row for row in joined if row.get(field) is None]
        present.sort(key=lambda row: row.get(field), reverse=descending)
        joined = present + missing
        frame = pd.DataFrame([{
            "Activo": row.get("name") or row["symbol"], "Símbolo / ID": row["symbol"], "Clase": row["asset_type"],
            "Precio": money(row.get("price"), row.get("currency") or "divisa no indicada"), "Variación proveedor": percent(row.get("change_pct")),
            "Volatilidad histórica": percent(row.get("volatility_pct")), "Volumen medio": row.get("avg_volume") or "—",
            "Capitalización": money(row.get("market_cap"), row.get("currency") or "divisa no indicada") if row.get("market_cap") else "—", "Fuente": row.get("source") or "sin consulta",
            "Última consulta": row.get("fetched_at") or "sin datos",
        } for row in joined])
        st.dataframe(frame, use_container_width=True, hide_index=True)
        remove_id = st.selectbox("Quitar activo de seguimiento", [item["id"] for item in watchlist], format_func=lambda value: next(f"{x['name'] or x['symbol']} ({x['asset_type']})" for x in watchlist if x["id"] == value), key="remove_watch_select")
        if st.button("Quitar de la lista", key="remove_watch_button"):
            remove_watch(remove_id)
            st.rerun()
        st.caption("Cada fila usa la última observación consultada manualmente. Los candidatos sin observación muestran datos vacíos; ordenar por un criterio no evalúa idoneidad ni rentabilidad futura.")

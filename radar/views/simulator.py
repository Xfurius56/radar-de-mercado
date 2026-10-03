from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from radar.db import (add_portfolio_mark, add_sim_trade, create_portfolio, get_setting,
                      list_portfolios, portfolio_history, portfolio_trades)
from radar.scoring import backtest_sma, holdings_from_trades
from radar.sources import alpha_vantage, coingecko
from radar.ui import call_source, money, percent, show_external_error


def _latest_prices(trades: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    prices: dict[tuple[str, str], float] = {}
    for trade in trades:
        prices[(trade["symbol"], trade["asset_type"])] = float(trade["price"])
    return prices


def _portfolio_marks_ui(portfolio: dict[str, Any], trades: list[dict[str, Any]], cash: float,
                        holdings: dict[tuple[str, str], float]) -> None:
    currency = portfolio["currency"]
    st.markdown("**Registrar valoración de la cartera virtual**")
    st.caption("Los precios se expresan en la moneda de la cartera. Puedes consultarlos desde una fuente conectada o introducir marcas manuales. No se realizan compras o ventas reales.")
    if holdings:
        if st.button("Consultar fuentes conectadas y guardar valoración", key=f"live_mark_{portfolio['id']}"):
            prices: dict[tuple[str, str], float] = {}
            errors: list[str] = []
            sources: list[str] = []
            for (symbol, asset_type), qty in holdings.items():
                if asset_type == "Cripto":
                    quote, error = call_source("CoinGecko", coingecko.market, symbol, currency.lower())
                else:
                    quote, error = call_source("Alpha Vantage", alpha_vantage.quote, symbol)
                    if not error and quote and not quote.get("currency"):
                        overview, overview_error = call_source("Alpha Vantage", alpha_vantage.overview, symbol)
                        if overview_error or not overview or not overview.get("Moneda reportada"):
                            error = f"Alpha Vantage no devolvió divisa para {symbol}; usa una valoración manual en {currency}."
                        else:
                            quote["currency"] = overview["Moneda reportada"]
                if error:
                    errors.append(f"{symbol}: {error}")
                elif quote.get("currency", "").upper() != currency.upper():
                    errors.append(f"{symbol}: la fuente informa {quote.get('currency')}; la cartera está en {currency} y no hay conversión automática.")
                else:
                    prices[(symbol, asset_type)] = float(quote["price"])
                    sources.append(f"{symbol}: {quote['source']} · {quote.get('as_of') or quote.get('fetched_at')}")
            if errors:
                for error in errors:
                    st.warning(error)
                st.info("No se guardó una marca parcial. Revisa las divisas o registra precios manuales convertidos por ti.")
            else:
                market_value = sum(qty * prices[key] for key, qty in holdings.items())
                benchmark_symbol, benchmark_price = "", None
                if currency.upper() == "USD":
                    benchmark, benchmark_error = call_source("Alpha Vantage", alpha_vantage.quote, "SPY")
                    if not benchmark_error and benchmark:
                        benchmark_overview, overview_error = call_source("Alpha Vantage", alpha_vantage.overview, "SPY")
                        if not overview_error and benchmark_overview and benchmark_overview.get("Moneda reportada") == currency.upper():
                            benchmark_symbol, benchmark_price = "SPY", float(benchmark["price"])
                add_portfolio_mark(portfolio["id"], cash, market_value, cash + market_value,
                                   benchmark_symbol, benchmark_price, "fuentes conectadas", "\n".join(sources))
                st.success(f"Valoración virtual guardada: {money(cash + market_value, currency)}.")
                for source in sources:
                    st.caption(source)
                if not benchmark_price:
                    st.caption("No se guardó una referencia SPY; la fuente puede estar limitada o la cartera usa otra divisa.")
        with st.form(f"manual_mark_{portfolio['id']}"):
            st.write("O introduce manualmente precios actuales convertidos a la moneda de la cartera:")
            manual_prices = {}
            for idx, (key, qty) in enumerate(holdings.items()):
                symbol, asset_type = key
                manual_prices[key] = st.number_input(
                    f"{symbol} ({qty:g} unidades · {asset_type}) — precio de valoración en {currency}",
                    min_value=0.0, value=0.0, step=1.0, key=f"manual_price_{portfolio['id']}_{idx}",
                )
            benchmark_symbol = st.text_input("Referencia opcional (p. ej., SPY)", value="", key=f"manual_bench_symbol_{portfolio['id']}").strip().upper()
            benchmark_price = st.number_input("Precio de la referencia en la moneda de la cartera (opcional)", min_value=0.0, value=0.0, step=1.0, key=f"manual_bench_price_{portfolio['id']}")
            manual_submit = st.form_submit_button("Guardar valoración manual")
        if manual_submit:
            if any(value <= 0 for value in manual_prices.values()):
                st.error("Introduce un precio mayor que cero para cada posición.")
            else:
                market_value = sum(qty * manual_prices[key] for key, qty in holdings.items())
                add_portfolio_mark(portfolio["id"], cash, market_value, cash + market_value,
                                   benchmark_symbol if benchmark_price > 0 else "",
                                   benchmark_price if benchmark_price > 0 else None,
                                   "entrada manual del usuario", "Precios introducidos por el usuario; no verificados ni convertidos por la app.")
                st.success("Valoración manual guardada. La app no verificó esos precios ni la conversión de divisa.")
                st.rerun()
    else:
        st.info("Registra una compra simulada para poder calcular una valoración de mercado.")


def _render_portfolios() -> None:
    with st.expander("Crear una cartera de prueba"):
        with st.form("new_virtual_portfolio"):
            name = st.text_input("Nombre de la cartera", value="Cartera educativa")
            currency = st.selectbox("Moneda de la cartera", ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"], index=["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"].index(get_setting("currency", "EUR")) if get_setting("currency", "EUR") in ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"] else 0)
            initial_cash = st.number_input("Saldo inicial virtual", min_value=1.0, value=10000.0, step=500.0)
            submitted = st.form_submit_button("Crear cartera", type="primary")
        if submitted:
            if not name.strip():
                st.error("Escribe un nombre para la cartera.")
            else:
                create_portfolio(name.strip(), currency, initial_cash)
                st.success("Cartera virtual creada.")
                st.rerun()

    portfolios = list_portfolios()
    if not portfolios:
        st.info("Crea una cartera para registrar operaciones ficticias.")
        return
    portfolio_id = st.selectbox("Cartera", [p["id"] for p in portfolios], format_func=lambda pid: next(f"{p['name']} · {p['initial_cash']:,.2f} {p['currency']}" for p in portfolios if p["id"] == pid))
    portfolio = next(p for p in portfolios if p["id"] == portfolio_id)
    trades = portfolio_trades(portfolio_id)
    cash, holdings = holdings_from_trades(portfolio["initial_cash"], trades)
    latest = portfolio_history(portfolio_id)
    c1, c2, c3 = st.columns(3)
    c1.metric("Efectivo virtual actual", money(cash, portfolio["currency"]))
    c2.metric("Posiciones", len(holdings))
    c3.metric("Último valor marcado", money(latest[-1]["total_value"], portfolio["currency"]) if latest else "Sin valoración")

    with st.expander("Registrar operación simulada"):
        with st.form(f"new_trade_{portfolio_id}"):
            c1, c2, c3 = st.columns(3)
            action = c1.selectbox("Acción", ["Compra", "Venta"])
            asset_type = c2.selectbox("Tipo", ["Acción", "ETF", "Cripto"])
            symbol_raw = c3.text_input("Símbolo / ID CoinGecko").strip()
            c1, c2, c3 = st.columns(3)
            quantity = c1.number_input("Cantidad", min_value=0.0, value=0.0, step=0.1, format="%.8f")
            price = c2.number_input(f"Precio simulado por unidad ({portfolio['currency']})", min_value=0.0, value=0.0, step=1.0)
            fee = c3.number_input(f"Comisión simulada ({portfolio['currency']})", min_value=0.0, value=0.0, step=0.5)
            submitted = st.form_submit_button("Registrar operación ficticia")
        if submitted:
            symbol = symbol_raw.lower() if asset_type == "Cripto" else symbol_raw.upper()
            if not symbol or quantity <= 0 or price <= 0:
                st.error("Introduce símbolo, cantidad y precio mayores que cero.")
            elif action == "Compra" and quantity * price + fee > cash:
                st.error(f"Saldo virtual insuficiente. Saldo actual: {money(cash, portfolio['currency'])}.")
            elif action == "Venta" and quantity > holdings.get((symbol, asset_type), 0):
                st.error("La cantidad supera la posición virtual disponible.")
            else:
                add_sim_trade(portfolio_id, symbol, asset_type, action, quantity, price, fee)
                st.success("Operación ficticia guardada. No se envió ninguna orden a un intermediario.")
                st.rerun()

    if trades:
        st.markdown("**Posiciones virtuales**")
        trade_frame = pd.DataFrame(trades)
        st.dataframe(trade_frame[["created_at", "action", "symbol", "asset_type", "quantity", "price", "fee"]].rename(columns={
            "created_at": "Fecha", "action": "Operación", "symbol": "Símbolo", "asset_type": "Tipo",
            "quantity": "Cantidad", "price": "Precio simulado", "fee": "Comisión simulada",
        }), use_container_width=True, hide_index=True)
    if holdings:
        st.dataframe(pd.DataFrame([{"Símbolo": key[0], "Tipo": key[1], "Cantidad": qty} for key, qty in holdings.items()]), use_container_width=True, hide_index=True)
        _portfolio_marks_ui(portfolio, trades, cash, holdings)
    elif latest:
        _portfolio_marks_ui(portfolio, trades, cash, holdings)

    history = portfolio_history(portfolio_id)
    if history:
        st.subheader("Evolución de las valoraciones guardadas")
        frame = pd.DataFrame(history)
        frame["fecha"] = pd.to_datetime(frame["created_at"], utc=True)
        frame["rendimiento_cartera_pct"] = (frame["total_value"] / float(portfolio["initial_cash"]) - 1) * 100
        chart = frame.set_index("fecha")[["rendimiento_cartera_pct"]].rename(columns={"rendimiento_cartera_pct": "Cartera virtual (%)"})
        first_benchmark = next((row["benchmark_price"] for row in history if row.get("benchmark_price") and row.get("benchmark_symbol")), None)
        if first_benchmark:
            benchmark_rows = [row for row in history if row.get("benchmark_price") and row.get("benchmark_symbol") == next(r["benchmark_symbol"] for r in history if r.get("benchmark_price"))]
            bench_symbol = next(r["benchmark_symbol"] for r in history if r.get("benchmark_price"))
            bench_frame = pd.DataFrame(benchmark_rows)
            bench_frame["fecha"] = pd.to_datetime(bench_frame["created_at"], utc=True)
            bench_frame["referencia_pct"] = (bench_frame["benchmark_price"] / float(first_benchmark) - 1) * 100
            chart = chart.join(bench_frame.set_index("fecha")[["referencia_pct"]].rename(columns={"referencia_pct": f"Referencia {bench_symbol} (%)"}), how="left")
        st.line_chart(chart, use_container_width=True)
        st.caption("Las marcas conectadas reflejan el instante de consulta; las marcas manuales no se verifican. La comparación con un índice solo se ofrece si has guardado sus precios y no ajusta por efectivo, divisas, dividendos ni riesgo.")
        st.dataframe(frame[["created_at", "cash", "market_value", "total_value", "benchmark_symbol", "valuation_source"]].rename(columns={
            "created_at": "Fecha", "cash": "Efectivo", "market_value": "Valor de posiciones", "total_value": "Total",
            "benchmark_symbol": "Referencia", "valuation_source": "Origen de marca",
        }), use_container_width=True, hide_index=True)


def _render_backtest() -> None:
    st.write("Estrategia didáctica de cruce de medias móviles. Requiere datos históricos; puedes consultarlos en Alpha Vantage o cargar un CSV propio con columnas date y close.")
    with st.form("backtest_av"):
        symbol = st.text_input("Símbolo bursátil para histórico", value="SPY").strip().upper()
        fetch = st.form_submit_button("Cargar hasta 100 sesiones desde Alpha Vantage")
    if fetch:
        rows, error = call_source("Alpha Vantage", alpha_vantage.daily_history, symbol, True)
        if error:
            show_external_error(error, "El análisis histórico")
        else:
            st.session_state["backtest_rows"] = rows
            st.session_state["backtest_source"] = f"Alpha Vantage · {symbol} · TIME_SERIES_DAILY"
            st.session_state["backtest_symbol"] = symbol
            st.success(f"Se cargaron {len(rows)} cierres diarios para {symbol}.")

    upload = st.file_uploader("O cargar histórico CSV propio", type=["csv"], key="historical_csv")
    if upload and st.button("Usar histórico CSV", key="use_historical_csv"):
        try:
            frame = pd.read_csv(upload)
            if not {"date", "close"}.issubset(frame.columns):
                raise ValueError("El archivo debe incluir las columnas date y close.")
            frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.strftime("%Y-%m-%d")
            frame["close"] = pd.to_numeric(frame["close"], errors="raise")
            rows = frame[["date", "close"]].to_dict("records")
            st.session_state["backtest_rows"] = rows
            st.session_state["backtest_source"] = "CSV aportado por el usuario"
            st.session_state["backtest_symbol"] = "Activo del CSV"
            st.success(f"Histórico cargado: {len(rows)} observaciones. Verifica tú la fuente y el formato.")
        except Exception as exc:
            st.error(f"CSV no utilizable: {exc}")

    rows = st.session_state.get("backtest_rows")
    if not rows:
        st.info("No hay un histórico cargado. Sin una fuente configurada, el simulador no inventa precios.")
        return
    st.caption(f"Datos actuales del simulador: {st.session_state.get('backtest_symbol')} · origen: {st.session_state.get('backtest_source')}.")
    with st.form("backtest_parameters"):
        c1, c2, c3 = st.columns(3)
        fast = c1.number_input("Media rápida (sesiones)", min_value=2, max_value=90, value=20)
        slow = c2.number_input("Media lenta (sesiones)", min_value=3, max_value=99, value=50)
        fee_pct = c3.number_input("Coste por operación (%)", min_value=0.0, max_value=5.0, value=0.1, step=0.05)
        run = st.form_submit_button("Calcular escenario histórico", type="primary")
    if run:
        if fast >= slow:
            st.error("La media rápida debe ser menor que la lenta.")
        else:
            try:
                st.session_state["backtest_result"] = backtest_sma(rows, int(fast), int(slow), float(fee_pct))
            except Exception as exc:
                st.error(f"No se pudo calcular: {exc}")
    result = st.session_state.get("backtest_result")
    if result:
        c1, c2, c3 = st.columns(3)
        c1.metric("Estrategia, periodo analizado", percent(result["strategy_return_pct"]))
        c2.metric("Comprar y mantener, mismo periodo", percent(result["buy_hold_return_pct"]))
        c3.metric("Volatilidad anualizada de estrategia", percent(result["annualized_volatility_pct"]))
        frame = pd.DataFrame(result["rows"]).set_index("date")
        st.line_chart(frame[["estrategia", "comprar_y_mantener"]].rename(columns={
            "estrategia": "Regla de medias", "comprar_y_mantener": "Comprar y mantener",
        }), use_container_width=True)
        st.caption(f"Periodo: {result['period_start']} a {result['period_end']} · {result['observations']} observaciones · medias {result['fast']}/{result['slow']} · coste por operación: {result['fee_pct']}%. Fuente: {st.session_state.get('backtest_source')}.")
        st.warning("Escenario histórico hipotético: la señal conocida al cierre de una sesión se aplica desde la sesión siguiente. Posición larga o efectivo; no incluye dividendos, deslizamiento, impacto de mercado, impuestos ni ejecución parcial. Una estrategia que funcionó en este tramo no demuestra que vaya a funcionar en el futuro.")


def render() -> None:
    st.title("Simulador y análisis histórico")
    st.write("Usa saldo ficticio. No se conecta a un bróker y no envía órdenes reales.")
    tabs = st.tabs(["Cartera virtual", "Estrategia histórica"])
    with tabs[0]:
        _render_portfolios()
    with tabs[1]:
        _render_backtest()

from __future__ import annotations

import pandas as pd
import streamlit as st

from radar.alerts import check_asset_alerts, check_news_alerts
from radar.db import (create_alert, get_setting, list_alerts, list_products, list_watchlist,
                      now_iso, update_alert)
from radar.sources import alpha_vantage, coingecko
from radar.ui import call_source, date_label

ASSET_ALERTS = ["Precio de activo", "Variación porcentual", "Palabra clave en noticias"]
PRODUCT_ALERTS = ["Margen estimado bajo", "Cambio de precio de producto", "Cambio de señal de demanda"]


def _review_watchlist() -> None:
    watch = list_watchlist()
    if not watch:
        st.info("No hay activos guardados para revisar.")
        return
    triggered_count = 0
    for item in watch:
        alerts = [a for a in list_alerts(active_only=True) if a["target"].upper() == item["symbol"].upper()]
        has_price = any(a["kind"] in {"precio", "variacion"} for a in alerts)
        has_news = any(a["kind"] == "noticia" for a in alerts)
        label = f"{item['symbol']} ({item['asset_type']})"
        if has_price:
            if item["asset_type"] == "Cripto":
                quote, error = call_source("CoinGecko", coingecko.market, item["symbol"], get_setting("currency", "EUR").lower())
            else:
                quote, error = call_source("Alpha Vantage", alpha_vantage.quote, item["symbol"])
            if error:
                st.warning(f"No se pudo revisar {label}: {error}")
            else:
                fired = check_asset_alerts(item["symbol"], quote)
                for detail in fired:
                    st.warning("Alerta activada: " + detail)
                    triggered_count += 1
                st.caption(f"{label}: condición comprobada con {quote['source']} · {quote.get('as_of') or quote.get('fetched_at')}.")
        if has_news:
            if item["asset_type"] == "Cripto":
                st.warning(f"No se revisaron noticias de {label}: este conector no ofrece noticias cripto para CoinGecko.")
                continue
            news, error = call_source("Alpha Vantage", alpha_vantage.news, item["symbol"], 10)
            if error:
                st.warning(f"Noticias de {label} no disponibles: {error}")
            else:
                fired = check_news_alerts(item["symbol"], news)
                for detail in fired:
                    st.warning("Alerta activada: " + detail)
                    triggered_count += 1
                st.caption(f"{label}: se revisaron {len(news)} noticias devueltas por la fuente.")
    st.success(f"Revisión manual terminada. Alertas activadas en esta revisión: {triggered_count}.")


def render() -> None:
    st.title("Alertas y seguimiento")
    st.write("Las alertas se revisan al consultar datos o guardar una ficha actualizada. No hay vigilancia en tiempo real ni ejecución automática.")
    tab_asset, tab_product, tab_list = st.tabs(["Activos", "Productos", "Alertas guardadas"])

    with tab_asset:
        st.caption("Las alertas de noticias usan el ticker de Alpha Vantage; CoinGecko no se consulta para noticias en esta versión.")
        st.caption("El umbral de precio debe estar en la divisa informada por la fuente; CoinGecko usa la moneda que elijas en Configuración.")
        with st.form("asset_alert_create"):
            kind_label = st.selectbox("Condición", ASSET_ALERTS)
            target = st.text_input("Símbolo o ID de CoinGecko").strip()
            c1, c2 = st.columns(2)
            operator = c1.selectbox("Condición", ["por encima de", "por debajo de"], disabled=kind_label == "Palabra clave en noticias")
            if kind_label == "Precio de activo":
                threshold = c2.number_input("Precio umbral", min_value=0.00000001, value=100.0, step=1.0)
                label = st.text_input("Nombre corto de la alerta", value=target)
                kind = "precio"
            elif kind_label == "Variación porcentual":
                threshold = c2.number_input("Variación umbral (%)", min_value=-100.0, max_value=1000.0, value=5.0, step=0.5)
                label = st.text_input("Nombre corto de la alerta", value=target)
                kind = "variacion"
            else:
                threshold = c2.number_input("Campo auxiliar", min_value=0.0, value=0.0, disabled=True)
                label = st.text_input("Palabra o frase que buscar en título/resumen")
                kind = "noticia"
            submitted = st.form_submit_button("Crear alerta", type="primary")
        if submitted:
            if not target:
                st.error("Indica el símbolo o ID del activo.")
            elif kind == "noticia" and not label.strip():
                st.error("Indica una palabra o frase para buscar.")
            else:
                create_alert(kind, target.upper(), operator, threshold, label.strip())
                st.success("Alerta guardada. Se comprobará en la próxima consulta manual pertinente.")
        if st.button("Revisar alertas de activos en seguimiento", type="secondary"):
            _review_watchlist()

    with tab_product:
        products = list_products()
        if not products:
            st.info("Añade una ficha en Buscador de productos para poder crear alertas.")
        else:
            with st.form("product_alert_create"):
                product_id = st.selectbox("Producto", [p["id"] for p in products], format_func=lambda pid: next(p["name"] for p in products if p["id"] == pid))
                alert_label = st.selectbox("Condición", PRODUCT_ALERTS)
                if alert_label == "Margen estimado bajo":
                    threshold = st.number_input("Umbral de margen (%)", min_value=-100.0, max_value=100.0, value=10.0, step=1.0)
                    operator = "por debajo de"
                    kind = "margen_producto"
                elif alert_label == "Cambio de precio de producto":
                    threshold = st.number_input("Variación absoluta del precio (%)", min_value=0.1, max_value=100.0, value=10.0, step=1.0)
                    operator = "cambio absoluto"
                    kind = "precio_producto"
                else:
                    threshold = st.number_input("Cambio mínimo de señal (puntos 0–100)", min_value=1.0, max_value=100.0, value=10.0, step=1.0)
                    operator = "cambio absoluto"
                    kind = "demanda_producto"
                submitted = st.form_submit_button("Crear alerta de producto", type="primary")
            if submitted:
                create_alert(kind, str(product_id), operator, threshold, alert_label)
                st.success("Alerta guardada. Se comprobará cuando guardes nuevos datos para esta ficha.")

    with tab_list:
        alerts = list_alerts()
        if not alerts:
            st.info("No hay alertas guardadas.")
        else:
            rows = [{"ID": a["id"], "Tipo": a["kind"], "Objetivo": a["label"] or a["target"],
                     "Regla": f"{a['operator']} {a['threshold']}", "Estado": a["status"],
                     "Activa": "Sí" if a["active"] else "No", "Creada": date_label(a["created_at"]),
                     "Activada": date_label(a.get("triggered_at")), "Detalle": a.get("details", "")} for a in alerts]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            selected_id = st.selectbox("Gestionar alerta", [a["id"] for a in alerts], format_func=lambda value: next(f"{a['id']} · {a['label'] or a['target']}" for a in alerts if a["id"] == value))
            chosen = next(a for a in alerts if a["id"] == selected_id)
            c1, c2 = st.columns(2)
            if c1.button("Desactivar alerta" if chosen["active"] else "Reactivar alerta"):
                update_alert(selected_id, active=not bool(chosen["active"]), status="pendiente" if not chosen["active"] else chosen["status"], triggered_at=None if not chosen["active"] else chosen.get("triggered_at"))
                st.rerun()
            if chosen["details"]:
                st.info(chosen["details"])
            st.caption("Las alertas activadas son de un solo disparo; puedes reactivarlas. No se envían notificaciones fuera de esta app.")

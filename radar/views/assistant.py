from __future__ import annotations

import json
import streamlit as st

from radar.assistant import answer, is_configured
from radar.db import get_setting, list_products
from radar.scoring import product_economics


def _context() -> str:
    parts = []
    for result in st.session_state.get("market_results", [])[-4:]:
        quote, stats = result.get("quote", {}), result.get("stats", {})
        parts.append(
            f"Activo: {result.get('symbol')} ({result.get('asset_type')}). Precio: {quote.get('price')} {quote.get('currency')}; "
            f"fecha informada: {quote.get('as_of')}; consultado: {quote.get('fetched_at')}; fuente: {quote.get('source')}; enlace: {quote.get('source_url')}. "
            f"Volatilidad histórica anualizada: {stats.get('volatility_pct')}; variación del periodo observado: {stats.get('period_return_pct')}; "
            f"periodo: {stats.get('period_start')} a {stats.get('period_end')}."
        )
        for article in result.get("news", [])[:5]:
            parts.append(f"Noticia: {article.get('title')} | fecha publicada: {article.get('published')} | fuente: {article.get('source')} | enlace: {article.get('url')}.")
    for product in list_products(favorites_only=True)[:5]:
        econ = product_economics(product)
        parts.append(
            f"Producto (entrada manual/importada): {product['name']}; costes declarados: producto {product['product_cost']} + envío {product['shipping_cost']} "
            f"+ publicidad por pedido {product['ad_cost']}; precio {product['sale_price']} {product['currency']}; margen aproximado {econ['margin_pct']}; "
            f"señal demanda {product['demand_score']} de fuente {product['demand_source']} a fecha {product['demand_updated']}; "
            f"fuente declarada {product['source_url']}; ficha actualizada {product['updated_at']}."
        )
    profile = {
        "país": get_setting("investor_country"), "horizonte": get_setting("investor_horizon"),
        "objetivo": get_setting("investor_goal"), "riesgo declarado": get_setting("investor_risk"),
    }
    if any(profile.values()):
        parts.append("Contexto educativo introducido por el usuario (no es una recomendación): " + json.dumps(profile, ensure_ascii=False))
    return "\n".join(parts)


def render() -> None:
    st.title("Asistente educativo")
    connected = is_configured()
    if connected:
        st.caption("Modo conectado: OpenAI API. El modelo recibe tu pregunta y el resumen de datos que aparece en esta pantalla; sus respuestas pueden contener errores. Verifica las fuentes enlazadas.")
    else:
        st.warning("Modo de demostración: no hay clave de OpenAI configurada. Las respuestas educativas son predefinidas; no consultan Internet ni representan datos actuales.")
    st.caption("No compartas datos personales o credenciales. Las preguntas y el contexto se envían a la API solo cuando está configurada; la solicitud pide no guardar la respuesta en estado de la API. El historial visible se conserva solo en esta sesión.")
    context = _context()
    if context:
        with st.expander("Datos disponibles para contextualizar respuestas"):
            st.write(context)
    else:
        st.info("No hay resultados de mercado ni productos favoritos en el contexto actual. El asistente responderá conceptos generales y señalará esa limitación.")
    if st.button("Borrar conversación de esta sesión", key="clear_chat"):
        st.session_state["chat_history"] = []
        st.rerun()
    history = st.session_state.setdefault("chat_history", [])
    for item in history:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item.get("mode"):
                st.caption(item["mode"])
    prompt = st.chat_input("Pregunta sobre conceptos o resultados disponibles")
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                response, mode = answer(prompt, context, history[:-1])
                st.markdown(response)
                st.caption(mode)
                history.append({"role": "assistant", "content": response, "mode": mode})
            except Exception as exc:
                st.error(f"No se pudo consultar la API de IA ({type(exc).__name__}). Revisa su estado y configuración en la documentación oficial.")
                st.caption("No se generó una respuesta local fingiendo una conexión.")

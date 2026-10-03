from __future__ import annotations

import streamlit as st

from radar.auth import clear_user_workspace
from radar.config import source_info
from radar.db import clear_user_data, get_all_settings, set_setting, source_statuses
from radar.ui import date_label

COUNTRIES = ["España", "México", "Argentina", "Chile", "Colombia", "Estados Unidos", "Otro"]
CURRENCIES = ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"]


def render() -> None:
    st.title("Configuración y fuentes")
    settings = get_all_settings()
    current_country = settings.get("country", "España")
    current_currency = settings.get("currency", "EUR")
    current_language = settings.get("source_language", "es")
    current_frequency = settings.get("refresh_frequency", "Manual")

    with st.form("preferences"):
        left, right = st.columns(2)
        country = left.selectbox("País objetivo", COUNTRIES, index=COUNTRIES.index(current_country) if current_country in COUNTRIES else 0)
        currency = right.selectbox("Moneda preferida", CURRENCIES, index=CURRENCIES.index(current_currency) if current_currency in CURRENCIES else 0)
        language = left.selectbox("Idioma preferido para las fuentes", ["es", "en", "pt", "fr", "de"], index=["es", "en", "pt", "fr", "de"].index(current_language) if current_language in ["es", "en", "pt", "fr", "de"] else 0)
        frequency = right.selectbox("Frecuencia objetivo de revisión", ["Manual", "Diaria", "Semanal"], index=["Manual", "Diaria", "Semanal"].index(current_frequency) if current_frequency in ["Manual", "Diaria", "Semanal"] else 0)
        saved = st.form_submit_button("Guardar preferencias", type="primary")
    if saved:
        for key, value in (("country", country), ("currency", currency), ("source_language", language), ("refresh_frequency", frequency)):
            set_setting(key, value)
        st.success("Preferencias guardadas en tu cuenta.")
    st.caption("La frecuencia expresa cuándo quieres revisar. Streamlit no ejecuta tareas en segundo plano ni consulta el mercado automáticamente. La moneda preferida no convierte importes entre divisas; cada cifra conserva la moneda que declara la fuente.")
    st.caption("El idioma se guarda como preferencia. El conector de Alpha Vantage usado aquí no filtra los resultados de noticias por idioma.")

    st.subheader("Conexiones")
    statuses = {item["source"]: item for item in source_statuses()}
    for source in source_info():
        status = statuses.get(source["name"], {})
        configured = bool(source["configured"])
        with st.container(border=True):
            access_label = "fichas manuales de tu cuenta" if source["name"] == "Investigación de productos" else ("credencial detectada" if configured else "sin credencial")
            st.markdown(f"**{source['name']}** · {access_label}")
            st.write(source["use"])
            shown_state = status.get("state", "sin consultar") if configured or source["name"] == "Investigación de productos" else "requiere configuración en este entorno"
            st.caption(f"Estado: {shown_state} · Último intento: {date_label(status.get('last_attempt'))} · Última respuesta correcta: {date_label(status.get('last_success'))}")
            if status.get("message"):
                st.caption(status["message"])
            if source["url"]:
                st.markdown(f"[Documentación oficial]({source['url']})")

    st.subheader("Configurar claves")
    st.write("En Streamlit Cloud, administra las claves desde **Manage app → Settings → Secrets**. No pegues secretos en una ficha, chat o repositorio público. Usa la clave publicable de Supabase junto con RLS; nunca pongas la clave `service_role` aquí.")
    st.code('SUPABASE_URL = "https://tu-proyecto.supabase.co"\nSUPABASE_ANON_KEY = "tu-clave-publicable"\nOPENAI_API_KEY = "tu-clave-de-openai"\nOPENAI_MODEL = "gpt-5"\nOPENAI_VISION_MODEL = "gpt-5"', language="toml")
    st.caption("Las cotizaciones de Alpha Vantage y CoinGecko siguen siendo opcionales y se configuran en los secretos con sus nombres terminados en _API_KEY.")

    st.subheader("Eliminar tus datos")
    st.write("Esto elimina las fichas, listas, alertas, carteras simuladas, progreso, preferencias y resultados de análisis asociados a tu cuenta.")
    confirmed = st.checkbox("Entiendo que se eliminarán los datos guardados en mi cuenta", key="confirm_delete_local")
    if st.button("Eliminar mis datos", type="secondary", disabled=not confirmed):
        clear_user_data()
        clear_user_workspace()
        st.session_state.pop("confirm_delete_local", None)
        st.success("Se han eliminado los datos de tu cuenta.")
        st.rerun()

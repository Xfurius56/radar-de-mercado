from __future__ import annotations

import streamlit as st

from radar.config import ROOT, source_info
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
        st.success("Preferencias guardadas en la base de datos local.")
    st.caption("La frecuencia expresa cuándo quieres revisar. Streamlit no ejecuta tareas en segundo plano ni consulta el mercado automáticamente. La moneda preferida no convierte importes entre divisas; cada cifra conserva la moneda que declara la fuente.")
    st.caption("El idioma se guarda como preferencia. El conector de Alpha Vantage usado aquí no filtra los resultados de noticias por idioma.")

    st.subheader("Conexiones")
    statuses = {item["source"]: item for item in source_statuses()}
    for source in source_info():
        status = statuses.get(source["name"], {})
        configured = bool(source["configured"])
        with st.container(border=True):
            access_label = "datos locales/manuales" if source["name"] == "Investigación de productos" else ("credencial detectada" if configured else "sin credencial")
            st.markdown(f"**{source['name']}** · {access_label}")
            st.write(source["use"])
            shown_state = status.get("state", "sin consultar") if configured or source["name"] == "Investigación de productos" else "requiere configuración en este entorno"
            st.caption(f"Estado: {shown_state} · Último intento: {date_label(status.get('last_attempt'))} · Última respuesta correcta: {date_label(status.get('last_success'))}")
            if status.get("message"):
                st.caption(status["message"])
            if source["url"]:
                st.markdown(f"[Documentación oficial]({source['url']})")

    st.subheader("Configurar claves")
    st.write("Crea un archivo **.env** en la carpeta del proyecto a partir de **.env.example** y añade tus claves allí. No las pegues en esta página: la app comprueba si existen, pero no las muestra ni las almacena en SQLite.")
    st.code("ALPHAVANTAGE_API_KEY=tu_clave\nCOINGECKO_API_KEY=tu_clave_demo\nOPENAI_API_KEY=tu_clave\nOPENAI_MODEL=gpt-5", language="text")
    st.caption(f"Los datos locales se guardan en {ROOT / 'data' / 'radar.db'}; las claves permanecen en variables de entorno o en el archivo local .env.")

    st.subheader("Borrar datos locales")
    st.write("Esto borra productos, listas, alertas, carteras simuladas, operaciones, progreso de lecciones y preferencias guardadas en SQLite. No elimina el archivo .env.")
    confirmed = st.checkbox("Entiendo que se eliminarán los datos guardados de la app", key="confirm_delete_local")
    if st.button("Borrar datos locales", type="secondary", disabled=not confirmed):
        clear_user_data()
        st.session_state.clear()
        st.success("Se han borrado los datos locales de la app.")
        st.rerun()

from __future__ import annotations

import streamlit as st

from radar.auth import logout, require_authenticated_user
from radar.ui import apply_style
from radar.views import alerts, assistant, home, image_analysis, investments, learning, products, settings, simulator

st.set_page_config(
    page_title="Radar de Mercado",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_style()

if not require_authenticated_user():
    st.stop()

with st.sidebar:
    st.title("🧭 Radar")
    st.caption("Espacio privado · investigación educativa")
    st.caption(st.session_state.get("_radar_user_email", "Cuenta autenticada"))
    page = st.radio(
        "Navegación",
        ["Inicio", "Productos", "Inversiones", "Simulador", "Alertas", "Analizar imágenes", "Aprender", "Asistente", "Configuración"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Tus registros se guardan en tu cuenta. No se envían órdenes ni se vigilan mercados en segundo plano.")
    if st.button("Cerrar sesión", use_container_width=True):
        logout()
        st.rerun()

views = {
    "Inicio": home.render,
    "Productos": products.render,
    "Inversiones": investments.render,
    "Simulador": simulator.render,
    "Alertas": alerts.render,
    "Analizar imágenes": image_analysis.render,
    "Aprender": learning.render,
    "Asistente": assistant.render,
    "Configuración": settings.render,
}
views[page]()

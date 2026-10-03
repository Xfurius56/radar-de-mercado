from __future__ import annotations

import streamlit as st

from radar.db import init_db
from radar.ui import apply_style
from radar.views import alerts, assistant, home, investments, learning, products, settings, simulator

st.set_page_config(
    page_title="Radar de Mercado",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
apply_style()

with st.sidebar:
    st.title("🧭 Radar")
    st.caption("Investigación educativa")
    page = st.radio(
        "Navegación",
        ["Inicio", "Productos", "Inversiones", "Simulador", "Alertas", "Aprender", "Asistente", "Configuración"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Los datos guardados son locales. No se envían órdenes ni se vigilan mercados en segundo plano.")

views = {
    "Inicio": home.render,
    "Productos": products.render,
    "Inversiones": investments.render,
    "Simulador": simulator.render,
    "Alertas": alerts.render,
    "Aprender": learning.render,
    "Asistente": assistant.render,
    "Configuración": settings.render,
}
views[page]()

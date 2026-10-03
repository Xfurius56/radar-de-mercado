from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from radar.config import source_keys
from radar.db import counts, get_setting, list_alerts, now_iso, set_setting, source_statuses
from radar.ui import date_label


def render() -> None:
    st.title("Radar de Mercado")
    st.write("Espacio de investigación educativa para productos y activos. Los resultados dependen de las fuentes y de los datos que hayas introducido.")
    summary = counts()
    previous_visit = get_setting("dashboard_last_seen")
    events = [item for item in list_alerts() if item["status"] == "activada"]
    if previous_visit:
        try:
            previous_dt = datetime.fromisoformat(previous_visit.replace("Z", "+00:00"))
            events = [item for item in events if item.get("triggered_at") and datetime.fromisoformat(item["triggered_at"].replace("Z", "+00:00")) > previous_dt]
        except ValueError:
            pass
    a, b, c, d = st.columns(4)
    a.metric("Productos registrados", summary["products"])
    b.metric("Activos en seguimiento", summary["watchlist"])
    c.metric("Alertas pendientes", summary["alerts"])
    d.metric("Cambios desde última visita", len(events))

    keys = source_keys()
    st.subheader("Estado de los datos")
    statuses = {row["source"]: row for row in source_statuses()}
    rows = []
    for source, configured in keys.items():
        entry = statuses.get(source, {})
        state = (entry.get("state") or "configurada; aún sin consulta") if configured else "requiere configuración en este entorno"
        rows.append({
            "Fuente": source,
            "Acceso": "Credencial detectada" if configured else "Sin credencial",
            "Estado": state,
            "Última consulta correcta": date_label(entry.get("last_success")),
            "Detalle": entry.get("message") or "No se ha consultado durante esta sesión de datos.",
        })
    rows.append({
        "Fuente": "Productos",
        "Acceso": "Fichas manuales de tu cuenta",
        "Estado": "Disponible",
        "Última consulta correcta": "al guardar cada ficha",
        "Detalle": "La demanda, los precios y el proveedor deben tener una fuente indicada por quien los registra.",
    })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Cambios importantes")
    if not events:
        st.info("No hay alertas activadas desde la última visita. Las condiciones se revisan cuando consultas una fuente o guardas nuevos datos; la app no vigila en segundo plano.")
    else:
        for event in events[:5]:
            st.markdown(f"**{event['label'] or event['target']}** · {date_label(event.get('triggered_at'))}")
            st.caption(event.get("details") or "Condición cumplida; consulta la pantalla de alertas para más información.")

    st.subheader("Cómo leer el panel")
    st.caption("Los productos registrados proceden de tus fichas manuales o de importaciones. Las cotizaciones externas incluyen proveedor y fecha. Una fuente sin credencial o con errores queda marcada como limitada; las estimaciones no son predicciones ni garantías.")
    set_setting("dashboard_last_seen", now_iso())

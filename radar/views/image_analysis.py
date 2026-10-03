from __future__ import annotations

import streamlit as st

from radar.config import env_value
from radar.db import (complete_image_analysis, delete_image_analysis, fail_image_analysis,
                      image_analyses, image_analysis_usage_24h, reserve_image_analysis)
from radar.image_analysis import analyze_image, prepare_image


def render() -> None:
    daily_limit = 5
    used_today = image_analysis_usage_24h()
    st.title("Análisis de imágenes")
    st.write("Sube una foto de producto o una captura de un gráfico. La imagen se analiza cuando pulsas el botón; no se conserva en Radar.")
    st.warning("El análisis es una ayuda de investigación, no verifica demanda o precios reales y no es una recomendación financiera. Para imágenes, el contenido se envía a OpenAI API; revisa sus condiciones antes de subir material privado.")
    if not env_value("OPENAI_API_KEY"):
        st.info("El administrador debe añadir OPENAI_API_KEY en Streamlit Cloud → Manage app → Settings → Secrets para activar el análisis.")

    mode = st.radio("¿Qué quieres estudiar?", ["Dropshipping", "Trading"], horizontal=True)
    upload = st.file_uploader("Imagen (JPG, PNG o WebP; máximo 8 MB)", type=["jpg", "jpeg", "png", "webp"], max_upload_size=10)
    question = st.text_area("¿Qué aspecto quieres que revise? (opcional)", max_chars=1200,
                            placeholder="Ej.: ¿Qué atributos se ven y qué tendría que verificar con el proveedor?")
    use_web_search = st.checkbox("Añadir búsqueda web actual (puede aumentar el coste de OpenAI)", value=False)
    consent = st.checkbox("Entiendo que, al analizar, la imagen optimizada y mi petición se enviarán a OpenAI API; la búsqueda web opcional también enviará la consulta al servicio de búsqueda.")
    st.caption(f"Límite de seguridad: {daily_limit} intentos de análisis por cuenta en 24 horas · usados: {used_today}.")
    image_bytes = None
    if upload is not None:
        try:
            image_bytes, _ = prepare_image(upload.getvalue())
            st.image(image_bytes, caption="Vista previa optimizada", use_container_width=True)
        except ValueError as exc:
            st.error(str(exc))

    if st.button("Analizar imagen", type="primary",
                 disabled=image_bytes is None or not env_value("OPENAI_API_KEY") or not consent or used_today >= daily_limit):
        reserved_id = None
        try:
            reserved_id = reserve_image_analysis(mode, "imagen.jpg")
            with st.spinner("Analizando la imagen…"):
                result = analyze_image(image_bytes, mode, question, use_web_search)
                complete_image_analysis(reserved_id, result)
            st.subheader("Resultado")
            st.markdown(result)
        except (ValueError, RuntimeError) as exc:
            if reserved_id is not None:
                try:
                    fail_image_analysis(reserved_id)
                except Exception:
                    pass
            st.error(str(exc))
        except Exception as exc:
            if reserved_id is not None:
                try:
                    fail_image_analysis(reserved_id)
                except Exception:
                    pass
            st.error(f"No se pudo completar el análisis ({type(exc).__name__}). Revisa la configuración de IA e inténtalo más tarde.")
    if used_today >= daily_limit:
        st.info("Has alcanzado el límite de análisis de esta cuenta. Podrás volver a usarlo cuando se libere un intento dentro de las próximas 24 horas.")

    st.subheader("Tus análisis recientes")
    records = image_analyses()
    if not records:
        st.caption("Los resultados que guardes aparecerán aquí solo dentro de tu cuenta.")
    for record in records:
        with st.expander(f"{record['mode']} · {record['file_name']} · {record['created_at']}"):
            st.markdown(record["analysis"])
            if st.button("Eliminar este resultado", key=f"delete_image_{record['id']}"):
                delete_image_analysis(int(record["id"]))
                st.rerun()

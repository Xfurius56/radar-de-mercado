from __future__ import annotations

import streamlit as st

from radar.db import lessons_progress, save_lesson
from radar.lessons import LESSONS


def render() -> None:
    st.title("Lecciones y aprendizaje")
    st.write("Módulos progresivos con ejemplos ficticios. El avance se guarda en la base de datos local de este proyecto.")
    progress = lessons_progress()
    completed_count = sum(bool(row.get("completed")) for row in progress.values())
    st.progress(completed_count / len(LESSONS) if LESSONS else 0)
    st.caption(f"Módulos completados: {completed_count} de {len(LESSONS)}.")
    next_lesson = next((lesson for lesson in LESSONS if not progress.get(lesson["id"], {}).get("completed")), None)
    if next_lesson:
        st.info(f"Siguiente módulo sugerido según tu progreso: {next_lesson['area']} · {next_lesson['title']}.")
    else:
        st.success("Has completado los módulos actuales. Puedes volver a cualquiera para repasar.")

    for lesson in LESSONS:
        done = bool(progress.get(lesson["id"], {}).get("completed"))
        with st.expander(f"{'✓ ' if done else ''}{lesson['area']} · {lesson['title']}", expanded=lesson is next_lesson):
            st.write(lesson["text"])
            feedback = st.session_state.pop(f"lesson_feedback_{lesson['id']}", None)
            if feedback is not None:
                if feedback:
                    st.success("Correcto. El concepto clave queda guardado como completado.")
                else:
                    st.info(f"La respuesta correcta es «{lesson['options'][lesson['answer']]}». Revisa la explicación y vuelve a intentarlo.")
            st.markdown("**Comprobación breve**")
            options = lesson["options"]
            choice = st.radio(lesson["question"], range(len(options)), format_func=lambda value: options[value], key=f"quiz_{lesson['id']}")
            exercise = st.text_area("Ejercicio de escenario ficticio", placeholder=lesson["exercise"], key=f"exercise_{lesson['id']}")
            if st.button("Comprobar y guardar progreso", key=f"check_{lesson['id']}"):
                correct = choice == lesson["answer"]
                save_lesson(lesson["id"], correct, 100 if correct else 0)
                st.session_state[f"lesson_feedback_{lesson['id']}"] = correct
                if exercise.strip():
                    st.session_state[f"lesson_exercise_{lesson['id']}"] = True
                st.rerun()
            if st.session_state.pop(f"lesson_exercise_{lesson['id']}", False):
                st.caption("El ejercicio se usa para tu reflexión en esta sesión; no se califica ni se guarda como perfil personal.")
            previous_score = progress.get(lesson["id"], {}).get("quiz_score")
            if previous_score is not None:
                st.caption(f"Último resultado guardado: {previous_score:.0f}%.")

    st.subheader("Glosario rápido")
    terms = {
        "Liquidez": "Facilidad de comprar o vender sin mover demasiado el precio; volumen por sí solo no la describe por completo.",
        "Volatilidad": "Variación de los rendimientos observados en un periodo; no es una medida exacta de pérdida futura.",
        "Apalancamiento": "Exposición mayor que el capital aportado; aumenta ganancias y pérdidas y puede generar liquidación.",
        "Punto de equilibrio": "Nivel de ventas en el que ingresos y costes considerados se igualan.",
        "Coste de adquisición": "Gasto para conseguir una venta, que puede incluir publicidad, comisiones y promociones.",
        "Deslizamiento": "Diferencia entre el precio esperado y el precio al que se ejecuta una orden.",
        "Diferencial": "Diferencia entre precio disponible de compra y precio disponible de venta.",
    }
    for term, definition in terms.items():
        st.markdown(f"**{term}:** {definition}")

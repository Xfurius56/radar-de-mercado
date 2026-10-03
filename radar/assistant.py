from __future__ import annotations

from typing import Any

from radar.config import env_value


def is_configured() -> bool:
    return bool(env_value("OPENAI_API_KEY"))


def answer(question: str, context: str, history: list[dict[str, str]] | None = None) -> tuple[str, str]:
    """Devuelve (respuesta, modo). El contexto es el único conjunto de datos de la app que se comparte."""
    if not is_configured():
        return demo_answer(question, context), "Demostración educativa; sin conexión a IA ni a datos actuales adicionales"
    from openai import OpenAI

    client = OpenAI(api_key=env_value("OPENAI_API_KEY"))
    transcript = []
    for item in (history or [])[-8:]:
        transcript.append(f"{item.get('role', 'user')}: {item.get('content', '')}")
    prior = "\n".join(transcript)
    system = (
        "Eres un mentor educativo en español de trading, inversión y dropshipping. "
        "Responde con claridad y rigor; explica términos. Distingue dato, estimación e hipótesis. "
        "No garantices rentabilidad ni des órdenes personalizadas de compra o venta. "
        "Usa únicamente los datos presentes en el contexto para afirmar hechos de mercado; si faltan, dilo. "
        "Cita el nombre y la fecha de las fuentes que aparezcan en el contexto. "
        "No afirmes que la app vigila mercados continuamente."
    )
    prompt = f"CONTEXTO DISPONIBLE EN LA APP:\n{context or 'No hay datos de mercado cargados para esta pregunta.'}\n\nCONVERSACIÓN RECIENTE:\n{prior or 'Sin mensajes previos.'}\n\nPREGUNTA ACTUAL:\n{question}"
    response = client.responses.create(
        model=env_value("OPENAI_MODEL", "gpt-5"),
        instructions=system,
        input=prompt,
        store=False,
    )
    return response.output_text, "OpenAI API; respuesta basada en el contexto que se muestra"


def demo_answer(question: str, context: str) -> str:
    q = question.casefold()
    if any(word in q for word in ("apalanc", "leverage", "margen")):
        core = (
            "El apalancamiento amplía la exposición respecto al capital aportado. Por ejemplo ficticio: con 100 € y exposición 5×, "
            "un movimiento del activo del 2% equivale aproximadamente a un 10% sobre esos 100 €, antes de costes; el movimiento contrario "
            "puede consumir capital con rapidez. El resultado real depende del producto, sus reglas y las comisiones."
        )
    elif any(word in q for word in ("punto de equilibrio", "break-even", "margen")):
        core = (
            "El punto de equilibrio indica cuántas ventas hacen falta para cubrir los costes fijos. En una cuenta simple: "
            "coste fijo de campaña ÷ contribución por pedido antes de ese coste. Si la contribución es cero o negativa, aumentar ventas "
            "no resuelve el problema. Usa costes observados y añade impuestos, devoluciones y comisiones cuando correspondan."
        )
    elif any(word in q for word in ("riesgo", "posición", "stop")):
        core = (
            "Una forma de limitar el riesgo por operación es fijar primero cuánto capital aceptarías perder y después calcular el tamaño: "
            "riesgo monetario ÷ distancia entre entrada y salida prevista. Esa salida puede ejecutarse peor de lo esperado por saltos de precio, "
            "liquidez o costes; un stop no garantiza el precio exacto."
        )
    else:
        core = (
            "Puedo ayudarte a descomponer la pregunta en datos, supuestos y riesgos. En esta versión no hay una clave de IA conectada: "
            "este modo ofrece explicaciones educativas predefinidas y no consulta Internet ni inventa cotizaciones, proveedores o tendencias."
        )
    if context.strip():
        core += "\n\nHay contexto local disponible, pero el modo de demostración no genera un análisis automático sobre él. Revisa en la pantalla las fuentes y fechas originales."
    return core

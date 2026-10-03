from __future__ import annotations

LESSONS = [
    {
        "id": "trading-01", "area": "Trading", "title": "Mercados, activos y órdenes",
        "text": "Una acción representa una participación en una empresa; un ETF agrupa activos y cotiza en bolsa; una criptomoneda es un activo digital cuyo mercado puede operar todo el día. Una orden de mercado prioriza ejecutar pronto al precio disponible. Una orden limitada fija el precio máximo de compra o mínimo de venta, pero puede no ejecutarse. El precio observado y el precio ejecutado pueden diferir.",
        "question": "¿Qué riesgo tiene una orden limitada?", "options": ["Puede no ejecutarse", "Garantiza el precio y la ejecución", "Elimina las comisiones"], "answer": 0,
        "exercise": "Escenario ficticio: una acción muestra 20,00 € y colocas una orden limitada de compra a 19,50 €. Explica dos resultados posibles.",
    },
    {
        "id": "trading-02", "area": "Trading", "title": "Riesgo y tamaño de posición",
        "text": "El tamaño de posición conecta el riesgo monetario elegido con la distancia entre la entrada y el nivel donde tu hipótesis deja de tener sentido. Fórmula didáctica: cantidad = riesgo monetario ÷ (entrada − salida prevista). Comisiones, deslizamiento y huecos de precio pueden elevar la pérdida. El apalancamiento amplifica tanto ganancias como pérdidas y puede provocar liquidaciones.",
        "question": "Si aceptas arriesgar 25 € y la distancia por unidad es 2,50 €, ¿cuántas unidades resultan antes de costes?", "options": ["10", "25", "0,1"], "answer": 0,
        "exercise": "Con esos mismos datos ficticios, enumera dos costes o eventos que podrían hacer que la pérdida supere 25 €.",
    },
    {
        "id": "trading-03", "area": "Inversión", "title": "Rentabilidad, volatilidad y horizonte",
        "text": "La rentabilidad histórica describe lo que ocurrió en un periodo concreto; no pronostica el futuro. La volatilidad mide cuánto variaron los rendimientos, no la probabilidad exacta de perder. Liquidez describe la facilidad de negociar sin mover mucho el precio; el volumen es solo una aproximación y depende del mercado y del instrumento. Diversificar reduce algunas concentraciones, pero no elimina el riesgo.",
        "question": "¿Qué describe mejor la volatilidad histórica?", "options": ["La variación pasada de rendimientos", "La rentabilidad futura garantizada", "La liquidez exacta"], "answer": 0,
        "exercise": "Compara de forma ficticia dos activos: A tuvo menor variación y B mayor rendimiento histórico. ¿Qué información adicional pedirías antes de compararlos?",
    },
    {
        "id": "drop-01", "area": "Dropshipping", "title": "Costes y margen por pedido",
        "text": "En dropshipping, el proveedor prepara y envía el producto al cliente, pero la tienda sigue siendo responsable de la oferta, atención y posventa. El margen por pedido debe descontar producto, envío, comisiones, impuestos aplicables, publicidad variable y una provisión razonable para devoluciones. El punto de equilibrio de una campaña divide el gasto fijo de la campaña entre la contribución de cada pedido antes de ese gasto.",
        "question": "¿Qué pasa si la contribución por pedido antes de publicidad fija es negativa?", "options": ["Cada venta añade pérdida antes de costes fijos", "Más ventas garantizan beneficio", "El coste de envío desaparece"], "answer": 0,
        "exercise": "Escenario ficticio: precio 40 €, producto 12 €, envío 5 €, comisión 2 €, impuestos estimados 4 €, reserva de devoluciones 2 € y anuncio por pedido 8 €. Calcula beneficio aproximado por pedido.",
    },
    {
        "id": "drop-02", "area": "Dropshipping", "title": "Validar producto y proveedor",
        "text": "Una señal de tendencia o una lista de anuncios no demuestra demanda rentable. Valida primero con evidencia trazable: muestras, tiempos de entrega observados, costes completos, preguntas de clientes y una prueba pequeña con límites de gasto. Comprueba quién responde por productos defectuosos, devoluciones, garantías, propiedad intelectual y normativa del país de venta. No uses reseñas inventadas ni afirmaciones que no puedas demostrar.",
        "question": "¿Qué evidencia ayuda a evaluar el plazo real del proveedor?", "options": ["Pedidos de muestra con fechas registradas", "Una promesa sin condiciones", "Un anuncio viral"], "answer": 0,
        "exercise": "Diseña una prueba ficticia de bajo coste y define qué resultado haría que pares antes de aumentar el gasto.",
    },
]


def lesson_by_id(lesson_id: str) -> dict | None:
    return next((lesson for lesson in LESSONS if lesson["id"] == lesson_id), None)

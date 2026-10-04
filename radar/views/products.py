from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd
import streamlit as st

from radar.alerts import check_product_update
from radar.db import add_product, get_setting, list_products, product_history, toggle_product_favorite, update_product
from radar.scoring import product_economics, product_score
from radar.ui import money, percent
from radar.views.image_analysis import render as render_image_analysis

CSV_COLUMNS = [
    "name", "category", "country", "currency", "provider", "provider_url", "source_url",
    "product_cost", "shipping_cost", "ad_cost", "platform_fee_pct", "tax_pct", "refund_pct",
    "sale_price", "launch_budget", "delivery_days", "supplier_quality", "demand_score",
    "demand_source", "demand_updated", "competition_score", "competitor_price", "competition_source",
    "fragile", "return_risk", "legal_risk", "brand_risk", "notes",
]


def _editor(product: dict[str, Any] | None, prefix: str) -> tuple[bool, dict[str, Any]]:
    current = product or {}
    pref_currency = current.get("currency") or get_setting("currency", "EUR")
    with st.form(f"product_form_{prefix}"):
        st.markdown("Los datos pueden ser manuales. Añade los enlaces y fechas que permitan verificarlos.")
        c1, c2 = st.columns(2)
        name = c1.text_input("Nombre del producto *", value=current.get("name", ""), key=f"{prefix}_name")
        category = c2.text_input("Categoría", value=current.get("category", ""), key=f"{prefix}_category")
        c1, c2, c3 = st.columns(3)
        country = c1.text_input("País de venta", value=current.get("country") or get_setting("country", "España"), key=f"{prefix}_country")
        currency = c2.selectbox("Moneda de esta ficha", ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"], index=["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"].index(pref_currency) if pref_currency in ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"] else 0, key=f"{prefix}_currency")
        provider = c3.text_input("Proveedor", value=current.get("provider", ""), key=f"{prefix}_provider")
        c1, c2 = st.columns(2)
        provider_url = c1.text_input("Enlace del proveedor", value=current.get("provider_url", ""), key=f"{prefix}_provider_url")
        source_url = c2.text_input("Enlace de evidencia o fuente", value=current.get("source_url", ""), key=f"{prefix}_source_url")

        st.markdown("**Costes y precio por pedido**")
        c1, c2, c3 = st.columns(3)
        product_cost = c1.number_input("Coste del producto", min_value=0.0, value=float(current.get("product_cost") or 0), step=1.0, key=f"{prefix}_product_cost")
        shipping_cost = c2.number_input("Envío", min_value=0.0, value=float(current.get("shipping_cost") or 0), step=1.0, key=f"{prefix}_shipping")
        ad_cost = c3.number_input("Publicidad variable por pedido", min_value=0.0, value=float(current.get("ad_cost") or 0), step=1.0, key=f"{prefix}_ad")
        c1, c2, c3, c4 = st.columns(4)
        platform_fee_pct = c1.number_input("Comisiones (%)", min_value=0.0, max_value=100.0, value=float(current.get("platform_fee_pct") or 0), step=0.5, key=f"{prefix}_fees")
        tax_pct = c2.number_input("Impuestos estimados (%)", min_value=0.0, max_value=100.0, value=float(current.get("tax_pct") or 0), step=0.5, key=f"{prefix}_tax")
        refund_pct = c3.number_input("Reserva por devoluciones (%)", min_value=0.0, max_value=100.0, value=float(current.get("refund_pct") or 0), step=0.5, key=f"{prefix}_refund")
        sale_price = c4.number_input("Precio de venta", min_value=0.0, value=float(current.get("sale_price") or 0), step=1.0, key=f"{prefix}_sale")
        launch_budget = st.number_input("Presupuesto fijo de prueba/campaña", min_value=0.0, value=float(current.get("launch_budget") or 0), step=5.0, key=f"{prefix}_launch")

        st.markdown("**Señales y riesgos**")
        c1, c2, c3 = st.columns(3)
        old_delivery = current.get("delivery_days")
        delivery_days = c1.number_input("Plazo de entrega (días; 0 = sin dato)", min_value=0, max_value=365, value=int(old_delivery or 0), key=f"{prefix}_delivery")
        old_quality = current.get("supplier_quality")
        quality = c2.number_input("Calidad observada del proveedor (1–5; 0 = sin dato)", min_value=0.0, max_value=5.0, value=float(old_quality or 0), step=0.5, key=f"{prefix}_quality")
        has_demand = c3.checkbox("Tengo señal de demanda documentada", value=current.get("demand_score") not in (None, ""), key=f"{prefix}_has_demand")
        c1, c2, c3 = st.columns(3)
        demand_score = c1.number_input("Señal de demanda (0–100)", min_value=0.0, max_value=100.0, value=float(current.get("demand_score") or 0), key=f"{prefix}_demand")
        demand_source = c2.text_input("Fuente de esa señal", value=current.get("demand_source", ""), key=f"{prefix}_demand_source")
        default_demand_date = current.get("demand_updated") or date.today().isoformat()
        try:
            demand_date = datetime.fromisoformat(default_demand_date).date()
        except (TypeError, ValueError):
            demand_date = date.today()
        demand_updated = c3.date_input("Fecha de la señal", value=demand_date, key=f"{prefix}_demand_date")
        c1, c2 = st.columns(2)
        has_competition = c1.checkbox("Tengo una evaluación de saturación", value=current.get("competition_score") not in (None, ""), key=f"{prefix}_has_comp")
        competition_score = c2.number_input("Saturación (0 baja – 100 alta)", min_value=0.0, max_value=100.0, value=float(current.get("competition_score") or 0), key=f"{prefix}_competition")
        c1, c2 = st.columns(2)
        competitor_price = c1.number_input("Precio de competidor observado (0 = sin dato)", min_value=0.0, value=float(current.get("competitor_price") or 0), step=1.0, key=f"{prefix}_competitor_price")
        competition_source = c2.text_input("Fuente/fecha del precio o saturación", value=current.get("competition_source", ""), key=f"{prefix}_competition_source")
        c1, c2, c3, c4 = st.columns(4)
        fragile = c1.checkbox("Producto frágil", value=bool(current.get("fragile")), key=f"{prefix}_fragile")
        return_risk = c2.checkbox("Devoluciones probablemente elevadas", value=bool(current.get("return_risk")), key=f"{prefix}_return_risk")
        legal_risk = c3.checkbox("Restricciones legales/regulatorias por verificar", value=bool(current.get("legal_risk")), key=f"{prefix}_legal_risk")
        brand_risk = c4.checkbox("Posible riesgo de marca/IP", value=bool(current.get("brand_risk")), key=f"{prefix}_brand")
        notes = st.text_area("Notas: evidencia a favor, dudas y validación siguiente", value=current.get("notes", ""), key=f"{prefix}_notes")
        submitted = st.form_submit_button("Guardar ficha", type="primary")
    values = {
        "name": name.strip(), "category": category.strip(), "country": country.strip(), "currency": currency,
        "provider": provider.strip(), "provider_url": provider_url.strip(), "source_url": source_url.strip(),
        "product_cost": product_cost, "shipping_cost": shipping_cost, "ad_cost": ad_cost,
        "platform_fee_pct": platform_fee_pct, "tax_pct": tax_pct, "refund_pct": refund_pct,
        "sale_price": sale_price, "launch_budget": launch_budget,
        "delivery_days": int(delivery_days) if delivery_days > 0 else None,
        "supplier_quality": quality if quality > 0 else None,
        "demand_score": demand_score if has_demand else None,
        "demand_source": demand_source if has_demand else "",
        "demand_updated": demand_updated.isoformat() if has_demand else "",
        "competition_score": competition_score if has_competition else None,
        "competitor_price": competitor_price if competitor_price > 0 else None,
        "competition_source": competition_source.strip(),
        "fragile": int(fragile), "return_risk": int(return_risk), "legal_risk": int(legal_risk),
        "brand_risk": int(brand_risk), "notes": notes.strip(),
    }
    return submitted, values


def _score_line(product: dict[str, Any], target_margin: float, weights: dict[str, float]) -> dict[str, Any]:
    result = product_score(product, target_margin, weights)
    economics = result["economics"]
    return {
        "id": product["id"], "name": product["name"], "category": product["category"],
        "country": product["country"], "provider": product["provider"], "currency": product["currency"],
        "sale_price": product["sale_price"], "landed_cost": float(product["product_cost"] or 0) + float(product["shipping_cost"] or 0),
        "profit": economics["profit_per_order"], "margin": economics["margin_pct"],
        "score": result["score"], "delivery_days": product["delivery_days"],
        "demand_score": product["demand_score"], "favorite": product["is_favorite"],
        "raw": product, "scoring": result,
    }


def _import_csv(upload) -> None:
    try:
        data = pd.read_csv(upload)
    except Exception as exc:
        st.error(f"No pude leer el CSV: {exc}")
        return
    if "name" not in data.columns:
        st.error("El CSV debe incluir una columna name.")
        return
    imported, errors = 0, []
    number_fields = {"product_cost", "shipping_cost", "ad_cost", "platform_fee_pct", "tax_pct", "refund_pct", "sale_price", "launch_budget", "delivery_days", "supplier_quality", "demand_score", "competition_score", "competitor_price"}
    for idx, row in data.iterrows():
        values: dict[str, Any] = {}
        for field in CSV_COLUMNS:
            value = row.get(field, None)
            if pd.isna(value):
                value = None
            if field in number_fields and value not in (None, ""):
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    errors.append(f"Fila {idx + 2}: {field} no es numérico.")
                    value = 0
            if field in {"fragile", "return_risk", "legal_risk", "brand_risk"}:
                value = int(str(value).strip().lower() in {"1", "true", "sí", "si", "yes"}) if value is not None else 0
            if value is None:
                if field in {"delivery_days", "supplier_quality", "demand_score", "competition_score", "competitor_price"}:
                    value = None
                else:
                    value = "" if field not in number_fields else 0
            values[field] = value
        if not str(values.get("name", "")).strip():
            errors.append(f"Fila {idx + 2}: falta name.")
            continue
        if not values.get("currency"):
            values["currency"] = get_setting("currency", "EUR")
        try:
            add_product(values)
            imported += 1
        except Exception as exc:
            errors.append(f"Fila {idx + 2}: {exc}")
    st.success(f"Fichas importadas: {imported}. Los datos CSV se registran como aportados por el usuario.")
    for error in errors[:8]:
        st.warning(error)


def render() -> None:
    st.title("Buscador de productos")
    st.write("Compara fichas de producto con costes y señales que hayas documentado. Sin catálogo conectado, la app no descubre productos ni demanda por sí sola.")
    tab_search, tab_add, tab_compare, tab_file = st.tabs(["Buscar y analizar", "Añadir o editar", "Comparar", "Importar CSV"])

    with tab_search:
        products = list_products()
        if not products:
            st.info("Aún no hay fichas. Añade un producto o importa un CSV para empezar.")
        else:
            cats = sorted({p["category"] for p in products if p["category"]})
            providers = sorted({p["provider"] for p in products if p["provider"]})
            c1, c2, c3, c4 = st.columns(4)
            country_filter = c1.selectbox("País", ["Todos"] + sorted({p["country"] for p in products if p["country"]}))
            category_filter = c2.selectbox("Categoría", ["Todas"] + cats)
            provider_filter = c3.selectbox("Proveedor", ["Todos"] + providers)
            target_margin = c4.number_input("Margen deseado (%)", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
            c1, c2, c3, c4 = st.columns(4)
            budget = c1.number_input("Presupuesto máximo en producto + envío (0 = sin filtro)", min_value=0.0, value=0.0, step=10.0)
            max_sale = c2.number_input("Precio de venta máximo (0 = sin filtro)", min_value=0.0, value=0.0, step=5.0)
            max_delivery = c3.number_input("Entrega máxima en días (0 = sin filtro)", min_value=0, max_value=365, value=0)
            filter_currency = c4.selectbox("Divisa de filtros monetarios", ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"], index=["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"].index(get_setting("currency", "EUR")) if get_setting("currency", "EUR") in ["EUR", "USD", "MXN", "ARS", "CLP", "COP", "GBP"] else 0)
            st.caption("El presupuesto y el precio máximo solo se aplican a fichas en la divisa elegida; no se convierten importes.")
            st.caption("Pesos configurables. Solo se usan factores con datos; los datos ausentes se muestran y no se rellenan.")
            w1, w2, w3, w4 = st.columns(4)
            weights = {
                "margen": w1.slider("Peso margen", 0, 100, 40),
                "demanda": w2.slider("Peso demanda", 0, 100, 25),
                "competencia": w3.slider("Peso competencia", 0, 100, 20),
                "entrega": w4.slider("Peso entrega", 0, 100, 15),
            }
            scored = [_score_line(p, target_margin, weights) for p in products]
            filtered = []
            for item in scored:
                p = item["raw"]
                if country_filter != "Todos" and p["country"] != country_filter:
                    continue
                if category_filter != "Todas" and p["category"] != category_filter:
                    continue
                if provider_filter != "Todos" and p["provider"] != provider_filter:
                    continue
                if (budget or max_sale) and p["currency"] != filter_currency:
                    continue
                if budget and item["landed_cost"] > budget:
                    continue
                if max_sale and float(item["sale_price"] or 0) > max_sale:
                    continue
                if max_delivery and (p["delivery_days"] is None or p["delivery_days"] > max_delivery):
                    continue
                filtered.append(item)
            filtered.sort(key=lambda item: item["score"] if item["score"] is not None else -1, reverse=True)
            if not filtered:
                st.info("Ninguna ficha cumple esos filtros.")
            for item in filtered:
                p, result = item["raw"], item["scoring"]
                economics = result["economics"]
                score_text = f"Índice de revisión {item['score']:.0f}/100" if item["score"] is not None else "Sin índice: faltan factores"
                with st.expander(f"{p['name']} · {score_text} · {p['country'] or 'país sin indicar'}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Beneficio/pedido estimado", money(economics["profit_per_order"], p["currency"]))
                    c2.metric("Margen estimado", percent(economics["margin_pct"]))
                    c3.metric("Entrega", f"{p['delivery_days']} días" if p["delivery_days"] is not None else "Sin dato")
                    c4.metric("Ventas para cubrir presupuesto fijo", str(economics["break_even_sales"] or "—"))
                    st.markdown("**Desglose del índice**")
                    factor_labels = {"margen": "Margen", "demanda": "Demanda", "competencia": "Menor saturación", "entrega": "Plazo"}
                    factor_text = " · ".join(f"{factor_labels[k]}: {'sin dato' if v is None else f'{v:.0f}/100'} (peso {weights[k]})" for k, v in result["factors"].items())
                    st.write(factor_text + (f" · penalizaciones de riesgo: −{result['penalties']:.0f}" if result["penalties"] else ""))
                    plus, minus = [], []
                    if economics["profit_per_order"] is not None and economics["profit_per_order"] > 0:
                        plus.append("Contribución por pedido positiva bajo los costes declarados.")
                    if p["demand_score"] is not None:
                        plus.append(f"Hay una señal documentada de demanda ({p['demand_score']:.0f}/100); su calidad depende de la fuente indicada.")
                    if p["supplier_quality"] is not None:
                        plus.append(f"Calidad observada del proveedor anotada por ti: {p['supplier_quality']:.1f}/5.")
                    if economics["profit_per_order"] is not None and economics["profit_per_order"] <= 0:
                        minus.append("La contribución estimada no es positiva con estos costes.")
                    if p["delivery_days"] is not None and p["delivery_days"] > 14:
                        minus.append("El plazo anotado supera dos semanas; puede afectar a conversión y devoluciones.")
                    if p["fragile"]:
                        minus.append("Producto frágil: revisa embalaje, daños y devoluciones.")
                    if p["return_risk"]:
                        minus.append("Se han marcado devoluciones probablemente elevadas; valida la causa y reserva de costes.")
                    if p["legal_risk"]:
                        minus.append("Hay restricciones legales o regulatorias por verificar antes de vender en ese país.")
                    if p["brand_risk"]:
                        minus.append("Posible riesgo de marca/propiedad intelectual; no lo promociones hasta resolverlo.")
                    if result["missing"]:
                        minus.append("Faltan datos: " + ", ".join(result["missing"]) + ".")
                    st.markdown("**A favor:** " + (" ".join(plus) if plus else "sin evidencia suficiente registrada."))
                    st.markdown("**En contra o por verificar:** " + (" ".join(minus) if minus else "los datos disponibles no señalan un impedimento específico."))
                    if p["source_url"]:
                        st.markdown(f"[Fuente/evidencia declarada]({p['source_url']})")
                    if p["provider_url"]:
                        st.markdown(f"[Proveedor declarado]({p['provider_url']})")
                    st.caption(f"Ficha actualizada: {p['updated_at'][:16].replace('T', ' ')} · señal de demanda: {p['demand_updated'] or 'sin dato'} · moneda de la ficha: {p['currency']}")
                    st.caption(f"Supuesto de coste: producto + envío + comisión + impuesto estimado + reserva de devoluciones + publicidad por pedido. Punto de equilibrio = presupuesto fijo ÷ contribución antes de publicidad por pedido. No incorpora costes que no hayas introducido.")
                    b1, b2 = st.columns(2)
                    if b1.button("Quitar de favoritos" if p["is_favorite"] else "Guardar en favoritos", key=f"fav_{p['id']}"):
                        toggle_product_favorite(p["id"], not bool(p["is_favorite"]))
                        st.rerun()
                    if p.get("notes"):
                        st.info(p["notes"])
            st.subheader("Ficha y validación de bajo coste")
            selected_id = st.selectbox("Elegir producto", [p["id"] for p in products], format_func=lambda pid: next(p["name"] for p in products if p["id"] == pid))
            selected = next(p for p in products if p["id"] == selected_id)
            st.markdown(f"**Hipótesis de cliente:** personas que buscan resolver una necesidad relacionada con «{selected['category'] or 'la función del producto'}». Esto es una hipótesis, no un segmento validado.")
            if selected.get("competitor_price"):
                st.markdown(f"Precio competidor anotado: {money(selected['competitor_price'], selected['currency'])} · evidencia: {selected.get('competition_source') or 'sin referencia indicada'}.")
            history = product_history(selected_id)
            if len(history) > 1:
                st.markdown("**Evolución de las anotaciones**")
                history_frame = pd.DataFrame(history)
                history_frame["observed_at"] = pd.to_datetime(history_frame["observed_at"], utc=True)
                demand_frame = history_frame.dropna(subset=["demand_score"])
                if not demand_frame.empty:
                    st.line_chart(demand_frame.set_index("observed_at")[["demand_score"]].rename(columns={"demand_score": "Señal de demanda anotada (0–100)"}), use_container_width=True)
                price_frame = history_frame.set_index("observed_at")[["sale_price", "competitor_price"]].rename(columns={"sale_price": "Precio propio", "competitor_price": "Precio competidor anotado"})
                st.line_chart(price_frame, use_container_width=True)
                st.caption("Esta serie refleja valores que tú guardaste; no equivale a una medición automática de tendencia o estacionalidad.")
                st.dataframe(history_frame[["observed_at", "sale_price", "competitor_price", "demand_score", "competition_score", "product_cost", "shipping_cost", "margin_pct"]].rename(columns={
                    "observed_at": "Fecha de registro", "sale_price": "Precio venta", "competitor_price": "Precio competidor",
                    "demand_score": "Demanda anotada", "competition_score": "Saturación anotada", "product_cost": "Coste producto",
                    "shipping_cost": "Coste envío", "margin_pct": "Margen estimado (%)",
                }), use_container_width=True, hide_index=True)
            st.markdown("**Prueba sugerida:** pide una muestra; registra plazo, estado y embalaje; entrevista a 5–10 posibles compradores sin inducir respuestas; compara costes completos de 2–3 proveedores; limita el gasto de una página de interés o campaña de prueba y define por adelantado el criterio para parar. No escales hasta resolver las devoluciones, normativa y derechos de marca.")

    with tab_add:
        products = list_products()
        mode = st.radio("Acción", ["Añadir ficha", "Editar ficha"], horizontal=True, key="product_edit_mode")
        selected = None
        if mode == "Editar ficha":
            if not products:
                st.info("No hay fichas para editar.")
            else:
                pid = st.selectbox("Ficha", [p["id"] for p in products], format_func=lambda value: next(p["name"] for p in products if p["id"] == value), key="edit_product_select")
                selected = next(p for p in products if p["id"] == pid)
        if mode == "Añadir ficha" or selected:
            submitted, values = _editor(selected, f"edit_{selected['id']}" if selected else "new")
            if submitted:
                if not values["name"]:
                    st.error("El nombre del producto es obligatorio.")
                elif selected:
                    old = update_product(selected["id"], values)
                    if old:
                        triggered = check_product_update(selected["id"], old, values)
                        st.success("Ficha actualizada. La fuente y las fechas quedan en el historial privado de tu cuenta.")
                        for detail in triggered:
                            st.warning(detail)
                else:
                    product_id = add_product(values)
                    st.success(f"Ficha guardada (n.º {product_id}). Los valores proceden de tu entrada; demanda y competencia no se verifican automáticamente.")

    with tab_compare:
        products = list_products()
        if len(products) < 2:
            st.info("Guarda al menos dos fichas para compararlas.")
        else:
            ids = st.multiselect("Selecciona productos", [p["id"] for p in products], default=[p["id"] for p in products[:2]], format_func=lambda pid: next(p["name"] for p in products if p["id"] == pid))
            rows = []
            for product in products:
                if product["id"] not in ids:
                    continue
                economics = product_economics(product)
                score = product_score(product)
                rows.append({"Producto": product["name"], "Precio": money(product["sale_price"], product["currency"]),
                             "Coste producto + envío": money(float(product["product_cost"] or 0) + float(product["shipping_cost"] or 0), product["currency"]),
                             "Beneficio estimado": money(economics["profit_per_order"], product["currency"]),
                             "Margen": percent(economics["margin_pct"]), "Índice de revisión": round(score["score"], 1) if score["score"] is not None else "sin datos",
                             "Demanda anotada": product["demand_score"] if product["demand_score"] is not None else "sin dato",
                             "Entrega (días)": product["delivery_days"] or "sin dato", "Proveedor": product["provider"] or "sin dato"})
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.caption("El índice es una ayuda configurable para ordenar investigación. No estima ventas ni rentabilidad futura.")

    with tab_file:
        st.write("El CSV debe usar estas columnas. Puedes dejar los campos desconocidos vacíos; los importes se interpretan en la moneda indicada por fila.")
        template = pd.DataFrame(columns=CSV_COLUMNS).to_csv(index=False).encode("utf-8")
        st.download_button("Descargar plantilla CSV", template, "plantilla_productos.csv", "text/csv")
        upload = st.file_uploader("Elegir un CSV", type=["csv"], key="product_csv")
        if upload and st.button("Importar fichas", key="import_products"):
            _import_csv(upload)


    with st.expander("Analizar foto y mercado del producto", expanded=False):
        render_image_analysis(mode_override="Dropshipping", embedded=True)

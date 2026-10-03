from __future__ import annotations

import math
from typing import Any


def product_economics(product: dict[str, Any]) -> dict[str, float | None]:
    price = float(product.get("sale_price") or 0)
    if price <= 0:
        return {"variable_cost": None, "profit_per_order": None, "margin_pct": None,
                "contribution_before_ads": None, "break_even_sales": None, "break_even_cpa": None}
    product_cost = float(product.get("product_cost") or 0)
    shipping = float(product.get("shipping_cost") or 0)
    ad_cost = float(product.get("ad_cost") or 0)
    platform = price * float(product.get("platform_fee_pct") or 0) / 100
    tax = price * float(product.get("tax_pct") or 0) / 100
    refund_reserve = price * float(product.get("refund_pct") or 0) / 100
    before_ads = price - product_cost - shipping - platform - tax - refund_reserve
    profit = before_ads - ad_cost
    margin = profit / price * 100
    launch_budget = float(product.get("launch_budget") or 0)
    break_even = math.ceil(launch_budget / before_ads) if launch_budget > 0 and before_ads > 0 else None
    return {
        "variable_cost": product_cost + shipping + platform + tax + refund_reserve + ad_cost,
        "profit_per_order": profit,
        "margin_pct": margin,
        "contribution_before_ads": before_ads,
        "break_even_sales": break_even,
        "break_even_cpa": before_ads,
    }


def product_score(product: dict[str, Any], target_margin: float = 20,
                  weights: dict[str, float] | None = None) -> dict[str, Any]:
    weights = weights or {"margen": 40, "demanda": 25, "competencia": 20, "entrega": 15}
    economics = product_economics(product)
    factors: dict[str, float | None] = {}
    margin = economics["margin_pct"]
    factors["margen"] = None if margin is None else max(0.0, min(100.0, float(margin) / max(target_margin, 1) * 70))
    demand = product.get("demand_score")
    factors["demanda"] = None if demand in (None, "") else max(0.0, min(100.0, float(demand)))
    competition = product.get("competition_score")
    factors["competencia"] = None if competition in (None, "") else 100.0 - max(0.0, min(100.0, float(competition)))
    delivery = product.get("delivery_days")
    factors["entrega"] = None if delivery in (None, "") else max(0.0, min(100.0, 100.0 - max(0, float(delivery)) * 2))
    used_weight = sum(float(weights.get(key, 0)) for key, value in factors.items() if value is not None)
    score = sum(float(value) * float(weights.get(key, 0)) for key, value in factors.items() if value is not None) / used_weight if used_weight else None
    penalties = 0.0
    if product.get("fragile"):
        penalties += 8
    if product.get("return_risk"):
        penalties += 10
    if product.get("legal_risk"):
        penalties += 20
    if product.get("brand_risk"):
        penalties += 25
    if score is not None:
        score = max(0.0, score - penalties)
    missing = [
        label for key, label in (("demand_score", "señal de demanda"), ("competition_score", "competencia"),
                                 ("delivery_days", "plazo de entrega"), ("provider", "proveedor"),
                                 ("provider_url", "enlace de proveedor"), ("source_url", "fuente/evidencia"))
        if product.get(key) in (None, "", 0)
    ]
    return {"score": score, "factors": factors, "weights": weights, "penalties": penalties,
            "missing": missing, "economics": economics}


def holdings_from_trades(initial_cash: float, trades: list[dict[str, Any]]) -> tuple[float, dict[tuple[str, str], float]]:
    cash = float(initial_cash)
    holdings: dict[tuple[str, str], float] = {}
    for trade in trades:
        key = (trade["symbol"], trade["asset_type"])
        qty = float(trade["quantity"])
        gross = qty * float(trade["price"])
        fee = float(trade.get("fee") or 0)
        if trade["action"] == "Compra":
            cash -= gross + fee
            holdings[key] = holdings.get(key, 0.0) + qty
        else:
            cash += gross - fee
            holdings[key] = holdings.get(key, 0.0) - qty
    return cash, {key: qty for key, qty in holdings.items() if qty > 1e-10}


def backtest_sma(rows: list[dict[str, Any]], fast: int = 20, slow: int = 50,
                 fee_pct: float = 0.1) -> dict[str, Any]:
    """SMA largo/corto con posición aplicada al siguiente día, sin usar el cierre futuro."""
    import pandas as pd

    frame = pd.DataFrame(rows).sort_values("date").drop_duplicates("date").reset_index(drop=True)
    if len(frame) < slow + 3:
        raise ValueError(f"Se necesitan al menos {slow + 3} sesiones; el proveedor devolvió {len(frame)}.")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["sma_fast"] = frame["close"].rolling(fast, min_periods=fast).mean()
    frame["sma_slow"] = frame["close"].rolling(slow, min_periods=slow).mean()
    signal = (frame["sma_fast"] > frame["sma_slow"]).astype(float)
    held = signal.shift(1).fillna(0.0)
    daily_return = frame["close"].pct_change().fillna(0.0)
    turnover = signal.diff().abs().shift(1).fillna(0.0)
    frame["estrategia"] = (1.0 + held * daily_return - turnover * fee_pct / 100).cumprod()
    frame["comprar_y_mantener"] = frame["close"] / frame["close"].iloc[0]
    frame = frame.dropna(subset=["sma_slow"]).reset_index(drop=True)
    if frame.empty:
        raise ValueError("No hay suficientes datos tras calcular las medias móviles.")
    frame["estrategia"] = frame["estrategia"] / frame["estrategia"].iloc[0]
    frame["comprar_y_mantener"] = frame["close"] / frame["close"].iloc[0]
    daily_strategy = frame["estrategia"].pct_change().dropna()
    volatility = float(daily_strategy.std() * math.sqrt(252) * 100) if len(daily_strategy) > 1 else 0.0
    return {
        "rows": frame[["date", "close", "sma_fast", "sma_slow", "estrategia", "comprar_y_mantener"]].to_dict("records"),
        "strategy_return_pct": (float(frame["estrategia"].iloc[-1]) - 1) * 100,
        "buy_hold_return_pct": (float(frame["comprar_y_mantener"].iloc[-1]) - 1) * 100,
        "annualized_volatility_pct": volatility,
        "period_start": frame["date"].iloc[0], "period_end": frame["date"].iloc[-1],
        "observations": len(frame), "fast": fast, "slow": slow, "fee_pct": fee_pct,
    }

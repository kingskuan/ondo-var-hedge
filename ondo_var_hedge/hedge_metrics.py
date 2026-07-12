"""Delta-neutral hedge cost / payback / divergence math.

All costs are per round-trip (open + close) of BOTH legs at notional N.
"""
from __future__ import annotations

from . import config


def round_trip_cost_usd(notional: float, var_spread_bps: float,
                        ondo_fee_rate: float) -> dict:
    """Cost to open+close a delta-neutral pair at `notional` per leg.

    Ondo leg: pay ondo_fee_rate per side (use maker if limit orders).
    Var leg:  pay spread_bps (Var charges $0 fees, cost is the spread).
    """
    ondo_cost = notional * ondo_fee_rate * 2  # open+close, both sides
    var_cost = notional * (var_spread_bps / 1e4) * 2
    total = ondo_cost + var_cost
    return {
        "notional_per_leg": notional,
        "ondo_cost": ondo_cost,
        "var_spread_cost": var_cost,
        "total_round_trip": total,
    }


def funding_spread_annualized(ondo_rate: float, var_rate: float,
                              interval_s: int = config.FUNDING_INTERVAL_S) -> float:
    """Net funding income rate per interval if Long Ondo + Short Var.

    Long Ondo receives +ondo_rate (if positive) / pays if negative.
    Short Var pays var_rate (if positive) / receives if negative.
    Net = ondo_rate - var_rate  (per interval, decimal of notional).
    """
    return ondo_rate - var_rate


def payback_round_trips(total_cost: float, funding_net_per_rt: float) -> float:
    """How many round-trips to recoup cost from funding spread alone.

    funding_net_per_rt = notional * net_rate (income per round trip).
    """
    if funding_net_per_rt <= 0:
        return float("inf")
    return total_cost / funding_net_per_rt


def divergence_flag(mark_var: float, mark_ondo: float,
                    threshold: float = config.MARK_DIVERGENCE_ALERT) -> tuple[bool, float]:
    if not mark_var or not mark_ondo:
        return False, 0.0
    diff = abs(mark_var - mark_ondo) / ((mark_var + mark_ondo) / 2)
    return diff > threshold, diff


def build_report(symbol: str, var: dict, ondo_funding: dict,
                 notional: float) -> dict:
    ondo_rate = ondo_funding.get("rate", 0.0)
    var_rate = var.get("funding_rate", 0.0)
    net_rate = funding_spread_annualized(ondo_rate, var_rate)
    cost = round_trip_cost_usd(notional, var.get("spread_bps", 0.0),
                               config.ONDO_MAKER_FEE * config.ONDO_FEE_DISCOUNT)
    funding_net_rt = notional * net_rate
    rt = payback_round_trips(cost["total_round_trip"], funding_net_rt)
    div_bad, div = divergence_flag(var.get("mark_price", 0.0),
                                    ondo_funding.get("mark_ondo", 0.0))
    return {
        "symbol": symbol,
        "ondo_funding_8h_%": round(ondo_rate * 100, 4),
        "var_funding_8h_%": round(var_rate * 100, 4),
        "net_funding_8h_%": round(net_rate * 100, 4),
        "var_spread_bps": round(var.get("spread_bps", 0.0), 3),
        "cost_round_trip_usd": round(cost["total_round_trip"], 2),
        "funding_net_per_rt_usd": round(funding_net_rt, 2),
        "payback_round_trips": (round(rt, 1) if rt != float("inf") else None),
        "mark_divergence": round(div * 100, 3) if div else 0.0,
        "divergence_alert": div_bad,
    }

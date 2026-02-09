# utils.py
from __future__ import annotations

import re
from typing import Tuple, Dict, Any, List

import pandas as pd
# ---------------- string / id utils ----------------
def slugify(s: str) -> str:
    s = str(s).strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-\.]", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_") or "Stock"


def fmt_num(x: float) -> str:
    if abs(x - int(x)) < 1e-12:
        return str(int(x))
    return (f"{x:.12g}").rstrip("0").rstrip(".")


def auto_stock_id(name: str, conc: float, unit: str) -> str:
    return f"{slugify(name)}_{fmt_num(conc)}{unit}"


# ---------------- unit conversion ----------------
def conc_from_amount_volume(
    amount: float,
    amount_unit: str,
    volume: float,
    volume_unit: str
) -> Tuple[float, str]:
    """
    amount / volume → concentration
    return: (value, unit='mM')
    """
    # amount → nmol
    amt_nmol = amount
    if amount_unit == "pmol":
        amt_nmol = amount / 1000.0
    elif amount_unit == "umol":
        amt_nmol = amount * 1000.0

    # volume → uL
    vol_uL = volume
    if volume_unit == "mL":
        vol_uL = volume * 1000.0

    conc_mM = amt_nmol / vol_uL if vol_uL > 0 else 0.0
    return conc_mM, "mM"


def to_mM(value: float, unit: str) -> float:
    if unit == "M":
        return value * 1000.0
    if unit == "mM":
        return value
    if unit == "uM":
        return value / 1000.0
    if unit == "nM":
        return value / 1_000_000.0
    raise ValueError(f"Unsupported conc unit: {unit}")


def from_mM(value_mM: float, unit: str) -> float:
    if unit == "M":
        return value_mM / 1000.0
    if unit == "mM":
        return value_mM
    if unit == "uM":
        return value_mM * 1000.0
    if unit == "nM":
        return value_mM * 1_000_000.0
    raise ValueError(f"Unsupported conc unit: {unit}")


def to_uL(value: float, unit: str) -> float:
    if unit == "uL":
        return value
    if unit == "mL":
        return value * 1000.0
    raise ValueError(f"Unsupported vol unit: {unit}")


def from_uL(value_uL: float, unit: str) -> float:
    if unit == "uL":
        return value_uL
    if unit == "mL":
        return value_uL / 1000.0
    raise ValueError(f"Unsupported vol unit: {unit}")


# ---------------- chemistry math ----------------
def amount_nmol_from_conc_vol(
    target_conc: float,
    target_unit: str,
    final_volume: float,
    final_vol_unit: str
) -> float:
    """
    c × V → amount (nmol)
    """
    c_mM = to_mM(target_conc, target_unit)
    v_uL = to_uL(final_volume, final_vol_unit)
    return c_mM * v_uL


def calc_volume_uL_from_target(
    stock_conc: float,
    stock_unit: str,
    target_conc: float,
    target_unit: str,
    final_volume: float,
    final_vol_unit: str
) -> float:
    """
    target concentration 기준으로 필요한 stock volume 계산
    """
    stock_mM = to_mM(stock_conc, stock_unit)
    target_mM = to_mM(target_conc, target_unit)
    final_uL = to_uL(final_volume, final_vol_unit)

    if stock_mM <= 0:
        return 0.0

    return (target_mM * final_uL) / stock_mM


# ---------------- reaction computation ----------------
def compute_reaction(
    card: Dict[str, Any],
    stocks_df,
    stock_options: List[str]
):
    """
    UI와 분리된 순수 reaction 계산 로직
    """
    n_target_rows = 0
    n_volume_rows = 0

    errors = []
    computed = []
    total_uL = 0.0

    final_uL = to_uL(card["final_volume"], card["final_vol_unit"])

    for i, r in enumerate(card["rows"], start=1):
        stock_sel = r["stock_sel"]
        tc, tu = r["target_conc"], r["target_unit"]
        vol, vu = r["vol"], r["vol_unit"]

        # stock 정보
        if stock_sel == "(DB 미등록: 임시 시약)":
            if not r["custom_name"]:
                continue
            sc, su = r["custom_stock_conc"], r["custom_stock_unit"]
            label = r["custom_name"]
            stock_id = None
        else:
            db = stocks_df[stocks_df["id"] == stock_sel]
            if db.empty:
                errors.append(f"Row {i}: invalid stock")
                continue
            sc = float(db.iloc[0]["stock_conc"])
            su = db.iloc[0]["stock_unit"]
            label = db.iloc[0]["name"]
            stock_id = stock_sel

        if sc <= 0:
            errors.append(f"Row {i}: invalid stock concentration")
            continue

        has_t = tc > 0
        has_v = vol > 0

        if has_t:
            n_target_rows += 1
        if has_v:
            n_volume_rows += 1

        if has_t and has_v:
            errors.append(f"Row {i}: target & volume both set")
            continue
        if not has_t and not has_v:
            continue

        if has_t:
            v_uL = calc_volume_uL_from_target(
                sc, su, tc, tu,
                card["final_volume"], card["final_vol_unit"]
            )
            vol_used = from_uL(v_uL, vu)
            tc2, tu2 = tc, tu
        else:
            v_uL = to_uL(vol, vu)
            eff_mM = (to_mM(sc, su) * v_uL) / final_uL if final_uL else 0
            tc2 = from_mM(eff_mM, tu)
            tu2 = tu
            vol_used = vol

        if n_target_rows > 0 and n_volume_rows > 1:
            errors.append(
                "Target conc 기준 계산 시 volume 직접 입력 row는 1개만 허용됩니다."
            )

        total_uL += to_uL(vol_used, vu)

        amt = amount_nmol_from_conc_vol(
            tc2, tu2,
            card["final_volume"], card["final_vol_unit"]
        )

        computed.append({
            "line_no": i,
            "reagent": label,
            "stock_conc": sc,
            "stock_unit": su,
            "target_conc": tc2,
            "target_unit": tu2,
            "volume": vol_used,
            "volume_unit": vu,
            "amount": amt,
            "amount_unit": "nmol",
            "note": r["note"],
            "stock_id": stock_id,
            "custom_name": r["custom_name"] if stock_id is None else None,
        })

    if total_uL - final_uL > 1e-6:
        errors.append("총 volume이 final volume 초과")

    return errors, computed, total_uL, final_uL

# utils.py - lookup_cf()를 아래처럼 교체 (None/empty 방어 포함)
def lookup_cf(cf_df, dye_name, target_wavelength) -> float:
    if not dye_name or cf_df is None or cf_df.empty:
        return 0.0

    hit = cf_df[
        (cf_df["dye_name"] == dye_name)
        & (cf_df["target_wavelength"] == target_wavelength)
    ]
    if hit.empty:
        return 0.0

    val = hit.iloc[0]["factor"]
    return float(val) if pd.notna(val) else 0.0

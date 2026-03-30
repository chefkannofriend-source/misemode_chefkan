#!/usr/bin/env python3
"""
MiseMode Unit Normalization Engine
Ported from chef_brain_v15_1_complete.js normalizeUnit()

Converts any input unit to standard kg or L.
Deterministic — no LLM involved, pure math.

Usage:
    echo '{"price": 10, "unit": "2x500g", "name": "flour"}' | python3 normalize_unit.py
    echo '[{"price":10,"unit":"lb","name":"beef"}, ...]' | python3 normalize_unit.py

Input:  JSON object or array with {price, unit, name}
Output: JSON with {price_per_std_unit, std_unit, audit_required}
"""

import json
import re
import sys
from pathlib import Path

# --- Load density library ---
_DENSITY_PATH = Path(__file__).parent.parent / "data" / "density.json"

def _load_density():
    if _DENSITY_PATH.exists():
        with open(_DENSITY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

DENSITY_LIBRARY = _load_density()

# --- Regex patterns (pre-compiled) ---
RE_MULTI = re.compile(r"(\d+)\s*[xX*×]\s*(\d+(?:\.\d+)?)\s*([a-z\u4e00-\u9fa5]+)")
RE_SIMPLE = re.compile(r"^(\d+(?:\.\d+)?)\s*([a-z\u4e00-\u9fa5]+)")
# box(15kg), case(12L), 箱(10kg), carton(6x1L)
RE_BOX = re.compile(r"(?:box|case|carton|crate|箱|盒)\s*\(?\s*(\d+(?:\.\d+)?)\s*([a-z\u4e00-\u9fa5]+)\s*\)?", re.IGNORECASE)

# --- Volume to liters conversion ---
VOLUME_TO_LITERS = {
    "gal": 3.785, "gallon": 3.785, "gallons": 3.785,
    "cup": 0.2366, "cups": 0.2366,
    "tbsp": 0.0148, "tbs": 0.0148, "tablespoon": 0.0148, "tablespoons": 0.0148,
    "tsp": 0.0049, "teaspoon": 0.0049, "teaspoons": 0.0049,
    "pt": 0.473, "pint": 0.473, "pints": 0.473,
    "qt": 0.946, "quart": 0.946, "quarts": 0.946,
}

# --- Unit aliases ---
KG_UNITS = {"kg", "kilogram", "kgs", "kilograms", "公斤"}
G_UNITS = {"g", "gram", "gms", "grams", "克"}
LB_UNITS = {"lb", "lbs", "pound", "pounds", "磅"}
OZ_UNITS = {"oz", "ounce", "ozs", "ounces"}
L_UNITS = {"l", "liter", "liters", "litre", "litres", "升"}
ML_UNITS = {"ml", "mls", "milliliters", "毫升"}


def get_specific_gravity(name: str) -> float | None:
    """Look up density (specific gravity) by ingredient name."""
    n = name.lower()
    for entry in DENSITY_LIBRARY:
        if any(k in n for k in entry["keys"]):
            return entry["sg"]
    return None


def normalize_unit(price: float, unit: str, name: str) -> dict:
    """
    Normalize price and unit to standard kg or L.

    Returns:
        {
            "price_per_std_unit": float,  # price per kg or per L
            "std_unit": str,              # "kg", "L", or original unit
            "audit_required": bool        # True if unit couldn't be fully resolved
        }
    """
    u_str = str(unit).strip()
    p = float(price) if price else 0.0

    if not u_str:
        return {"price_per_std_unit": p, "std_unit": "N/A", "audit_required": True}

    total_qty = 1.0
    clean_unit = u_str.lower()

    # Parse box/case/carton: "box(15kg)" → unpack to inner unit
    m_box = RE_BOX.match(clean_unit)
    if m_box:
        box_qty = float(m_box.group(1))
        box_unit = m_box.group(2)
        # Price is for the whole box, inner content is box_qty of box_unit
        # Recurse with unpacked values: price stays the same, unit becomes inner
        return normalize_unit(p, f"{box_qty * total_qty}{box_unit}", name)

    # Parse compound units like "2x500g" or "3X1.5kg"
    m_multi = RE_MULTI.match(clean_unit)
    m_simple = RE_SIMPLE.match(clean_unit)

    if m_multi:
        total_qty = float(m_multi.group(1)) * float(m_multi.group(2))
        clean_unit = m_multi.group(3)
    elif m_simple:
        total_qty = float(m_simple.group(1))
        clean_unit = m_simple.group(2)

    # --- Weight units ---
    if clean_unit in KG_UNITS:
        return {"price_per_std_unit": _r(p / total_qty), "std_unit": "kg", "audit_required": False}

    if clean_unit in G_UNITS:
        return {"price_per_std_unit": _r(p / (total_qty / 1000)), "std_unit": "kg", "audit_required": False}

    if clean_unit in LB_UNITS:
        return {"price_per_std_unit": _r(p / (total_qty * 0.453592)), "std_unit": "kg", "audit_required": False}

    if clean_unit in OZ_UNITS:
        return {"price_per_std_unit": _r(p / (total_qty * 0.0283495)), "std_unit": "kg", "audit_required": False}

    # --- Metric volume ---
    if clean_unit in L_UNITS:
        return {"price_per_std_unit": _r(p / total_qty), "std_unit": "L", "audit_required": False}

    if clean_unit in ML_UNITS:
        return {"price_per_std_unit": _r(p / (total_qty / 1000)), "std_unit": "L", "audit_required": False}

    # --- Imperial volume (try density conversion to kg) ---
    liters_per_unit = VOLUME_TO_LITERS.get(clean_unit, 0)
    if liters_per_unit > 0:
        total_liters = liters_per_unit * total_qty
        sg = get_specific_gravity(name)
        if sg:
            return {"price_per_std_unit": _r(p / (total_liters * sg)), "std_unit": "kg", "audit_required": False}
        else:
            return {"price_per_std_unit": _r(p / total_liters), "std_unit": "L", "audit_required": True}

    # --- Spoon (volume-based, treated like tbsp/tsp) ---
    if clean_unit in {"spoon", "spoons"}:
        # 1 spoon ≈ 1 tablespoon = 0.0148 L
        total_liters = 0.0148 * total_qty
        sg = get_specific_gravity(name)
        if sg:
            return {"price_per_std_unit": _r(p / (total_liters * sg)), "std_unit": "kg", "audit_required": False}
        else:
            return {"price_per_std_unit": _r(p / total_liters), "std_unit": "L", "audit_required": True}

    # --- Informal / kitchen units → estimated kg ---
    #   half       → 0.075 kg (half an onion, half a lemon, etc.)
    #   piece/whole/slice/个/片/块 → context-dependent estimate by ingredient
    #   clove/sprig/瓣/枝 → 0.005 kg
    #   pinch/dash  → 0.001 kg
    #   zest/peel   → 0.004 kg
    #   to taste/适量 → 0.001 kg
    #   love        → price = 0 (priceless)

    if clean_unit in {"love", "爱"}:
        return {"price_per_std_unit": 0, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"to taste", "to_taste", "tt", "适量", "少许"}:
        kg = 0.001 * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"pinch", "dash", "撮"}:
        kg = 0.001 * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"clove", "cloves", "sprig", "sprigs", "瓣", "枝"}:
        kg = 0.005 * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"zest", "peel", "皮"}:
        kg = 0.004 * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"half", "半", "半个"}:
        kg = 0.075 * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    if clean_unit in {"piece", "pieces", "pcs", "pc", "whole",
                       "slice", "slices", "个", "片", "块", "只", "条", "根"}:
        kg = _estimate_piece_weight(name) * total_qty
        return {"price_per_std_unit": _r(p / kg) if kg else p, "std_unit": "kg", "audit_required": False}

    # --- Unrecognized unit ---
    return {"price_per_std_unit": p, "std_unit": u_str, "audit_required": True}


def _estimate_piece_weight(name: str) -> float:
    """
    Estimate weight per piece/slice based on ingredient type.
    Returns kg per piece.
    """
    n = name.lower()

    # Eggs
    if any(k in n for k in ["egg", "蛋", "鸡蛋", "鸭蛋"]):
        return 0.060

    # Bread
    if any(k in n for k in ["bread", "bun", "brioche", "toast", "面包", "吐司", "包"]):
        return 0.080

    # Cheese (slice)
    if any(k in n for k in ["cheese", "芝士", "奶酪", "起司"]):
        return 0.020

    # Garlic (clove-like when counted as piece)
    if any(k in n for k in ["garlic", "蒜", "大蒜"]):
        return 0.010

    # Onion, lemon, lime, tomato, potato — medium whole
    if any(k in n for k in ["onion", "洋葱", "lemon", "柠檬", "lime", "青柠",
                             "tomato", "番茄", "potato", "土豆", "马铃薯"]):
        return 0.150

    # Carrot, zucchini, cucumber
    if any(k in n for k in ["carrot", "胡萝卜", "zucchini", "西葫芦", "cucumber", "黄瓜"]):
        return 0.180

    # Chicken breast, thigh
    if any(k in n for k in ["chicken breast", "鸡胸", "chicken thigh", "鸡腿"]):
        return 0.200

    # Shrimp / prawn (per piece)
    if any(k in n for k in ["shrimp", "prawn", "虾"]):
        return 0.015

    # Scallop
    if any(k in n for k in ["scallop", "扇贝"]):
        return 0.025

    # Default: 0.100 kg per piece (conservative middle ground)
    return 0.100


def _r(val: float) -> float:
    """Round to 2 decimal places."""
    return round(val, 2)


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    data = json.loads(raw)

    # Support single object or array
    if isinstance(data, dict):
        items = [data]
    elif isinstance(data, list):
        items = data
    else:
        print(json.dumps({"error": "Input must be a JSON object or array"}))
        sys.exit(1)

    results = []
    for item in items:
        result = normalize_unit(
            price=item.get("price", 0),
            unit=item.get("unit", ""),
            name=item.get("name", "")
        )
        result["input_name"] = item.get("name", "")
        result["input_unit"] = item.get("unit", "")
        result["input_price"] = item.get("price", 0)
        results.append(result)

    if len(results) == 1:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

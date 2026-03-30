#!/usr/bin/env python3
"""
MiseMode Cost Calculator
Deterministic cost calculation — no LLM involved, pure math.
Supports sub-recipes (recursive cost calculation).

Usage:
    python3 calc_cost.py --dish "Wagyu Burger"
    python3 calc_cost.py --all
    python3 calc_cost.py --suggest-price "Wagyu Burger" --target-fc 30
    python3 calc_cost.py --report
    echo "Wagyu Burger" | python3 calc_cost.py

Output: JSON cost breakdown with per-ingredient line costs and totals.
"""

import json
import sys
from pathlib import Path
from datetime import date

DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_ingredient_map(ingredients: list) -> dict:
    return {ing["id"]: ing for ing in ingredients}


def build_menu_map(menu: list) -> dict:
    return {dish["id"]: dish for dish in menu}


def true_cost(price: float, yield_pct: float) -> float:
    """True Cost = Price / Yield%. If yield is 0 or missing, use price as-is."""
    if not yield_pct or yield_pct <= 0:
        return price
    return price / yield_pct


def calc_dish_cost(dish_id: str, bom: list, ing_map: dict, menu_map: dict,
                   _visited: set | None = None) -> dict:
    """
    Calculate cost breakdown for a single dish.
    Supports sub-recipes: if ingredient_id matches a dish_id in menu_map,
    recursively calculate that dish's cost first.
    """
    if _visited is None:
        _visited = set()

    # Circular reference protection
    if dish_id in _visited:
        return {"lines": [], "total_cost": 0, "missing_price": [],
                "error": f"Circular reference detected: {dish_id}"}
    _visited.add(dish_id)

    lines = []
    total = 0.0
    missing = []

    dish_bom = [b for b in bom if b["menu_item_id"] == dish_id]

    for entry in dish_bom:
        ing_id = entry["ingredient_id"]
        qty = float(entry.get("qty", 0))

        # Check if this "ingredient" is actually a sub-recipe (another dish)
        if ing_id in menu_map and ing_id not in ing_map:
            sub_cost = calc_dish_cost(ing_id, bom, ing_map, menu_map, _visited.copy())
            sub_total = sub_cost["total_cost"]
            # Sub-recipe cost per unit = its total cost (for 1 batch)
            # qty here means how many batches of the sub-recipe are used
            line_cost = round(qty * sub_total, 2)
            total += line_cost

            sub_name = menu_map[ing_id]["name"]
            lines.append({
                "ingredient": f"[Sub] {sub_name}",
                "qty": qty,
                "unit": "batch",
                "price_per_unit": round(sub_total, 2),
                "yield_pct": 1.0,
                "true_cost_per_unit": round(sub_total, 2),
                "line_cost": line_cost,
                "status": "sub_recipe",
                "sub_detail": sub_cost["lines"]
            })
            missing.extend(sub_cost["missing_price"])
            continue

        ing = ing_map.get(ing_id)

        if not ing:
            lines.append({
                "ingredient": f"[UNKNOWN: {ing_id}]",
                "qty": qty,
                "unit": entry.get("unit", "?"),
                "price_per_unit": 0,
                "yield_pct": 1.0,
                "true_cost_per_unit": 0,
                "line_cost": 0,
                "status": "missing"
            })
            missing.append(ing_id)
            continue

        price = float(ing.get("price", 0))
        yld = float(ing.get("yield_pct", 1.0))
        tc = true_cost(price, yld)
        line_cost = round(qty * tc, 2)
        total += line_cost

        status = "ok"
        if price == 0:
            status = "no_price"
            missing.append(ing.get("name", ing_id))

        lines.append({
            "ingredient": ing.get("name", ing_id),
            "qty": qty,
            "unit": ing.get("unit", entry.get("unit", "?")),
            "price_per_unit": round(price, 2),
            "yield_pct": yld,
            "true_cost_per_unit": round(tc, 2),
            "line_cost": line_cost,
            "status": status
        })

    return {
        "lines": lines,
        "total_cost": round(total, 2),
        "missing_price": missing
    }


def calc_servings(dish_id: str, bom: list, ing_map: dict, menu_map: dict) -> dict:
    """
    Calculate how many servings of a dish can be made with current stock.
    Bottleneck ingredient determines the limit.
    """
    dish_bom = [b for b in bom if b["menu_item_id"] == dish_id]
    if not dish_bom:
        return {"servings": 0, "bottleneck": None, "details": [], "error": "No BOM found"}

    details = []
    min_servings = float("inf")
    bottleneck = None

    for entry in dish_bom:
        ing_id = entry["ingredient_id"]
        bom_qty = float(entry.get("qty", 0))

        if bom_qty <= 0:
            continue

        # Sub-recipe: check if it's a dish
        if ing_id in menu_map and ing_id not in ing_map:
            # For sub-recipes, check sub-recipe's own bottleneck
            sub = calc_servings(ing_id, bom, ing_map, menu_map)
            # How many batches of sub-recipe can we make?
            sub_batches = sub["servings"]
            # This dish needs `bom_qty` batches per serving
            possible = int(sub_batches / bom_qty) if bom_qty > 0 else 0
            details.append({
                "ingredient": f"[Sub] {menu_map[ing_id]['name']}",
                "stock": sub_batches,
                "unit": "batches",
                "need_per_serving": bom_qty,
                "possible_servings": possible,
                "is_bottleneck": False
            })
            if possible < min_servings:
                min_servings = possible
                bottleneck = f"[Sub] {menu_map[ing_id]['name']}"
            continue

        ing = ing_map.get(ing_id)
        if not ing:
            details.append({
                "ingredient": f"[UNKNOWN: {ing_id}]",
                "stock": 0, "unit": "?",
                "need_per_serving": bom_qty,
                "possible_servings": 0,
                "is_bottleneck": False
            })
            min_servings = 0
            bottleneck = f"[UNKNOWN: {ing_id}]"
            continue

        stock = float(ing.get("current_stock", 0))
        possible = int(stock / bom_qty) if bom_qty > 0 else 0

        details.append({
            "ingredient": ing.get("name", ing_id),
            "stock": stock,
            "unit": ing.get("unit", "?"),
            "need_per_serving": bom_qty,
            "possible_servings": possible,
            "is_bottleneck": False
        })

        if possible < min_servings:
            min_servings = possible
            bottleneck = ing.get("name", ing_id)

    # Mark bottleneck(s)
    if min_servings == float("inf"):
        min_servings = 0
    for d in details:
        if d["possible_servings"] == min_servings:
            d["is_bottleneck"] = True

    return {
        "servings": min_servings,
        "bottleneck": bottleneck,
        "details": details
    }


def find_dishes(menu: list, name: str) -> list:
    """Find dishes by name (exact then fuzzy)."""
    exact = [d for d in menu if d["name"].lower() == name.lower()]
    if exact:
        return exact
    return [d for d in menu if name.lower() in d["name"].lower()]


def build_results(dishes: list, bom: list, ing_map: dict, menu_map: dict) -> list:
    results = []
    for dish in dishes:
        cost = calc_dish_cost(dish["id"], bom, ing_map, menu_map)
        sp = dish.get("selling_price", 0) or 0
        results.append({
            "dish_name": dish["name"],
            "dish_id": dish["id"],
            "selling_price": sp,
            "category": dish.get("category", ""),
            "total_cost": cost["total_cost"],
            "profit": round(sp - cost["total_cost"], 2) if sp else None,
            "margin_pct": round((1 - cost["total_cost"] / sp) * 100, 1) if sp else None,
            "fc_pct": round(cost["total_cost"] / sp * 100, 1) if sp else None,
            "lines": cost["lines"],
            "missing_price": cost["missing_price"]
        })
    return results


def generate_report(results: list) -> str:
    """Generate a markdown report."""
    today = date.today().isoformat()
    lines = [
        f"# MiseMode Cost Report",
        f"Generated: {today}",
        "",
        "## Menu Summary",
        "",
        "| # | Dish | Food Cost | Sell Price | Profit | FC% | Margin% | Status |",
        "|---|------|-----------|------------|--------|-----|---------|--------|",
    ]

    for i, r in enumerate(results, 1):
        sp = f"${r['selling_price']:.2f}" if r['selling_price'] else "—"
        profit = f"${r['profit']:.2f}" if r['profit'] is not None else "—"
        fc = f"{r['fc_pct']}%" if r['fc_pct'] is not None else "—"
        margin = f"{r['margin_pct']}%" if r['margin_pct'] is not None else "—"

        status = "✅"
        if r['missing_price']:
            status = "⚠️ incomplete"
        elif r['fc_pct'] and r['fc_pct'] > 35:
            status = "⚠️ high FC"
        elif not r['selling_price']:
            status = "⚠️ no price"

        lines.append(f"| {i} | {r['dish_name']} | ${r['total_cost']:.2f} | {sp} | {profit} | {fc} | {margin} | {status} |")

    # Per-dish detail
    for r in results:
        lines.append("")
        lines.append(f"### {r['dish_name']}")
        if r['selling_price']:
            lines.append(f"Selling Price: ${r['selling_price']:.2f} | Food Cost: ${r['total_cost']:.2f} | FC%: {r['fc_pct']}% | Margin: {r['margin_pct']}%")
        lines.append("")
        lines.append("| Ingredient | Qty | Unit | $/Unit | Yield | True Cost | Line Cost |")
        lines.append("|------------|-----|------|--------|-------|-----------|-----------|")
        for line in r['lines']:
            yld = f"{line['yield_pct']*100:.0f}%" if line['yield_pct'] != 1.0 else "100%"
            lines.append(
                f"| {line['ingredient']} | {line['qty']:.3f} | {line['unit']} | "
                f"${line['price_per_unit']:.2f} | {yld} | ${line['true_cost_per_unit']:.2f} | "
                f"${line['line_cost']:.2f} |"
            )
        lines.append(f"| | | | | | **Total** | **${r['total_cost']:.2f}** |")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MiseMode Cost Calculator")
    parser.add_argument("--dish", type=str, help="Dish name to calculate cost for")
    parser.add_argument("--all", action="store_true", help="Calculate cost for all dishes")
    parser.add_argument("--suggest-price", type=str, help="Suggest selling price for a dish")
    parser.add_argument("--target-fc", type=float, default=30, help="Target food cost %% (default: 30)")
    parser.add_argument("--report", action="store_true", help="Generate markdown report for all dishes")
    parser.add_argument("--servings", type=str, help="Calculate possible servings for a dish based on current stock")
    parser.add_argument("--servings-all", action="store_true", help="Calculate possible servings for all dishes")
    args = parser.parse_args()

    ingredients = load_json("ingredients.json")
    menu = load_json("menu.json")
    bom = load_json("bom.json")
    ing_map = build_ingredient_map(ingredients)
    menu_map = build_menu_map(menu)

    # --- Servings mode ---
    if args.servings or args.servings_all:
        if args.servings_all:
            target = menu
        else:
            target = find_dishes(menu, args.servings)
            if not target:
                print(json.dumps({"error": f"Dish not found: {args.servings}"}))
                sys.exit(1)

        results = []
        for dish in target:
            sv = calc_servings(dish["id"], bom, ing_map, menu_map)
            results.append({
                "dish_name": dish["name"],
                "dish_id": dish["id"],
                "possible_servings": sv["servings"],
                "bottleneck": sv["bottleneck"],
                "details": sv["details"]
            })

        out = results[0] if len(results) == 1 else results
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    # --- Suggest price mode ---
    if args.suggest_price:
        dishes = find_dishes(menu, args.suggest_price)
        if not dishes:
            print(json.dumps({"error": f"Dish not found: {args.suggest_price}"}))
            sys.exit(1)
        results = []
        for dish in dishes:
            cost = calc_dish_cost(dish["id"], bom, ing_map, menu_map)
            tc = cost["total_cost"]
            target = args.target_fc / 100
            suggested = round(tc / target, 2) if target > 0 else 0
            results.append({
                "dish_name": dish["name"],
                "food_cost": tc,
                "target_fc_pct": args.target_fc,
                "suggested_price": suggested,
                "current_price": dish.get("selling_price", 0),
                "missing_price": cost["missing_price"]
            })
        out = results[0] if len(results) == 1 else results
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    # --- Report mode ---
    if args.report:
        results = build_results(menu, bom, ing_map, menu_map)
        report = generate_report(results)
        report_dir = DATA_DIR / "reports"
        report_dir.mkdir(exist_ok=True)
        report_path = report_dir / f"{date.today().isoformat()}-cost-report.md"
        report_path.write_text(report, encoding="utf-8")
        print(json.dumps({
            "report_path": str(report_path),
            "dishes_count": len(results),
            "generated": date.today().isoformat()
        }))
        return

    # --- Standard cost calculation ---
    if args.all:
        target_dishes = menu
    elif args.dish:
        target_dishes = find_dishes(menu, args.dish)
        if not target_dishes:
            print(json.dumps({"error": f"Dish not found: {args.dish}"}))
            sys.exit(1)
    else:
        dish_name = sys.stdin.read().strip()
        if not dish_name:
            print(json.dumps({"error": "No dish specified. Use --dish, --all, or pipe via stdin."}))
            sys.exit(1)
        target_dishes = find_dishes(menu, dish_name)
        if not target_dishes:
            print(json.dumps({"error": f"Dish not found: {dish_name}"}))
            sys.exit(1)

    results = build_results(target_dishes, bom, ing_map, menu_map)

    if len(results) == 1:
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

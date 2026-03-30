#!/usr/bin/env python3
"""
MiseMode Category Detective
Ported from chef_brain_v15_1_complete.js detectCategory_()

Deterministic ingredient classification using keyword matching.
Supports English + Chinese.

Usage:
    echo '["Wagyu Beef", "Olive Oil", "三文鱼"]' | python3 detect_category.py
    echo '"chicken breast"' | python3 detect_category.py

Output: JSON with category for each ingredient name.
"""

import json
import re
import sys

# Category rules — order matters (first match wins)
CATEGORY_RULES = [
    {
        "category": "Seasoning & Oils",
        "pattern": re.compile(
            r"oil|sauce|vinegar|salt|sugar|syrup|honey|spice|pepper|curry|ketchup|mayo|miso|"
            r"paste|dressing|stock|broth|vanilla|cinnamon|msg|marinade|mustard|wasabi|"
            r"soy|sesame|chili flake|paprika|cumin|turmeric|oregano|thyme|rosemary|bay leaf|"
            r"油|酱|醋|盐|糖|蜂蜜|香料|胡椒|番茄酱|味噌|酱汁|高汤|肉汤|香草|肉桂|味精|芥末|酱油",
            re.IGNORECASE
        )
    },
    {
        "category": "Beverages",
        "pattern": re.compile(
            r"water|soda|juice|drink|beer|wine|alcohol|coffee|tea|latte|coke|cola|pepsi|sprite|"
            r"lemonade|cocktail|sparkling|tonic|kombucha|fanta|"
            r"水|苏打|果汁|饮料|啤酒|葡萄酒|咖啡|茶|可乐|雪碧|柠檬水|鸡尾酒",
            re.IGNORECASE
        )
    },
    {
        "category": "Dairy & Eggs",
        "pattern": re.compile(
            r"milk|cream|cheese|yogurt|egg|cheddar|mozzarella|parmesan|feta|ricotta|"
            r"ice cream|butter|mascarpone|brie|camembert|gruyere|gouda|burrata|stracciatella|"
            r"牛奶|奶油|奶酪|酸奶|蛋|鸡蛋|切达|马苏里拉|帕尔马|羊乳酪|冰淇淋|黄油|芝士",
            re.IGNORECASE
        )
    },
    {
        "category": "Meat",
        "pattern": re.compile(
            r"beef|pork|chicken|lamb|duck|turkey|meat|steak|wagyu|bacon|ham|sausage|chorizo|"
            r"salami|burger|meatball|liver|veal|venison|rabbit|short rib|ribeye|tenderloin|"
            r"prosciutto|pancetta|foie gras|"
            r"牛肉|猪肉|鸡肉|羊肉|鸭肉|火鸡|肉|牛排|和牛|培根|火腿|香肠|汉堡|肉丸|肝|鹅肝|猪扒",
            re.IGNORECASE
        )
    },
    {
        "category": "Seafood",
        "pattern": re.compile(
            r"fish|salmon|tuna|shrimp|prawn|crab|lobster|scallop|clam|oyster|squid|octopus|"
            r"cod|sushi|sashimi|mussel|anchovy|sardine|sea bass|turbot|halibut|snapper|"
            r"bacalhau|calamari|"
            r"鱼|三文鱼|金枪鱼|虾|对虾|蟹|龙虾|扇贝|蛤|牡蛎|鱿鱼|章鱼|鳕鱼|寿司|刺身|多宝鱼|鲈鱼|马介休|馬介休",
            re.IGNORECASE
        )
    },
    {
        "category": "Produce",
        "pattern": re.compile(
            r"onion|tomato|potato|garlic|ginger|carrot|lettuce|cabbage|spinach|kale|"
            r"mushroom|cucumber|chili|corn|broccoli|bean|celery|asparagus|eggplant|"
            r"zucchini|pumpkin|avocado|basil|parsley|cilantro|mint|scallion|leek|"
            r"lemon|lime|orange|apple|banana|berry|grape|melon|fruit|vegetable|salad|"
            r"arugula|radish|fennel|artichoke|palm|truffle|shallot|"
            r"洋葱|番茄|土豆|大蒜|姜|胡萝卜|生菜|卷心菜|菠菜|蘑菇|黄瓜|辣椒|"
            r"玉米|西兰花|豆|芹菜|芦笋|茄子|西葫芦|南瓜|牛油果|罗勒|欧芹|香菜|"
            r"薄荷|葱|韭葱|柠檬|青柠|橙子|苹果|香蕉|浆果|葡萄|瓜|水果|蔬菜|沙拉",
            re.IGNORECASE
        )
    },
    {
        "category": "Dry Goods & Grocery",
        "pattern": re.compile(r".*")  # fallback — matches everything
    }
]


def detect_category(name: str) -> str:
    """Classify an ingredient by name using keyword matching."""
    for rule in CATEGORY_RULES:
        if rule["pattern"].search(name):
            # Skip the fallback rule if we haven't matched yet
            if rule["category"] == "Dry Goods & Grocery":
                return rule["category"]
            return rule["category"]
    return "Dry Goods & Grocery"


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    data = json.loads(raw)

    if isinstance(data, str):
        print(json.dumps({"name": data, "category": detect_category(data)}, ensure_ascii=False))
    elif isinstance(data, list):
        results = [{"name": n, "category": detect_category(n)} for n in data]
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"error": "Input must be a string or array of strings"}))
        sys.exit(1)


if __name__ == "__main__":
    main()

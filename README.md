# MiseMode — AI Food Cost Agent

An AI-powered food cost calculator for restaurant operators. No app to download, no account to create — open a folder, talk to AI, get results.

> "I spent a year building a restaurant SaaS. Nobody used it. Then I replaced it with a folder."

## What It Does

Send a photo of your **invoice** — ingredient database built automatically.
Send a photo of your **recipe** — cost breakdown calculated instantly.
Say **"和牛出成率 65%"** — true cost recalculated across all affected dishes.

**True Cost = Price ÷ Yield%**. Most restaurants calculate purchase price, not usable cost. A $300/kg beef with 65% yield actually costs $461.54/kg. This is the #1 reason restaurants miscalculate food cost.

## How It Works

This folder is the product. `CLAUDE.md` defines all behavior. The AI client (Claude Code, Cursor, or any AI IDE) is the runtime.

```
misemode_chefkan/
├── CLAUDE.md              # The agent's brain — all 11 flows defined here
├── data/
│   ├── ingredients.json   # Ingredient database (price, yield%, stock)
│   ├── menu.json          # Menu items (cost, selling price, margin)
│   ├── bom.json           # Bill of Materials (recipes)
│   ├── density.json       # Density reference for volume→weight conversion
│   ├── price_history.json # Price change tracking
│   └── examples/          # Sample data to try it out
└── scripts/
    ├── calc_cost.py       # Cost calculation engine (supports sub-recipes)
    ├── normalize_unit.py  # Unit conversion (kg/g/lb/oz/L/ml/box/gallon...)
    └── detect_category.py # Auto-categorization (EN + CN)
```

**LLM handles**: understanding, extraction, fuzzy matching, language detection.
**Scripts handle**: all math — unit conversion, cost calculation, yield adjustment. Deterministic, auditable, no hallucination.

## Quick Start

```bash
git clone https://github.com/chefkannofriend-source/misemode_chefkan && cd misemode_chefkan
```

That's it. No dependencies to install. Open the folder in [Claude Code](https://claude.ai/code) or any AI IDE that reads `CLAUDE.md`, then send an invoice photo or Excel — your ingredient database builds itself.

To try with sample data:
```bash
cp data/examples/*.json data/
python3 scripts/calc_cost.py --all
```

## 11 Flows

| # | Flow | Trigger |
|---|------|---------|
| 1 | Invoice → Build Ingredient DB | Send invoice/Excel/CSV with prices |
| 2 | Recipe → Cost Calculation | Send recipe photo/text |
| 3 | Set Yield% | "出成率", "yield" |
| 4 | Menu Cost Overview | "所有菜的成本", "menu overview" |
| 5 | Audit & Batch Fix | "缺什么信息", "check missing" |
| 6 | Sub-Recipe | "子配方", "sub recipe" |
| 7 | Suggest Selling Price | "建议售价", "suggest price" |
| 8 | Price History | "价格历史", "price history" |
| 9 | Inventory Check + Servings | "库存", "还能卖几份" |
| 10 | Sales Backflush (POS) | Send POS report, "今天卖了..." |
| 11 | Generate Report | "生成报告", "report" |

## Key Features

- **Photo → Database**: Invoice photo or Excel → ingredient database in seconds
- **True Cost**: Price ÷ Yield% — the cost metric professionals use
- **Sub-Recipes**: Sauces, stocks, bases — recursive cost calculation
- **Unit Conversion**: kg, g, lb, oz, L, ml, gallon, box(15kg), 箱(10kg), pieces, spoons...
- **Bilingual**: Chinese + English, auto-detected
- **Sales Backflush**: POS data → auto stock deduction → anomaly detection (ghost food, over-portioning)
- **Servings Calculator**: How many servings can you make? Bottleneck ingredient identified
- **Price Tracking**: Detect price changes across invoices, alert affected dishes

## Requirements

- Python 3.9+
- An AI client that reads CLAUDE.md (Claude Code, Cursor, etc.)

## Philosophy

- **Folder as product**: No server, no database, no deployment
- **AI as runtime**: The AI client executes the flows defined in CLAUDE.md
- **Scripts for math**: LLM never does arithmetic — all calculation is deterministic Python
- **Zero friction**: No signup, no onboarding — send an invoice and start

## License

MIT

## Author

**Chef Kan** — 18 years in the restaurant industry. Built this to solve my own problem.

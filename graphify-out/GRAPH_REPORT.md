# Graph Report - personal-finance  (2026-10-13)

## Corpus Check
- Corpus is ~8,747 words - fits in a single context window. You may not need a graph.

## Summary
- 261 nodes · 468 edges · 11 communities (9 shown, 2 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Budget Projection Engine
- Hub Investment Metrics
- Hub UI & App Shell
- Investment Strategies
- Hub Data Store
- README & Project Ideas
- Metrics Tests
- Earning Rate Model
- Preprocessing Stubs
- Project Package

## God Nodes (most connected - your core abstractions)
1. `BudgetCalculator` - 14 edges
2. `MortgageStrategy` - 13 edges
3. `PresellingStrategy` - 13 edges
4. `period_result()` - 10 edges
5. `HousingStrategy` - 10 edges
6. `RentStrategy` - 10 edges
7. `Finance Hub` - 10 edges
8. `_ts()` - 9 edges
9. `annualized_return()` - 9 edges
10. `InvestmentStrategy` - 9 edges

## Surprising Connections (you probably didn't know these)
- `FinancialStrategy` --uses--> `InvestmentStrategy`  [INFERRED]
  src/BudgetCalculator.py → src/investment.py
- `main()` --uses--> `RiskAdjustedStrategy`  [INFERRED]
  src/BudgetCalculator.py → src/investment.py
- `run_financial_projection()` --calls--> `RiskAdjustedStrategy`  [INFERRED]
  src/BudgetCalculator.py → src/investment.py
- `FinancialStrategy` --uses--> `HousingStrategy`  [INFERRED]
  src/BudgetCalculator.py → src/housing.py
- `BudgetCalculator` --uses--> `MortgageStrategy`  [INFERRED]
  src/BudgetCalculator.py → src/housing.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Finance Hub app pages** — readme_earning_rate_page, readme_portfolio_page, readme_checkin_page, readme_settings_page [EXTRACTED 1.00]
- **Common data and visualization stack** — readme_pandas, readme_plotly, readme_matplotlib, readme_streamlit [INFERRED 0.75]
- **Investment tracking project cluster** — readme_finance_hub, readme_portfolio_analyzer, readme_net_worth_tracker [INFERRED 0.65]

## Communities (11 total, 2 thin omitted)

### Community 0 - "Budget Projection Engine"
Cohesion: 0.06
Nodes (25): dataclasses, pandas, BudgetCalculator, FinancialStrategy, main(), run_financial_projection(), DataFrame, Combines housing and investment strategies with allocation rates. (+17 more)

### Community 1 - "Hub Investment Metrics"
Cohesion: 0.09
Nodes (43): DateLike, datetime, DatetimeIndex, account_summary(), account_values(), annualized_return(), _between(), capital_needed() (+35 more)

### Community 2 - "Hub UI & App Shell"
Cohesion: 0.09
Nodes (19): Figure, Finance hub: run with ``uv run streamlit run hub/app.py``., colors(), earning_hero(), end_label(), Money, Formatting, colours and shared widgets for the hub's pages., Dot and label on a line's last point. (+11 more)

### Community 3 - "Investment Strategies"
Cohesion: 0.08
Nodes (20): plotly_express, BasicInvestmentStrategy, InvestmentSimulator, InvestmentStrategy, main(), prepare_comparison_data(), ABC, DataFrame (+12 more)

### Community 4 - "Hub Data Store"
Cohesion: 0.14
Nodes (27): add_transaction(), add_valuations(), is_initialized(), Ledger, load(), load_sample(), load_settings(), _path() (+19 more)

### Community 5 - "README & Project Ideas"
Cohesion: 0.14
Nodes (28): Personal Finance Python Projects README, Budgeting and Expense Tracker, Cash Flow Forecasting Tool, ccxt, Check-in page, Plain CSV/JSON data storage (data/hub, FINANCE_HUB_DATA), Debt Payoff Calculator and Tracker, Earning rate page (+20 more)

### Community 6 - "Metrics Tests"
Cohesion: 0.19
Nodes (8): pytest, frames(), test_annualized_return_accounts_for_deposit_timing(), test_annualized_return_ignores_short_history(), test_monthly_breakdown_earnings_add_up(), test_never_valued_account_is_worth_its_transactions(), test_period_result_splits_contributions_income_and_growth(), test_value_rolls_forward_from_last_valuation()

### Community 7 - "Earning Rate Model"
Cohesion: 0.22
Nodes (5): EarningRate, Series, What the accounts earn per year at their annual ``rates``., An amount earned per year, expressed per unit of time., run_rate()

### Community 8 - "Preprocessing Stubs"
Cohesion: 0.32
Nodes (3): PDFExtractor, PreprocessingStrategy, ABC

## Knowledge Gaps
- **8 isolated node(s):** `personal-finance`, `XIRR (money-weighted return)`, `Plain CSV/JSON data storage (data/hub, FINANCE_HUB_DATA)`, `uv`, `pytest` (+3 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 106 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Are the 4 inferred relationships involving `BudgetCalculator` (e.g. with `MortgageStrategy` and `PresellingStrategy`) actually correct?**
  _`BudgetCalculator` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `MortgageStrategy` (e.g. with `BudgetCalculator` and `main()`) actually correct?**
  _`MortgageStrategy` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `PresellingStrategy` (e.g. with `BudgetCalculator` and `main()`) actually correct?**
  _`PresellingStrategy` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `personal-finance`, `XIRR (money-weighted return)`, `Plain CSV/JSON data storage (data/hub, FINANCE_HUB_DATA)` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Budget Projection Engine` be split into smaller, more focused modules?**
  _Cohesion score 0.062310949788263764 - nodes in this community are weakly interconnected._
- **Should `Hub Investment Metrics` be split into smaller, more focused modules?**
  _Cohesion score 0.08973172987974098 - nodes in this community are weakly interconnected._
- **Should `Hub UI & App Shell` be split into smaller, more focused modules?**
  _Cohesion score 0.08669354838709678 - nodes in this community are weakly interconnected._
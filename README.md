# Personal Finance Python Projects

This repository contains various Python project ideas for managing personal finances. Each project offers a unique scope and set of features to help organize and visualize your financial data.

---

## Finance Hub

A local Streamlit app that tracks your investments and shows how fast your money earns money.

```bash
uv sync
uv run streamlit run hub/app.py
```

On first launch, load the sample portfolio to look around, or start fresh and add your own accounts.

- **Earning rate:** what your money earns per hour, day, month and year, plus a live counter of today's earnings. Shows actual returns against your expectations, cash income from dividends and interest, how much earning power extra monthly investing adds, your freedom number, and which bills your earnings already cover.
- **Portfolio:** value against what you put in, per-account returns (money-weighted, XIRR), and allocation by type and platform.
- **Check-in:** a monthly routine to type in each account's value, plus logging deposits, withdrawals, dividends and interest.
- **Settings:** your accounts and expected returns, pay, expenses, and the bills to track.

Data is stored as plain CSV/JSON in `data/hub/`, which git ignores. Set `FINANCE_HUB_DATA` to store it elsewhere.

**How the numbers work:** deposits and withdrawals are your own money moving in or out. Dividends and interest are earnings paid into the account; if you move them out, log a withdrawal. A valuation is an account's total value on that date, and between valuations the hub estimates value as the last valuation plus anything logged since. Earnings are always the change in value minus your net deposits.

Run the tests with `uv run pytest`.

---

## Project Ideas

### 1. Budgeting and Expense Tracker
**Scope**: Develop a tool to categorize expenses, track spending, and visualize spending patterns.

- **Features**:
  - Import transactions (CSV/Excel) from bank statements.
  - Categorize expenses (e.g., food, rent, entertainment).
  - Set monthly budgets per category.
  - Visualize spending vs. budget using charts.

- **Tech Stack**: `pandas` for data manipulation, `matplotlib`/`Plotly` for visualization.

---

### 2. Net Worth Tracker
**Scope**: Track net worth over time by keeping a record of assets (cash, stocks, properties) and liabilities (loans, mortgages).

- **Features**:
  - Add different types of assets and liabilities.
  - Automatically fetch stock prices for investments.
  - Visualize net worth trends over time.

- **Tech Stack**: `pandas`, `yfinance` for stock data, `Plotly`/`matplotlib` for visualizations.

---

### 3. Housing Costs Calculator
**Scope**: Check feasibility of different housing strategies.

- **Features**:
  - Mortgage vs Preselling vs Rent

- **Tech Stack**: `pandas`, and `plotly` for an interactive interface.

### 4. Automated Envelope Budgeting System
**Scope**: Create a digital envelope budgeting system to allocate budgets to specific “envelopes” (like groceries, rent, savings, etc.).

- **Features**:
  - Virtual envelopes with allocated funds.
  - Automatic adjustments to envelope balances as expenses are added.
  - Track and visualize envelope balance trends.

- **Tech Stack**: SQLite for data storage, `pandas`, and `streamlit` for an interactive interface.

---

### 4. Investment Portfolio Analyzer
**Scope**: Track investments and analyze portfolio performance.

- **Features**:
  - Track various types of investments (stocks, mutual funds, crypto).
  - Calculate performance metrics like ROI, CAGR, and volatility.
  - Diversification analysis and risk assessment.
  - Fetch live data from APIs to keep the portfolio updated.

- **Tech Stack**: `pandas`, `yfinance` or `ccxt` (for crypto), visualization libraries like `matplotlib`/`Plotly`.

---

### 5. Financial Goal Tracker
**Scope**: Define and track financial goals like saving for a vacation, buying a house, or retiring early.

- **Features**:
  - Define goals, set target amounts, and deadlines.
  - Track progress towards each goal.
  - Calculate and suggest monthly savings to stay on track.

- **Tech Stack**: `pandas`, `streamlit` for dashboards, `matplotlib`/`Plotly`.

---

### 6. Debt Payoff Calculator and Tracker
**Scope**: Plan and track debt payoff with simulation options for various payoff methods (e.g., avalanche, snowball).

- **Features**:
  - Track outstanding debts (loans, credit cards).
  - Simulate payoff timelines with interest savings.
  - Visualize progress and compare payoff strategies.

- **Tech Stack**: `pandas`, `matplotlib`/`Plotly` for visualizations.

---

### 7. Cash Flow Forecasting Tool
**Scope**: Predict future cash flow based on income, expenses, and savings goals.

- **Features**:
  - Analyze historical income and spending patterns.
  - Forecast upcoming cash flow.
  - Alerts for upcoming expenses or potential cash shortfalls.

- **Tech Stack**: `pandas` for data analysis, `Prophet` for forecasting, `matplotlib`/`Plotly` for visualizations.

---

## Getting Started

1. Clone the repository.
2. Set up a virtual environment and install dependencies for the project you choose.
3. Refer to individual project folders for further setup and usage instructions.

---

## Contribution

Feel free to contribute additional features or project ideas to expand the repository! Open an issue or submit a pull request.

---

## License

This repository is licensed under the MIT License. See `LICENSE` for details.

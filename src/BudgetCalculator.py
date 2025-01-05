from dataclasses import dataclass

import pandas as pd

from housing import HousingStrategy, MortgageStrategy, PresellingStrategy, RentStrategy
from investment import InvestmentStrategy, RiskAdjustedStrategy
from visualizer import Plots, Print


@dataclass
class FinancialStrategy:
    """Combines housing and investment strategies with allocation rates."""

    housing_strategy: HousingStrategy
    investment_strategy: InvestmentStrategy
    savings_rate: float
    investments_rate: float

    name = "Finance Strategy"

    def __str__(self) -> str:
        return f"{self.name}"

    def __format__(self, format_spec):
        return format(str(self), format_spec)


class BudgetCalculator:
    """Enhanced budget calculator that considers both housing and investment strategies."""

    def __init__(
        self,
        financial_strategy: FinancialStrategy,
        salary: float,
        other_income: float,
        daily_living_expenses: float,
        other_expenses: float,
    ) -> None:
        self.financial_strategy = financial_strategy
        self.salary = salary
        self.other_income = other_income
        self.daily_living_expense = daily_living_expenses
        self.other_expenses = other_expenses

        Print.print_dict("Starting Parameters", self.__dict__)
        print()

    def calculate_total_income(self) -> float:
        return self.salary + self.other_income

    def calculate_budget(self) -> float:
        total_income = self.calculate_total_income()
        housing_cost = self.financial_strategy.housing_strategy.calculate_housing_cost()
        total_expenses = housing_cost + self.daily_living_expense + self.other_expenses
        return total_income - total_expenses

    def increase_income(self, pct: float):
        self.salary += self.salary * pct
        self.other_income += self.other_income * pct

    def increase_expense(self, pct: float):
        self.daily_living_expense += self.daily_living_expense * pct
        self.other_expenses += self.other_expenses * pct

    def calculate_financial_projection(
        self,
        savings: float,
        investments: float,
        liabilities: float,
        months: int,
        income_increase: float,
        expense_increase: float,
        house_value_increase: float,
    ) -> pd.DataFrame:
        start = {
            "savings": savings,
            "investments": investments,
            "liabilities": liabilities,
            "months": months,
            "income_increase": income_increase,
            "expense_increase": expense_increase,
            "house_value_increase": house_value_increase,
        }

        Print.print_dict("Financial Projection Seed", start)
        print()

        net_worth_values = []
        savings_values = []
        liabilities_values = []
        house_values = []
        investments_values = []
        investment_returns = []
        housing_costs = []
        cashflow_values = []

        housing = self.financial_strategy.housing_strategy
        is_owned = isinstance(housing, (MortgageStrategy, PresellingStrategy))
        is_rented = isinstance(housing, RentStrategy)

        for month in range(1, months + 1):
            # Increase income and expenses annually
            if month % 12 == 1 and month > 1:
                self.increase_income(pct=income_increase)
                self.increase_expense(pct=expense_increase)

                # Update house value or rent
                if is_owned:
                    housing.increase_house_value(house_value_increase)
                elif is_rented:
                    housing.increase_rent(expense_increase)

            # Update housing costs
            if isinstance(housing, (MortgageStrategy, PresellingStrategy)):
                housing.set_ammortization()
                housing.set_yearly_cost()

            # Calculate monthly budget
            budget = self.calculate_budget()

            # Calculate investment returns
            investment_return = (
                self.financial_strategy.investment_strategy.calculate_monthly_return(
                    investments
                )
            )
            investments += investment_return

            # Allocate budget
            if budget >= 0:
                savings += budget * self.financial_strategy.savings_rate
                investments += budget * self.financial_strategy.investments_rate
            else:
                # Handle negative budget by drawing from investments
                investments += budget

            # Get house value if applicable
            house_value = housing.house_value if is_owned else 0

            # Record values
            cashflow_values.append(budget)
            investments_values.append(investments)
            investment_returns.append(investment_return)
            savings_values.append(savings)
            liabilities_values.append(liabilities)
            house_values.append(house_value)
            housing_costs.append(housing.calculate_housing_cost())
            net_worth_values.append(savings + investments - liabilities + house_value)

        df = pd.DataFrame(
            {
                "net_worth": net_worth_values,
                "house_value": house_values,
                "housing_cost": housing_costs,
                "cashflow": cashflow_values,
                "investments": investments_values,
                "investment_returns": investment_returns,
                "savings": savings_values,
                "liabilities": liabilities_values,
            },
            index=[i for i in range(1, months + 1)],
        )

        return df

    def analyze_projection(self, projection: pd.DataFrame):
        stats = {
            "duration_months": len(projection),
            "negative_cashflow_months": len(projection[projection.cashflow < 0]),
            "total_investment_returns": projection.investment_returns.sum(),
            "final_net_worth": projection.net_worth.iloc[-1],
            "net_worth_growth": (
                projection.net_worth.iloc[-1] / projection.net_worth.iloc[0] - 1
            )
            * 100,
            "average_monthly_return": projection.investment_returns.mean(),
        }

        Print.print_dict("Financial Projection Analysis", stats)
        print()

        print(
            f"End of Month {stats['duration_months']} Details:",
            projection.iloc[-1],
            sep="\n",
        )
        print(
            f"\nCashflow Distribution:\n{projection.cashflow.value_counts().sort_index()}"
        )
        print(f"\nNegative Value Months:\n{projection[(projection<0).any(axis=1)]}")


def main():
    # Sample parameters
    SALARY = 143000
    OTHER_INCOME = 0
    DAILY_LIVING_EXPENSE = 50000
    OTHER_EXPENSE = 0
    SAVINGS = 1000000
    INVESTMENTS = 4000000
    LIABILITIES = 0
    MONTHS = 360

    # Growth rates
    INCOME_INCREASE = 0.07
    EXPENSE_INCREASE = 0.05
    INVESTMENT_INCREASE = 0.07
    SAVINGS_INCREASE = 0.002
    HOUSE_VALUE_INCREASE = 0.02
    HOUSING_LOAN_INTEREST = 0.07

    # Allocation rates
    SAVINGS_RATE = 0
    INVESTMENTS_RATE = 1

    # Property rates
    PROPERTY_TAX_RATE = 0.02
    MAINTENANCE_COST_RATE = 0.0

    # Create housing strategy (example using mortgage)
    mortgage_strategy = MortgageStrategy(
        house_value=22506000,
        down_payment=22506000 * 0.2,
        loan_term_months=240,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax_rate=PROPERTY_TAX_RATE,
        maintenance_cost_rate=MAINTENANCE_COST_RATE,
    )

    preselling_strategy = PresellingStrategy(
        house_value=22050600,
        preselling_down_payment=2370665.91,
        lump_sum=17644661.35,
        loan_down_payment=17644661.35 * 0.2,
        loan_term_months=240,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax_rate=PROPERTY_TAX_RATE,
        maintenance_cost_rate=MAINTENANCE_COST_RATE,
    )

    rent_strategy = RentStrategy(rent=50000)

    def run_financial_projection(housing_strategy):
        # Create investment strategy (example using risk-adjusted)
        investment_strategy = RiskAdjustedStrategy(
            base_return_rate=0.08,  # 8% base return
            risk_level="moderate",
        )

        # Create combined financial strategy
        financial_strategy = FinancialStrategy(
            housing_strategy=housing_strategy,
            investment_strategy=investment_strategy,
            savings_rate=SAVINGS_RATE,
            investments_rate=INVESTMENTS_RATE,
        )

        # Create calculator instance
        calculator = BudgetCalculator(
            financial_strategy=financial_strategy,
            salary=SALARY,
            other_income=OTHER_INCOME,
            daily_living_expenses=DAILY_LIVING_EXPENSE,
            other_expenses=OTHER_EXPENSE,
        )

        # Calculate projection
        projection = calculator.calculate_financial_projection(
            savings=SAVINGS,
            investments=INVESTMENTS,
            liabilities=LIABILITIES,
            months=MONTHS,
            income_increase=INCOME_INCREASE,
            expense_increase=EXPENSE_INCREASE,
            house_value_increase=HOUSE_VALUE_INCREASE,
        )

        # Analyze results
        calculator.analyze_projection(projection)

        # Plot results
        Plots.plot_net_worth(projection)

    # Example usage
    housing_strategy = MortgageStrategy(
        house_value=22506000,
        down_payment=22506000 * 0.2,
        loan_term_months=240,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax_rate=PROPERTY_TAX_RATE,
        maintenance_cost_rate=MAINTENANCE_COST_RATE,
    )

    run_financial_projection(mortgage_strategy)
    run_financial_projection(preselling_strategy)
    run_financial_projection(rent_strategy)


if __name__ == "__main__":
    main()

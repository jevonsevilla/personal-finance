import pandas as pd

from housing import HousingStrategy, MortgageStrategy, PresellingStrategy, RentStrategy
from visualizer import Plots, Print


class BudgetCalculator:
    """context class for calculating budget and expected net worth."""

    def __init__(
        self,
        housing_strategy: HousingStrategy,
        salary: float,
        other_income: float,
        daily_living_expenses: float,
        other_expenses: float,
        savings_rate: float,
        investments_rate: float,
    ) -> None:
        self.housing_strategy = housing_strategy
        self.salary = salary
        self.other_income = other_income
        self.daily_living_expense = daily_living_expenses
        self.other_expenses = other_expenses
        self.savings_rate = savings_rate
        self.investments_rate = investments_rate

        Print.print_dict("Starting Parameters", self.__dict__)
        print()

    def calculate_total_income(self) -> float:
        return self.salary + self.other_income

    def calculate_budget(self) -> float:
        total_income = self.calculate_total_income()
        housing_cost = self.housing_strategy.calculate_housing_cost()
        total_expenses = housing_cost + self.daily_living_expense + self.other_expenses
        return total_income - total_expenses

    def increase_income(self, pct: float):
        self.salary += self.salary * pct
        self.other_income += self.salary * pct

    def increase_expense(self, pct: float):
        self.daily_living_expense += self.daily_living_expense * pct
        self.other_expenses += self.daily_living_expense * pct

    def calculate_net_worth_series(
        self,
        savings: float,
        investments: float,
        liabilities: float,
        months: int,
        income_increase: float,
        expense_increase: float,
        house_value_increase: float,
        investment_increase: float,
    ) -> pd.DataFrame:
        start = {
            "savings": savings,
            "investments": investments,
            "liabilities": liabilities,
            "months": months,
            "income_increase": income_increase,
            "expense_increase": expense_increase,
            "house_value_increase": house_value_increase,
            "investment_increase": investment_increase,
        }

        Print.print_dict("Generation Seed", start)
        print()

        net_worth_values = []

        savings_values = []
        liabilities_values = []
        house_values = []
        investments_values = []
        housing_costs = []
        cashflow_values = []

        for month in range(1, months + 1):
            # Increase income, expenses and investments annually
            if month % 12 == 1 and month > 1:
                self.increase_income(pct=income_increase)
                self.increase_expense(pct=expense_increase)

                if isinstance(
                    self.housing_strategy, (MortgageStrategy, PresellingStrategy)
                ):
                    self.housing_strategy.increase_house_value(house_value_increase)
                elif isinstance(self.housing_strategy, RentStrategy):
                    self.housing_strategy.increase_rent(expense_increase)

                investments += investments * investment_increase

            if isinstance(
                self.housing_strategy, (MortgageStrategy, PresellingStrategy)
            ):
                self.housing_strategy.set_ammortization()
                self.housing_strategy.set_yearly_cost()

            budget = self.calculate_budget()

            if budget >= 0:
                savings += budget * self.savings_rate
                investments += budget * self.investments_rate
            if budget < 0:
                investments += budget

            house_value = (
                self.housing_strategy.house_value
                if isinstance(
                    self.housing_strategy, (MortgageStrategy, PresellingStrategy)
                )
                else 0
            )

            cashflow_values.append(budget)
            investments_values.append(investments)
            savings_values.append(savings)
            liabilities_values.append(liabilities)
            house_values.append(house_value)
            housing_costs.append(self.housing_strategy.calculate_housing_cost())

            net_worth_values.append(savings + investments - liabilities + house_value)

        df = pd.DataFrame(
            {
                "net_worth": net_worth_values,
                "house_value": house_values,
                "housing_cost": housing_costs,
                "cashflow": cashflow_values,
                "investments": investments_values,
                "savings": savings_values,
                "liabilities": liabilities_values,
            },
            index=[i for i in range(1, month + 1)],
        )

        print(f"End of Month {months}:", df.iloc[-1], sep="\n")
        print(f"\n{df.cashflow.value_counts().sort_index()}")
        print(f"\n{df[(df<0).any(axis=1)]}")

        return df


# Sample usage
def main() -> pd.DataFrame:
    # Inputs
    SALARY = 143000
    OTHER_INCOME = 0
    DAILY_LIVING_EXPENSE = 50000
    OTHER_EXPENSE = 0
    SAVINGS = 1000000
    INVESTMENTS = 4000000
    LIABILITIES = 0
    MONTHS = 360
    INCOME_INCREASE = 0.07
    EXPENSE_INCREASE = 0.06
    INVESTMENT_INCREASE = 0.06
    HOUSE_VALUE_INCREASE = 0.02
    HOUSING_LOAN_INTEREST = 0.09

    SAVINGS_RATE = 0
    INVESTMENTS_RATE = 1

    PROPERTY_TAX_RATE = 0.0
    MAINTENANCE_COST_RATE = 0

    ## Mortgage
    mortgage_house_value = 22506000
    mortgage_lump_sum = mortgage_house_value
    mortgage_down_payment = mortgage_lump_sum * 0.2
    mortgage_loan_term_months = 240

    ## Rent
    rent = 50000

    ## Preselling
    preselling_house_value = 22506000
    interest_free_downpayment = 2370665.91
    preselling_lump_sum = 17644661.35
    # preselling_loan_dp = preselling_lump_sum * 0.2
    preselling_loan_term_months = 240

    # Own with Mortgage
    mortgage_strategy = MortgageStrategy(
        house_value=mortgage_house_value,
        down_payment=mortgage_down_payment,
        loan_term_months=mortgage_loan_term_months,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax_rate=PROPERTY_TAX_RATE,
        maintenance_cost_rate=MAINTENANCE_COST_RATE,
    )

    calculator_own = BudgetCalculator(
        salary=SALARY,
        other_income=OTHER_INCOME,
        other_expenses=OTHER_EXPENSE,
        housing_strategy=mortgage_strategy,
        daily_living_expenses=DAILY_LIVING_EXPENSE,
        savings_rate=SAVINGS_RATE,
        investments_rate=INVESTMENTS_RATE,
    )
    net_worth_own = calculator_own.calculate_net_worth_series(
        savings=SAVINGS,
        investments=INVESTMENTS,
        liabilities=LIABILITIES,
        months=MONTHS,
        income_increase=INCOME_INCREASE,
        expense_increase=EXPENSE_INCREASE,
        house_value_increase=HOUSE_VALUE_INCREASE,
        investment_increase=INVESTMENT_INCREASE,
    )

    Plots.plot_net_worth(cashflow=net_worth_own)

    # Own with Preselling
    preselling_strategy = PresellingStrategy(
        house_value=preselling_house_value,
        preselling_down_payment=interest_free_downpayment,
        lump_sum=preselling_lump_sum,
        loan_down_payment=preselling_lump_sum * 0.2,
        loan_term_months=preselling_loan_term_months,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax_rate=PROPERTY_TAX_RATE,
        maintenance_cost_rate=MAINTENANCE_COST_RATE,
    )

    calculator_preselling = BudgetCalculator(
        salary=SALARY,
        other_income=OTHER_INCOME,
        other_expenses=OTHER_EXPENSE,
        housing_strategy=preselling_strategy,
        daily_living_expenses=DAILY_LIVING_EXPENSE,
        savings_rate=SAVINGS_RATE,
        investments_rate=INVESTMENTS_RATE,
    )

    net_worth_preselling = calculator_preselling.calculate_net_worth_series(
        savings=SAVINGS,
        investments=INVESTMENTS,
        liabilities=LIABILITIES,
        months=MONTHS,
        income_increase=INCOME_INCREASE,
        expense_increase=EXPENSE_INCREASE,
        house_value_increase=HOUSE_VALUE_INCREASE,
        investment_increase=INVESTMENT_INCREASE,
    )

    Plots.plot_net_worth(net_worth_preselling)

    # Rent and Invest
    rent_strategy = RentStrategy(rent=rent)

    calculator_rent = BudgetCalculator(
        salary=SALARY,
        other_income=OTHER_INCOME,
        other_expenses=OTHER_EXPENSE,
        housing_strategy=rent_strategy,
        daily_living_expenses=DAILY_LIVING_EXPENSE,
        savings_rate=SAVINGS_RATE,
        investments_rate=INVESTMENTS_RATE,
    )

    net_worth_rent = calculator_rent.calculate_net_worth_series(
        savings=SAVINGS,
        investments=INVESTMENTS,
        liabilities=LIABILITIES,
        months=MONTHS,
        income_increase=INCOME_INCREASE,
        expense_increase=EXPENSE_INCREASE,
        house_value_increase=HOUSE_VALUE_INCREASE,
        investment_increase=INVESTMENT_INCREASE,
    )

    Plots.plot_net_worth(net_worth_rent)

    return net_worth_preselling


if __name__ == "__main__":
    main()

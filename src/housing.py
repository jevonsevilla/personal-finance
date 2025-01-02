from abc import ABC, abstractmethod

import pandas as pd

from interest import calculate_ammortization_schedule
from visualizer import Visualizer

pd.options.display.float_format = "{:,.2f}".format


class HousingStrategy(ABC):
    @abstractmethod
    def calculate_housing_cost(self) -> float:
        pass


class MortgageStrategy(HousingStrategy):
    """concrete strategy for owning with mortgage."""

    def __init__(
        self,
        house_value: float,
        down_payment: float,
        loan_term_months: int,
        loan_interest_rate: float,
        property_tax: float,
        maintenance_cost: float,
    ) -> None:
        super().__init__()
        self.house_value = house_value
        self.down_payment = down_payment
        self.loan_term_months = loan_term_months
        self.loan_interest_rate = loan_interest_rate
        self.property_tax = property_tax
        self.maintenance_cost = maintenance_cost

        self.month = 0

        print("Using Mortgage Strategy...\n")

    def calculate_housing_cost(self) -> float:
        return self.ammortization + self.property_tax + self.maintenance_cost

    def calculate_yearly_cost(self) -> float:
        return self.property_tax + self.maintenance_cost

    def create_ammortization_schedule(self) -> None:
        self.ammortization_schedule: pd.DataFrame = calculate_ammortization_schedule(
            principal=self.principal,
            annual_rate=self.loan_interest_rate,
            years=self.loan_term_months / 12,
        )

    def set_ammortization(self):
        # Ammortization done
        if self.month > self.loan_term_months:
            self.ammortization = 0
        # Bank Loan (downpayment)
        elif self.month == 0:
            self.ammortization = self.down_payment
            self.principal = self.house_value - self.down_payment

            self.create_ammortization_schedule()
        # Bank Loan (monthly)
        elif self.month > 0:
            self.ammortization = self.ammortization_schedule.monthly_payment[0]

        self.month += 1

    def increase_house_value(self, percentage: float):
        self.house_value += self.house_value * percentage


class PresellingStrategy(HousingStrategy):
    """concrete strategy for owning with preselling."""

    def __init__(
        self,
        house_value: float,
        preselling_down_payment: float,
        lump_sum: float,
        loan_down_payment: float,
        loan_term_months: int,
        loan_interest_rate: float,
        property_tax: float,
        maintenance_cost: float,
    ) -> None:
        self.house_value = house_value
        self.preselling_down_payment = preselling_down_payment
        self.lump_sum = lump_sum
        self.loan_down_payment = loan_down_payment
        self.loan_term_months = loan_term_months
        self.loan_interest_rate = loan_interest_rate
        self.property_tax = property_tax
        self.maintenance_cost = maintenance_cost

        self.month = 0

        print("Using Preselling Strategy...")
        print()

    def calculate_housing_cost(self) -> float:
        return self.ammortization + self.property_tax + self.maintenance_cost

    def calculate_yearly_cost(self) -> float:
        return self.property_tax + self.maintenance_cost

    def create_ammortization_schedule(self) -> None:
        self.ammortization_schedule: pd.DataFrame = calculate_ammortization_schedule(
            principal=self.principal,
            annual_rate=self.loan_interest_rate,
            years=self.loan_term_months / 12,
        )

    def set_ammortization(self):
        # Ammortization done
        if self.month > (60 + self.loan_term_months + 1):
            self.ammortization = 0
        # Preselling (downpayment)
        elif self.month == 0:
            self.ammortization = self.preselling_down_payment
        # Preselling (tiered)
        elif self.month <= 24:
            self.ammortization = 52513.87
        elif self.month <= 48:
            self.ammortization = 73519.42
        elif self.month <= 60:
            self.ammortization = 168044.39
        # Bank Loan (downpayment)
        elif self.month == 61:
            self.ammortization = self.loan_down_payment
            self.principal = self.lump_sum

            self.create_ammortization_schedule()
        # Bank Loan (monthly)
        elif self.month > 61:
            self.ammortization = self.ammortization_schedule.monthly_payment[0]

        self.month += 1

    def increase_house_value(self, percentage: float):
        self.house_value += self.house_value * percentage


class RentStrategy(HousingStrategy):
    """concrete strategy for renting."""

    def __init__(self, rent):
        self.rent = rent
        print("Use Rent and Invest Strategy")
        print()

    def calculate_housing_cost(self) -> float:
        return self.rent

    def increase_rent(self, percentage: float):
        self.rent += self.rent * percentage


class BudgetCalculator:
    """context class for calculating budget and expected net worth."""

    def __init__(
        self,
        salary: float,
        other_income: float,
        housing_strategy: HousingStrategy,
        daily_living_expenses: float,
        other_expenses: float,
        savings_rate: float,
        investments_rate: float,
    ) -> None:
        self.salary = salary
        self.other_income = other_income
        self.housing_strategy = housing_strategy
        self.daily_living_expense = daily_living_expenses
        self.other_expenses = other_expenses
        self.savings_rate = savings_rate
        self.investments_rate = investments_rate

        print("Starting Parameters:")
        for key, value in self.__dict__.items():
            print(f"{key}: {value}")
        print()

    def calculate_total_income(self) -> float:
        return self.salary + self.other_income

    def calculate_budget(self) -> float:
        total_income = self.calculate_total_income()
        housing_cost = self.housing_strategy.calculate_housing_cost()
        total_expenses = housing_cost + self.daily_living_expense + self.other_expenses
        return total_income - total_expenses

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
                self.salary += self.salary * income_increase
                self.other_income += self.other_income * income_increase
                self.daily_living_expense += (
                    self.daily_living_expense * expense_increase
                )
                self.other_expenses += self.other_expenses * expense_increase

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

        print(f"\nEnd of Month {months}:", df.iloc[-1], sep="\n")
        print(f"\n{df.cashflow.value_counts().sort_index()}")
        return df


# Sample usage
def main() -> pd.DataFrame:
    # Inputs
    SALARY = 143000
    OTHER_INCOME = 0
    DAILY_LIVING_EXPENSE = 0
    OTHER_EXPENSE = 0
    SAVINGS = 1000000
    INVESTMENTS = 4000000
    LIABILITIES = 0
    MONTHS = 360
    INCOME_INCREASE = 0.06
    EXPENSE_INCREASE = 0.05
    INVESTMENT_INCREASE = 0.07
    HOUSE_VALUE_INCREASE = 0.02
    HOUSING_LOAN_INTEREST = 0.09

    SAVINGS_RATE = 0
    INVESTMENTS_RATE = 1

    PROPERTY_TAX = 3
    MAINTENANCE_COST = 3

    ## Mortgage
    mortgage_house_value = 23000000
    mortgage_lump_sum = mortgage_house_value
    mortgage_down_payment = mortgage_lump_sum * 0.2
    mortgage_loan_term_months = 240
    mortgage_property_tax = 0
    mortgage_maintenance_cost = 0

    ## Rent
    rent = 50000

    ## Preselling
    preselling_house_value = 22506000
    interest_free_downpayment = 2370665.91
    preselling_lump_sum = 17644661.35
    # preselling_loan_dp = preselling_lump_sum * 0.2
    preselling_loan_term_months = 240
    preselling_property_tax = 0
    preselling_maintenance_cost = 0

    # Own with Mortgage
    mortgage_strategy = MortgageStrategy(
        house_value=mortgage_house_value,
        down_payment=mortgage_down_payment,
        loan_term_months=mortgage_loan_term_months,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax=mortgage_property_tax,
        maintenance_cost=mortgage_maintenance_cost,
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

    Visualizer.plot_net_worth(cashflow=net_worth_own)

    # Own with Preselling
    preselling_strategy = PresellingStrategy(
        house_value=preselling_house_value,
        preselling_down_payment=interest_free_downpayment,
        lump_sum=preselling_lump_sum,
        loan_down_payment=preselling_lump_sum * 0.2,
        loan_term_months=preselling_loan_term_months,
        loan_interest_rate=HOUSING_LOAN_INTEREST,
        property_tax=preselling_property_tax,
        maintenance_cost=preselling_maintenance_cost,
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

    Visualizer.plot_net_worth(net_worth_preselling)

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

    Visualizer.plot_net_worth(net_worth_rent)

    return net_worth_preselling


if __name__ == "__main__":
    test = main()

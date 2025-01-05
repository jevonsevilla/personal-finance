from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from interest import calculate_ammortization_schedule
from visualizer import Print

pd.options.display.float_format = "{:,.2f}".format


class HousingStrategy(ABC):
    """Abstract base class for housing strategies."""

    name = "Default"

    @abstractmethod
    def calculate_housing_cost(self) -> float:
        pass

    def __str__(self) -> str:
        return f"{self.name}"

    def __format__(self, format_spec):
        return format(str(self), format_spec)


@dataclass
class MortgageStrategy(HousingStrategy):
    """Concrete strategy for owning with mortgage."""

    house_value: float
    down_payment: float
    loan_term_months: int
    loan_interest_rate: float
    property_tax_rate: float
    maintenance_cost_rate: float

    # Non-init fields
    month: int = field(init=False, default=0)
    owned: bool = field(init=False, default=True)
    ammortization: float = field(init=False, default=0)
    property_tax: float = field(init=False, default=0)
    maintenance_cost: float = field(init=False, default=0)
    principal: float = field(init=False, default=0)
    ammortization_schedule: Optional[pd.DataFrame] = field(init=False, default=None)

    def __post_init__(self):
        self.name = "Mortgage"
        Print.print_dict("Housing Values", self.__dict__)
        print()

    def calculate_housing_cost(self) -> float:
        return self.ammortization + self.property_tax + self.maintenance_cost

    def set_yearly_cost(self):
        if self.owned:
            self.property_tax = (self.house_value * self.property_tax_rate) / 12
            self.maintenance_cost = (self.house_value * self.maintenance_cost_rate) / 12
        else:
            self.property_tax = 0
            self.maintenance_cost = 0

    def create_ammortization_schedule(self) -> None:
        self.ammortization_schedule = calculate_ammortization_schedule(
            principal=self.principal,
            annual_rate=self.loan_interest_rate,
            years=self.loan_term_months / 12,
        )

    def set_ammortization(self):
        if self.month > self.loan_term_months:
            self.ammortization = 0
        elif self.month == 0:
            self.ammortization = self.down_payment
            self.principal = self.house_value - self.down_payment
            self.create_ammortization_schedule()
            self.owned = True
        elif self.month > 0:
            self.ammortization = self.ammortization_schedule.monthly_payment[0]

        self.month += 1

    def increase_house_value(self, percentage: float):
        self.house_value += self.house_value * percentage


@dataclass
class PresellingStrategy(HousingStrategy):
    """Concrete strategy for owning with preselling."""

    house_value: float
    preselling_down_payment: float
    lump_sum: float
    loan_down_payment: float
    loan_term_months: int
    loan_interest_rate: float
    property_tax_rate: float
    maintenance_cost_rate: float

    # Non-init fields
    month: int = field(init=False, default=0)
    owned: bool = field(init=False, default=False)
    ammortization: float = field(init=False, default=0)
    property_tax: float = field(init=False, default=0)
    maintenance_cost: float = field(init=False, default=0)
    principal: float = field(init=False, default=0)
    ammortization_schedule: Optional[pd.DataFrame] = field(init=False, default=None)

    def __post_init__(self):
        self.name = "Preselling"
        Print.print_dict("Housing Values", self.__dict__)
        print()

    def calculate_housing_cost(self) -> float:
        return self.ammortization + self.property_tax + self.maintenance_cost

    def set_yearly_cost(self):
        if self.owned:
            self.property_tax = (self.house_value * self.property_tax_rate) / 12
            self.maintenance_cost = (self.house_value * self.maintenance_cost_rate) / 12
        else:
            self.property_tax = 0
            self.maintenance_cost = 0

    def create_ammortization_schedule(self) -> None:
        self.ammortization_schedule = calculate_ammortization_schedule(
            principal=self.principal,
            annual_rate=self.loan_interest_rate,
            years=self.loan_term_months / 12,
        )

    def set_ammortization(self):
        if self.month > (60 + self.loan_term_months + 1):
            self.ammortization = 0
        elif self.month == 0:
            self.ammortization = self.preselling_down_payment
        elif self.month <= 24:
            self.ammortization = 52513.87
        elif self.month <= 48:
            self.ammortization = 73519.42
        elif self.month <= 60:
            self.ammortization = 168044.39
        elif self.month == 61:
            self.ammortization = self.loan_down_payment + 1260332.95
            self.principal = self.lump_sum
            self.create_ammortization_schedule()
            self.owned = True
        elif self.month > 61:
            self.ammortization = self.ammortization_schedule.monthly_payment[0]

        self.month += 1

    def increase_house_value(self, percentage: float):
        self.house_value += self.house_value * percentage


@dataclass
class RentStrategy(HousingStrategy):
    """Concrete strategy for renting."""

    rent: float

    def __post_init__(self):
        self.name = "Rent"
        Print.print_dict("Housing Values", self.__dict__)
        print()

    def calculate_housing_cost(self) -> float:
        return self.rent

    def increase_rent(self, percentage: float):
        self.rent += self.rent * percentage


def main():
    # Example values for different strategies

    # Mortgage example - PHP 23000000 house
    mortgage_strategy = MortgageStrategy(
        house_value=22506000.0,
        down_payment=22506000 * 0.2,  # 20% down payment
        loan_term_months=360,  # 30-year mortgage
        loan_interest_rate=0.09,  # 6.5% interest rate
        property_tax_rate=0.02,  # 1% property tax
        maintenance_cost_rate=0.01,  # 1% maintenance cost
    )

    # Preselling example - PHP 450,000 house
    preselling_strategy = PresellingStrategy(
        house_value=22506000.0,
        preselling_down_payment=2370665.91,  # Initial down payment
        lump_sum=17644661.35,  # Amount to be financed
        loan_down_payment=17644661.35 * 0.2,  # Down payment at turnover
        loan_term_months=240,  # 20-year mortgage
        loan_interest_rate=0.09,  # 6.5% interest rate
        property_tax_rate=0.02,  # 1% property tax
        maintenance_cost_rate=0.01,  # 1% maintenance cost
    )

    # Rent example - PHP 2,500 monthly rent
    rent_strategy = RentStrategy(rent=90000.0)

    # Simulate costs for first year (12 months)
    print("\nMonthly costs for first year:")
    print("-" * 50)

    strategies = [mortgage_strategy, preselling_strategy, rent_strategy]

    for month in range(36):
        print(f"\nMonth {month + 1}")
        for strategy in strategies:
            # Update monthly costs
            if isinstance(strategy, (MortgageStrategy, PresellingStrategy)):
                strategy.set_yearly_cost()
                strategy.set_ammortization()

            # Calculate and display monthly cost
            monthly_cost = strategy.calculate_housing_cost()
            print(f"{strategy.name}: PHP {monthly_cost:,.2f}")

    # Simulate property value increase (3% annual appreciation)
    print("\nProperty value after 3% annual appreciation:")
    print("-" * 50)
    for strategy in strategies:
        if isinstance(strategy, (MortgageStrategy, PresellingStrategy)):
            original_value = strategy.house_value
            strategy.increase_house_value(0.03)
            print(
                f"{strategy.name}: PHP {original_value:,.2f} → PHP {strategy.house_value:,.2f}"
            )
        elif isinstance(strategy, RentStrategy):
            original_rent = strategy.rent
            strategy.increase_rent(0.03)
            print(
                f"{strategy.name}: PHP {original_rent:,.2f} → PHP {strategy.rent:,.2f}"
            )


if __name__ == "__main__":
    main()

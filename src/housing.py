from abc import ABC, abstractmethod

import pandas as pd

from interest import calculate_ammortization_schedule

pd.options.display.float_format = "{:,.2f}".format


class HousingStrategy(ABC):
    name = "Default"

    @abstractmethod
    def calculate_housing_cost(self) -> float:
        pass

    def __str__(self) -> str:
        return f"{self.name}"

    def __format__(self, format_spec):
        return format(str(self), format_spec)


class MortgageStrategy(HousingStrategy):
    """concrete strategy for owning with mortgage."""

    def __init__(
        self,
        house_value: float,
        down_payment: float,
        loan_term_months: int,
        loan_interest_rate: float,
        property_tax_rate: float,
        maintenance_cost_rate: float,
    ) -> None:
        super().__init__()
        self.house_value = house_value
        self.down_payment = down_payment
        self.loan_term_months = loan_term_months
        self.loan_interest_rate = loan_interest_rate
        self.property_tax_rate = property_tax_rate
        self.maintenance_cost_rate = maintenance_cost_rate

        self.month = 0
        self.owned = False

        self.name = "Mortgage"

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
            self.owned = True
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
        property_tax_rate: float,
        maintenance_cost_rate: float,
    ) -> None:
        self.house_value = house_value
        self.preselling_down_payment = preselling_down_payment
        self.lump_sum = lump_sum
        self.loan_down_payment = loan_down_payment
        self.loan_term_months = loan_term_months
        self.loan_interest_rate = loan_interest_rate
        self.property_tax_rate = property_tax_rate
        self.maintenance_cost_rate = maintenance_cost_rate

        self.month = 0
        self.owned = False

        self.name = "Preselling"
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
            self.owned = True
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

        self.name = "Rent"
        print()

    def calculate_housing_cost(self) -> float:
        return self.rent

    def increase_rent(self, percentage: float):
        self.rent += self.rent * percentage


# Sample usage
def main():
    # Inputs
    HOUSING_LOAN_INTEREST = 0.09
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

    # Rent and Invest
    rent_strategy = RentStrategy(rent=rent)

    print(mortgage_strategy)
    print(preselling_strategy)
    print(rent_strategy)

    return preselling_strategy


if __name__ == "__main__":
    test = main()

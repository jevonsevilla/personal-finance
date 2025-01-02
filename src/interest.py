import pandas as pd

from visualizer import Print


def calculate_ammortization_schedule(principal, annual_rate, years) -> pd.DataFrame:
    monthly_rate = annual_rate / 12
    total_payments = years * 12
    monthly_payment = (
        principal * monthly_rate / (1 - (1 + monthly_rate) ** -total_payments)
    )

    schedule = []
    cashout = 0
    balance = principal

    for i in range(1, int(total_payments) + 1):
        interest = balance * monthly_rate
        principal_payment = monthly_payment - interest
        balance -= principal_payment

        schedule.append(
            {
                "month": i,
                "monthly_payment": round(monthly_payment, 3),
                "interest": round(interest, 3),
                "principal": round(principal_payment, 3),
                "remaining_balance": round(balance, 3),
            }
        )
        cashout += monthly_payment

    stats = {
        "total principal": principal,
        "total cashout for loan": cashout,
        "monthly payment": monthly_payment,
    }

    Print.print_dict("Bank Loan Details", stats)

    return pd.DataFrame(schedule)


def main():
    principal = 6000000
    annual_rate = 0.09
    years = 20

    schedule = calculate_ammortization_schedule(principal, annual_rate, years)

    return schedule


if __name__ == "__main__":
    schedule = main()

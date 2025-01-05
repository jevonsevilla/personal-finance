# investment_strategy.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict

import pandas as pd
import plotly.express as px


class InvestmentStrategy(ABC):
    """Abstract base class for investment strategies."""

    @abstractmethod
    def calculate_monthly_return(self, current_investment: float) -> float:
        """Calculate monthly return based on current investment amount."""
        pass

    @abstractmethod
    def get_monthly_growth_factor(self) -> float:
        """Get the monthly growth multiplier."""
        pass


@dataclass
class BasicInvestmentStrategy(InvestmentStrategy):
    """Simple investment strategy with fixed annual return rate."""

    annual_return_rate: float

    def __post_init__(self):
        """Convert annual rate to monthly rate using compound interest formula."""
        self.monthly_return_rate = (1 + self.annual_return_rate) ** (1 / 12) - 1

    def calculate_monthly_return(self, current_investment: float) -> float:
        return current_investment * self.monthly_return_rate

    def get_monthly_growth_factor(self) -> float:
        return 1 + self.monthly_return_rate


@dataclass
class RiskAdjustedStrategy(InvestmentStrategy):
    """Investment strategy that considers risk levels and adjusts returns accordingly."""

    base_return_rate: float
    risk_level: str  # 'conservative', 'moderate', or 'aggressive'

    def __post_init__(self):
        risk_multipliers = {"conservative": 0.7, "moderate": 1.0, "aggressive": 1.3}
        adjusted_rate = self.base_return_rate * risk_multipliers[self.risk_level]
        self.monthly_return_rate = (1 + adjusted_rate) ** (1 / 12) - 1

    def calculate_monthly_return(self, current_investment: float) -> float:
        return current_investment * self.monthly_return_rate

    def get_monthly_growth_factor(self) -> float:
        return 1 + self.monthly_return_rate


class InvestmentSimulator:
    """Simulator for running investment scenarios."""

    def __init__(self, initial_investment: float, strategy: InvestmentStrategy):
        self.initial_investment = initial_investment
        self.strategy = strategy

    def simulate_growth(
        self, months: int, monthly_contribution: float = 0
    ) -> pd.DataFrame:
        """Simulate investment growth over time with optional monthly contributions."""
        investment_value = self.initial_investment
        values = []
        returns = []
        contributions = []
        total_invested = self.initial_investment

        for month in range(months):
            # Calculate return before adding new contribution
            monthly_return = self.strategy.calculate_monthly_return(investment_value)
            investment_value += monthly_return

            # Add monthly contribution
            investment_value += monthly_contribution
            total_invested += monthly_contribution

            values.append(investment_value)
            returns.append(monthly_return)
            contributions.append(total_invested)

        return pd.DataFrame(
            {
                "total_value": values,
                "monthly_return": returns,
                "total_contributed": contributions,
            },
            index=range(1, months + 1),
        )

    def plot_growth(self, df: pd.DataFrame, title: str = "Investment Growth Over Time"):
        """Plot the investment growth over time using Plotly Express."""
        # Prepare data for plotting
        plot_df = df.reset_index()
        plot_df.columns = [
            "Month",
            "Total Value",
            "Monthly Return",
            "Total Contributed",
        ]

        fig = px.line(
            plot_df,
            x="Month",
            y=["Total Value", "Total Contributed"],
            title=title,
            labels={"value": "Value (PHP)", "variable": "Metric"},
            template="plotly_white",
        )

        # Customize the layout
        fig.update_layout(
            hovermode="x unified",
            legend_title_text="",
            xaxis_title="Month",
            yaxis_title="Value (PHP)",
            showlegend=True,
        )

        return fig


def prepare_comparison_data(results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Prepare data for strategy comparison visualization."""
    comparison_data = []

    for strategy_name, df in results.items():
        temp_df = df.reset_index()
        temp_df["Strategy"] = strategy_name
        temp_df.columns = [
            "Month",
            "Total Value",
            "Monthly Return",
            "Total Contributed",
            "Strategy",
        ]
        comparison_data.append(temp_df)

    return pd.concat(comparison_data, axis=0)


def main():
    # Example usage with different strategies
    print("Investment Growth Simulation\n")

    # Basic strategy example
    basic_strategy = BasicInvestmentStrategy(
        annual_return_rate=0.07
    )  # 8% annual return
    basic_simulator = InvestmentSimulator(
        initial_investment=10000, strategy=basic_strategy
    )

    # Risk-adjusted strategy examples
    conservative_strategy = RiskAdjustedStrategy(
        base_return_rate=0.07, risk_level="conservative"
    )
    moderate_strategy = RiskAdjustedStrategy(
        base_return_rate=0.07, risk_level="moderate"
    )
    aggressive_strategy = RiskAdjustedStrategy(
        base_return_rate=0.07, risk_level="aggressive"
    )

    # Simulate different scenarios

    scenarios = {
        "Basic 8% Return": basic_strategy,
        "Conservative": conservative_strategy,
        "Moderate": moderate_strategy,
        "Aggressive": aggressive_strategy,
    }

    results = {}
    for name, strategy in scenarios.items():
        simulator = InvestmentSimulator(initial_investment=10000, strategy=strategy)
        results[name] = simulator.simulate_growth(
            months=120,  # 10 years
            monthly_contribution=500,
        )

        final_value = results[name]["total_value"].iloc[-1]
        total_contributed = results[name]["total_contributed"].iloc[-1]
        total_return = final_value - total_contributed

        print(f"\n{name} Strategy Results:")
        print(f"Final Value: PHP{final_value:,.2f}")
        print(f"Total Contributed: PHP{total_contributed:,.2f}")
        print(f"Total Return: PHP{total_return:,.2f}")
        print(f"Return Percentage: {(total_return/total_contributed)*100:.1f}%")

    # Create comparison visualization
    comparison_df = prepare_comparison_data(results)
    fig = px.line(
        comparison_df,
        x="Month",
        y="Total Value",
        color="Strategy",
        title="Investment Strategy Comparison",
        labels={"Total Value": "Value (PHP)"},
        template="plotly_white",
    )

    fig.update_layout(
        hovermode="x unified",
        legend_title_text="Strategy",
        xaxis_title="Month",
        yaxis_title="Value (PHP)",
        showlegend=True,
    )

    # Show the plot
    fig.show()


if __name__ == "__main__":
    main()

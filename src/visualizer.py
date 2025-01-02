import plotly.express as px


class Visualizer:
    """class to visualize results."""

    @staticmethod
    def plot_net_worth(cashflow) -> None:
        plt = px.line(
            cashflow,
            y=["net_worth", "investments", "house_value", "housing_cost", "cashflow"],
        )
        plt.update_layout(
            title="Finance Timeline",
            xaxis_title="month",
            yaxis_title="pesos",
            hovermode="x unified",  # Ensures that hover information for the same x is shown for both traces
        )
        plt.show()

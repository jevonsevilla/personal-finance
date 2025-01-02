import plotly.express as px


class Plots:
    """class to plot results."""

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


class Print:
    """class to print text."""

    @staticmethod
    def print_dict(title: str, stats: dict) -> None:
        max_key_width = max(len(key) for key in stats.keys())

        print(f"{title}:")
        for key, (value) in stats.items():
            try:
                print(f"{key:{max_key_width}} : {value:{15},.2f}")
            except ValueError:
                print(f"{key:{max_key_width}} : {str(value):>{15}}")

    # @staticmethod
    # def print_arguments(func):
    #     def wrapper(*args, **kwargs):
    #         print(f"Calling {func.__name__}")
    #         Print.print_dict("Func Name", kwargs)

    #     return wrapper

"""Formatting, colours and shared widgets for the hub's pages."""

import json
import math
import uuid
from dataclasses import dataclass

import plotly.graph_objects as go
import streamlit as st

# Validated data-viz palette, stepped separately for each theme.
_COLORS = {
    "light": {
        "accent": "#2a78d6",
        "second": "#eb6834",
        "negative": "#e34948",
        "context": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
    },
    "dark": {
        "accent": "#3987e5",
        "second": "#d95926",
        "negative": "#e66767",
        "context": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
    },
}


def colors() -> dict[str, str]:
    return _COLORS[st.context.theme.type or "light"]


def wash(hex_color: str, alpha: float = 0.1) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


@dataclass(frozen=True)
class Money:
    """Formats amounts in the user's currency."""

    symbol: str

    def __call__(self, value: float, decimals: int = 0, signed: bool = False) -> str:
        sign = "−" if value < 0 else ("+" if signed and value > 0 else "")
        return f"{sign}{self.symbol}{abs(value):,.{decimals}f}"

    def compact(self, value: float) -> str:
        sign = "−" if value < 0 else ""
        for size, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
            if abs(value) >= size:
                return f"{sign}{self.symbol}{abs(value) / size:,.1f}{suffix}"
        return self(value)


def pct(rate: float | None, decimals: int = 1) -> str:
    return "—" if rate is None else f"{rate * 100:.{decimals}f}%"


def duration(months: int | None) -> str:
    if months is None:
        return "over 100 years"
    years, rem = divmod(months, 12)
    if not years:
        return f"{rem} month{'s' * (rem != 1)}"
    return f"{years + rem / 12:.1f} years"


def earning_hero(per_day: float, per_second: float, caption: str, money: Money) -> None:
    """The page's lead number, plus a counter of what's been earned so far today."""
    uid = f"hub-ticker-{uuid.uuid4().hex}"
    # Enough decimals that the counter visibly moves every second.
    decimals = min(4, max(2, math.ceil(-math.log10(abs(per_second))) + 1)) if per_second else 2
    st.html(
        f"""
        <style>
          .hub-hero {{ padding: 0.25rem 0 0.5rem; line-height: 1.15; }}
          .hub-hero .label {{ font-size: 1rem; opacity: 0.75; }}
          .hub-hero .value {{ font-size: clamp(3rem, 9vw, 4.5rem); font-weight: 700; margin: 0.15rem 0; }}
          .hub-hero .unit {{ font-size: 1.5rem; font-weight: 500; opacity: 0.75; }}
          .hub-hero .ticker {{ font-size: 1.15rem; margin-top: 0.35rem; }}
          .hub-hero .ticker span {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
          .hub-hero .caption {{ font-size: 0.9rem; opacity: 0.65; margin-top: 0.35rem; }}
        </style>
        <div class="hub-hero">
          <div class="label">Your money is earning</div>
          <div class="value">{money(per_day)} <span class="unit">per day</span></div>
          <div class="ticker"><span id="{uid}">{money(0, decimals)}</span> earned so far today</div>
          <div class="caption">{caption}</div>
        </div>
        <script>
          (() => {{
            const el = document.getElementById("{uid}");
            if (!el) return;
            const perDay = {per_day!r};
            const symbol = {json.dumps(money.symbol)};
            const fmt = new Intl.NumberFormat("en-US", {{
              minimumFractionDigits: {decimals}, maximumFractionDigits: {decimals},
            }});
            const tick = () => {{
              if (!el.isConnected) return clearInterval(timer);
              const now = new Date();
              const midnight = new Date(now).setHours(0, 0, 0, 0);
              const earned = perDay * (now - midnight) / 86400000;
              el.textContent = (earned < 0 ? "−" : "") + symbol + fmt.format(Math.abs(earned));
            }};
            const timer = setInterval(tick, 100);
            tick();
          }})();
        </script>
        """,
        unsafe_allow_javascript=True,
    )


def style_chart(fig: go.Figure, money: Money, height: int = 320) -> go.Figure:
    c = colors()
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=8, t=8, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor=c["axis"], ticks="")
    fig.update_yaxes(
        gridcolor=c["grid"],
        gridwidth=1,
        zeroline=True,
        zerolinecolor=c["axis"],
        zerolinewidth=1,
        tickprefix=money.symbol,
        tickformat="~s",
    )
    return fig


def end_label(
    fig: go.Figure, x, y, text: str, color: str, position: str = "top left"
) -> None:
    """Dot and label on a line's last point."""
    fig.add_trace(
        go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            marker=dict(size=9, color=color),
            text=[text],
            textposition=position,
            cliponaxis=False,
            hoverinfo="skip",
            showlegend=False,
        )
    )


def show_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, config={"displayModeBar": False})

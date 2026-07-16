#!/usr/bin/env python3
"""Draft exhibits from data already in the repo (proof-of-feasibility figures).

Figure D1: AWS on-demand USD/GPU-hr, us-east-1, monthly effective prices
           (primary source: AWS Price List Bulk API — data/processed/).
Figure D2: AKT market capitalization (Coin Metrics) with AKT emission-regime
           change dates from the hand-collected governance table.

Output: exhibits/figD1_aws_gpu_price.png, exhibits/figD2_akt_regimes.png
These are working exhibits for the paper's Figure 1/2 slots; final versions
add the Akash price series once the executed-lease/snapshot data lands.
"""

import csv
import os
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
OUT = os.path.join(HERE, "..", "exhibits")
os.makedirs(OUT, exist_ok=True)

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e8e7e3"
SERIES = {"H100-80GB": "#2a78d6", "A100-40GB": "#008300", "A100-80GB": "#e87ba4", "H200": "#eda100"}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "text.color": INK, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10,
})


def fig_d1():
    rows = list(csv.DictReader(open(os.path.join(DATA, "processed", "aws_gpu_benchmark_monthly.csv"))))
    keep = {"p5.48xlarge": "H100-80GB", "p4d.24xlarge": "A100-40GB",
            "p4de.24xlarge": "A100-80GB", "p5en.48xlarge": "H200"}
    series = {}
    for r in rows:
        cls = keep.get(r["instance_type"])
        if cls:
            d = date(int(r["month"][:4]), int(r["month"][5:7]), 1)
            series.setdefault(cls, []).append((d, float(r["price_usd_per_gpu_hr"])))

    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150)
    for cls, pts in series.items():
        pts.sort()
        xs, ys = zip(*pts)
        ax.step(xs, ys, where="post", color=SERIES[cls], linewidth=2, label=cls)
        ax.annotate(f"{cls}  ${ys[-1]:.2f}", xy=(xs[-1], ys[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
    cut = date(2025, 6, 1)
    ax.axvline(cut, color=INK2, linewidth=0.8, linestyle=(0, (4, 3)))
    ax.annotate("AWS price cut, June 2025\n(−25% to −44%)", xy=(cut, 9.3), xytext=(-8, 0),
                textcoords="offset points", ha="right", fontsize=9, color=INK2)
    ax.set_ylabel("USD per GPU-hour (on-demand, us-east-1)", color=INK2)
    ax.set_ylim(0, 13.5)
    ax.set_xlim(date(2022, 12, 1), date(2027, 4, 1))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Hyperscaler GPU pricing is a step function: flat 29 months, one cut",
                 loc="left", fontsize=11, color=INK, pad=12)
    fig.text(0.01, 0.01, "Source: AWS Price List Bulk API, monthly offer versions (per-GPU = instance price ÷ 8; bundled CPU/RAM biases level up)",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(OUT, "figD1_aws_gpu_price.png"))
    plt.close(fig)


def fig_d2():
    # Coin Metrics CapMrktEstUSD has corrupt near-zero values in a few early-2021
    # windows (documented in CODEBOOK) — drop implausible caps below $1M.
    rows = [r for r in csv.DictReader(open(os.path.join(DATA, "processed", "akt_market_daily.csv")))
            if r["market_cap_usd"] and float(r["market_cap_usd"]) >= 1e6]
    xs = [date.fromisoformat(r["date"]) for r in rows]
    ys = [float(r["market_cap_usd"]) / 1e6 for r in rows]

    events = [  # (date, label, label row: 0 = high, 1 = low — staggered to avoid collisions)
        (date(2023, 7, 27), "Prop 211\nmin 5→8%", 0),
        (date(2024, 1, 7), "Props 240/241\n13–20%", 1),
        (date(2024, 8, 8), "Prop 265\n8–13%", 0),
        (date(2025, 3, 14), "Prop 283\n4–8%", 1),
        (date(2026, 3, 23), "BME: usage\nburns AKT", 0),
    ]

    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=150)
    ax.plot(xs, ys, color=SERIES["H100-80GB"], linewidth=2)
    ax.set_yscale("log")
    ax.set_ylim(8, 9000)
    for d, label, row in events:
        ax.axvline(d, color=INK2, linewidth=0.8, linestyle=(0, (4, 3)))
        ax.annotate(label, xy=(d, 9000), xytext=(3, -6 - row * 26), textcoords="offset points",
                    va="top", fontsize=7.5, color=INK2)
    ax.set_ylabel("AKT market capitalization, USD millions (log scale)", color=INK2)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Token value vs. emission-regime changes: the H2 identification setting",
                 loc="left", fontsize=11, color=INK, pad=12)
    fig.text(0.01, 0.01, "Sources: Coin Metrics community data (market cap, daily); regime dates hand-collected from Akash governance records",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(OUT, "figD2_akt_regimes.png"))
    plt.close(fig)


if __name__ == "__main__":
    fig_d1()
    fig_d2()
    print("wrote exhibits to", OUT)

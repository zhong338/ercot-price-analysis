"""
cQuant / Zema Global - Energy Analyst Programming Exercise
============================================================
Solution in Python (pandas). One script, end-to-end.

HOW TO RUN:
    1. Point INPUT_DIR at the folder holding the ERCOT_DA_Prices_*.csv files.
    2. Outputs are written to OUTPUT_DIR (created automatically).
    3. python main.py

All system-specific parameters live in the CONFIG block directly below so an
evaluator can re-point paths without hunting through the code.
"""

# ----------------------------------------------------------------------------
# CONFIG  (the only things an evaluator should ever need to change)
# ----------------------------------------------------------------------------
import os

INPUT_DIR  = "/mnt/user-data/uploads"          # where the historical CSVs live
OUTPUT_DIR = "/home/claude/output"             # everything we produce goes here

# ----------------------------------------------------------------------------
# IMPORTS
# ----------------------------------------------------------------------------
import glob
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")                          # non-interactive backend (no display needed)
import matplotlib.pyplot as plt

# Create the output directory and the two required subfolders up front.
os.makedirs(OUTPUT_DIR, exist_ok=True)
FORMATTED_DIR = os.path.join(OUTPUT_DIR, "formattedSpotHistory")
PROFILES_DIR  = os.path.join(OUTPUT_DIR, "hourlyShapeProfiles")
os.makedirs(FORMATTED_DIR, exist_ok=True)
os.makedirs(PROFILES_DIR, exist_ok=True)


# ============================================================================
# TASK 1 - Read every historical file and combine into one tidy data frame.
# ============================================================================
# The four yearly files share the schema: Date, SettlementPoint, Price.
# We read them all, stack them, and parse Date into a real datetime ONCE so
# every later task can pull Year/Month/Hour from it cheaply.
price_files = sorted(glob.glob(os.path.join(INPUT_DIR, "ERCOT_DA_Prices_*.csv")))
df = pd.concat((pd.read_csv(f) for f in price_files), ignore_index=True)

df["Date"]  = pd.to_datetime(df["Date"])       # "2016-01-01 00:00:00" -> datetime64
df["Year"]  = df["Date"].dt.year
df["Month"] = df["Date"].dt.month
df["Hour"]  = df["Date"].dt.hour               # 0..23, hour-BEGINNING convention

# Sanity checks (printed so we can eyeball that Task 1 actually worked).
print("TASK 1  rows: {:,} | points: {} | dates: {} -> {}".format(
    len(df), df["SettlementPoint"].nunique(),
    df["Date"].min().date(), df["Date"].max().date()))


# ============================================================================
# TASK 2 - Average price per settlement point per year-month. DO NOT filter
#          out non-positive prices: negatives are real in power markets.
# ============================================================================
monthly_avg = (
    df.groupby(["SettlementPoint", "Year", "Month"], as_index=False)["Price"]
      .mean()
      .rename(columns={"Price": "AveragePrice"})
)

# ============================================================================
# TASK 3 - Write it out with EXACTLY these four columns, in this order.
# ============================================================================
monthly_avg[["SettlementPoint", "Year", "Month", "AveragePrice"]].to_csv(
    os.path.join(OUTPUT_DIR, "AveragePriceByMonth.csv"), index=False)
print("TASK 2/3  monthly rows: {} (note: < 15*48 because HB_PAN is partial)".format(len(monthly_avg)))


# ============================================================================
# TASK 4 - Hourly price volatility = std dev of hourly LOG RETURNS,
#          per HUB (HB_) per year. Load zones (LZ_) are excluded.
#          Filter to strictly positive prices first: ln() needs P > 0.
# ============================================================================
hubs = df[df["SettlementPoint"].str.startswith("HB_")].copy()
hubs = hubs[hubs["Price"] > 0]                 # drop <=0 BEFORE taking logs

vol_rows = []
for (point, year), g in hubs.groupby(["SettlementPoint", "Year"]):
    g = g.sort_values("Date")                  # returns must be in time order
    log_returns = np.log(g["Price"]).diff()    # r_t = ln(P_t) - ln(P_{t-1})
    vol = log_returns.std()                     # sample std dev (ddof=1)
    vol_rows.append({"SettlementPoint": point, "Year": year, "HourlyVolatility": vol})

volatility = pd.DataFrame(vol_rows)

# ============================================================================
# TASK 5 - Write volatilities. Column names are case-sensitive.
# ============================================================================
volatility[["SettlementPoint", "Year", "HourlyVolatility"]].to_csv(
    os.path.join(OUTPUT_DIR, "HourlyVolatilityByYear.csv"), index=False)
print("TASK 4/5  volatility rows: {}".format(len(volatility)))

# ============================================================================
# TASK 6 - For each year, the hub with the highest volatility.
# ============================================================================
idx = volatility.groupby("Year")["HourlyVolatility"].idxmax()
max_vol = volatility.loc[idx, ["SettlementPoint", "Year", "HourlyVolatility"]]
max_vol.to_csv(os.path.join(OUTPUT_DIR, "MaxVolatilityByYear.csv"), index=False)
print("TASK 6  most volatile hub per year:")
print(max_vol.to_string(index=False))


# ============================================================================
# TASK 7 - Reshape to the cQuant wide format: one file per settlement point.
#          Columns: Variable, Date(day), X1..X24 where X1 = hour beginning
#          00:00 (hour-beginning convention => X(h+1) holds hour h).
# ============================================================================
df["Day"]    = df["Date"].dt.normalize()                       # midnight of that day
df["XCol"]   = "X" + (df["Hour"] + 1).astype(str)              # hour 0 -> X1, hour 23 -> X24
x_order = [f"X{i}" for i in range(1, 25)]                      # keep columns ordered X1..X24

for point, g in df.groupby("SettlementPoint"):
    wide = g.pivot_table(index="Day", columns="XCol", values="Price", aggfunc="mean")
    wide = wide.reindex(columns=x_order)                       # enforce X1..X24 order; DST gap -> NaN
    wide = wide.reset_index().rename(columns={"Day": "Date"})
    wide["Variable"] = point
    wide["Date"] = wide["Date"].dt.strftime("%Y-%m-%d")        # YYYY-MM-DD like the templates
    wide = wide[["Variable", "Date"] + x_order]                # exact template column order
    wide.to_csv(os.path.join(FORMATTED_DIR, f"spot_{point}.csv"), index=False)
print("TASK 7  wrote {} files to formattedSpotHistory/".format(df["SettlementPoint"].nunique()))


# ============================================================================
# BONUS - Mean plots (hubs / zones), monthly averages over time.
# ============================================================================
# Build a real first-of-month date so the x-axis is chronological, per the hint.
monthly_avg["PlotDate"] = pd.to_datetime(
    dict(year=monthly_avg["Year"], month=monthly_avg["Month"], day=1))

def plot_group(prefix, title, fname):
    sub = monthly_avg[monthly_avg["SettlementPoint"].str.startswith(prefix)]
    fig, ax = plt.subplots(figsize=(13, 6))
    for point, gp in sub.groupby("SettlementPoint"):
        gp = gp.sort_values("PlotDate")
        ax.plot(gp["PlotDate"], gp["AveragePrice"], label=point, linewidth=1.4)
    ax.set_title(title); ax.set_xlabel("Month"); ax.set_ylabel("Avg Price ($/MWh)")
    ax.legend(ncol=2, fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUTPUT_DIR, fname), dpi=120); plt.close(fig)

plot_group("HB_", "Settlement Hub - Monthly Average Price", "SettlementHubAveragePriceByMonth.png")
plot_group("LZ_", "Load Zone - Monthly Average Price",      "LoadZoneAveragePriceByMonth.png")
print("BONUS  wrote two mean-plot PNGs")

# ============================================================================
# BONUS - Volatility comparison across hubs by year (grouped bar chart).
# ============================================================================
pivot_vol = volatility.pivot(index="SettlementPoint", columns="Year", values="HourlyVolatility")
fig, ax = plt.subplots(figsize=(12, 6))
pivot_vol.plot(kind="bar", ax=ax, width=0.8)
ax.set_title("Hourly Volatility by Hub and Year")
ax.set_xlabel("Settlement Hub"); ax.set_ylabel("Hourly Volatility (std of log returns)")
ax.legend(title="Year"); ax.grid(alpha=0.3, axis="y")
fig.tight_layout(); fig.savefig(os.path.join(OUTPUT_DIR, "VolatilityByHubYear.png"), dpi=120)
plt.close(fig)
print("BONUS  wrote volatility bar chart")

# ============================================================================
# BONUS - Normalized hourly shape profiles: per point, 12 months x 7 weekdays
#          = 84 profiles of 24 hours each, normalized so each averages to 1.0.
# ============================================================================
df["DOW"] = df["Date"].dt.dayofweek            # 0=Mon .. 6=Sun

for point, g in df.groupby("SettlementPoint"):
    # Average price for each (month, weekday, hour) cell.
    cell = g.groupby(["Month", "DOW", "Hour"])["Price"].mean().reset_index()
    # Reshape so each row is one (month, weekday) profile across 24 hour columns.
    prof = cell.pivot_table(index=["Month", "DOW"], columns="Hour", values="Price")
    # Normalize each row so its 24 values average to exactly 1.0.
    prof = prof.div(prof.mean(axis=1), axis=0)
    prof.columns = [f"X{h+1}" for h in prof.columns]   # X1..X24
    prof = prof.reset_index()
    prof.to_csv(os.path.join(PROFILES_DIR, f"profile_{point}.csv"), index=False)
print("BONUS  wrote {} hourly-shape-profile files".format(df["SettlementPoint"].nunique()))

print("\nDONE. All outputs in:", OUTPUT_DIR)

# Energy Analyst Programming Exercise — ERCOT Power Price Analysis

Solution to the cQuant / Zema Global energy analyst exercise. Reads four years of
hourly ERCOT day-ahead settlement prices (2016–2019) and produces monthly average
prices, hourly price volatility, cQuant model-ready spot files, normalized hourly
shape profiles, and supporting plots.

## Requirements
- Python 3.9+
- pandas, numpy, matplotlib

```bash
pip install pandas numpy matplotlib
```

## How to run
1. Open `main.py` and set the two paths in the CONFIG block at the top:
   - `INPUT_DIR`  — folder containing the `ERCOT_DA_Prices_*.csv` files
   - `OUTPUT_DIR` — where results are written (created automatically)
2. Run:
   ```bash
   python main.py
   ```

## Repository structure
```
.
├── main.py                       # single end-to-end script
├── README.md
├── .gitignore
├── historicalPriceData/          # input: ERCOT_DA_Prices_2016..2019.csv
└── output/                       # all generated deliverables
    ├── AveragePriceByMonth.csv
    ├── HourlyVolatilityByYear.csv
    ├── MaxVolatilityByYear.csv
    ├── SettlementHubAveragePriceByMonth.png
    ├── LoadZoneAveragePriceByMonth.png
    ├── VolatilityByHubYear.png
    ├── formattedSpotHistory/     # 15 spot_<Point>.csv files (wide, model-ready)
    └── hourlyShapeProfiles/      # 15 profile_<Point>.csv files (84 profiles each)
```

## Outputs
- **AveragePriceByMonth.csv** (Tasks 2–3): monthly average price per settlement point. Non-positive prices retained.
- **HourlyVolatilityByYear.csv** (Tasks 4–5): std dev of hourly log returns, per hub per year.
- **MaxVolatilityByYear.csv** (Task 6): the most volatile hub each year.
- **formattedSpotHistory/** (Task 7): one wide-format file per point — `Variable, Date, X1..X24` (hour-beginning).
- **hourlyShapeProfiles/** (Bonus): per point, 12×7 = 84 normalized 24-hour profiles, each averaging exactly 1.0.
- **\*.png** (Bonus): monthly-average line plots and a volatility comparison bar chart.

## Methodology notes
- Negative prices are kept for monthly averages (they are real in deregulated markets) and filtered to `> 0` only before log returns, since `ln` requires positive values.
- Volatility uses the sample standard deviation (`ddof=1`) of hourly log returns, computed within each hub-year.
- `HB_PAN` only appears from 2019-04-06; the code makes no assumption that every point spans all four years.
- DST spring-forward days (e.g. 2016-03-13) contain 23 hours; the missing hour is left blank in the wide format rather than interpolated.

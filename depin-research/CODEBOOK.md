# Codebook (running — master-doc prep rule 7)

Becomes the data section + replication appendix. One row per variable:
variable, unit, source, transformation.

## `data/processed/aws_gpu_benchmark_monthly.csv`

| Variable | Unit | Source | Transformation |
|---|---|---|---|
| `month` | YYYY-MM (UTC) | AWS offer `versionEffectiveBeginDate` | truncated to month; AWS publishes ~1 version/month with an explicit effective range |
| `instance_type` | — | AWS Price List | filter to p4d/p4de/p5/p5e/p5en/p6-b200 |
| `gpu_model` | — | mapping in `pull_aws_gpu_pricing.py` | p5→H100-80GB, p4d→A100-40GB, p4de→A100-80GB, p5e/p5en→H200, p6-b200→B200 |
| `gpu_count` | GPUs/instance | AWS instance spec | constant 8 for all included types |
| `price_usd_per_instance_hr` | USD/hr | AWS Price List `pricePerUnit.USD` | filtered: Linux, preInstalledSw=NA, tenancy=Shared, capacitystatus=Used, OnDemand, unit=Hrs, price>0 |
| `price_usd_per_gpu_hr` | USD/GPU-hr | derived | instance price ÷ 8. **Bias note (master doc):** bundled CPU/RAM/NVMe/EFA means this OVERSTATES the pure-GPU price → biases the DePIN gap upward; state in Methods |

Known events in series: single price cut 2025-06 (p5 −44.0%, p4d/p4de −33.0%,
p5en −25.4%); prices flat 2023-01→2025-05 and 2025-06→2026-07.

## `data/processed/akt_market_daily.csv`

| Variable | Unit | Source | Transformation |
|---|---|---|---|
| `date` | YYYY-MM-DD UTC | Coin Metrics community | none |
| `market_cap_usd` | USD | `CapMrktEstUSD` | none (estimated/forward-filled supply basis per CM docs) |
| `volume_usd` | USD/day | `volume_reported_spot_usd_1d` | reported spot volume — liquidity control only, not load-bearing |
| `price_usd` | USD | `ReferenceRateUSD` | **trailing week only** — full series arrives via `pull_akt_usd.py` (CoinGecko) |

## `data/raw/coingecko/akt_usd_daily.csv` (after user-machine pull)

| Variable | Unit | Source | Transformation |
|---|---|---|---|
| `price_usd`, `market_cap_usd`, `volume_usd` | USD | CoinGecko market_chart, daily, UTC last-obs | none |
| `implied_supply_akt` | AKT | derived | market_cap ÷ price; validate ≥1 week vs chain supply before use |
| `net_issuance_akt` | AKT/day | derived | Δ implied_supply; NET of BME burns after 2026-03-23 |

## `data/raw/akash/emissions_incentives_table.csv`

| Variable | Unit | Source | Transformation |
|---|---|---|---|
| `date_effective` | YYYY-MM-DD | governance discussions / on-chain props | hand-collected; VERIFY flags noted per row |
| `inflation_{min,max}_{before,after}` | fraction/yr | proposal texts | mint-module BOUNDS, not realized emissions |
| `community_tax_{before,after}` | fraction | proposal texts | share of block rewards to community pool |

## `data/processed/panel_daily.csv` (assembled by `build_panel.py`)

| Variable | Unit | Notes |
|---|---|---|
| `date` | YYYY-MM-DD UTC | missing days logged to `panel_missing_days.txt`, never filled |
| `platform` | — | `aws-ondemand`, `akash` (spot + executed-lease platforms to be added) |
| `gpu_class` | — | comparable-hardware key (H100-80GB, A100-40GB/80GB, H200, B200) |
| `price_usd_per_gpu_hr` | USD/GPU-hr | see `price_kind` |
| `price_kind` | — | `posted-ondemand` (AWS), `posted-ask-weightedavg` (Akash gpu-prices), later `executed-median` (Numia/indexer — the master-doc aggregation rule) and `spot` (AWS, needs authed account) |

## Outstanding variables (blocked here, scripted for user machine)

- Akash executed-lease median USD/GPU-hr by class (Numia BigQuery / indexer).
- AWS spot per-GPU-hr (authed `DescribeSpotPriceHistory`, 90-day rolling — start
  archiving now, or license a third-party spot history).
- Provider `audited` flag joined to leases (H3).
- Realized daily AKT emissions from chain (`/cosmos/mint/v1beta1/*` or Numia).

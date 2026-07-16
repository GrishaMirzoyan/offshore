# Akash emissions & incentives — hand-collected table (H2 input)

Companion to `data/raw/akash/emissions_incentives_table.csv`. Collected 2026-07-16
from GitHub governance discussions (primary drafts of on-chain proposals) and
secondary coverage. Rows marked VERIFY need an on-chain cross-check (Mintscan /
Polkachu / Numia) — those hosts were unreachable from the collection environment.

## Parameter regime timeline (mint module bounds)

| Effective | Prop | Inflation min | Inflation max | Community tax | Note |
|-----------|------|--------------|---------------|---------------|------|
| genesis → 2023-07 | — | 5% | 15% | 10% | pre-GPU era |
| 2023-07-27 | 211 | **8%** | 15% | **25%** | GPU-marketplace incentive funding |
| 2024-01-07 | 240/241 | **13%** | **20%** | **40%** | peak-emissions regime |
| 2024-08-08 | 265 | **8%** | **13%** | 40% | first cut; tax hike dropped in redraft |
| 2025-03-14* | 283 | **4%** | **8%** | 40% | *submission date — VERIFY effective date |
| 2026-03-23 | 318 (or 257 — reconcile) | — | — | — | BME (AEP-76): usage burns AKT |

## Why this matters for H2

- Realized inflation moves **within** [min, max] as a function of the bonded
  ratio (standard Cosmos mint module) — the table gives regime bounds, not the
  emission path. The daily realized-emissions series should be built from
  implied circulating supply (`pull_akt_usd.py` derives it) and validated
  against chain supply for at least one overlapping week.
- Secondary sources quote realized annualized inflation of 8.12% (Q4 2025) and
  8.94% (Q1 2026, Messari). 8.94% exceeding the 8% Prop-283 cap is suspicious —
  possibly a different measurement basis (supply growth vs mint rate). Flagged;
  do not use secondary inflation numbers in the regression.
- The five regime dates give clean candidate break points / instruments:
  emissions changes that are *not* driven by contemporaneous compute demand.
- BME (2026-03-23) reverses the sign of the mechanism: after activation,
  deployment spend *burns* AKT (Messari: 53,520 AKT burned 2026-03-23→31,
  ≈5,950/day; later coverage cites ≈14,395/day 7-day net). H2's
  emission-subsidy channel is therefore regime-dependent — worth one sentence
  in the paper, and it makes the pre/post-BME contrast a bonus test.

## Provider-side incentive programs (funded from community pool)

Prop 211's stated purpose includes provider/tenant incentives for the GPU
marketplace. Specific program disbursements (e.g., provider incentive pilots)
are NOT yet collected — they sit in individual community-pool spend proposals.
TODO (user machine): enumerate community-pool spend proposals on Mintscan or
via Numia SQL and hand-code the GPU-provider-incentive subset with amounts and
dates. These are direct subsidy payments and belong in H2 alongside emissions.

## Sources

- Prop 211 draft: https://github.com/orgs/akash-network/discussions/272
- Props 240/241 draft: https://github.com/orgs/akash-network/discussions/424
- Prop 265 draft: https://github.com/orgs/akash-network/discussions/641
- AEP-76 / BME: https://github.com/orgs/akash-network/discussions/1034 and https://akash.network/roadmap/aep-76/
- Messari State of Akash Q1 2025 (Prop 283): https://messari.io/report/state-of-akash-q1-2025
- Grey-lit rule (master doc): these cite what actors SAID; the dataset is the price evidence.

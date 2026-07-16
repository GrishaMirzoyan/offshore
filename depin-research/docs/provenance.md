# Provenance log — raw layer

Master-doc prep rule 1: raw layer untouched; every file listed with source,
endpoint, and pull date. All timestamps UTC.

| File | Source | Endpoint / URL | Pulled | Coverage | Notes |
|---|---|---|---|---|---|
| `data/raw/aws/ec2_gpu_ondemand_history.csv` | AWS Price List Bulk API (public, primary) | `pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/{version}/us-east-1/index.json`, 44 monthly versions 20230104170711→20260715224843 | 2026-07-16 | 2022-12 → 2026-07 (monthly effective ranges) | Streamed, never stored whole; extractor `scripts/pull_aws_gpu_pricing.py`; all OS/tenancy/capacity variants kept |
| `data/raw/aws/provenance_aws.json` | (generated with the above) | — | 2026-07-16 | — | machine-readable provenance |
| `data/raw/coinmetrics/akt.csv` | Coin Metrics community data archive (GitHub mirror) | `raw.githubusercontent.com/coinmetrics-io/data/master/csv/akt.csv` | 2026-07-16 | 2021-03-12 → 2026-05-24 daily | Full market cap + spot volume; ReferenceRateUSD trailing week only — full price series comes from CoinGecko pull |
| `data/raw/akash/emissions_incentives_table.csv` | Hand-collected: GitHub governance discussions (primary proposal drafts) + Messari coverage | discussions 272, 424, 641, 1034; messari.io State of Akash | 2026-07-16 | 2023-07 → 2026-03 events | Two rows flagged VERIFY (Prop 283 effective date; BME proposal number 257 vs 318) — cross-check on-chain from user machine |
| `data/raw/sunrun/` (empty) | — | investors.sunrun.com press release 2026-07-08 | NOT PULLED | — | Egress-blocked; archive-as-PDF task open (docs/sunrun_release.md) |

## Environment constraint (affects what could be pulled 2026-07-16)

Collection ran inside a Claude Code remote sandbox whose egress allowlist
permits GitHub, AWS pricing, and package registries — and blocks
console.akash.network, api.cloudmos.io, chain REST hosts, CoinGecko and all
exchange APIs, web.archive.org, Messari, and news sites. Scripts
`probe_pipeline.py`, `pull_akt_usd.py`, `snapshot_gpu_prices.py` are written
to run from an unrestricted machine to close the gaps; each writes its own
provenance record.

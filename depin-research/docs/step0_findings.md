# Step 0 findings — what the Akash indexer actually exposes (2026-07-16)

The live probe could not run from this environment (egress allowlist blocks
`console.akash.network`, `api.coingecko.com`, `web.archive.org`, chain REST
hosts and every exchange API). Instead, the Console API's **source code** was
read directly (public repo `akash-network/console`, plus the pre-migration
`cloudmos` routes) to establish exactly which endpoints exist and what they
return. `scripts/probe_pipeline.py` is ready to measure actual depth from an
unrestricted machine.

## Endpoints confirmed from source

| Endpoint | Returns | History? |
|---|---|---|
| `GET /v1/graph-data/{name}` | daily `{date, value}` snapshots + current | **Yes — daily since genesis (2021)** |
| `GET /v1/gpu-breakdown?vendor=&model=` | per **date × vendor × model**: providerCount, nodeCount, totalGpus, leasedGpus, gpuUtilization | **Yes — daily** (depth to be measured; GPU support began late 2023) |
| `GET /v1/gpu-prices` | per model×RAM×interface: min/max/avg/**weightedAverage**/median USD price + availability | **No — current snapshot only** (cache 120 s) |
| `GET /v1/gpu` | current allocatable/allocated per model | No |
| `GET /v1/gpu-models` | model catalog (from `akash-network/provider-configs`) | n/a |
| `GET /v1/market-data` | AKT market data (proxied CoinGecko) | No |

Valid `graph-data` names (from `statsService.ts`): `dailyUAktSpent`,
`dailyUUsdcSpent`, `dailyUUsdSpent`, `dailyLeaseCount`, `totalUAktSpent`,
`totalUUsdcSpent`, `totalUUsdSpent`, `activeLeaseCount`, `totalLeaseCount`,
`activeCPU`, `activeGPU`, `activeMemory`, `activeStorage`.

## What this means for the panel

1. **Network-level daily price indices are constructible back to genesis**:
   e.g. `dailyUUsdSpent / activeLeaseCount` (USD per active lease-day) and
   AKT-vs-USD spend composition. These mix CPU and GPU leases — usable for the
   long window, honest about aggregation.
2. **Model-level daily quantities exist** (`gpu-breakdown`: capacity, leased
   counts, utilization per GPU model) — the supply/utilization side of H1/H3.
3. **Model-level daily PRICES do not have a public history endpoint.** The
   indexer database has the underlying bids/leases, but the API only serves a
   current aggregate. Recovery paths, in order of cost:
   - **Wayback Machine** archives of `/v1/gpu-prices` (and the older
     `api.cloudmos.io/v1/gpu-prices`, `gpus.akash.network`): the probe script
     counts snapshots via the CDX API. If coverage is ≳weekly since early
     2024/2025 → reconstruct a model-level series from archives.
   - **Daily snapshot campaign starting now**: `scripts/snapshot_gpu_prices.py`
     (+ `docs/snapshot_workflow_template.yml` for GitHub Actions). Every day of
     delay is a day of model-level price history lost.
   - **Numia public BigQuery datasets** (Cosmos chains incl. Akash): full
     bid/lease event history queryable with SQL using a free GCP account —
     the path to *executed* lease prices (master doc aggregation rule: median of
     executed leases, not posted asks). No indexer rebuild needed.
   - Full chain replay through the open-source indexer (last resort; heavy).
4. **Quality flags for H3**: provider `audited` attribute is in the indexer
   provider tables; the executed-lease path (Numia or indexer) carries it.

## Provisional verdict (to confirm by running the probe)

**YELLOW, leaning usable**: long daily history for network aggregates +
quantities + AKT/USD + AWS benchmark is effectively certain; model-level price
history is snapshot-only via the public API and must come from archives /
Numia / a snapshot campaign that should start immediately. Per the master doc,
YELLOW = narrow the window, start logging now — with the concrete upgrade path
that Numia SQL can deliver executed-lease medians for the full window, which
would flip the design to GREEN without waiting.

## Immediate actions (user machine, ~30 min)

1. `python3 depin-research/scripts/probe_pipeline.py` — records depths, saves
   day-1 gpu-prices snapshot, prints verdict.
2. Enable the daily snapshot workflow (template in docs/) or a cron job.
3. `python3 depin-research/scripts/pull_akt_usd.py` — full AKT/USD daily CSV.
4. Check Wayback CDX output in `probe_out/wayback_coverage.json`.
5. (Optional, unlocks executed prices) create a free GCP project → query
   Numia's Akash dataset for lease/bid events.

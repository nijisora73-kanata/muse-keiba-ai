# Muse Keiba AI — Phase 1

Auditable CSV → SQLite → immutable prediction snapshot → post-race evaluation.

**Status:** operational proof-of-concept, not a live race feed or a demonstrated profitable predictor. No external data source is connected. Demo inputs are **fictional**; never use the demo to place bets. Target: at most **3 JRA graded races per week** during Phase 1, later expand after data rights/quality checks.

## Quick start (Python 3.12+)

```bash
python -m pip install -e '.[test]'
pytest -q
muse-keiba init --db runtime/keiba.sqlite3
muse-keiba import-entries --db runtime/keiba.sqlite3 --csv examples/entries.csv --allow-demo
muse-keiba import-history --db runtime/keiba.sqlite3 --csv examples/history.csv --allow-demo
muse-keiba predict --db runtime/keiba.sqlite3 --race-id DEMO-20261115-001 --as-of 2026-11-14T20:00:00+09:00 --allow-demo --out runtime/predictions.json
muse-keiba import-results --db runtime/keiba.sqlite3 --csv examples/results.csv --allow-demo
muse-keiba evaluate --db runtime/keiba.sqlite3 --race-id DEMO-20261115-001 --out runtime/evaluation.json
```

All timestamps are ISO-8601 with timezone offsets; example input times are intentionally fictional. Entries, history and results each require `source_id`, `observed_at` (when this system learned it), and `source_published_at` (when provider published it). The prediction cutoff (`--as-of`) is strictly respected. The engine does **not** fall back to data acquired after cutoff. Nothing fetches websites automatically.

## CSV contract

See [docs/csv_spec.md](docs/csv_spec.md) for required columns, meanings, sample data, allowed nulls and validation. One CSV row = one horse's entry, one historical run, or one finishing result. Files must be UTF-8 with header; leave absent optional fields blank.

## What the Phase 1 model does

- `equal_probability_v1`: each declared runner receives `1/N`, verified per race to sum to 1; no fabricated horse-specific predictive advantage. A rank is deterministic (horse number) solely to give stable output, **not a recommendation**. Model may output `見送り`.
- A weighted feature model is deliberately not yet included: historical coverage and bias audits must come first. Recent runs are stored and checked for time leakage, not secretly transformed into unreliable probabilities.
- `evaluate`: winner log loss (`-log p_winner`), multiclass Brier score (`sum_h (p_h - 1[h is winner])²`), top-rank hit and a strictly hypothetical win-bet outcome are recorded. No real stakes placed.
- Baseline predictions are not odds-based. Market odds are only future work after licensing and timestamped snapshots are available.

## Muse operator procedure

1. Data owner approves sources and usage (including storage, automated access and redistribution). Never mass-scrape public websites without permission.
2. Import approved entries and previous runs. Resolve missing data; reject demo rows in real operations.
3. After the scheduled source data are published and ingested, invoke `predict` with an explicit cutoff and save the produced JSON to Muse's prediction board. Predictions are append-only in SQLite.
4. After **official** final results are available, import results and evaluate. Corrected inputs do not change earlier snapshots; a new prediction uses a new cutoff and is recorded separately.
5. Keep the SQLite DB in durable, backed-up private storage, **not GitHub**. Restore-test routinely. GitHub Actions in this repo only runs unit tests, **not** ingest nor live predictions.
6. A Muse cron runner can call these commands after authorized CSV delivery is arranged; never infer scheduled API connectivity from the presence of a cron job.

## Safety and known gaps

No live racing data connector, no valid licensed feed, no model trained on genuine past racing results, no automated betting. Live ops require a vetted data adapter, persistent storage and backups, race schedule and time-zone handling, completeness validation, valid runner changes/scratches, realistic predictions and calibration on chronological holdouts. Predicted probabilities do not guarantee positive ROI.

## Local test

```bash
python -m pip install -e '.[test]'
pytest -q
```

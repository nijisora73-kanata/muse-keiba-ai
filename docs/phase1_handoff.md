# Phase 1 handoff (2026-11-15)

ChatGPT created the initial Python/SQLite research prototype as a ZIP for Kanata/Master to import, rather than overwriting the existing README. The CSV specification was pushed separately to docs/csv_spec.md.

## Contents of ZIP
pyproject.toml, .gitignore, README.md, config/settings.json, docs/{csv_spec,data_sources,prediction_policy}.md, src/muse_keiba/{__init__,__main__,core,cli}.py, examples/{entries,history,results}.csv, tests/test_pipeline.py, .github/workflows/test.yml.

**Archive delivery:** ChatGPT conversation attachment named muse-keiba-ai-phase1.zip (the GitHub connector cannot transfer that archive directly).

## Verified locally
- Python source compilation successful
- `PYTHONPATH=src pytest -q` -> **7 passed**
- CLI dry run: init -> import entries -> import history -> predict -> import results -> evaluate completed with fictional sample race.
- Baseline is equal probability, with `見送り` decision, not a proven betting prediction model.
- No JRA/API feed is connected. Only manually provided, approved CSV input.

## Review needed before integrating
1. Review CSV definitions in docs/csv_spec.md and examples in the archive.
2. Reconcile existing GitHub README with the archive README (do not overwrite contributors' changes).
3. Add extracted files to repository, commit, run GitHub Actions tests.
4. Confirm persistent Muse DB backups and data-source permissions.
5. Expand race/event modeling for scratches, dead-heats, nonfinishers and same-day cutoffs before real forecasts.

## Sample command
```bash
python -m pip install -e '.[test]'
pytest -q
muse-keiba init --db runtime/keiba.sqlite3
muse-keiba import-entries --db runtime/keiba.sqlite3 --csv examples/entries.csv --allow-demo
muse-keiba import-history --db runtime/keiba.sqlite3 --csv examples/history.csv --allow-demo
muse-keiba predict --db runtime/keiba.sqlite3 --race-id DEMO-20261115-001 --as-of 2026-11-14T20:00:00+09:00 --allow-demo
muse-keiba import-results --db runtime/keiba.sqlite3 --csv examples/results.csv --allow-demo
muse-keiba evaluate --db runtime/keiba.sqlite3 --race-id DEMO-20261115-001
```

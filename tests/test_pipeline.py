import csv
import json
import math
from pathlib import Path
import pytest
from muse_keiba.core import DataError, init, import_rows, predict, evaluate, read_csv

BASE=Path(__file__).resolve().parents[1]
CUTOFF="2026-11-14T20:00:00+09:00"
RACE="DEMO-20261115-001"

def db(tmp_path):
    path=tmp_path/"test.sqlite3"
    init(path)
    import_rows(path,BASE/"examples/entries.csv","entries",True)
    import_rows(path,BASE/"examples/history.csv","history",True)
    return path

def test_full_pipeline(tmp_path):
    path=db(tmp_path)
    x=predict(path,RACE,CUTOFF,True)
    assert x["decision"]=="見送り"
    assert len(x["runners"])==3
    assert sum(r["win_probability"] for r in x["runners"])==pytest.approx(1)
    assert x["history_rows_visible"]==3
    assert predict(path,RACE,CUTOFF,True)["snapshot_id"]==x["snapshot_id"]
    import_rows(path,BASE/"examples/results.csv","results",True)
    y=evaluate(path,RACE)["evaluations"]
    assert len(y)==1
    assert y[0]["log_loss"]==pytest.approx(math.log(3))
    assert y[0]["brier_multiclass"]==pytest.approx(2/3)
    assert y[0]["top_rank_hit"] is False
    assert y[0]["hypothetical_payout_yen"]==0

def test_demo_optin(tmp_path):
    init(tmp_path/"x.db")
    with pytest.raises(DataError,match="allow-demo"):
        import_rows(tmp_path/"x.db",BASE/"examples/entries.csv","entries")

def test_cutoff_and_no_future_entries(tmp_path):
    path=db(tmp_path)
    with pytest.raises(DataError,match="no pre-cutoff"):
        predict(path,RACE,"2026-11-13T00:00:00+09:00",True)
    with pytest.raises(DataError,match="cutoff must be before"):
        predict(path,RACE,"2026-11-15T11:00:00+09:00",True)

def test_csv_schema_reject_unknown_column(tmp_path):
    raw=(BASE/"examples/entries.csv").read_text(encoding="utf-8")
    p=tmp_path/"bad.csv"
    p.write_text(raw.replace("data_kind\n","data_kind,extra\n",1),encoding="utf-8")
    with pytest.raises(DataError,match="expected header"):
        read_csv(p,"entries")

def test_conflicting_snapshot_is_rejected(tmp_path):
    path=db(tmp_path)
    raw=(BASE/"examples/entries.csv").read_text(encoding="utf-8").replace("架空の流星","架空の別名")
    p=tmp_path/"conflict.csv"
    p.write_text(raw,encoding="utf-8")
    with pytest.raises(DataError,match="immutable source revision"):
        import_rows(path,p,"entries",True)

def test_results_need_complete_field(tmp_path):
    path=db(tmp_path)
    predict(path,RACE,CUTOFF,True)
    raw=(BASE/"examples/results.csv").read_text(encoding="utf-8").splitlines()
    p=tmp_path/"partial.csv"
    p.write_text("\n".join(raw[:-1])+"\n",encoding="utf-8")
    import_rows(path,p,"results",True)
    with pytest.raises(DataError,match="incomplete"):
        evaluate(path,RACE)

def test_invalid_naive_timestamp(tmp_path):
    raw=(BASE/"examples/entries.csv").read_text(encoding="utf-8").replace("2026-11-14T08:00:00+09:00","2026-11-14T08:00:00")
    p=tmp_path/"naive.csv"
    p.write_text(raw,encoding="utf-8")
    with pytest.raises(DataError,match="timezone-aware"):
        read_csv(p,"entries")

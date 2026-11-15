"""CSV, SQLite, leak-safe equal-probability snapshots and evaluation.

Data ingestion is **manual only** until provider authorization is approved.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sqlite3
from datetime import date, datetime, time, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=9))
KIND = {"demo", "real"}
SURFACE = {"turf", "dirt"}
GRADES = {"G1", "G2", "G3", "OTHER"}
SOURCE_COLS = {"source_id", "source_published_at", "observed_at", "data_kind"}
FIELDS = {
    "entries": "race_id race_date track race_number grade surface distance_m horse_id horse_name horse_number gate jockey carried_kg scratch source_id source_published_at observed_at data_kind".split(),
    "history": "horse_id past_race_id race_date finish_position field_size surface distance_m going last3f_sec source_id source_published_at observed_at data_kind".split(),
    "results": "race_id horse_id finish_position win_payout_per_100yen source_id source_published_at observed_at data_kind".split(),
}
OPTIONAL = {
    "entries": {"gate", "jockey", "carried_kg"},
    "history": {"going", "last3f_sec"},
    "results": {"win_payout_per_100yen"},
}
ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

class DataError(ValueError):
    pass

def iso(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if d.tzinfo is None or d.utcoffset() is None:
            raise ValueError("missing timezone")
        return d.astimezone(timezone.utc)
    except (TypeError, ValueError) as e:
        raise DataError(f"invalid timezone-aware timestamp: {value!r}") from e

def day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as e:
        raise DataError(f"invalid date: {value!r}") from e

def integer(v, field, low, high):
    try:
        n = int(v)
        if str(n) != str(v).strip() or not low <= n <= high:
            raise ValueError()
        return n
    except (TypeError, ValueError):
        raise DataError(f"invalid {field}: {v!r}") from None

def number(v, field, low, high):
    try:
        n = float(v)
        if not math.isfinite(n) or not low <= n <= high:
            raise ValueError()
        return n
    except (TypeError, ValueError):
        raise DataError(f"invalid {field}: {v!r}") from None

def identifier(v, field):
    if not ID_RE.fullmatch(v):
        raise DataError(f"invalid {field}: {v!r}")
    return v

def validate(row, kind):
    for field in FIELDS[kind]:
        if field not in OPTIONAL[kind] and (row.get(field) is None or row[field].strip() == ""):
            raise DataError(f"{kind}: missing required {field}")
    for field in ("source_id",):
        identifier(row[field], field)
    for name in ("observed_at", "source_published_at"):
        row[name] = iso(row[name]).isoformat()
    if iso(row["source_published_at"]) > iso(row["observed_at"]):
        raise DataError("source published after observed")
    if row["data_kind"] not in KIND:
        raise DataError("invalid data_kind")
    if kind == "entries":
        for x in ("race_id", "horse_id"):
            identifier(row[x], x)
        row["race_date"] = day(row["race_date"]).isoformat()
        row["race_number"] = integer(row["race_number"], "race_number", 1, 12)
        row["horse_number"] = integer(row["horse_number"], "horse_number", 1, 18)
        row["distance_m"] = integer(row["distance_m"], "distance_m", 800, 4000)
        row["scratch"] = integer(row["scratch"], "scratch", 0, 1)
        if row["grade"] not in GRADES or row["surface"] not in SURFACE or not row["track"].strip() or not row["horse_name"].strip():
            raise DataError("invalid grade/surface/track/horse_name")
        row["gate"] = integer(row["gate"], "gate", 1, 8) if row["gate"] else None
        row["carried_kg"] = number(row["carried_kg"], "carried_kg", 40, 70) if row["carried_kg"] else None
    elif kind == "history":
        for x in ("horse_id", "past_race_id"):
            identifier(row[x], x)
        row["race_date"] = day(row["race_date"]).isoformat()
        row["finish_position"] = integer(row["finish_position"], "finish_position", 1, 30)
        row["field_size"] = integer(row["field_size"], "field_size", row["finish_position"], 30)
        row["distance_m"] = integer(row["distance_m"], "distance_m", 800, 4000)
        if row["surface"] not in SURFACE:
            raise DataError("invalid surface")
        row["last3f_sec"] = number(row["last3f_sec"], "last3f_sec", 1, 120) if row["last3f_sec"] else None
        # A completed run cannot be published before the race day in local JST.
        if iso(row["source_published_at"]).astimezone(JST).date() < day(row["race_date"]):
            raise DataError("history published before race date")
    else:
        identifier(row["race_id"], "race_id")
        identifier(row["horse_id"], "horse_id")
        row["finish_position"] = integer(row["finish_position"], "finish_position", 1, 30)
        row["win_payout_per_100yen"] = integer(row["win_payout_per_100yen"], "win_payout_per_100yen", 0, 100000000) if row["win_payout_per_100yen"] else None
    return row

def read_csv(path, kind):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None or set(reader.fieldnames) != set(FIELDS[kind]):
            raise DataError(f"{kind}: expected header columns exactly {FIELDS[kind]}; got {reader.fieldnames}")
        data = []
        for i, row in enumerate(reader, 2):
            if None in row:
                raise DataError(f"line {i}: extra unlabelled values")
            try:
                data.append(validate(row, kind))
            except DataError as e:
                raise DataError(f"line {i}: {e}") from e
    if not data:
        raise DataError("empty CSV")
    return data

def connect(db):
    path = Path(db)
    path.parent.mkdir(parents=True, exist_ok=True)
    cn = sqlite3.connect(path)
    cn.row_factory = sqlite3.Row
    cn.execute("PRAGMA foreign_keys=ON")
    cn.execute("PRAGMA journal_mode=WAL")
    return cn

DDL = """
CREATE TABLE IF NOT EXISTS entries (
 race_id TEXT NOT NULL, horse_id TEXT NOT NULL, horse_number INTEGER NOT NULL,
 observed_at TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY (race_id, horse_id, observed_at)
);
CREATE TABLE IF NOT EXISTS history (
 horse_id TEXT NOT NULL, past_race_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY (horse_id, past_race_id, observed_at)
);
CREATE TABLE IF NOT EXISTS results (
 race_id TEXT NOT NULL, horse_id TEXT NOT NULL, observed_at TEXT NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY (race_id, horse_id, observed_at)
);
CREATE TABLE IF NOT EXISTS forecasts (
 snapshot_id TEXT PRIMARY KEY, race_id TEXT NOT NULL, cutoff TEXT NOT NULL,
 generated_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entry_race ON entries(race_id);
CREATE INDEX IF NOT EXISTS idx_hist_horse ON history(horse_id);
CREATE INDEX IF NOT EXISTS idx_results_race ON results(race_id);
CREATE INDEX IF NOT EXISTS idx_forecast_race ON forecasts(race_id);
"""

def init(db):
    cn = connect(db)
    try:
        cn.executescript(DDL)
    finally:
        cn.close()

def import_rows(db, path, kind, allow_demo=False):
    rows = read_csv(path, kind)
    if any(r["data_kind"] == "demo" for r in rows) and not allow_demo:
        raise DataError("demo data requires --allow-demo")
    table = kind
    keys = {"entries": ("race_id", "horse_id", "observed_at"), "history": ("horse_id", "past_race_id", "observed_at"), "results": ("race_id", "horse_id", "observed_at")}[kind]
    seen = set()
    for r in rows:
        key = tuple(r[k] for k in keys)
        if key in seen:
            raise DataError(f"duplicate row key: {key}")
        seen.add(key)
    with connect(db) as cn:
        # Validate the incoming batch against existing data; a duplicate snapshot with differing bytes must fail.
        for r in rows:
            if kind != "entries":
                ref = cn.execute("SELECT payload FROM entries WHERE horse_id=?" + (" AND race_id=?" if kind == "results" else "") + " LIMIT 1", (r["horse_id"],r["race_id"]) if kind == "results" else (r["horse_id"],)).fetchone()
                if ref is None:
                    raise DataError(f"unknown entry horse_id={r['horse_id']}; import entries first")
                if json.loads(ref["payload"])["data_kind"] != r["data_kind"]:
                    raise DataError("mixed demo/real data")
            if kind == "results":
                race_date = day(json.loads(ref["payload"])["race_date"])
                if iso(r["source_published_at"]).astimezone(JST).date() < race_date:
                    raise DataError("results published before race date")
            old = cn.execute(f"SELECT payload FROM {table} WHERE " + " AND ".join(f"{k}=?" for k in keys), tuple(r[k] for k in keys)).fetchone()
            payload = json.dumps(r, sort_keys=True, ensure_ascii=False)
            if old and old["payload"] != payload:
                raise DataError("immutable source revision key conflict: use a new observed_at")
        for r in rows:
            cols = list(keys) + (["horse_number"] if kind == "entries" else []) + ["payload"]
            payload = json.dumps(r, sort_keys=True, ensure_ascii=False)
            cn.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", [r[k] for k in cols if k != "payload"] + [payload])
        cn.commit()
    return len(rows)

def latest(cn, table, cutoff, where=None, args=()):
    # Append-only snapshots, select latest observed before the cutoff per natural key.
    key = {"entries": ("race_id", "horse_id"), "history": ("horse_id", "past_race_id"), "results": ("race_id", "horse_id")}[table]
    q = f"SELECT payload FROM {table} WHERE observed_at<=?" + (" AND " + where if where else "") + " ORDER BY observed_at DESC"
    out = {}
    for r in cn.execute(q, (cutoff, *args)):
        obj = json.loads(r["payload"])
        if obj["source_published_at"] > cutoff:
            continue
        group = tuple(obj[k] for k in key)
        if group not in out:
            out[group] = obj
    return list(out.values())

def predict(db, race_id, as_of, allow_demo=False):
    cutoff = iso(as_of).isoformat()
    with connect(db) as cn:
        all_entries = latest(cn, "entries", cutoff, "race_id=?", (race_id,))
        if not all_entries:
            raise DataError("no pre-cutoff entries: abstain")
        invariant = {tuple(e[k] for k in ("race_date", "track", "race_number", "grade", "surface", "distance_m", "data_kind")) for e in all_entries}
        if len(invariant) != 1:
            raise DataError("inconsistent race-wide entry attributes")
        if len({e["horse_number"] for e in all_entries}) != len(all_entries):
            raise DataError("duplicate horse number")
        if len({e["horse_id"] for e in all_entries}) != len(all_entries):
            raise DataError("duplicate horse id")
        if any(e["data_kind"] == "demo" for e in all_entries) and not allow_demo:
            raise DataError("demo data requires --allow-demo")
        if iso(as_of).astimezone(JST).date() >= day(all_entries[0]["race_date"]):
            raise DataError("cutoff must be before race date (v1 conservative boundary)")
        active = sorted([e for e in all_entries if e["scratch"] == 0], key=lambda x: x["horse_number"])
        if len(active) < 2:
            raise DataError("fewer than two active runners: abstain")
        # Guard history only: a vetted model can use these rows later; v1 ignores them.
        hist = latest(cn, "history", cutoff)
        related_ids = {e["horse_id"] for e in active}
        valid_history = [h for h in hist if h["horse_id"] in related_ids and day(h["race_date"]) < day(active[0]["race_date"])]
        n = len(active)
        prob = 1 / n
        prediction = {
            "schema_version": "1.0", "model": "equal_probability_v1",
            "race_id": race_id, "race_date": active[0]["race_date"], "cutoff": cutoff,
            "data_kind": active[0]["data_kind"], "decision": "見送り",
            "reason": "Baseline only; no validated horse-specific predictive signal or bookmaker odds.",
            "runners": [{"horse_id": e["horse_id"], "horse_number": e["horse_number"], "horse_name": e["horse_name"], "win_probability": prob} for e in active],
            "history_rows_visible": len(valid_history),
            "sources": sorted({e["source_id"] for e in all_entries} | {h["source_id"] for h in valid_history}),
            "probability_sum": sum(prob for _ in active),
        }
        canon = json.dumps(prediction, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        pred_id = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        prediction["snapshot_id"] = pred_id
        cn.execute("INSERT OR IGNORE INTO forecasts (snapshot_id,race_id,cutoff,generated_at,payload) VALUES (?,?,?,?,?)", (pred_id, race_id, cutoff, datetime.now(timezone.utc).isoformat(), json.dumps(prediction, ensure_ascii=False, sort_keys=True)))
        cn.commit()
        return prediction

def evaluate(db, race_id):
    now = datetime.now(timezone.utc).isoformat()
    with connect(db) as cn:
        forecasts = [json.loads(row["payload"]) for row in cn.execute("SELECT payload FROM forecasts WHERE race_id=? ORDER BY cutoff,snapshot_id", (race_id,))]
        if not forecasts:
            raise DataError("no forecasts")
        results = latest(cn, "results", now, "race_id=?", (race_id,))
        if not results:
            raise DataError("no results")
        out=[]
        for forecast in forecasts:
            if any(r["data_kind"] != forecast["data_kind"] for r in results):
                raise DataError("mixed result kinds")
            runners=forecast["runners"]
            expected={r["horse_id"] for r in runners}
            by_id={r["horse_id"]: r for r in results}
            if len(results) != len(by_id) or set(by_id) != expected:
                raise DataError("incomplete/mismatched results; cannot evaluate")
            places=[r["finish_position"] for r in results]
            if sorted(places) != list(range(1, len(expected)+1)):
                raise DataError("results have tied, missing or invalid positions")
            if any(r["source_published_at"] <= forecast["cutoff"] for r in results):
                raise DataError("result published before forecast cutoff")
            winner=next(r for r in results if r["finish_position"] == 1)
            probabilities={r["horse_id"]:r["win_probability"] for r in runners}
            if len(probabilities) != len(runners) or not math.isclose(sum(probabilities.values()),1,abs_tol=1e-10):
                raise DataError("invalid probability vector")
            w=probabilities[winner["horse_id"]]
            if w<=0:
                raise DataError("log loss undefined for zero winner probability")
            top=sorted(runners, key=lambda r:(-r["win_probability"],r["horse_number"]))[0]["horse_id"]
            payout=winner["win_payout_per_100yen"]
            out.append({"snapshot_id":forecast["snapshot_id"], "race_id":race_id, "cutoff":forecast["cutoff"], "winner_id":winner["horse_id"], "log_loss":-math.log(w), "brier_multiclass":sum((p-(1 if h==winner["horse_id"] else 0))**2 for h,p in probabilities.items()), "top_rank_hit":top==winner["horse_id"], "hypothetical_stake_yen":100, "hypothetical_payout_yen": payout if top==winner["horse_id"] and payout is not None else (0 if top!=winner["horse_id"] else None), "note":"Top rank is horse-number tiebreak only, not a betting recommendation."})
        return {"evaluations":out}

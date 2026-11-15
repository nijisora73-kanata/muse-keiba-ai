# CSV Contract v1.0 — review request for かなた

Encoding: UTF-8 (BOM is tolerated); commas and standard RFC4180 quoting; header names are **exact**; dates/times are ISO-8601 with explicit `Z` or `+09:00` offset. Missing values may be empty **only where optional**. Duplicate keys, invalid enum/ranges, ambiguous timestamps, and unknown race / horse IDs are rejected. In all files `source_id` is an attribution key chosen for an authorized provider or human reviewer, not proof of a license; `source_published_at` is provider publication time, `observed_at` is when Muse received the row. `source_published_at <= observed_at` is required. `data_kind` must be `demo` or `real`; demo and real cannot be mixed in one race. If source is not licensed for automated retrieval, use manually imported authorized CSV and preserve audit evidence outside this repository.

## entries.csv — one row per horse in race

| Column | Required | Format / meaning |
|---|---|---|
| race_id | yes | stable ID, ASCII letters/numbers/_/- only; internal identifier not necessarily a JRA-issued code |
| race_date | yes | YYYY-MM-DD, JST date |
| track | yes | JRA venue text (e.g. 東京); no blind venue inference |
| race_number | yes | integer 1–12 |
| grade | yes | G1, G2, G3 or OTHER |
| surface | yes | turf or dirt |
| distance_m | yes | integer 800–4000 |
| horse_id | yes | stable ID per horse |
| horse_name | yes | display name |
| horse_number | yes | integer 1–18, unique within race |
| gate | no | integer 1–8, blank if unannounced |
| jockey | no | display text |
| carried_kg | no | decimal 40–70 kg |
| scratch | yes | 0 or 1; scratched runners excluded from probabilities |
| source_id | yes | attribution ID |
| source_published_at | yes | timestamp with timezone |
| observed_at | yes | timestamp with timezone |
| data_kind | yes | demo or real |

**Race-wide invariant:** date/venue/number/grade/surface/distance and kind must agree for all race rows. Every horse/horse-number must be unique. Entries are snapshots; update prior to prediction using explicit new `observed_at`. If runners scratched after prediction, the original immutable forecast remains, and a new revision should be issued (future improvement: explicit scratch-event schema).

## history.csv — one completed prior run per horse

| Column | Required | Meaning |
|---|---|---|
| horse_id | yes | references entries horse |
| past_race_id | yes | stable run ID / race ID, uniqueness per horse |
| race_date | yes | YYYY-MM-DD |
| finish_position | yes | integer >= 1 |
| field_size | yes | integer >= finish_position and <= 30 |
| surface | yes | turf or dirt |
| distance_m | yes | 800–4000 |
| going | no | source's track condition as a literal text, e.g. 良 |
| last3f_sec | no | final 3-furlong time in seconds, positive decimal |
| source_id | yes | attribution ID |
| source_published_at | yes | timestamp with timezone |
| observed_at | yes | timestamp with timezone |
| data_kind | yes | demo or real |

**No leakage:** prior race date must be strictly before target race date; `observed_at <= cutoff`, `source_published_at <= cutoff`, and source publication timestamp must not be earlier than completion date for a non-simulated run. Historical runs are stored but intentionally **not used** by `equal_probability_v1`.

## results.csv — one completed result per runner (finishers only in v1)

| Column | Required | Meaning |
|---|---|---|
| race_id | yes | existing race |
| horse_id | yes | existing entrant |
| finish_position | yes | 1..N (unique), final official finishing place; dead heats not yet supported |
| win_payout_per_100yen | no | integer nonnegative, populated for winner if known |
| source_id | yes | attribution ID |
| source_published_at | yes | timezone timestamp |
| observed_at | yes | timezone timestamp |
| data_kind | yes | demo or real |

**v1 restriction:** all non-scratched runners must have exactly one finishing result, with positions from 1..N. Refuse incomplete or dead-heat races instead of guessing. Official outcome must be published after the race date; evaluation also rejects result timestamps not later than the prediction cutoff. Payout is optional, and simulated profit is only possible when winning payout is provided.

## Priority review questions

1. Which specific permitted source can supply `source_published_at` reliably? If not available, record verified human-release timestamp with documented provenance, not a guessed time.
2. Can we persist official identifiers and late scratches/cancellations while preserving earlier snapshots?
3. How will ties, disqualifications, and non-finishers be represented in schema v1.1?
4. What are approved redistribution and retention terms for each supplied field?
5. How will durable Muse SQLite storage be backed up and restored?

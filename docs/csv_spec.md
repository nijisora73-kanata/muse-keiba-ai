# Phase 1 CSV Contract v1.0 (review draft)

Encoding: UTF-8 (BOM allowed), comma-delimited with exact headers. Datetimes must have timezone offsets. Source publication timestamp and ingestion timestamp are distinct; source_published_at <= observed_at. ID fields are stable strings. Empty values only for listed optional fields. source_id is attribution, not proof of data-use rights. data_kind is demo or real. Never mix demo and real in a race.

## entries.csv
race_id,race_date,track,race_number,grade,surface,distance_m,horse_id,horse_name,horse_number,gate,jockey,carried_kg,scratch,source_id,source_published_at,observed_at,data_kind

Each row = one entrant in one JRA race. Required: all except gate,jockey,carried_kg. race_date=YYYY-MM-DD (JST), race_number 1..12, grade G1/G2/G3/OTHER, surface turf/dirt, distance_m 800..4000, horse_number 1..18, scratch 0/1. Gate optional 1..8; carried_kg optional 40..70. Unique horse_id and horse_number per race. Race-wide attributes must agree. Later source revisions use a later observed_at; prior snapshots must not be overwritten.

## history.csv
horse_id,past_race_id,race_date,finish_position,field_size,surface,distance_m,going,last3f_sec,source_id,source_published_at,observed_at,data_kind

One prior completed run of a horse. Required: all except going,last3f_sec. finish_position 1..field_size; field_size <=30. Last3f_sec optional numeric seconds. Past race date must precede target date. A historical row is usable in prediction only if observed_at and source_published_at are <= forecast cutoff.

## results.csv
race_id,horse_id,finish_position,win_payout_per_100yen,source_id,source_published_at,observed_at,data_kind

One official result per runner, no ties/dead heats/nonfinishers in v1. Required except win_payout_per_100yen. Finish positions exactly 1..N for all forecast runners; incomplete results fail evaluation. Payout in JPY per 100 JPY win stake, optional. Results must not have been available at forecast cutoff.

## Known limits and review questions
- v1 forecast cutoff is before race date (conservative; race-time field needed to support same-day forecasts).
- No sanctioned automated provider has yet been connected.
- Runner scratches, cancellations, dead heats, disqualifications and nonfinishers need a v1.1 extension.
- Determine reliable source_published_at provenance and approved data retention/redistribution.
- Confirm durable DB storage and restore-tested backups before real operation.

The full prototype including example CSVs and tests is available as an archive in the ChatGPT collaboration handoff.
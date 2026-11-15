# Prediction and audit policy

- A forecast must only see records whose `observed_at` and `source_published_at` are at or before its explicit `as_of` timestamp.
- Prediction `as_of` must be earlier than local race date (strict pre-race boundary for v1; intraday cutoffs require a race off-time field later).
- Freeze runner set and model/version as JSON in the DB. Never modify it after a result. Repeated identical requests are idempotent; altered data with same race and cutoff creates a separate snapshot digest.
- Abstain when source quality, missing runners, or post-cutoff data make prediction inappropriate.
- Compare equal-probability baseline before fitting models. Use chronological train/validation/test; avoid selection bias and report calibration rather than promise of winnings.
- For Phase 1 race selection, maximum three JRA graded events per week where records are complete. This is a configuration policy, not enforced by the single-race CLI yet.

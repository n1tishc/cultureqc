# Growth model backtest (SYNTHETIC — harness correctness check, not real prediction accuracy)

**No real C2C12/CTC sequences are cached yet** (culture/replay.py's own docstring: the real
Slice 1b cache has sequence_id/frame_idx unset for every row). Every stream below is a
hand-generated synthetic curve replayed through the real culture/replay.py + culture/growth.py
code path — this checks the fitting/prediction/bootstrap code is correct, not real prediction
accuracy. `on_model` streams are exact logistics (an optimistic ceiling — growth.py's own
logistic candidate is literally the generating function); `off_model` streams are asymmetric
(Richards, nu=3) curves that are **not** one of growth.py's two candidates — the fairer check.

**This table must not be quoted as the §12 claims-policy backtest sentence until re-run on
real cached sequences.** Also note: `n_windows` counts (stream x reach_threshold) pairs, not
independent trials -- the three reach thresholds for one stream/repositioning often resolve to
the same or an overlapping visit prefix, so at these small counts the coverage % is a rough
signal, not a calibrated estimate (that needs many more, less-correlated streams -- real
sequences, once cached, would supply that naturally).

**`on_model` + `with_repositioning` coverage is well below 90% -- this is a known limit, not a
bug:** growth.py's bootstrap resamples residuals *within* the AIC-chosen model only; it never
lets a resample prefer the other model, so it misses model-selection uncertainty. That's exactly
what dominates here -- on sparse, noisy early-reach prefixes, logistic vs Gompertz AIC often ties
(diagnosed directly: one such prefix scored -10.56 vs -11.55, an effective coin flip), and
whichever wins can extrapolate the same short prefix to a meaningfully different T*. See
culture/growth.py's own docstring for the same caveat.

Groups with fewer than 3 resolved windows are omitted from this
table (one window is one data point -- a median/coverage % over 1-2 of them isn't a summary
statistic); they're still in the CSV, not hidden, just not presented as if they were.

| family | repositioning | n_windows | median abs error (h) | 90% interval coverage |
|---|---|---|---|---|
| off_model | with_repositioning | 3 | 17.5 | 100% |
| on_model | with_repositioning | 21 | 19.7 | 48% |
| on_model | without_repositioning | 20 | 4.8 | 100% |

Omitted for n_windows < 3 (see growth_backtest.csv for the raw rows): off_model/without_repositioning (n=1)

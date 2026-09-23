# Growth model — 3 example segments (SYNTHETIC, §6.4 checkpoint)

Fabricated fixture sequences replayed through the real culture/replay.py + culture/growth.py
code path (same pattern as demo/flask_timeline.py / scripts/backtest_growth.py) — never a claim
about real cell growth.

- **good** (Good — healthy growth, target reached with a tight interval): **logistic** chosen (logistic AIC=-15.9, gompertz AIC=-10.9) &middot; T* = 76h, 90% CI [64h, 93h] &middot; doubling (early) 12.0h
- **poor** (Poor — slow, late-inflecting growth: reached, but late and wide): **logistic** chosen (logistic AIC=-27.2, gompertz AIC=-23.6) &middot; T* = 229h, 90% CI [205h, 283h] &middot; doubling (early) 47.1h
- **plateau** (Plateau — carrying capacity below target: NOT_REACHED): **logistic** chosen (logistic AIC=-20.3, gompertz AIC=-18.6) &middot; T* = `NOT_REACHED` &middot; doubling (early) 22.8h

Note the doubling-time pair above: **plateau** reports a *faster* early doubling time than
**poor** even though plateau never reaches the target and poor eventually does. That's
expected, not a bug — doubling time is a rate (how fast growth is happening right now),
independent of the fitted ceiling K (how high it will ever get). Plateau's generating curve
rises steeply to a low ceiling; poor's rises slowly throughout to a much higher one. See
culture/growth.py:_area_doubling_time's docstring.

# Growth model — 3 example segments (SYNTHETIC, §6.4 checkpoint)

Fabricated fixture sequences replayed through the real culture/replay.py + culture/growth.py
code path (same pattern as demo/flask_timeline.py / scripts/backtest_growth.py) — never a claim
about real cell growth.

- **good** (Good — healthy growth, target reached with a tight interval): **logistic** chosen (logistic AIC=-15.9, gompertz AIC=-10.9) &middot; T* = 76h, 90% CI [64h, 93h] &middot; doubling (early) 12.0h
- **poor** (Poor — slow, late-inflecting growth: reached, but late and wide): **logistic** chosen (logistic AIC=-27.2, gompertz AIC=-23.6) &middot; T* = 229h, 90% CI [205h, 283h] &middot; doubling (early) 47.1h
- **plateau** (Plateau — carrying capacity below target: NOT_REACHED): **logistic** chosen (logistic AIC=-20.3, gompertz AIC=-18.6) &middot; T* = `NOT_REACHED` &middot; doubling (early) 22.8h

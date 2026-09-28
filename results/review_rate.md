# Human-review rate from the confluency confidence floor

Generated 2026-09-28T16:48:04Z by `scripts/review_rate.py`. No model runs: confidences are the compute cache's (Cellpose-SAM cpsam_v2, Colab GPU, nb/03), full resolution, same formula as the live path. C2C12 images: Ker et al., *Sci Data* 5:180237 (2018), CC BY 4.0; fault frames are simulated from them.

Rule: confidence below the floor (0.30, `culture/rules.py` default) returns `human_review`. With the classifier demoted it is the only rule that does; the anomaly flag is review-only and does not change the action, and quality-gate failures return REIMAGE (`results/quality_gate_c2c12.md`). Frames within a sequence are not independent; n sequences is the sample size.

| group | sequences | images | sent to review | note |
|---|---|---|---|---|
| C2C12 held-out, full frames | 14 | 1228 | 70 (5.7%) | — |
| C2C12 tuning, full frames | 10 | 860 | 47 (5.5%) | comparison only |
| C2C12 held-out, confluency 0-20% | 14 | 750 | 0 (0.0%) | — |
| C2C12 held-out, confluency 20-40% | 13 | 318 | 0 (0.0%) | — |
| C2C12 held-out, confluency 40-60% | 8 | 160 | 70 (43.8%) | — |
| EVICAN eval2019 (real, expert masks) | — | 98 | 3 (3.1%) | — |
| C2C12 simulated lamp dimming | 24 | 552 | 60 (10.9%) | simulated fault frames |
| C2C12 simulated contamination | 4 | 97 | 13 (13.4%) | simulated fault frames |
| C2C12 held-out, 0.25-frame FOV crops | 14 | 4912 | 451 (9.2%) | each crop segmented on its own, as the replay visits are |

Held-out C2C12 review rate per sequence: 090303_exp1_F0003 8.2%, 090303_exp1_F0014 0%, 090318_exp1_F0001 0%, 090318_exp1_F0003 0%, 090318_exp1_F0005 0%, 090318_exp1_F0007 0%, 090318_exp1_F0011 31.5%, 090318_exp1_F0013 24.7%, 090318_exp1_F0016 0%, 090325_exp1_F0003 0%, 090325_exp1_F0007 0%, 090325_exp1_F0011 14.9%, 090325_exp1_F0013 0%, 090325_exp1_F0018 0%.

Highest held-out C2C12 confluency: 57.0%, so no frame reaches the 60-100% bins. Held-out frames at 40% or more, per sequence (sent to review / frames): 090303_exp1_F0003 7/9, 090318_exp1_F0001 0/14, 090318_exp1_F0003 0/11, 090318_exp1_F0011 28/38, 090318_exp1_F0013 22/44, 090325_exp1_F0003 0/16, 090325_exp1_F0011 13/16, 090325_exp1_F0013 0/12.

# Branch publication and CI runtime correction

The owner explicitly authorized pushing `slice-1b-compute-cache` and deploying
its v4 website. Commit `0007bc2107c1738c3ea1be69ae12abe6a2f18a41` was pushed
normally, without force, merge to `main`, tag or repository-setting changes.
Unrelated local ZIP archives and `files/` were excluded.

## Verified first publication

- Vercel production deployment `7212885391` reports success for that exact SHA
  under `Production – cultureqc-cvoy`.
- `https://cultureqc-cvoy.vercel.app/`, `/records` and `/validation` are reachable.
- The production JavaScript contains the same SHA and the illustrative review.
  JavaScript and CSS hashes match a local build of the committed revision.
- Local pre-push validation: 222 focused Python tests, 15 Node tests, production
  build, unchanged generated site-data hash and Space source-copy parity passed.
- GitHub run `39510280196`: site build, API contract and offline host contract
  passed. Broader Python CI reported 747 passed, 45 skipped and four failures.

## CI failure and correction

The four failures were frozen-report comparisons in the EVICAN and C2C12 replay
suites, not changed per-image decisions. The reports were frozen on CPython
3.14.7, as both manifests already record, while general CI used Python 3.11.
A minimal replay of the EVICAN aggregation with identical JSON input reproduced
the CI mismatch under local Python 3.11.5 and matched under Python 3.14.7:

| Aggregate | Python 3.11 | Frozen / Python 3.14.7 |
|---|---|---|
| Uncalibrated MAE, pp | 8.356606060606058 | 8.35660606060606 |
| Configured MAE, pp | 3.7801212121212115 | 3.780121212121212 |

The follow-up pins the general Python CI job to the recorded 3.14.7 reference
runtime and documents that cross-version byte identity is not guaranteed. It
does not change any replay source, frozen bundle/hash, decision, scientific
threshold or assertion. The independent API contract job stays on Python 3.11.
This corrects a missing runtime constraint; it does not establish general
cross-version numerical reproducibility.

Only the website is deployed. Hugging Face console/API/raw-demo services remain
untouched. Human screen-reader and actual 200% zoom checks remain pending, V3
remains gated, and no biological or commercial-clearance gate is closed by a push.

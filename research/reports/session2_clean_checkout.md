# Second-stage clean checkout verification — 2026-11-17

Tested source commit: `9fdd2c2` (local coordination baselines/development study).
Created a detached clean worktree and reused the pinned existing virtual
environment. This is clean-source verification, not a second fresh dependency
installation, independent laboratory replication or cross-platform test.

Executed from that checkout:

```text
python -m pytest tests -q --junitxml=<main-worktree>/research/reports/session2_clean_checkout_tests.xml
python scripts/validate_async.py --smoke --out local-validation
python scripts/analyze_async.py --input results/async/development_2026_11_17 --out local-tables
```

Outcomes: **275 passed in 8.56 seconds**; all six analytic smoke cases verified;
all **1,470** stored development replays independently validated. Regenerated
analysis JSON matched the committed analysis exactly, including map-cluster
bootstrap estimates and all-outcome counts. Committed source files matched
every recorded LF-normalized study package hash. Original historical results
and the user's existing dashboard edit were also checked unchanged by hashes.
The reserved final holdout specification retained its original hash.

Eight upstream PIBT tests and 40 native reference runs were executed separately
earlier in this session and are recorded in their own artifacts. They are not
misreported as part of this clean-checkout test count. LSRP did not build/run.

This final follow-up commit contains verification evidence/documentation only.
No method, physical model, experimental result or claim changed after testing.

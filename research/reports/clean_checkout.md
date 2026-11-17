# Clean checkout verification

Code commit: `abb7170` (Add audited asynchronous MAPF research foundation).

Created a detached Git worktree at
`D:\Multi Agent Path Finding\verification-research`. Reused the already installed
repository virtual environment; this is clean-source verification, not a second
independent dependency installation or cross-machine replication.

Commands actually run from that checkout, using the virtual environment's Python:

```text
python -m pytest tests -q --junitxml=<main-worktree>/research/reports/clean_checkout_tests.xml
python scripts/validate_async.py --smoke --out local-validation
python scripts/generate_research_figures.py --input local-validation --out local-figures
```

Outcomes: **197 passed in 2.49 s**; all six analytic replay cases verified;
all six data-derived figures rendered. XML is preserved beside this report.
No comparison experiments or final holdout were run. The final follow-up commit
contains this verification evidence only, not a change to the tested engine.

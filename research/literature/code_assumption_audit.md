# Closest-code audit — 2026-11-17

| Prior work | Original code inspected | Consequence |
|---|---|---|
| PIBT | author Python `run/step/funcPIBT/DistTable`; C++ `run/funcPIBT` | Full-grid BFS/joint arrays are privileged; goals may be vacated. Unmodified Python reproduction is now executed separately. |
| Causal-PIBT | `agent.cpp`, `causal_pibt.cpp`, `mapf_random.cpp`, `problem.cpp`, app/graph integration | Shared occupancy queries and interacting-agent updates are atomic, rather than arbitrary packet delivery. Native reproduction preserves this distinction. |
| LSRP | headers, main, graph I/O, toy example/build files | Joint states/planned durations; modern optional support required. README license ambiguity prevents redistribution. Not executed. |

Primary sections checked against code:

- [PIBT](https://www.ijcai.org/Proceedings/2019/0076.pdf), sections 3–4:
  interaction groups must be identified; reachability can involve leaving goals.
  Its adjacent-pair cycle condition must not be casually equated with biconnectivity.
- [Causal-PIBT](https://arxiv.org/html/2005.13187), model, algorithms, properties
  and reachability appendix: fair activation and atomic interactions matter.
- [LSRP](https://arxiv.org/html/2412.11678), sections 2–5: duration conflicts and
  joint-state asynchronous push constrain comparability.

This resolves specific implementation assumptions, not the entire 15-paper
systematic review. Remaining source gaps and late-2026 work require review before
submission. Missing assumptions are not inferred from titles.

G1 decision: standard nonexpiring claims plus a freshness threshold do not
establish an independently novel method. Proceed with a **descriptive development
boundary study** isolating map-report overhead and failure/progress while holding
ownership fixed. Native references demonstrate the assumption gap; they do not
establish superiority under matched inputs. Do not draft an improvement abstract.

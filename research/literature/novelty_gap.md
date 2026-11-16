# Novelty gate G1 — OPEN, no contribution claim accepted

Three closest algorithmic comparisons are PIBT, Causal-PIBT and LSRP. Malka,
Shofer, MAGIC and communication-focused learned policies constrain the hidden-map
and messaging parts. A new combination is not evidence of a new mechanism.

| Closest work | Checked boundary | Missing evidence before a claim |
|---|---|---|
| [PIBT](https://www.ijcai.org/Proceedings/2019/0076.pdf), communication section and theorem 2 | local priority propagation; graph-conditional progress | how a new protocol differs under stale messages, beyond timestamped priorities |
| [Causal-PIBT](https://cdn.aaai.org/ojs/17347/17347-13-20841-1-2-20210518.pdf), model and theorem 2 | known graph and extended occupancy | full activation/communication assumptions and code equivalence |
| [LSRP](https://rap-lab.github.io/documents/publications/2025_AAAI_LSRP_ShuaiZhou.pdf), sections 2-4 | joint state and duration conflicts | fair local adaptation without importing joint state |
| [Shofer](https://doi.org/10.1609/icaps.v33i1.27219) | contingent preplanning of uncertain obstacles | full-text comparison still blocked by direct access |
| [Malka](https://mapf.info/abstracts/RSter24c.html) | affected-agent online repair | exact centralized/information/timing assumptions unverified |
| [MAGIC](https://arxiv.org/pdf/2609.40269), section III | shared uncertain-map belief | distinguish timestamped commitments from map-inference contribution |
| [LC-MAPF](https://arxiv.org/pdf/2605.07637), problem formulation | learned multi-round local coordination | match information and transport assumptions before empirical comparison |
| [DMM](https://arxiv.org/abs/2609.32019) | intent refinement before action | full-text assumptions still unverified |

Provisional direction: a controlled descriptive study of when stale information
increases waiting versus invalid attempted actions at local bottlenecks. This
is a question, not a priority claim. No candidate protocol has been tuned, no
contemporary baseline reproduced, and no improvement measured. There is no basis
for a methods manuscript yet. Finish source/code review and author assessment,
then either specify a distinct mechanism or pursue a reproducibility benchmark.

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

Update 2026-11-17: see `code_assumption_audit.md` and
`../reports/development_results.md`. Native PIBT/Causal-PIBT are reproduced and
a standard local claim/reporting prototype has been evaluated. It is not an
independently distinct new method. Development byte savings do not establish a
waiting/travel improvement, and progress remains poor. G1 and the improvement
gate remain unpassed. A descriptive reproducibility/boundary study is the honest
current outcome; modern matched baselines and progress recovery precede any
methods manuscript or final-holdout claim.

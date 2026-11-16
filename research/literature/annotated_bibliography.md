# Provisional annotated bibliography

Checked 2026-11-16. These notes distinguish inspected primary sections from
metadata-only records. They are not a completed systematic full-text review;
the missing proof/implementation audits keep G1 open. No reported performance
from another paper is treated as a result reproduced in this repository.

## PIBT — Okumura et al., IJCAI 2019

[Primary paper](https://www.ijcai.org/Proceedings/2019/0076.pdf). The model,
communication discussion and graph-conditional reachability statement were
inspected. PIBT coordinates adjacent moves through changing priorities,
inheritance and backtracking. Its synchronous iterative model and conditional
progress argument are essential comparison points. The conclusion explicitly
identifies asynchronous communication/movement as future work; that observation
does not imply every later extension leaves the same gap. The public pibt2
repository corresponds to a later journal implementation, so wrapping it must
record the version rather than silently calling it the 2019 algorithm.

For this project, the important limitation is the mismatch between a cycle-rich
graph assumption and arbitrary dead ends or single-width corridors. A failure
outside those assumptions is not evidence against the theorem. Before a fair
experiment, audit the selected implementation's goal handling, graph access,
priority messages and timing model. An adaptation to hidden maps must report
which guarantees are lost. A timestamp attached to priorities is not by itself
a demonstrated new contribution. Full proof and source-code equivalence remain
open review tasks.

## Causal-PIBT — Okumura, Tamura and Defago, AAAI 2021

[Primary paper](https://cdn.aaai.org/ojs/17347/17347-13-20841-1-2-20210518.pdf).
The time-independent model and theorem 2 were inspected. Agents know the graph;
contracted/requesting/extended states distinguish holding a location, asking to
move, and occupying head/tail while extended. The conditional reachability
statement includes biconnectivity and fewer agents than vertices. The scheduler,
activation fairness and exact communication assumptions must also be audited
before transferring the theorem. Asynchronous execution is therefore already
substantial prior work, not a contribution established by this project's event
queue.

The public implementation is the strongest immediate candidate for studying
progress under variable durations. However, giving that implementation a true
graph while a proposed policy sees only local cells would not answer a
matched-information question. First reproduce its native setting and label it
as a known-map reference; then document any local-map adaptation separately.
Failure with a stopped owner or missing messages should separate safety from
liveness. The new simulator's endpoint-resource abstraction supports examining
such traces, but does not constitute a faithful Causal-PIBT reproduction. Code
and complete proof review remain pending.

## LSRP — Zhou, Zhao and Ren, AAAI 2025

[Author PDF](https://rap-lab.github.io/documents/publications/2025_AAAI_LSRP_ShuaiZhou.pdf).
Sections 2–4 establish the relevant model and mechanism. Actions have positive
durations, agents share a clock, movements occupy endpoint resources, and the
method works with joint search states and cached asynchronous planning actions.
That is more specific than describing it merely as a decentralized asynchronous
planner. Its PIBT-derived coordination is a close algorithmic comparator;
timing support alone cannot distinguish a proposed freshness mechanism.

The verified public code landing page provides an implementation to inspect,
not a baseline already built or executed here. Integration requires recording
its state information, duration assumptions, objective and model boundaries.
The repository's legacy follow convention cannot be silently substituted for
duration conflicts. Likewise, unpredictable physical delay and delayed network
knowledge are separate axes; support for one must not imply the other. A useful
first experiment would reproduce a native known-map timeline before any
partial-map or lossy-message adaptation. The complete reachability proof,
implementation behavior and later LSRP* relationship remain open. No comparative
runtime or quality result is claimed from this source.

## PRIMAL2 — Damani et al., 2020 preprint / RA-L 2021

[Primary PDF](https://arxiv.org/pdf/2010.08184). The arXiv record links the 2021
published version; the attachment's 2020 date denotes its initial preprint.
The local observation discussion includes corridor endpoints, orientations,
blocking information and predicted neighbor motion. Those features matter for
an information-access comparison: a small visible window does not necessarily
mean an agent has no topology-derived or shared information. Corridor-aware
coordination also predates this project.

Before using PRIMAL2 as a matched baseline, inspect precisely how corridor
metadata is produced and whether that preprocessing uses the complete map or
agents beyond a field of view. Do not infer those privileges solely from the
word decentralized. Lifelong goal assignment differs from the primary one-shot
scope here, so any evaluation adaptation needs an explicit label. Training
architecture must be separated from deployed policy input. The inspected
sections support including this method in related work, but not a claim that
it tolerates arbitrary latency, packet loss or unknown topology. Model weights,
environment conventions and source-code reproduction remain unverified in this
milestone. No learned component has been added locally.

## SCRIMP — Wang et al., 2023 source version

[Primary PDF](https://arxiv.org/pdf/2303.00605). The abstract and communication
discussion were inspected. SCRIMP combines reinforcement/imitation learning,
small local fields of view and transformer communication. The text discusses
global communication and a local alternative. Consequently it is inaccurate
to treat every experiment under the same generic local-communication label.
The source record was verified without independently resolving its final venue
or claiming a new publication status.

For this project, the relevant overlap is coordination through exchanged
representations under limited visual information. A proposed selective-message
method must compare against the actual communication variant, count serialized
cost under an agreed interface, and avoid giving one policy more peers or map
preprocessing. Packet loss, stochastic transit time and clock assumptions remain
unverified; the title is insufficient evidence about any of them. Reproduction
would require the released model, exact observation channels, conflict
resolution behavior and training/evaluation split. Those tasks have not been
executed. This paper constrains a broad learned-communication claim, but does
not establish whether a specific new commitment protocol is distinct or useful.

## MAPF under obstacle uncertainty — Shofer, Shani and Stern, ICAPS 2023

[Primary citation](https://doi.org/10.1609/icaps.v33i1.27219). Indexed primary
abstract content and bibliographic identity were checked, but the direct
publisher PDF returned access denial. The checked material describes uncertain
obstacles and centralized contingent planning before execution. It therefore
prevents claiming that reacting to hidden obstacles is a new problem. It does
not justify filling in the paper's precise execution, communication or formal
guarantee fields; those stay unverified in the matrix.

The next review must recover a legitimate full text, enumerate the observation
branches, and determine which execution modes share information. Then select
one documented scenario and reproduce it under the original assumptions.
Comparing a contingent offline plan with online local decisions requires clear
labels for preparation cost, runtime information and observation timing. Do not
use a generic partial-map A* implementation as an authentic reproduction of
this method. At present the bibliography establishes overlap and an access
blockage, not a fully verified limitation or an experimentally demonstrated
failure mode. That distinction is a remaining G1 blocker rather than a reason
to omit this close prior work.

## Online inaccurate-map planning — Malka, Shani and Stern, IROS 2024

[Author-maintained record](https://mapf.info/abstracts/RSter24c.html). The
checked abstract describes interleaving sensing, planning and execution in
inaccurate graphs, repairing affected agents and deferring distant conflicts.
The original IEEE full text was not accessible in this session. Exact
centralization, action timing and communication assumptions therefore remain
unverified. The method is directly relevant to proposed incremental repairs;
that broad idea cannot be attributed to this project.

The next step is to recover the primary algorithm and its experimental
conventions, rather than assume a locally implemented replan loop is equivalent.
Record how the affected-agent set is computed, what map information is shared,
and when new observations become available. A global dependency check could
invalidate a decentralized same-information comparison even if repair itself
is local. Conversely, failure in a lossy asynchronous extension would not
refute the published method without matching its assumptions. No public-code
availability or reproduced performance is asserted here. This record supports
an overlap warning and a concrete reading task; the proposed novelty question
cannot be accepted merely because those unresolved details have not yet been
verified.

## MAGIC — Parimi et al., September 2026 preprint

[Primary PDF](https://arxiv.org/pdf/2609.40269). The record and problem sections
were inspected. The work treats fixed hidden discrepancies using a shared
probabilistic belief, spatial inference and detour-aware planning costs. Its
arXiv comment says under review; this is not confirmation of publication or
acceptance. The shared-belief formulation is a relevant distinction from the
independent local fact stores implemented here.

However, independent fact stores are infrastructure, not evidence of novelty.
A future claim must isolate what freshness changes about commitments or
execution, rather than rename uncertainty-aware routing. Comparison also needs
to separate map-discovery age, neighbor-intention age and resource ownership.
Those are different information types with different consequences for safety.
Before finalizing G1, inspect the full algorithm, source availability and
observation-sharing assumptions, and identify a concrete test that distinguishes
the mechanisms without changing information privileges. None of the paper's
reported improvements has been reproduced locally. No numerical performance
from it is included as our evidence. This newer work narrows the candidate
question and demonstrates why the literature must be refreshed before any
eventual submission.

## EECBS — Li, Ruml and Koenig, AAAI 2021

[Publisher citation](https://doi.org/10.1609/aaai.v35i14.17466) and
[author repository](https://github.com/Jiaoyang-Li/EECBS). Indexed publisher
metadata/abstract and the repository landing page were checked. Direct
publisher access was blocked, so complete method/proof verification remains
pending. EECBS is a bounded-suboptimal centralized solver and a stronger oracle
candidate than the educational CBS implementation. Its existence prevents a
claim of contemporary centralized superiority based only on the legacy code.

Before running it, record the selected revision, build dependencies, license,
suboptimality setting, time budget and map convention. Compare solution
efficiency with the same inputs, while disclosing implementation-language and
hardware differences for runtime. Its global map and fleet input belong in an
oracle column; they cannot be granted to a primary matched local competitor
without changing the question. There is no compiled binary, executed EECBS
run, or measured speed comparison in this milestone. The record supports a
baseline shortlist and reproduction task. It does not substitute for native
benchmark validation, nor establish how an offline solution should be safely
executed with uncertain action duration.

## MAPF-LNS2 — Li et al., AAAI 2022

[Author PDF](https://idm-lab.org/bib/abstracts/papers/aaai22a.pdf) and
[public code](https://github.com/Jiaoyang-Li/MAPF-LNS2). The author record,
available PDF and selected implementation discussion were inspected. LNS2
repairs colliding path sets by selecting neighborhoods and replanning; it is a
centralized large-scale reference. This constrains broad claims about repair
and scalability. Its published implementation context must be preserved when
interpreting comparisons with pure Python planners.

The important integration question is which inputs and collision conventions
the selected revision expects. A complete joint path set and known map would
be privileged under the new local-information setting. That is useful oracle
context, but cannot establish an advantage of a decentralized mechanism under
equal inputs. Before claiming a reproduction, build and test the actual solver,
record configuration and source hashes, verify returned trajectories, and
label asynchronous execution adapters separately. This session checked code
availability but did not compile or run it. The full proof and implementation
audit remain open. No speed, success, cost or scalability figure from the paper
is reported as a locally reproduced result.

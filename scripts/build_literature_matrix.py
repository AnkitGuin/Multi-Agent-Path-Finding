"""Materialize the literature matrix from manually checked primary-source notes.

Unverified fields deliberately remain unverified; this is not an automated
paper-review tool. Do not infer deployment guarantees from titles/abstracts.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = "id,authors,year,title,venue,status,doi_or_url,public_code,problem_variant,training,planning_architecture,execution_architecture,full_map_available,sensing,communication,async_actions,async_messages,collision_model,formal_guarantee,benchmarks,metrics,closest_overlap,verified_notes".split(",")
ROWS = [
    dict(id="stern2019", authors="Stern et al.", year=2019,
         title="Multi-Agent Pathfinding: Definitions, Variants, and Benchmarks", venue="SoCS",
         status="peer-reviewed", doi_or_url="https://arxiv.org/pdf/1906.08291",
         problem_variant="taxonomy and benchmarks", training="not applicable",
         collision_model="variant dependent", closest_overlap="explicit model choices",
         verified_notes="2026-11-16: primary PDF accessed; definitions sections inspected; not full systematic review"),
    dict(id="sharon2015", authors="Sharon; Stern; Felner; Sturtevant", year=2015,
         title="Conflict-based search for optimal multi-agent pathfinding", venue="Artificial Intelligence 219",
         status="peer-reviewed", doi_or_url="https://www.sciencedirect.com/science/article/pii/S0004370214001386",
         problem_variant="classical MAPF", training="not applicable", planning_architecture="centralized",
         full_map_available="yes", closest_overlap="legacy oracle",
         verified_notes="2026-11-16: publisher metadata/abstract verified; author PDF redirect inaccessible; proof audit pending"),
    dict(id="li2021eecbs", authors="Li; Ruml; Koenig", year=2021,
         title="EECBS: A Bounded-Suboptimal Search for Multi-Agent Path Finding", venue="AAAI",
         status="peer-reviewed", doi_or_url="https://doi.org/10.1609/aaai.v35i14.17466",
         public_code="https://github.com/Jiaoyang-Li/EECBS", training="not applicable",
         planning_architecture="centralized", full_map_available="yes", closest_overlap="strong oracle baseline",
         verified_notes="2026-11-16: indexed publisher record and public repository checked; direct publisher bot-blocked; full text pending"),
    dict(id="li2022lns2", authors="Li; Chen; Harabor; Stuckey; Koenig", year=2022,
         title="MAPF-LNS2: Fast Repairing for Multi-Agent Path Finding via Large Neighborhood Search",
         venue="AAAI", status="peer-reviewed", doi_or_url="https://idm-lab.org/bib/abstracts/papers/aaai22a.pdf",
         public_code="https://github.com/Jiaoyang-Li/MAPF-LNS2", training="not applicable",
         planning_architecture="centralized", full_map_available="yes", closest_overlap="collision-driven repair",
         verified_notes="2026-11-16: author record/PDF and code landing page checked; selected implementation sections inspected; not reproduced"),
    dict(id="okumura2019pibt", authors="Okumura; Machida; Defago; Tamura", year=2019,
         title="Priority Inheritance with Backtracking for Iterative Multi-agent Path Finding",
         venue="IJCAI", status="peer-reviewed", doi_or_url="https://www.ijcai.org/Proceedings/2019/0076.pdf",
         public_code="https://github.com/Kei18/pibt2 (later AIJ-22 implementation; version difference)",
         training="not applicable", problem_variant="iterative MAPF", planning_architecture="decentralizable",
         communication="local propagation", async_actions="no in this model",
         formal_guarantee="conditional graph-cycle reachability", closest_overlap="priority and backtracking",
         verified_notes="2026-11-16: primary model/communication/theorem sections inspected; full proof/code audit pending"),
    dict(id="damani2021primal2", authors="Damani; Luo; Wenzel; Sartoretti", year=2021,
         title="PRIMAL2: Pathfinding via Reinforcement and Imitation Multi-Agent Learning -- Lifelong",
         venue="IEEE RA-L", status="published version linked by arXiv; preprint first 2020",
         doi_or_url="https://arxiv.org/pdf/2010.08184", problem_variant="lifelong partially observable MAPF",
         training="reinforcement and imitation", execution_architecture="decentralized policy",
         sensing="local observation with corridor features", closest_overlap="corridor conventions",
         verified_notes="2026-11-16: source PDF corridor observation section inspected; global preprocessing privileges require audit"),
    dict(id="wang2023scrimp", authors="Wang; Xiang; Huang; Sartoretti", year=2023,
         title="SCRIMP: Scalable Communication for Reinforcement- and Imitation-Learning-Based Multi-Agent Pathfinding",
         venue="arXiv source version", status="preprint record verified; venue not rechecked",
         doi_or_url="https://arxiv.org/pdf/2303.00605", training="reinforcement and imitation",
         execution_architecture="local policy with communication", sensing="small FOV",
         communication="transformer global/local variants", closest_overlap="learned communication",
         verified_notes="2026-11-16: PDF abstract and communication section inspected; packet-loss guarantees unverified"),
    dict(id="skrynnik2024mcts", authors="Skrynnik; Andreychuk; Yakovlev; Panov", year=2024,
         title="Decentralized Monte Carlo Tree Search for Partially Observable Multi-Agent Pathfinding",
         venue="AAAI", status="peer-reviewed", doi_or_url="https://doi.org/10.1609/aaai.v38i16.29703",
         public_code="https://github.com/AIRI-Institute/mats-lp (publisher link; code not audited)",
         problem_variant="partially observable lifelong MAPF", planning_architecture="decentralized MCTS",
         sensing="local observations", communication="restricted", closest_overlap="local online planning",
         verified_notes="2026-11-16: indexed publisher metadata/abstract verified; direct access blocked; full text unverified"),
    dict(id="okumura2021causal", authors="Okumura; Tamura; Defago", year=2021,
         title="Time-Independent Planning for Multiple Moving Agents", venue="AAAI", status="peer-reviewed",
         doi_or_url="https://cdn.aaai.org/ojs/17347/17347-13-20841-1-2-20210518.pdf",
         public_code="https://github.com/Kei18/time-independent-planning", training="not applicable",
         planning_architecture="online distributed", full_map_available="yes",
         async_actions="time-independent atomic transitions", collision_model="extended head/tail occupancy",
         formal_guarantee="biconnected graph and agents fewer than vertices; other scheduler assumptions must be audited",
         closest_overlap="asynchronous commitment", verified_notes="2026-11-16: model and theorem 2 inspected; full scheduler/proof audit pending"),
    dict(id="zhou2025lsrp", authors="Zhou; Zhao; Ren", year=2025,
         title="Loosely Synchronized Rule-Based Planning for Multi-Agent Path Finding with Asynchronous Actions",
         venue="AAAI", status="peer-reviewed", doi_or_url="https://rap-lab.github.io/documents/publications/2025_AAAI_LSRP_ShuaiZhou.pdf",
         public_code="https://github.com/rap-lab-org/public_LSRP", training="not applicable",
         planning_architecture="joint-state search", full_map_available="yes",
         async_actions="positive edge durations; shared clock", collision_model="duration endpoint conflicts",
         closest_overlap="asynchronous PIBT-derived coordination",
         verified_notes="2026-11-16: sections 2-4 inspected; not evidence of delayed/lossy decentralized deployment"),
    dict(id="shofer2023ou", authors="Shofer; Shani; Stern", year=2023,
         title="Multi Agent Path Finding Under Obstacle Uncertainty", venue="ICAPS", status="peer-reviewed",
         doi_or_url="https://doi.org/10.1609/icaps.v33i1.27219", problem_variant="hidden obstacles",
         planning_architecture="centralized contingent preplanning", full_map_available="uncertain obstacles",
         closest_overlap="observation-conditioned plans",
         verified_notes="2026-11-16: indexed primary PDF abstract verified; direct full text bot-blocked; execution guarantees unverified"),
    dict(id="malka2024im", authors="Malka; Shani; Stern", year=2024,
         title="Online Planning for Multi Agent Path Finding in Inaccurate Maps", venue="IROS",
         status="peer-reviewed", doi_or_url="https://mapf.info/abstracts/RSter24c.html",
         problem_variant="inaccurate graph", sensing="nearby edge verification",
         closest_overlap="selective online replanning",
         verified_notes="2026-11-16: author abstract and IROS citation verified; IEEE full text inaccessible; algorithm details unverified"),
    dict(id="parimi2026magic", authors="Parimi; Chan; Zhang; Chen; Williams", year=2026,
         title="Belief-Aware Multi-Agent Path Finding under Map Uncertainty", venue="arXiv",
         status="preprint; arXiv comments say under review", doi_or_url="https://arxiv.org/pdf/2609.40269",
         problem_variant="fixed hidden discrepancies", full_map_available="shared uncertain map belief",
         closest_overlap="belief-aware detour costs",
         verified_notes="2026-11-16: record and model sections inspected; no publication acceptance inferred"),
    dict(id="vyaltsev2026lc", authors="Vyaltsev et al.", year=2026,
         title="Learning to Communicate Locally for Large-Scale Multi-Agent Pathfinding", venue="arXiv",
         status="preprint", doi_or_url="https://arxiv.org/pdf/2605.07637",
         problem_variant="decentralized MAPF", communication="multi-round local learned messages",
         async_actions="synchronous problem formulation", closest_overlap="local coordination through messages",
         verified_notes="2026-11-16: record/PDF problem sections inspected; delayed transport assumptions unverified"),
    dict(id="vyaltsev2026dmm", authors="Vyaltsev; Andreychuk; Zlotnikova; Yakovlev; Panov; Skrynnik", year=2026,
         title="Decentralized Master-Mind: Joint Action Refinement through Iterative Intent Denoising in Multi-Agent Pathfinding",
         venue="arXiv", status="preprint", doi_or_url="https://arxiv.org/abs/2609.32019",
         training="imitation and reinforcement per abstract", communication="iterative local intent refinement",
         closest_overlap="coordination before action commitment",
         verified_notes="2026-11-16: primary record/abstract verified; PDF fetch failed; full assumptions unverified")
]


def main():
    directory = ROOT / "research/literature"
    for row in ROWS:
        if row["id"] == "okumura2019pibt":
            row["verified_notes"] += "; 2026-11-17: author Python AIJ-version code audited and vendored unchanged; 8 upstream tests and 20 native runs passed; vacatable-goal semantics recorded"
        elif row["id"] == "okumura2021causal":
            row["communication"] = "atomic interacting-agent updates; arbitrary packet implementation not specified"
            row["execution_architecture"] = "native known-graph atomic activation; vacatable goals"
            row["verified_notes"] += "; 2026-11-17: algorithm/code/activation assumptions inspected; original C++ built; 20 native traces independently checked"
        elif row["id"] == "zhou2025lsrp":
            row["verified_notes"] += "; 2026-11-17: original source audited; GCC6.3 build failed; conflicting README license statements; not reproduced"
    with (directory/"literature_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, FIELDS)
        writer.writeheader()
        writer.writerows({key: row.get(key, "unverified") for key in FIELDS} for row in ROWS)
    (directory/"source_review_manifest.json").write_text(json.dumps(
        dict(checked_date="2026-11-17", rows=ROWS,
             review_status="partial; primary identities checked, not a full-text systematic review"), indent=2), encoding="utf-8")
    print(f"wrote {len(ROWS)} checked primary-source records")


if __name__ == "__main__":
    main()

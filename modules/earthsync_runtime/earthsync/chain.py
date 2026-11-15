"""EvidenceFusion chain: NASA source -> transformation -> feature -> constraint rule -> evaluation -> decision input.

EarthSync does not own crop rules (SoilBrain does) and does not decide rotations (RootShift does).
A ``ConstraintRule`` is therefore *supplied by the caller* with its owner and evidence. EarthSync's job is to
(1) evaluate the NASA-derived feature against that rule, honouring bounds and missing data, and
(2) record the complete lineage so any downstream number can be traced back to a NASA dataset.

Evaluation outcomes (``status``)
  satisfied / violated        - decidable from the feature (even with missing days, if the bound decides it)
  indeterminate_bounded       - missing days make the feature straddle the threshold
  insufficient_evidence       - feature could not be computed: downstream must NOT draw a confident conclusion
"""
from __future__ import annotations

import hashlib
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from .cache import canonical_json
from .schemas import (EvidenceRecord, Feature, Insufficiency, InsufficiencyCode, ProvenanceEdge, ProvenanceGraph, ProvenanceNode, EnvironmentalSeries)

_OPS = {">=": lambda v, t: v >= t, ">": lambda v, t: v > t, "<=": lambda v, t: v <= t, "<": lambda v, t: v < t}


class ConstraintRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    description: str
    violation_if: Literal[">=", ">", "<=", "<"]
    threshold: float
    unit: str
    owner: str = "SoilBrain"
    rule_source: str                     # citation, or 'DEMO ...' when illustrative
    rule_evidence_urls: list[str] = Field(default_factory=list)
    is_demo: bool = False
    applies_to: str = ""                 # e.g. crop/stage label supplied by owner
    consequence_if_violated: str = ""    # plain-language consequence supplied by owner


class ConstraintEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evaluation_id: str
    rule_id: str
    feature_id: str
    status: Literal["satisfied", "violated", "indeterminate_bounded", "insufficient_evidence"]
    observed_value: Optional[float] = None
    observed_lower: Optional[float] = None
    observed_upper: Optional[float] = None
    threshold: float
    margin: Optional[float] = None       # signed: positive = on the violating side
    decision_effect: Literal["none", "flag_risk", "refuse_confident_conclusion"]
    insufficiency: list[Insufficiency] = Field(default_factory=list)
    message: str
    is_synthetic: bool = False
    is_demo_rule: bool = False


class EvidenceChain(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: str = "1.0.0"
    chain_id: str
    title: str
    question: str
    features: list[Feature]
    rule: ConstraintRule
    evaluation: ConstraintEvaluation
    graph: ProvenanceGraph
    farmer_interpretation: dict[str, Any]
    banner: Optional[str] = None
    is_synthetic: bool = False
    is_demo_rule: bool = False
    limitations: list[str] = Field(default_factory=list)


def evaluate_rule(rule: ConstraintRule, feature: Feature) -> ConstraintEvaluation:
    eid = "eval:" + hashlib.sha256(canonical_json([rule.rule_id, feature.feature_id, rule.threshold]).encode()).hexdigest()[:10]
    common = dict(evaluation_id=eid, rule_id=rule.rule_id, feature_id=feature.feature_id, threshold=rule.threshold,
                  is_synthetic=feature.is_synthetic, is_demo_rule=rule.is_demo)
    if feature.unit and rule.unit and feature.unit != rule.unit:
        ins = Insufficiency(code=InsufficiencyCode.unit_unrecognized, message=f"Feature unit {feature.unit!r} != rule unit {rule.unit!r}")
        return ConstraintEvaluation(status="insufficient_evidence", decision_effect="refuse_confident_conclusion", insufficiency=[ins],
                                    message="Unit mismatch between feature and rule; refusing to compare.", **common)
    if feature.status == "insufficient" or feature.value is None:
        return ConstraintEvaluation(status="insufficient_evidence", decision_effect="refuse_confident_conclusion", insufficiency=list(feature.insufficiency),
                                    message=("Essential NASA-derived input unavailable: " + "; ".join(i.message for i in feature.insufficiency)) or "Feature unavailable",
                                    **common)
    op = _OPS[rule.violation_if]
    lo = feature.value_lower if feature.value_lower is not None else feature.value
    hi = feature.value_upper if feature.value_upper is not None else feature.value
    if feature.status == "bounded" and feature.value_upper is None:
        # one-sided lower bound only (e.g. rainfall total with missing days): only 'violated' for >= rules can be certain
        hi = float("inf")
    sign = 1.0 if rule.violation_if in (">=", ">") else -1.0
    margin = sign * (feature.value - rule.threshold)
    sure_violation = op(lo, rule.threshold) and op(hi, rule.threshold)
    sure_ok = (not op(lo, rule.threshold)) and (not op(hi, rule.threshold))
    if feature.status == "computed" or sure_violation or sure_ok:
        violated = op(feature.value, rule.threshold) if feature.status == "computed" else sure_violation
        return ConstraintEvaluation(status="violated" if violated else "satisfied", observed_value=feature.value, observed_lower=lo, observed_upper=None if hi == float("inf") else hi,
                                    margin=margin, decision_effect="flag_risk" if violated else "none",
                                    message=f"{feature.name} = {feature.value:g} {feature.unit} vs rule '{rule.violation_if} {rule.threshold:g}' -> {'VIOLATED' if violated else 'not violated'}.",
                                    **common)
    return ConstraintEvaluation(status="indeterminate_bounded", observed_value=feature.value, observed_lower=lo, observed_upper=None if hi == float("inf") else hi,
                                margin=margin, decision_effect="refuse_confident_conclusion",
                                insufficiency=[Insufficiency(code=InsufficiencyCode.insufficient_coverage,
                                                              message="Missing days leave the feature on both sides of the threshold; cannot decide.", severity="blocking")],
                                message=f"{feature.name} lies in [{lo:g}, {'inf' if hi == float('inf') else format(hi, 'g')}] {feature.unit}: straddles threshold {rule.threshold:g}.",
                                **common)


def interpretation(rule: ConstraintRule, ev: ConstraintEvaluation, feature: Feature) -> dict[str, Any]:
    """Plain-language, non-prescriptive interpretation. ``key``+``params`` allow Agent 09 to localise (English/Bangla)."""
    params = {"feature": feature.name, "value": ev.observed_value, "unit": feature.unit, "threshold": rule.threshold, "window": f"{feature.window_start} to {feature.window_end}",
              "applies_to": rule.applies_to}
    if ev.status == "violated":
        text = (f"In {params['window']} the NASA-derived grid-cell estimate for '{feature.name}' was {ev.observed_value:g} {feature.unit}, past the "
                f"supplied limit of {rule.threshold:g}. {rule.consequence_if_violated or 'This is a risk flag for the rule owner to weigh; it is not a measurement of your field.'}")
        key = "evidence.rule_violated"
    elif ev.status == "satisfied":
        text = (f"In {params['window']} the grid-cell estimate for '{feature.name}' ({ev.observed_value:g} {feature.unit}) stayed within the supplied limit of "
                f"{rule.threshold:g}. Local conditions on your field can still differ.")
        key = "evidence.rule_satisfied"
    elif ev.status == "indeterminate_bounded":
        text = f"Gaps in the satellite/model record mean '{feature.name}' could be either side of {rule.threshold:g}; no conclusion is drawn."
        key = "evidence.rule_indeterminate"
    else:
        text = f"EarthSync does not have enough NASA-derived data to evaluate this constraint ({ev.message}). No conclusion is drawn and nothing was assumed."
        key = "evidence.insufficient"
    return {"key": key, "params": params, "text_en": text, "is_prescriptive": False}


def build_graph(chain_id: str, series: list[EnvironmentalSeries], evidence: dict[str, EvidenceRecord], feature: Feature, rule: ConstraintRule,
                ev: ConstraintEvaluation, interp: dict[str, Any], extra_series: list[EnvironmentalSeries] | None = None) -> ProvenanceGraph:
    nodes: dict[str, ProvenanceNode] = {}
    edges: list[ProvenanceEdge] = []

    def add_node(n: ProvenanceNode) -> None:
        nodes.setdefault(n.node_id, n)

    def add_series(s: EnvironmentalSeries) -> None:
        add_node(ProvenanceNode(node_id=s.series_id, kind="series", label=f"{s.provider_variable} ({s.unit})",
                                detail={"variable": s.variable, "mode": s.retrieval_mode, "data_type": s.data_type, "is_synthetic": s.is_synthetic,
                                        "span": [s.dates[0], s.dates[-1]], "footprint": s.spatial.cell_id}))
        e = evidence.get(s.evidence_id)
        if e is None:
            return
        src_id = f"src:{e.source_id}:{e.evidence_id}"
        add_node(ProvenanceNode(node_id=src_id, kind="source", label=f"{e.provider} - {e.dataset_name}",
                                detail={"source_id": e.source_id, "url": e.original_url, "retrieved_at_utc": e.retrieved_at_utc, "mode": e.retrieval_mode,
                                        "license": e.license.name, "version": e.dataset_version, "is_synthetic": e.is_synthetic, "evidence_id": e.evidence_id,
                                        "native_resolution": f"{e.spatial.native_resolution_lat_deg}x{e.spatial.native_resolution_lon_deg} deg"}))
        # derived evidence: link to its inputs recursively
        in_ids = e.extras.get("input_series_ids") if e.extras else None
        if in_ids:
            for t in e.transformations:
                tid = f"xf:{e.evidence_id}:{t.step_id}"
                add_node(ProvenanceNode(node_id=tid, kind="transformation", label=t.name, detail={"params": t.params, "version": t.version, "description": t.description}))
                edges.append(ProvenanceEdge(src=tid, dst=s.series_id, relation="produces"))
                for iid in in_ids:
                    edges.append(ProvenanceEdge(src=iid, dst=tid, relation="derived_by"))
            edges.append(ProvenanceEdge(src=src_id, dst=s.series_id, relation="retrieved_as"))
        else:
            tid = f"xf:{e.evidence_id}:harmonise"
            add_node(ProvenanceNode(node_id=tid, kind="transformation", label="harmonise: fill->missing, units, QC bounds",
                                    detail={"steps": [t.name for t in e.transformations]}))
            edges.append(ProvenanceEdge(src=src_id, dst=s.series_id, relation="retrieved_as"))
            edges.append(ProvenanceEdge(src=tid, dst=s.series_id, relation="produces"))

    all_series = list(series) + list(extra_series or [])
    for s in all_series:
        add_series(s)
    fid = feature.feature_id
    add_node(ProvenanceNode(node_id=fid, kind="feature", label=f"{feature.name} [{feature.status}]",
                            detail={"value": feature.value, "unit": feature.unit, "window": [feature.window_start, feature.window_end], "method": feature.method_id,
                                    "params": feature.method_params, "coverage": feature.coverage.model_dump() if feature.coverage else None}))
    mid = f"xf:{fid}:method"
    add_node(ProvenanceNode(node_id=mid, kind="transformation", label=f"feature method: {feature.method_id}", detail={"params": feature.method_params, "version": feature.method_version}))
    for sid in feature.input_series_ids:
        edges.append(ProvenanceEdge(src=sid, dst=mid, relation="derived_by"))
    edges.append(ProvenanceEdge(src=mid, dst=fid, relation="produces"))
    rid = f"rule:{rule.rule_id}"
    add_node(ProvenanceNode(node_id=rid, kind="rule", label=f"{rule.owner} rule: {rule.description}",
                            detail={"threshold": rule.threshold, "unit": rule.unit, "source": rule.rule_source, "is_demo": rule.is_demo, "urls": rule.rule_evidence_urls}))
    edges.append(ProvenanceEdge(src=fid, dst=ev.evaluation_id, relation="evaluated_against"))
    edges.append(ProvenanceEdge(src=rid, dst=ev.evaluation_id, relation="evaluated_against"))
    add_node(ProvenanceNode(node_id=ev.evaluation_id, kind="evaluation", label=f"{ev.status}", detail=ev.model_dump(mode="json")))
    did = f"decision_input:{chain_id}"
    add_node(ProvenanceNode(node_id=did, kind="decision_input", label="RootShift/SoilBrain constraint input",
                            detail={"decision_effect": ev.decision_effect, "note": "EarthSync supplies evidence; rotation decision belongs to RootShift."}))
    edges.append(ProvenanceEdge(src=ev.evaluation_id, dst=did, relation="constrains"))
    iid = f"interp:{chain_id}"
    add_node(ProvenanceNode(node_id=iid, kind="interpretation", label=interp["text_en"][:140], detail={"key": interp["key"]}))
    edges.append(ProvenanceEdge(src=did, dst=iid, relation="explained_as"))
    # keep only edges whose endpoints exist
    edges = [e for e in edges if e.src in nodes and e.dst in nodes]
    return ProvenanceGraph(graph_id=f"graph:{chain_id}", nodes=list(nodes.values()), edges=edges)


def validate_graph(g: ProvenanceGraph) -> list[str]:
    """Return a list of integrity problems (empty = OK): dangling edges, cycles, features/evals not reachable from a source."""
    ids = {n.node_id for n in g.nodes}
    problems = [f"dangling edge {e.src}->{e.dst}" for e in g.edges if e.src not in ids or e.dst not in ids]
    adj: dict[str, list[str]] = {i: [] for i in ids}
    for e in g.edges:
        if e.src in adj:
            adj[e.src].append(e.dst)
    state: dict[str, int] = {}

    def dfs(u: str) -> bool:
        state[u] = 1
        for v in adj.get(u, []):
            if state.get(v) == 1 or (state.get(v) is None and dfs(v)):
                return True
        state[u] = 2
        return False

    if any(state.get(i) is None and dfs(i) for i in ids):
        problems.append("cycle detected")
    sources = {n.node_id for n in g.nodes if n.kind == "source"}
    seen, stack = set(sources), list(sources)
    while stack:
        u = stack.pop()
        for v in adj.get(u, []):
            if v not in seen:
                seen.add(v)
                stack.append(v)
    for n in g.nodes:
        if n.kind in ("series", "feature", "evaluation", "decision_input", "interpretation") and n.node_id not in seen:
            problems.append(f"{n.kind} {n.node_id} not reachable from any NASA/source node")
    return problems


def graph_to_mermaid(g: ProvenanceGraph) -> str:
    sh = {"source": "([{}])", "series": "[{}]", "transformation": "{{{{{}}}}}", "feature": "[/{}/]", "rule": "[[{}]]", "evaluation": "{}", "decision_input": "[{}]", "interpretation": "({})"}
    idx = {n.node_id: f"n{i}" for i, n in enumerate(g.nodes)}
    lines = ["flowchart LR"]
    for n in g.nodes:
        label = n.label.replace('"', "'")[:70]
        fmt = sh.get(n.kind, "[{}]")
        lines.append(f'  {idx[n.node_id]}{fmt.format(chr(34) + label + chr(34))}')
    for e in g.edges:
        lines.append(f"  {idx[e.src]} -->|{e.relation}| {idx[e.dst]}")
    return "\n".join(lines)


def build_chain(*, title: str, question: str, feature: Feature, rule: ConstraintRule, series: list[EnvironmentalSeries], evidence: dict[str, EvidenceRecord],
                extra_series: list[EnvironmentalSeries] | None = None, limitations: list[str] | None = None) -> EvidenceChain:
    ev = evaluate_rule(rule, feature)
    interp = interpretation(rule, ev, feature)
    cid = "chain:" + hashlib.sha256(canonical_json([feature.feature_id, rule.rule_id, rule.threshold]).encode()).hexdigest()[:10]
    syn = feature.is_synthetic
    banner = ("SYNTHETIC DEMONSTRATION DATA - generated for UI/pipeline demonstration, NOT a NASA retrieval. Do not present these numbers as measurements."
              if syn else None)
    if rule.is_demo:
        banner = (banner + " " if banner else "") + "DEMO RULE - threshold is illustrative and must be replaced by a cited value from the rule owner."
    g = build_graph(cid, series, evidence, feature, rule, ev, interp, extra_series)
    return EvidenceChain(chain_id=cid, title=title, question=question, features=[feature], rule=rule, evaluation=ev, graph=g, farmer_interpretation=interp,
                         banner=banner, is_synthetic=syn, is_demo_rule=rule.is_demo,
                         limitations=(limitations or []) + [
                             "Grid-cell estimate (tens of km), not a measurement in the field.",
                             "EarthSync supplies evidence only; the rotation decision and crop rule belong to RootShift/SoilBrain."])

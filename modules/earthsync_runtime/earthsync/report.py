"""Exportable EvidenceFusion report: JSON (frontend-ready) + Markdown (human-readable)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from . import chain as CH
from .compare import DatasetComparison
from .schemas import EnvironmentalSeries, EvidenceRecord, clean_floats


def build_report(*, location: dict, chains: list[CH.EvidenceChain], evidence: dict[str, EvidenceRecord], series: dict[str, EnvironmentalSeries],
                 comparison: Optional[DatasetComparison], availability: Optional[dict], extra_features: Optional[list] = None) -> dict:
    syn = any(c.is_synthetic for c in chains) or any(s.is_synthetic for s in series.values())
    used_ev = sorted({n.detail["evidence_id"] for c in chains for n in c.graph.nodes if n.kind == "source"})
    unavailable = []
    if availability:
        unavailable = [{"source_id": r["source_id"], "name": r["name"], "access_now": r["access_now"], "reason": r["reason"]}
                       for r in availability["sources"] if r["priority"] in ("P0", "P1") and r["access_now"] not in ("available_via_cache", "available_real_fixture", "methodology_only", "owned_by_other_agent")]
    return clean_floats({
        "schema_version": "1.0.0", "report_type": "earthsync_evidencefusion",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_synthetic": syn,
        "banner": ("SYNTHETIC DEMONSTRATION DATA - not a NASA retrieval; numbers illustrate the pipeline only." if syn else None),
        "location": location,
        "chains": [c.model_dump(mode="json") for c in chains],
        "extra_features": [f.model_dump(mode="json") for f in (extra_features or [])],
        "evidence_records": [evidence[i].model_dump(mode="json") for i in used_ev if i in evidence],
        "comparison": comparison.model_dump(mode="json") if comparison else None,
        "unavailable_priority_sources": unavailable,
        "series_summaries": [{"series_id": s.series_id, "variable": s.provider_variable, "unit": s.unit, "span": [s.dates[0], s.dates[-1]], "mode": s.retrieval_mode,
                              "data_type": s.data_type, "is_synthetic": s.is_synthetic, "footprint": s.spatial.cell_id} for s in series.values()],
    })


def _fmt(v, nd=1):
    return "n/a" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def render_markdown(rep: dict) -> str:
    L: list[str] = ["# EarthSync EvidenceFusion report", ""]
    if rep.get("banner"):
        L += [f"> **{rep['banner']}**", ""]
    loc = rep["location"]
    L += [f"**Location:** {loc.get('label', '')} ({loc.get('lat')}, {loc.get('lon')}) · generated {rep['generated_at_utc']}", "",
          "_Each result below is a chain: NASA source → harmonised series → feature → supplied rule → evaluation → input for RootShift. "
          "Values describe a grid cell, not an individual field._", ""]
    for c in rep["chains"]:
        f = c["features"][0]
        ev = c["evaluation"]
        L += [f"## {c['title']}", f"**Question:** {c['question']}", ""]
        if c.get("banner"):
            L += [f"> {c['banner']}", ""]
        L += ["| Step | Detail |", "|---|---|"]
        for n in c["graph"]["nodes"]:
            d = n["detail"]
            if n["kind"] == "source":
                L.append(f"| {'SYNTHETIC source (NOT NASA)' if d.get('is_synthetic') else 'NASA/source'} | {n['label']} · mode `{d.get('mode')}` · retrieved {d.get('retrieved_at_utc') or 'n/a'} · {d.get('native_resolution')} · {d.get('license')} · {d.get('url') or 'n/a'} |")
            elif n["kind"] == "series":
                L.append(f"| Series | {n['label']} · {d['span'][0]}…{d['span'][1]} · `{d['data_type']}` · {d['footprint']} |")
            elif n["kind"] == "transformation":
                L.append(f"| Transformation | {n['label']} |")
        cov = f.get("coverage") or {}
        L += [f"| Feature | **{f['name']}** = {_fmt(f['value'])} {f['unit']} · status `{f['status']}` · window {f['window_start']}…{f['window_end']} · valid {cov.get('valid_days')}/{cov.get('expected_days')} days |",
              f"| Rule ({c['rule']['owner']}) | {c['rule']['description']} · threshold {c['rule']['threshold']} {c['rule']['unit']} · source: {c['rule']['rule_source']} |",
              f"| Evaluation | `{ev['status']}` → decision effect `{ev['decision_effect']}` |", ""]
        L += [f"**Interpretation (non-prescriptive):** {c['farmer_interpretation']['text_en']}", ""]
        if f.get("caveats"):
            L += ["Caveats: " + " ".join(f["caveats"]), ""]
    cmp = rep.get("comparison")
    L += ["## Rainfall cross-check (POWER vs second product)"]
    if not cmp or cmp["status"] != "computed":
        why = "; ".join(i["message"] for i in (cmp or {}).get("insufficiency", [])) or "No second precipitation dataset was supplied."
        L += [f"**Not run.** {why}", "_No substitute value was used; downstream receives a typed insufficiency._", ""]
    else:
        m = cmp["metrics"]
        L += [f"Compared {cmp['a_label']} with {cmp['b_label']} over {cmp['n_valid_pairs']} paired days ({cmp['unit']}). Totals: A {_fmt(m['total_a'])}, B {_fmt(m['total_b'])} "
              f"(envelope {_fmt(cmp['envelope_totals']['total_min'])}–{_fmt(cmp['envelope_totals']['total_max'])}). r = {_fmt(m['pearson_r'], 2)}. "
              f"Flags: {', '.join(cmp['disagreement_flags']) or 'none'}. Use: **{cmp['recommended_use']}**.", ""]
    L += ["## Priority sources not available in this report"]
    for u in rep.get("unavailable_priority_sources", []):
        L.append(f"- **{u['source_id']}** ({u['access_now']}): {u['reason']}")
    L += ["", "## Evidence records"]
    for e in rep["evidence_records"]:
        L.append(f"- `{e['evidence_id']}` {e['dataset_name']} · {e['provider']} · mode `{e['retrieval_mode']}` · sha256 `{(e.get('payload_sha256') or 'n/a')[:12]}` · license {e['license']['name']}"
                 + (" · **SYNTHETIC**" if e["is_synthetic"] else ""))
    L += ["", "## Lineage graph (Mermaid)"]
    for c in rep["chains"]:
        g = CH.ProvenanceGraph.model_validate(c["graph"])
        L += [f"```mermaid\n{CH.graph_to_mermaid(g)}\n```", ""]
    L += ["## Limitations", "- POWER is gridded reanalysis/satellite-blend meteorology, not an in-field sensor and not a forecast.",
          "- Rules marked DEMO are illustrative; crop thresholds belong to SoilBrain.", "- EarthSync supplies evidence; RootShift owns the rotation decision."]
    return "\n".join(L) + "\n"


def to_json(rep: dict) -> str:
    return json.dumps(rep, indent=2, ensure_ascii=False)

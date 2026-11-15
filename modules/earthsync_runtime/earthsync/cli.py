"""Command line: python -m earthsync <command>   (JSON on stdout; exit code 0 ok / 2 insufficient)"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import chain as CH
from .access_policy import AccessPolicy
from .manifest import write_manifest
from .report import build_report, render_markdown, to_json
from .service import EarthSync

PILOTS = {"BD_RAJSHAHI_BARIND": (24.3745, 88.6042, "BD", "Rajshahi (Barind Tract), Bangladesh"), "US_IOWA_STORY": (42.0308, -93.6319, "US", "Story County, Iowa, USA")}


def _dump(o) -> None:
    print(json.dumps(o, indent=2, ensure_ascii=False, default=lambda x: x.model_dump(mode="json") if hasattr(x, "model_dump") else str(x)))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="earthsync")
    ap.add_argument("--offline", action="store_true", help="never touch the network")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("manifest", help="print source manifest summary").add_argument("--write", action="store_true")
    a = sub.add_parser("availability"); a.add_argument("--country", required=True); a.add_argument("--lat", type=float, required=True); a.add_argument("--lon", type=float, required=True)
    s = sub.add_parser("series"); [s.add_argument(f"--{k}", type=float if k in ("lat", "lon") else str, required=True) for k in ("lat", "lon", "start", "end")]
    s.add_argument("--vars", default="T2M,PRECTOTCORR"); s.add_argument("--allow-synthetic", action="store_true")
    r = sub.add_parser("report", help="end-to-end EvidenceFusion report for a pilot"); r.add_argument("--pilot", choices=list(PILOTS), default="BD_RAJSHAHI_BARIND")
    r.add_argument("--year", type=int, default=2024); r.add_argument("--allow-synthetic", action="store_true"); r.add_argument("--out", default="examples")
    args = ap.parse_args(argv)
    pol = AccessPolicy()
    pol.offline = pol.offline or args.offline
    es = EarthSync(pol)
    if args.cmd == "manifest":
        if args.write:
            print(write_manifest())
        _dump([{k: e[k] for k in ("source_id", "organizer_listed", "priority_bd", "priority_us", "live_decision", "applicability")} for e in es.list_sources()])
        return 0
    if args.cmd == "availability":
        _dump(es.get_data_availability(args.country, args.lat, args.lon)); return 0
    if args.cmd == "series":
        res = es.get_environmental_series(args.lat, args.lon, args.start, args.end, tuple(args.vars.split(",")), allow_fixture=args.allow_synthetic)
        _dump(res); return 0 if res.status != "insufficient" else 2
    if args.cmd == "report":
        lat, lon, cc, label = PILOTS[args.pilot]
        res = es.get_environmental_series(lat, lon, f"{args.year - 1}-01-01", f"{args.year}-12-31",
                                          ("T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "ALLSKY_SFC_SW_DWN", "RH2M", "WS2M", "PS"), allow_fixture=args.allow_synthetic)
        if res.status == "insufficient":
            _dump(res); return 2
        S = es.series_objects(res)
        chains = es.demo_chains(S, args.year) if cc == "BD" else es.demo_chains(S, args.year, md_dryspell=("06-01", "08-31"), md_heat=("07-01", "07-31"))
        cmp = es.compare_climate_datasets(S.get("PRECTOTCORR"), None, missing_label="second precipitation dataset (GPM IMERG extract not supplied)")
        rep = build_report(location={"label": label, "lat": lat, "lon": lon, "country_iso": cc}, chains=chains, evidence=es.store["evidence"], series=S, comparison=cmp,
                           availability=es.get_data_availability(cc, lat, lon))
        out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
        (out / f"evidencefusion_report_{args.pilot}.json").write_text(to_json(rep), encoding="utf-8")
        (out / f"evidencefusion_report_{args.pilot}.md").write_text(render_markdown(rep), encoding="utf-8")
        print(f"wrote {out}/evidencefusion_report_{args.pilot}.(json|md)")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())

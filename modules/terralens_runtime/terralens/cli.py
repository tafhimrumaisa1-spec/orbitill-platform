"""Command-line entry point: ``python3 -m terralens <command>``."""
from __future__ import annotations

import argparse
import json
import sys

from . import catalog, data, field, router, server
from .types import Status


def _print(payload: dict, pretty: bool = True) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
    else:
        print(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")))


def _profile(args) -> int:
    profile = router.get_region_profile(
        args.lat, args.lon, locale=args.locale, requested_region=args.region
    )
    _print(profile.to_dict(), pretty=not args.compact)
    return 0


def _search(args) -> int:
    results = data.store().search(args.query, args.country, args.limit)
    _print({"query": args.query, "results": results}, pretty=not args.compact)
    return 0


def _field(args) -> int:
    geometry_payload = None
    if args.path and args.path != "-":
        geometry_payload = json.loads(open(args.path, encoding="utf-8").read())
    elif args.path == "-":
        geometry_payload = json.loads(sys.stdin.read())
    if isinstance(geometry_payload, dict) and geometry_payload.get("type") == "Feature":
        geometry_payload = geometry_payload.get("geometry")

    selection = field.select_field(
        geometry_payload=geometry_payload,
        lat=args.lat,
        lon=args.lon,
        requested_region=args.region,
        locale=args.locale,
    )
    _print(selection.to_dict(), pretty=not args.compact)
    return 0 if selection.status == Status.OK else 2


def _health(_args) -> int:
    store = data.store()
    _print({
        "service": "terralens-region-explorer",
        "dataVersion": store.data_version,
        "counts": store.index.get("counts", {}),
        "regions": list(catalog.REGION_PACKS),
        "layers": len(catalog.RASTER_LAYERS) + len(catalog.BOUNDARY_LAYERS) + 1,
        "sources": len(catalog.SOURCES),
        "warnings": store.build_report.get("warnings", []),
    })
    return 0


def _regions(_args) -> int:
    _print({"regions": router.region_packs()})
    return 0


def _layers(args) -> int:
    layers = catalog.all_layers(args.country)
    _print({
        "layers": [layer.to_dict() for layer in layers],
        "gibsBaseUrl": catalog.GIBS_URL,
    }, pretty=not args.compact)
    return 0


def _sources(_args) -> int:
    _print({
        "schemaVersion": catalog.SCHEMA_VERSION,
        "sources": [source.to_dict() for source in catalog.SOURCES.values()],
    })
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="terralens",
        description="TerraLens Region Explorer: geography, map layers and region intelligence routing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    serve_cmd = sub.add_parser("serve", help="run the map UI and JSON API")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8765)
    serve_cmd.add_argument("--quiet", action="store_true")
    serve_cmd.set_defaults(func=lambda a: (server.serve(a.host, a.port, a.quiet), 0)[1])

    profile_cmd = sub.add_parser("profile", help="get a region profile for a coordinate")
    profile_cmd.add_argument("--lat", type=float, required=True)
    profile_cmd.add_argument("--lon", type=float, required=True)
    profile_cmd.add_argument("--region", default=None, help="expected region id (adds a warning if it does not match)")
    profile_cmd.add_argument("--locale", default="en", choices=["en", "bn"])
    profile_cmd.add_argument("--compact", action="store_true")
    profile_cmd.set_defaults(func=_profile)

    search_cmd = sub.add_parser("search", help="search bundled administrative units (English or Bangla)")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--country", default=None, choices=["BD", "US"])
    search_cmd.add_argument("--limit", type=int, default=12)
    search_cmd.add_argument("--compact", action="store_true")
    search_cmd.set_defaults(func=_search)

    field_cmd = sub.add_parser("field", help="validate a field polygon or select a point")
    field_cmd.add_argument("path", nargs="?", help="GeoJSON file path, or - for stdin")
    field_cmd.add_argument("--lat", type=float, default=None)
    field_cmd.add_argument("--lon", type=float, default=None)
    field_cmd.add_argument("--region", default=None)
    field_cmd.add_argument("--locale", default="en", choices=["en", "bn"])
    field_cmd.add_argument("--compact", action="store_true")
    field_cmd.set_defaults(func=_field)

    health_cmd = sub.add_parser("health", help="show data version and bundled counts")
    health_cmd.set_defaults(func=_health)

    regions_cmd = sub.add_parser("regions", help="list region packs and their extents")
    regions_cmd.set_defaults(func=_regions)

    layers_cmd = sub.add_parser("layers", help="list map layers, units and native resolutions")
    layers_cmd.add_argument("--country", default=None, choices=["BD", "US"])
    layers_cmd.add_argument("--compact", action="store_true")
    layers_cmd.set_defaults(func=_layers)

    sources_cmd = sub.add_parser("sources", help="print the source and licence register")
    sources_cmd.set_defaults(func=_sources)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())

"""CLI: python -m aquasense evaluate request.json | state | alerts | replay | do-i-need-water | serve [port]"""
from __future__ import annotations

import json
import sys

from . import contract

CMDS = {"evaluate": contract.evaluateWaterBalance, "state": contract.getFarmState, "alerts": contract.getFarmAlerts,
        "replay": contract.replayFarmTimeline, "do-i-need-water": contract.answerDoINeedWater,
        "crop-et": contract.estimateCropET, "apply-event": contract.applyFarmEvent}


def serve(port: int):
    from http.server import BaseHTTPRequestHandler, HTTPServer

    routes = {"/" + k: v for k, v in CMDS.items()}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            fn = routes.get(self.path)
            if not fn:
                self.send_response(404); self.end_headers(); return
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            out = json.dumps(fn(body), ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8"); self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass
    print(f"AquaSense on http://127.0.0.1:{port}  POST {sorted(routes)}")
    HTTPServer(("127.0.0.1", port), H).serve_forever()


def main(argv=None):
    a = argv or sys.argv[1:]
    if not a or a[0] not in list(CMDS) + ["serve"]:
        print(__doc__); return 2
    if a[0] == "serve":
        serve(int(a[1]) if len(a) > 1 else 8606); return 0
    req = json.load(open(a[1])) if len(a) > 1 and a[1] != "-" else json.load(sys.stdin)
    print(json.dumps(CMDS[a[0]](req), indent=2, ensure_ascii=False))
    return 0

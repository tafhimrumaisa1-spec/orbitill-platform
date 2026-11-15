# Deployment preparation

No external deployment has been performed. Publication requires the participant’s approval.

## Local judge demo

Prerequisites: Python 3.11+ and Node 20+ for the integration tests. The runtime itself uses Python’s standard library plus the delivered EarthSync and AquaSense packages.

Windows PowerShell:

```powershell
cd orbitill-platform
.\run_local.ps1
```

Linux/WSL:

```sh
cd /path/to/ORBITILL/orbitill-platform
sh ./run_local.sh
```

Open `http://127.0.0.1:8400/`. The working research route is `/planner.html`; `/api/health` is the health check.

## GitHub + Vercel preparation

The `orbitill-platform` directory is the intended public repository root. It is self-contained; audited EarthSync, AquaSense and TerraLens runtime code is vendored under `modules/`.

`vercel.json` uses `apps/web` as the static output and routes API requests to the Python `BaseHTTPRequestHandler` entry point at `api/index.py`. This follows Vercel's current Python runtime and rewrite contracts. Runtime data required by the functions is explicitly included.

In Vercel:

1. Import the GitHub repository with its root directory left at the repository root.
2. Use the **Other** framework preset; do not override the output directory because it is committed in `vercel.json`.
3. Do not add NASA credentials: the judged computation uses verified offline POWER bundles.
4. Deploy a preview first, then verify `/`, `/terralens/`, `/planner.html`, `/api/health`, `/api/terralens/health` and the scenario POST.
5. Promote to production only after the participant approves the preview URL.

Vercel's Python runtime is currently documented as beta. Keep the local server command below as the reliable judge-demo fallback.

The server defaults to `127.0.0.1:8400` and respects injected `HOST` and `PORT` environment variables for hosting.

## Release gates

- Public URL opens World, Bangladesh, USA and RootShift routes.
- Scenario POST returns a new model-run ID after an input change.
- All images, scripts and styles return HTTP 200.
- No secret or personal farm coordinate is present.
- Source repository visibility and final publication are approved by the participant.

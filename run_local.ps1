$ErrorActionPreference = 'Stop'
$platformRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = @(
  (Join-Path $platformRoot 'modules\earthsync_runtime'),
  (Join-Path $platformRoot 'modules\aquasense_runtime'),
  (Join-Path $platformRoot 'modules\terralens_runtime'),
  $platformRoot
) -join [IO.Path]::PathSeparator

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python 3.11 or newer is required.' }
Set-Location $platformRoot
Write-Host 'ORBITILL: http://127.0.0.1:8400/'
Write-Host 'RootShift demo: http://127.0.0.1:8400/planner.html'
Write-Host 'TerraLens: http://127.0.0.1:8400/terralens/'
& $python.Source -B -m services.science_api.server

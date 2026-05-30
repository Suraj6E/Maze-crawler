# Run a Maze Crawler (`crawl`) match and write a self-contained HTML replay.
#
# Usage:
#   ./run.ps1                                         # crawl-agent vs random
#   ./run.ps1 -P1 agents/crawl-agent -P2 agents/crawl-agent -Seed 7
#   ./run.ps1 -Open                                   # also open the replay in your browser
#
# The replay is a standalone HTML file — just open it; no server needed.

param(
    [string]$P1 = "agents/crawl-agent/main.py",
    [string]$P2 = "random",
    [string]$Output = "data/crawl_replay.html",
    [int]$Seed = 42,
    [switch]$Open
)

$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot ".venv/Scripts/python.exe"

# Allow passing an agent folder; default to its main.py
if (Test-Path (Join-Path $PSScriptRoot $P1) -PathType Container) { $P1 = "$P1/main.py" }
if ((Test-Path (Join-Path $PSScriptRoot $P2) -PathType Container)) { $P2 = "$P2/main.py" }

& $py (Join-Path $PSScriptRoot "scripts/run_crawl.py") $P1 $P2 --seed $Seed --out $Output

if ($Open) { Start-Process (Join-Path $PSScriptRoot $Output) }

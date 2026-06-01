"""Run a Maze Crawler match and open the replay.

This is the project's entry point — it plays one game between two agents on the
Kaggle `crawl` environment, writes a self-contained HTML replay, prints the
result, and (by default) opens the replay in your browser.

Agents are referenced by NAME (a folder under agents/ containing main.py), or by
an explicit path, or the built-in "random".

Examples
--------
    python main.py                       # default matchup (greedy vs random)
    python main.py greedy baseline        # greedy (P1) vs baseline (P2)
    python main.py --p1 baseline --p2 greedy
    python main.py greedy random --seed 7 # different map
    python main.py --list                 # list available agents

Add your own strategy by creating  agents/<name>/main.py  with an
`agent(obs, config)` function — then run  python main.py <name> random.
Game rules / diagrams are in  GAME_GUIDE.md.
"""

import argparse
import logging
import os
import sys
import webbrowser
from pathlib import Path

from viewer import write_viewer

# Importing kaggle_environments dumps a wall of OpenSpiel / litellm noise: Python
# INFO logs PLUS a C extension that writes straight to the OS stderr fd (so a
# normal Python redirect can't catch it). Silence logging and redirect fd 1/2
# only for the duration of the import.
logging.disable(logging.WARNING)
_devnull = os.open(os.devnull, os.O_WRONLY)
_saved = (os.dup(1), os.dup(2))
os.dup2(_devnull, 1)
os.dup2(_devnull, 2)
try:
    from kaggle_environments import make
finally:
    os.dup2(_saved[0], 1)
    os.dup2(_saved[1], 2)
    os.close(_saved[0])
    os.close(_saved[1])
    os.close(_devnull)

AGENTS_DIR = Path("agents")
DEFAULT_P1 = "greedy"
DEFAULT_P2 = "random"


def available_agents():
    """Names of agents/<name>/ folders that contain a main.py."""
    if not AGENTS_DIR.is_dir():
        return []
    return sorted(p.name for p in AGENTS_DIR.iterdir() if (p / "main.py").is_file())


def resolve_agent(name):
    """Turn an agent name / path / "random" into something env.run accepts."""
    if name == "random":
        return "random"
    p = Path(name)
    if p.is_file():                       # explicit path to a .py
        return str(p)
    candidate = AGENTS_DIR / name / "main.py"
    if candidate.is_file():               # a name under agents/
        return str(candidate)
    agents = ", ".join(available_agents()) or "(none found)"
    sys.exit(f"Unknown agent '{name}'. Available: {agents}, random (or pass a path to a .py file).")


def main():
    ap = argparse.ArgumentParser(
        description="Run a Maze Crawler (crawl) match.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Agents are names under agents/ (e.g. greedy, baseline), a path to a .py, or 'random'.",
    )
    ap.add_argument("p1", nargs="?", default=DEFAULT_P1, help=f"player 1 agent (default: {DEFAULT_P1})")
    ap.add_argument("p2", nargs="?", default=DEFAULT_P2, help=f"player 2 agent (default: {DEFAULT_P2})")
    ap.add_argument("--p1", dest="p1_opt", help="player 1 agent (overrides positional)")
    ap.add_argument("--p2", dest="p2_opt", help="player 2 agent (overrides positional)")
    ap.add_argument("--seed", type=int, default=42, help="map/random seed (default: 42)")
    ap.add_argument("--out", default="data/crawl_replay.html", help="replay output path")
    ap.add_argument("--no-open", action="store_true", help="do not open the replay in a browser")
    ap.add_argument("--list", action="store_true", help="list available agents and exit")
    args = ap.parse_args()

    if args.list:
        print("Available agents (agents/<name>/main.py):")
        for name in available_agents():
            print(f"  {name}")
        print("  random   (built-in)")
        return

    p1_name = args.p1_opt or args.p1
    p2_name = args.p2_opt or args.p2
    p1, p2 = resolve_agent(p1_name), resolve_agent(p2_name)

    env = make("crawl", configuration={"randomSeed": args.seed}, debug=True)
    print(f"Running: {p1_name}  vs  {p2_name}   (seed {args.seed})")
    env.run([p1, p2])

    s0, s1 = env.steps[-1][0], env.steps[-1][1]
    print(f"Result -> {p1_name} (P1): reward={s0['reward']} ({s0['status']}) | "
          f"{p2_name} (P2): reward={s1['reward']} ({s1['status']})")
    if s0["reward"] == s1["reward"]:
        print("Outcome: draw / tie")
    else:
        winner = p1_name if s0["reward"] > s1["reward"] else p2_name
        print(f"Outcome: {winner} wins")

    out = write_viewer(env, args.out)
    print(f"\nReplay written to {out}")
    print("Viewer controls: light/dark theme | View All/P1/P2 (per-player fog) | playback")

    if args.no_open:
        print("Open it in any browser to watch (or drop --no-open next time).")
    else:
        webbrowser.open(out.resolve().as_uri())
        print("Opening the replay in your browser...")


if __name__ == "__main__":
    main()

"""Run a Maze Crawler match and open the replay.

This is the project's entry point — it plays one game between two agents on the
Kaggle `crawl` environment, writes a self-contained HTML replay, prints the
result, and (by default) opens the replay in your browser.

Examples
--------
    python main.py                          # your agent vs the built-in "random"
    python main.py --seed 7                  # a different map
    python main.py --p2 agents/crawl-agent/main.py   # your agent vs a copy of itself
    python main.py random random --no-open   # two random agents, don't open browser

You edit your strategy in  agents/crawl-agent/main.py  (the `agent` function).
Game rules / diagrams are in  GAME_GUIDE.md.
"""

import argparse
import logging
import os
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

DEFAULT_AGENT = "agents/crawl-agent/main.py"


def main():
    ap = argparse.ArgumentParser(description="Run a Maze Crawler (crawl) match.")
    ap.add_argument("p1", nargs="?", default=DEFAULT_AGENT,
                    help='player 1: path to an agent .py, or "random" (default: your agent)')
    ap.add_argument("p2", nargs="?", default="random",
                    help='player 2: path to an agent .py, or "random" (default: random)')
    ap.add_argument("--seed", type=int, default=42, help="map/random seed (default: 42)")
    ap.add_argument("--out", default="data/crawl_replay.html", help="replay output path")
    ap.add_argument("--no-open", action="store_true", help="do not open the replay in a browser")
    args = ap.parse_args()

    env = make("crawl", configuration={"randomSeed": args.seed}, debug=True)
    print(f"Running: {args.p1}  vs  {args.p2}   (seed {args.seed})")
    env.run([args.p1, args.p2])

    p0, p1 = env.steps[-1][0], env.steps[-1][1]
    print(f"Result -> player_0: reward={p0['reward']} ({p0['status']}) | "
          f"player_1: reward={p1['reward']} ({p1['status']})")
    if p0["reward"] == p1["reward"]:
        print("Outcome: draw / tie")
    else:
        print(f"Outcome: player_{0 if p0['reward'] > p1['reward'] else 1} wins")

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

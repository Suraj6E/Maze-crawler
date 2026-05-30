"""Run a Maze Crawler (`crawl`) match and write a self-contained HTML replay.

Usage:
    python scripts/run_crawl.py [P1] [P2] [--seed N] [--out FILE]

P1/P2 may be a path to an agent .py file or a built-in name ("random").
Defaults: agents/crawl-agent/main.py vs random, seed 42, data/crawl_replay.html
"""
import argparse
import logging
import os
import sys

# kaggle_environments emits a wall of import-time noise: Python INFO logs PLUS an
# OpenSpiel C-extension that writes directly to the OS stderr fd (so a Python-level
# redirect won't catch it). Silence logging and redirect fd 1/2 during the import.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("p1", nargs="?", default="agents/crawl-agent/main.py")
    ap.add_argument("p2", nargs="?", default="random")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/crawl_replay.html")
    args = ap.parse_args()

    env = make("crawl", configuration={"randomSeed": args.seed}, debug=True)
    print(f"Running: {args.p1}  vs  {args.p2}   (seed {args.seed})")
    env.run([args.p1, args.p2])

    final = env.steps[-1]
    r0, r1 = final[0]["reward"], final[1]["reward"]
    s0, s1 = final[0]["status"], final[1]["status"]
    print(f"Result -> player_0: reward={r0} ({s0}) | player_1: reward={r1} ({s1})")
    if r0 == r1:
        print("Outcome: draw / tie")
    else:
        print(f"Outcome: player_{0 if r0 > r1 else 1} wins")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(env.render(mode="html"))
    print(f"\nReplay written to {args.out}")
    print("Open it directly in your browser (double-click the file) to watch.")


if __name__ == "__main__":
    main()
